from flask import Blueprint, jsonify, request, render_template
from sqlalchemy import extract, func
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from app.models.models import Transaction, Category, Goal
from app import db

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard/monthly')
def monthly_dashboard():
    return render_template('dashboard/monthly.html')

@bp.route('/dashboard/yearly')
def yearly_dashboard():
    return render_template('dashboard/yearly.html')

@bp.route('/api/dashboard/data')
def get_dashboard_data():
    # Obter parâmetros de data
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    period = request.args.get('period', 'monthly')  # monthly ou yearly

    if start_date:
        start_date = datetime.strptime(start_date + '-01', '%Y-%m-%d').date()
    else:
        if period == 'yearly':
            start_date = date(date.today().year, 1, 1)
        else:
            start_date = date.today().replace(day=1)

    if end_date:
        end_date = datetime.strptime(end_date + '-01', '%Y-%m-%d').date()
        end_date = (end_date + relativedelta(months=1)) - relativedelta(days=1)
    else:
        if period == 'yearly':
            end_date = date(date.today().year, 12, 31)
        else:
            end_date = (date.today().replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)

    # Buscar transações e metas no período
    transactions = Transaction.query.join(Category).filter(
        Transaction.date.between(start_date, end_date)
    ).all()

    goals = Goal.query.filter(
        Goal.start_date <= end_date,
        (Goal.end_date.is_(None) | (Goal.end_date >= start_date))
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
        'receita_vs_despesa': {
            'receitas': [0] * len(months),
            'despesas': [0] * len(months)
        },
        'fechamento_mensal': [0] * len(months),
        'despesas_categoria': {},
        'investimentos': {
            'reserva_emergencia': [0] * len(months),
            'saving_anterior': [0] * len(months),
            'investimentos': [0] * len(months)
        },
        'metas_realizado': {},
        'saving_rate': [0] * len(months),
        'cash_flow': {
            'receitas': 0,
            'despesas_fixas': 0,
            'despesas_variaveis': 0,
            'investimentos': 0
        },
        'projecao_mensal': [0] * len(months)
    }

    # Processar transações
    for transaction in transactions:
        month_idx = months.index(transaction.date.strftime('%Y-%m'))
        category_type = transaction.category.type
        category_name = transaction.category.name

        # Receita vs Despesa
        if category_type == 'income':
            data['receita_vs_despesa']['receitas'][month_idx] += transaction.amount
        elif category_type == 'expense':
            data['receita_vs_despesa']['despesas'][month_idx] += abs(transaction.amount)

            # Despesas por categoria
            if category_name not in data['despesas_categoria']:
                data['despesas_categoria'][category_name] = [0] * len(months)
            data['despesas_categoria'][category_name][month_idx] += abs(transaction.amount)

            # Cash Flow
            if 'Fixa' in category_name:
                data['cash_flow']['despesas_fixas'] += abs(transaction.amount)
            else:
                data['cash_flow']['despesas_variaveis'] += abs(transaction.amount)

        elif category_type == 'investment':
            if 'Reserva' in category_name:
                data['investimentos']['reserva_emergencia'][month_idx] += transaction.amount
            else:
                data['investimentos']['investimentos'][month_idx] += transaction.amount
            data['cash_flow']['investimentos'] += transaction.amount

    # Calcular fechamento mensal e saving rate
    for i in range(len(months)):
        receita = data['receita_vs_despesa']['receitas'][i]
        despesa = data['receita_vs_despesa']['despesas'][i]
        investimento = (
            data['investimentos']['reserva_emergencia'][i] +
            data['investimentos']['investimentos'][i]
        )
        
        data['fechamento_mensal'][i] = receita - despesa + investimento
        
        if receita > 0:
            data['saving_rate'][i] = (investimento / receita) * 100
        else:
            data['saving_rate'][i] = 0

    # Processar metas
    for goal in goals:
        category_name = goal.category.name if goal.category else 'Sem categoria'
        if category_name not in data['metas_realizado']:
            data['metas_realizado'][category_name] = {
                'meta': goal.target_amount,
                'realizado': 0
            }
        
        # Buscar transações relacionadas à meta
        if goal.category:
            transactions_meta = Transaction.query.filter(
                Transaction.category_id == goal.category_id,
                Transaction.date.between(start_date, end_date)
            ).all()
            
            data['metas_realizado'][category_name]['realizado'] = sum(
                t.amount for t in transactions_meta
            )

    # Calcular projeção mensal
    acumulado = 0
    for i in range(len(months)):
        saldo = data['fechamento_mensal'][i]
        acumulado += saldo
        data['projecao_mensal'][i] = acumulado

    return jsonify(data)

