from flask import Blueprint, jsonify, request, render_template, send_file
from sqlalchemy import extract, func
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from app.models.models import Transaction, Category
from app import db
import pandas as pd
import io

# Criar o blueprint com url_prefix
bp = Blueprint('financial_flow', __name__, url_prefix='/financial-flow')

@bp.route('/')
def show_financial_flow():
    return render_template('financial_flow.html')

@bp.route('/api')
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

    # Inicializar arrays para cada categoria
    receitas = {'name': 'Receitas', 'type': 'section_header', 'values': [0] * len(months), 'details': {}}
    reserva = {'name': 'Reserva Emergência', 'type': 'investment', 'values': [0] * len(months)}
    investimentos = {'name': 'Investimentos', 'type': 'investment', 'values': [0] * len(months)}
    saving_anterior = {'name': 'Saving Ano Anterior', 'type': 'saving', 'values': [0] * len(months)}
    despesas = {'name': 'Despesas', 'type': 'section_header', 'values': [0] * len(months), 'details': {}}

    # Processar transações
    for transaction in transactions:
        month_idx = months.index(transaction.date.strftime('%Y-%m'))
        category_type = transaction.category.type
        category_name = transaction.category.name
        amount = transaction.amount

        if category_type == 'income':
            if category_name not in receitas['details']:
                receitas['details'][category_name] = {'name': category_name, 'type': 'income_item', 'values': [0] * len(months)}
            receitas['details'][category_name]['values'][month_idx] += amount
            receitas['values'][month_idx] += amount
        
        elif category_type == 'expense':
            if category_name not in despesas['details']:
                despesas['details'][category_name] = {'name': category_name, 'type': 'expense_item', 'values': [0] * len(months)}
            despesas['details'][category_name]['values'][month_idx] += amount
            despesas['values'][month_idx] += amount
        
        elif category_type == 'investment':
            if 'Reserva' in category_name:
                reserva['values'][month_idx] += amount
            elif 'Saving' in category_name and str(date.today().year - 1) in category_name:
                saving_anterior['values'][month_idx] += amount
            else:
                investimentos['values'][month_idx] += amount

    # Organizar linhas da tabela
    # 1. Seção de Receitas
    data['rows'].append(receitas)
    for item in sorted(receitas['details'].values(), key=lambda x: x['name']):
        data['rows'].append(item)
    data['rows'].append({'name': 'SUBTOTAL RECEITAS', 'type': 'subtotal', 'values': receitas['values'].copy()})
    data['rows'].append({'name': '', 'type': 'spacer', 'values': [0] * len(months)})

    # 2. Seção de Investimentos (considerados como receitas para cálculos)
    data['rows'].append(reserva)
    data['rows'].append(investimentos)
    data['rows'].append(saving_anterior)
    subtotal_investimentos = {'name': 'SUBTOTAL INVESTIMENTOS', 'type': 'subtotal', 
                            'values': [sum(x) for x in zip(reserva['values'], 
                                                         investimentos['values'], 
                                                         saving_anterior['values'])]}
    data['rows'].append(subtotal_investimentos)
    data['rows'].append({'name': '', 'type': 'spacer', 'values': [0] * len(months)})

    # 3. Seção de Despesas
    data['rows'].append(despesas)
    for item in sorted(despesas['details'].values(), key=lambda x: x['name']):
        data['rows'].append(item)
    data['rows'].append({'name': 'SUBTOTAL DESPESAS', 'type': 'subtotal', 'values': despesas['values'].copy()})
    data['rows'].append({'name': '', 'type': 'spacer', 'values': [0] * len(months)})

    # 4. Calcular totais
    # Entradas = Receitas + Investimentos + Reserva + Saving
    entradas = {'name': 'Total Entradas', 'type': 'total', 'values': []}
    for i in range(len(months)):
        total_entrada = (receitas['values'][i] + reserva['values'][i] + 
                        investimentos['values'][i] + saving_anterior['values'][i])
        entradas['values'].append(total_entrada)

    # Saídas = Despesas
    saidas = {'name': 'Total Saídas', 'type': 'total', 'values': despesas['values'].copy()}

    # 5. Calcular fechamento mensal (Entradas - Saídas)
    fechamento = {'name': 'Fechamento Mensal', 'type': 'highlight', 'values': []}
    for i in range(len(months)):
        saldo = entradas['values'][i] - abs(saidas['values'][i])
        fechamento['values'].append(saldo)

    # 6. Calcular projeção acumulada
    projecao = {'name': 'Projeção Mensal (Saving+Invest)', 'type': 'highlight', 'values': []}
    acumulado = 0
    for i in range(len(months)):
        acumulado += fechamento['values'][i]
        projecao['values'].append(acumulado)

    # 7. Calcular percentual de gastos
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

@bp.route('/api/export')
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
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            section_format = workbook.add_format({
                'bold': True,
                'bg_color': '#e9ecef',
                'border': 1
            })
            
            money_format = workbook.add_format({
                'num_format': 'R$ #,##0.00',
                'border': 1,
                'align': 'right'
            })
            
            money_format_negative = workbook.add_format({
                'num_format': 'R$ #,##0.00',
                'font_color': 'red',
                'border': 1,
                'align': 'right'
            })
            
            percent_format = workbook.add_format({
                'num_format': '0.0%',
                'border': 1,
                'align': 'right'
            })
            
            highlight_format = workbook.add_format({
                'bold': True,
                'bg_color': '#cfe2ff',
                'num_format': 'R$ #,##0.00',
                'border': 1,
                'align': 'right'
            })
            
            subtotal_format = workbook.add_format({
                'bold': True,
                'bg_color': '#f8f9fa',
                'num_format': 'R$ #,##0.00',
                'border': 1,
                'align': 'right',
                'top': 2
            })
            
            # Aplicar formatação
            for idx, row in enumerate(df_data):
                excel_row = idx + 1
                row_type = next((r['type'] for r in data['rows'] if r['name'] == row[0]), None)
                
                if row_type == 'section_header':
                    worksheet.set_row(excel_row, None, section_format)
                elif row_type == 'subtotal':
                    worksheet.set_row(excel_row, None, subtotal_format)
                elif row_type == 'highlight':
                    worksheet.set_row(excel_row, None, highlight_format)
                elif row_type == 'percentage':
                    worksheet.set_row(excel_row, None, percent_format)
                else:
                    for col in range(1, len(columns)):
                        value = row[col]
                        if isinstance(value, (int, float)):
                            if value < 0:
                                worksheet.write(excel_row, col, value, money_format_negative)
                            else:
                                worksheet.write(excel_row, col, value, money_format)
            
            # Formatar cabeçalho
            for col in range(len(columns)):
                worksheet.write(0, col, columns[col], header_format)
            
            # Ajustar largura das colunas
            worksheet.set_column(0, 0, 30)  # Coluna de categorias
            worksheet.set_column(1, len(columns)-1, 15)  # Colunas de valores
            
            # Congelar painéis
            worksheet.freeze_panes(1, 1)
        
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