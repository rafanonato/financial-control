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
        'rows': [
            {'name': 'Receitas', 'type': 'income', 'values': [0] * len(months), 'details': {}},
            {'name': 'Reserva Emergência', 'type': 'reserve', 'values': [0] * len(months), 'details': {}},
            {'name': 'Investimentos', 'type': 'investment', 'values': [0] * len(months), 'details': {}},
            {'name': 'Saving 2023', 'type': 'saving', 'values': [0] * len(months)},
            {'name': 'Despesas', 'type': 'expense', 'values': [0] * len(months), 'details': {}}
        ]
    }

    # Processar transações
    for transaction in transactions:
        month_idx = months.index(transaction.date.strftime('%Y-%m'))
        category_type = transaction.category.type
        category_name = transaction.category.name

        # Atualizar detalhes por categoria
        if category_type == 'income':
            if category_name not in data['rows'][0]['details']:
                data['rows'][0]['details'][category_name] = [0] * len(months)
            data['rows'][0]['details'][category_name][month_idx] += transaction.amount
            data['rows'][0]['values'][month_idx] += transaction.amount
        elif category_type == 'expense':
            if category_name not in data['rows'][4]['details']:
                data['rows'][4]['details'][category_name] = [0] * len(months)
            data['rows'][4]['details'][category_name][month_idx] += transaction.amount
            data['rows'][4]['values'][month_idx] += transaction.amount
        elif category_type == 'investment':
            if 'Reserva' in category_name:
                if category_name not in data['rows'][1]['details']:
                    data['rows'][1]['details'][category_name] = [0] * len(months)
                data['rows'][1]['details'][category_name][month_idx] += transaction.amount
                data['rows'][1]['values'][month_idx] += transaction.amount
            else:
                if category_name not in data['rows'][2]['details']:
                    data['rows'][2]['details'][category_name] = [0] * len(months)
                data['rows'][2]['details'][category_name][month_idx] += transaction.amount
                data['rows'][2]['values'][month_idx] += transaction.amount

    # Calcular entradas (Receitas + Investimentos + Reserva Emergência)
    entradas = {
        'name': 'Entradas', 
        'type': 'total', 
        'values': []
    }
    for i in range(len(months)):
        total_entradas = (
            data['rows'][0]['values'][i] +  # Receitas
            data['rows'][1]['values'][i] +  # Reserva Emergência
            data['rows'][2]['values'][i] +  # Investimentos
            data['rows'][3]['values'][i]    # Saving ano anterior
        )
        entradas['values'].append(total_entradas)
    
    # Calcular saídas (apenas despesas)
    saidas = {
        'name': 'Saídas', 
        'type': 'total', 
        'values': [abs(value) for value in data['rows'][4]['values']]
    }

    # Adicionar linhas de totais
    data['rows'].extend([entradas, saidas])

    # Calcular projeção mensal (Saving + Invest)
    projecao = {'name': 'Projeção Mensal (Saving+Invest)', 'type': 'projection', 'values': []}
    acumulado = 0
    for i in range(len(months)):
        entrada = entradas['values'][i]
        saida = saidas['values'][i]
        saldo = entrada - saida
        acumulado += saldo
        projecao['values'].append(acumulado)
    data['rows'].append(projecao)

    # Calcular percentual do gasto mensal (Despesas / Entradas)
    percentual = {'name': '% do gasto mensal', 'type': 'percentage', 'values': []}
    for i in range(len(months)):
        entrada = entradas['values'][i]
        if entrada > 0:
            total_despesas = abs(saidas['values'][i])
            percentual['values'].append((total_despesas / entrada) * 100)
        else:
            percentual['values'].append(0)
    data['rows'].append(percentual)

    return jsonify(data)

@bp.route('/api/financial-flow/export')
def export_financial_flow():
    format_type = request.args.get('format', 'excel')
    
    # Obter os dados do fluxo financeiro
    data = get_financial_flow().get_json()
    
    # Criar DataFrame
    df_data = []
    for row in data['rows']:
        row_data = [row['name']] + row['values']
        df_data.append(row_data)
    
    columns = ['Categoria'] + data['months']
    df = pd.DataFrame(df_data, columns=columns)
    
    # Exportar no formato solicitado
    if format_type == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Fluxo Financeiro', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Fluxo Financeiro']
            
            # Formatar células
            money_format = workbook.add_format({
                'num_format': 'R$ #,##0.00',
                'align': 'right'
            })
            percent_format = workbook.add_format({
                'num_format': '0.0%',
                'align': 'right'
            })
            header_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#f8f9fa'
            })
            
            # Aplicar formatação
            worksheet.set_row(0, None, header_format)
            for idx, row in enumerate(data['rows']):
                if row['type'] == 'percentage':
                    worksheet.set_row(idx + 1, None, percent_format)
                else:
                    worksheet.set_row(idx + 1, None, money_format)
                
                # Destacar linhas importantes
                if row['type'] in ['total', 'projection']:
                    for col in range(len(columns)):
                        cell_format = workbook.add_format({
                            'num_format': money_format['num_format'],
                            'align': 'right',
                            'bold': True,
                            'bg_color': '#cfe2ff'
                        })
                        worksheet.write(idx + 1, col, df.iloc[idx, col], cell_format)
            
            # Ajustar largura das colunas
            worksheet.set_column(0, 0, 25)  # Coluna de categorias
            worksheet.set_column(1, len(columns) - 1, 15)  # Colunas de valores
        
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