@bp.route('/api/dashboard/export/<format>')
def export_dashboard(format):
    # TODO: Implementar exportação de gráficos/relatórios
    pass 

class DashboardController:
    def get_dashboard_data(self, period='monthly', start_date=None, end_date=None):
        """Obtém os dados para o dashboard."""
        # Processar datas
        if start_date:
            start_date = datetime.strptime(start_date + '-01', '%Y-%m-%d').date()
        else:
            if period == 'yearly':
                start_date = date(date.today().year, 1, 1)
            else:
                start_date = date.today().replace(day=1)

        if end_date:
            end_date = datetime.strptime(end_date + '-01', '%Y-%m-%d').date()
            end_date = (end_date + relativedelta(months=1)) - relativedelta(days=1)
        else:
            if period == 'yearly':
                end_date = date(date.today().year, 12, 31)
            else:
                end_date = (date.today().replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)

        # Buscar transações e metas
        transactions = Transaction.query.join(Category).filter(
            Transaction.date.between(start_date, end_date)
        ).all()

        goals = Goal.query.filter(
            Goal.start_date <= end_date,
            (Goal.end_date.is_(None) | (Goal.end_date >= start_date))
        ).all()

        # Preparar estrutura de dados
        months = []
        current = start_date
        while current <= end_date:
            months.append(current.strftime('%Y-%m'))
            current += relativedelta(months=1)

        data = {
            'months': months,
            'receita_vs_despesa': {
                'receitas': [0] * len(months),
                'despesas': [0] * len(months)
            },
            'fechamento_mensal': [0] * len(months),
            'despesas_categoria': {},
            'investimentos': {
                'reserva_emergencia': [0] * len(months),
                'saving_anterior': [0] * len(months),
                'investimentos': [0] * len(months)
            },
            'metas_realizado': {},
            'saving_rate': [0] * len(months),
            'cash_flow': {
                'receitas': 0,
                'despesas_fixas': 0,
                'despesas_variaveis': 0,
                'investimentos': 0
            },
            'projecao_mensal': [0] * len(months)
        }

        # Processar transações
        for transaction in transactions:
            month_idx = months.index(transaction.date.strftime('%Y-%m'))
            category_type = transaction.category.type
            category_name = transaction.category.name

            # Receita vs Despesa
            if category_type == 'income':
                data['receita_vs_despesa']['receitas'][month_idx] += transaction.amount
            elif category_type == 'expense':
                data['receita_vs_despesa']['despesas'][month_idx] += abs(transaction.amount)

                # Despesas por categoria
                if category_name not in data['despesas_categoria']:
                    data['despesas_categoria'][category_name] = [0] * len(months)
                data['despesas_categoria'][category_name][month_idx] += abs(transaction.amount)

                # Cash Flow
                if 'Fixa' in category_name:
                    data['cash_flow']['despesas_fixas'] += abs(transaction.amount)
                else:
                    data['cash_flow']['despesas_variaveis'] += abs(transaction.amount)

            elif category_type == 'investment':
                if 'Reserva' in category_name:
                    data['investimentos']['reserva_emergencia'][month_idx] += transaction.amount
                else:
                    data['investimentos']['investimentos'][month_idx] += transaction.amount
                data['cash_flow']['investimentos'] += transaction.amount

        # Calcular fechamento mensal e saving rate
        for i in range(len(months)):
            receita = data['receita_vs_despesa']['receitas'][i]
            despesa = data['receita_vs_despesa']['despesas'][i]
            investimento = (
                data['investimentos']['reserva_emergencia'][i] +
                data['investimentos']['investimentos'][i]
            )
            
            data['fechamento_mensal'][i] = receita - despesa + investimento
            
            if receita > 0:
                data['saving_rate'][i] = (investimento / receita) * 100
            else:
                data['saving_rate'][i] = 0

        # Processar metas
        for goal in goals:
            category_name = goal.category.name if goal.category else 'Sem categoria'
            if category_name not in data['metas_realizado']:
                data['metas_realizado'][category_name] = {
                    'meta': goal.target_amount,
                    'realizado': 0
                }
            
            # Buscar transações relacionadas à meta
            if goal.category:
                transactions_meta = Transaction.query.filter(
                    Transaction.category_id == goal.category_id,
                    Transaction.date.between(start_date, end_date)
                ).all()
                
                data['metas_realizado'][category_name]['realizado'] = sum(
                    t.amount for t in transactions_meta
                )

        # Calcular projeção mensal
        acumulado = 0
        for i in range(len(months)):
            saldo = data['fechamento_mensal'][i]
            acumulado += saldo
            data['projecao_mensal'][i] = acumulado

        return data 