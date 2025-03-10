from flask import Blueprint, jsonify, request, render_template, send_file
from sqlalchemy import extract, func
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from app.models.models import Transaction, Category
from app import db
import pandas as pd
import io

bp = Blueprint('financial_flow', __name__)

@bp.route('/financial-flow')
def show_financial_flow():
    return render_template('financial_flow.html')

@bp.route('/api/financial-flow')
def get_financial_flow():
    # Obter parâmetros de data
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)

    if start_date:
        start_date = datetime.strptime(start_date + '-01', '%Y-%m-%d').date()
    else:
        # Se não especificado, usar o ano atual
        start_date = date(date.today().year, 1, 1)

    if end_date:
        end_date = datetime.strptime(end_date + '-01', '%Y-%m-%d').date()
        # Ir até o final do mês
        end_date = (end_date + relativedelta(months=1)) - relativedelta(days=1)
    else:
        end_date = date(date.today().year, 12, 31)

    # Buscar transações no período
    transactions = Transaction.query.join(Category).filter(
        Transaction.date.between(start_date, end_date)
    ).all()

    # Organizar dados por mês
    months = []
    current = start_date
    while current <= end_date:
        months.append(current.strftime('%Y-%m'))
        current += relativedelta(months=1)

    # Inicializar estrutura de dados
    data = {
        'months': months,
        'rows': []
    }

    # Seção de Receitas
    receitas = {'name': 'Receitas', 'type': 'section_header', 'values': [0] * len(months)}
    receitas_details = {}

    # Seção de Investimentos e Reservas
    reserva = {'name': 'Reserva Emergência', 'type': 'investment', 'values': [0] * len(months)}
    investimentos = {'name': 'Investimentos', 'type': 'investment', 'values': [0] * len(months)}
    saving_2024 = {'name': 'Saving 2024', 'type': 'saving', 'values': [0] * len(months)}

    # Seção de Despesas
    despesas = {'name': 'Despesas', 'type': 'section_header', 'values': [0] * len(months)}
    despesas_details = {}

    # Processar transações
    for transaction in transactions:
        month_idx = months.index(transaction.date.strftime('%Y-%m'))
        category_type = transaction.category.type
        category_name = transaction.category.name
        amount = transaction.amount

        if category_type == 'income':
            if category_name not in receitas_details:
                receitas_details[category_name] = {'name': category_name, 'type': 'income_item', 'values': [0] * len(months)}
            receitas_details[category_name]['values'][month_idx] += amount
            receitas['values'][month_idx] += amount
        
        elif category_type == 'expense':
            if category_name not in despesas_details:
                despesas_details[category_name] = {'name': category_name, 'type': 'expense_item', 'values': [0] * len(months)}
            despesas_details[category_name]['values'][month_idx] += amount
            despesas['values'][month_idx] += amount
        
        elif category_type == 'investment':
            if 'Reserva' in category_name:
                reserva['values'][month_idx] += amount
            elif 'Saving 2024' in category_name:
                saving_2024['values'][month_idx] += amount
            else:
                investimentos['values'][month_idx] += amount

    # Organizar linhas da tabela
    data['rows'].append(receitas)
    for item in sorted(receitas_details.values(), key=lambda x: x['name']):
        data['rows'].append(item)
    
    data['rows'].append({'name': 'SUBTOTAL RECEITAS', 'type': 'subtotal', 'values': receitas['values'].copy()})
    data['rows'].append({'name': '', 'type': 'spacer', 'values': [0] * len(months)})
    
    data['rows'].append(reserva)
    data['rows'].append(investimentos)
    data['rows'].append(saving_2024)
    data['rows'].append({'name': 'SUBTOTAL INVESTIMENTOS', 'type': 'subtotal', 
                        'values': [sum(x) for x in zip(reserva['values'], investimentos['values'], saving_2024['values'])]})
    data['rows'].append({'name': '', 'type': 'spacer', 'values': [0] * len(months)})
    
    data['rows'].append(despesas)
    for item in sorted(despesas_details.values(), key=lambda x: x['name']):
        data['rows'].append(item)
    data['rows'].append({'name': 'SUBTOTAL DESPESAS', 'type': 'subtotal', 'values': despesas['values'].copy()})
    data['rows'].append({'name': '', 'type': 'spacer', 'values': [0] * len(months)})

    # Calcular totais
    entradas = {'name': 'Total Entradas', 'type': 'total', 'values': receitas['values'].copy()}
    saidas = {'name': 'Total Saídas', 'type': 'total', 'values': []}
    for i in range(len(months)):
        total_saidas = (reserva['values'][i] + investimentos['values'][i] + 
                       saving_2024['values'][i] + despesas['values'][i])
        saidas['values'].append(total_saidas)
    
    # Calcular fechamento mensal
    fechamento = {'name': 'Fechamento Mensal', 'type': 'highlight', 'values': []}
    for i in range(len(months)):
        saldo = entradas['values'][i] - saidas['values'][i]
        fechamento['values'].append(saldo)

    # Calcular projeção acumulada
    projecao = {'name': 'Projeção Mensal (Saving+Invest)', 'type': 'highlight', 'values': []}
    acumulado = 0
    for i in range(len(months)):
        acumulado += fechamento['values'][i]
        projecao['values'].append(acumulado)

    # Calcular percentual de gastos
    percentual = {'name': '% do gasto mensal', 'type': 'percentage', 'values': []}
    for i in range(len(months)):
        if entradas['values'][i] > 0:
            perc = (abs(despesas['values'][i]) / entradas['values'][i]) * 100
            percentual['values'].append(perc)
        else:
            percentual['values'].append(0)

    # Adicionar totais à tabela
    data['rows'].extend([
        entradas,
        saidas,
        fechamento,
        {'name': '', 'type': 'spacer', 'values': [0] * len(months)},
        projecao,
        percentual
    ])

    return jsonify(data)

@bp.route('/api/financial-flow/export')
def export_financial_flow():
    format_type = request.args.get('format', 'excel')
    
    # Obter os dados do fluxo financeiro
    data = get_financial_flow().get_json()
    
    # Criar DataFrame
    df_data = []
    for row in data['rows']:
        if row['type'] != 'spacer':  # Ignorar linhas vazias
            row_data = [row['name']] + row['values']
            df_data.append(row_data)
    
    columns = ['Categoria'] + [datetime.strptime(m, '%Y-%m').strftime('%b/%Y') for m in data['months']]
    df = pd.DataFrame(df_data, columns=columns)
    
    # Exportar no formato solicitado
    if format_type == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Fluxo Financeiro', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Fluxo Financeiro']
            
            # Formatar células
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#f8f9fa',
                'border': 1
            })
            money_format = workbook.add_format({
                'num_format': 'R$ #,##0.00',
                'border': 1
            })
            money_format_negative = workbook.add_format({
                'num_format': 'R$ #,##0.00',
                'font_color': 'red',
                'border': 1
            })
            percent_format = workbook.add_format({
                'num_format': '0.0%',
                'border': 1
            })
            highlight_format = workbook.add_format({
                'bold': True,
                'bg_color': '#cfe2ff',
                'num_format': 'R$ #,##0.00',
                'border': 1
            })
            
            # Aplicar formatação
            for idx, row in enumerate(data['rows']):
                if row['type'] == 'spacer':
                    continue
                excel_row = df_data.index([row['name']] + row['values']) + 1
                if row['type'] == 'percentage':
                    worksheet.set_row(excel_row, None, percent_format)
                elif row['type'] == 'highlight':
                    worksheet.set_row(excel_row, None, highlight_format)
                elif row['type'] == 'section_header':
                    worksheet.set_row(excel_row, None, header_format)
                else:
                    for col in range(1, len(columns)):
                        value = row['values'][col-1]
                        if value < 0:
                            worksheet.write(excel_row, col, value, money_format_negative)
                        else:
                            worksheet.write(excel_row, col, value, money_format)
            
            # Ajustar largura das colunas
            worksheet.set_column(0, 0, 30)  # Coluna de categorias
            worksheet.set_column(1, len(columns)-1, 15)  # Colunas de valores
        
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='fluxo_financeiro.xlsx'
        )
    
    elif format_type == 'pdf':
        # TODO: Implementar exportação para PDF
        pass
    
    return jsonify({'error': 'Formato não suportado'}), 400 