from app import app
import plotly
import plotly.express as px
import plotly.graph_objects as go
import json
import pandas as pd
import numpy as np
from datetime import datetime
from calendar import monthrange
from sqlalchemy import extract, func

def generate_monthly_charts(transactions, month, year):
    """
    Gera gráficos para o dashboard mensal
    
    Args:
        transactions: Lista de transações
        month: Mês selecionado
        year: Ano selecionado
        
    Returns:
        Dicionário com os gráficos em formato JSON
    """
    charts = {}
    
    # Converter transações para DataFrame
    data = []
    for t in transactions:
        data.append({
            'data': pd.to_datetime(t.date),  # Convertendo para datetime64
            'descrição': t.description,
            'valor': t.amount,
            'categoria': t.category.name,
            'tipo': t.category.type,
            'cor': t.category.color
        })
    
    if not data:
        # Retornar gráficos vazios se não houver dados
        return {
            'pie_expenses': '{}',
            'pie_income': '{}',
            'bar_daily': '{}',
            'balance': '{}'
        }
    
    df = pd.DataFrame(data)
    
    # Gráfico de pizza para despesas
    expenses = df[df['valor'] < 0].copy()
    if not expenses.empty:
        expenses['valor_abs'] = expenses['valor'].abs()
        fig_expenses = px.pie(
            expenses, 
            values='valor_abs', 
            names='categoria',
            color='categoria',
            color_discrete_map={cat: cor for cat, cor in zip(expenses['categoria'], expenses['cor'])},
            title=f'Despesas - {month}/{year}'
        )
        charts['pie_expenses'] = json.dumps(fig_expenses, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        charts['pie_expenses'] = '{}'
    
    # Gráfico de pizza para receitas
    income = df[df['valor'] > 0]
    if not income.empty:
        fig_income = px.pie(
            income, 
            values='valor', 
            names='categoria',
            color='categoria',
            color_discrete_map={cat: cor for cat, cor in zip(income['categoria'], income['cor'])},
            title=f'Receitas - {month}/{year}'
        )
        charts['pie_income'] = json.dumps(fig_income, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        charts['pie_income'] = '{}'
    
    # Gráfico de barras para evolução diária
    df['dia'] = df['data'].dt.day  # Agora podemos usar .dt pois data é datetime64
    daily_balance = df.groupby('dia')['valor'].sum().reset_index()
    
    # Garantir que todos os dias do mês estejam presentes
    days_in_month = monthrange(int(year), int(month))[1]
    all_days = pd.DataFrame({'dia': range(1, days_in_month + 1)})
    daily_balance = all_days.merge(daily_balance, on='dia', how='left').fillna(0)
    
    # Calcular saldo acumulado
    daily_balance['saldo_acumulado'] = daily_balance['valor'].cumsum()
    
    fig_daily = go.Figure()
    fig_daily.add_trace(go.Bar(
        x=daily_balance['dia'],
        y=daily_balance['valor'],
        name='Valor Diário',
        marker_color='lightblue'
    ))
    fig_daily.add_trace(go.Scatter(
        x=daily_balance['dia'],
        y=daily_balance['saldo_acumulado'],
        name='Saldo Acumulado',
        marker_color='darkblue'
    ))
    fig_daily.update_layout(
        title=f'Evolução Diária - {month}/{year}',
        xaxis_title='Dia',
        yaxis_title='Valor (R$)',
        barmode='group'
    )
    charts['bar_daily'] = json.dumps(fig_daily, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Gráfico de indicadores de saldo
    total_income = df[df['valor'] > 0]['valor'].sum()
    total_expenses = df[df['valor'] < 0]['valor'].sum()
    balance = total_income + total_expenses
    
    fig_balance = go.Figure()
    fig_balance.add_trace(go.Indicator(
        mode="number+delta",
        value=balance,
        number={'prefix': "R$", 'valueformat': '.2f'},
        delta={'position': "top", 'reference': 0, 'valueformat': '.2f'},
        title={'text': "Saldo Mensal"},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    charts['balance'] = json.dumps(fig_balance, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Calcular taxa de poupança (saving rate)
    if total_income > 0:
        saving_rate = (balance / total_income) * 100
    else:
        saving_rate = 0
    
    fig_saving_rate = go.Figure()
    fig_saving_rate.add_trace(go.Indicator(
        mode="gauge+number",
        value=saving_rate,
        number={'suffix': "%", 'valueformat': '.1f'},
        title={'text': "Taxa de Poupança"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkgreen"},
            'steps': [
                {'range': [0, 20], 'color': "lightcoral"},
                {'range': [20, 40], 'color': "lightyellow"},
                {'range': [40, 100], 'color': "lightgreen"}
            ]
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    charts['saving_rate'] = json.dumps(fig_saving_rate, cls=plotly.utils.PlotlyJSONEncoder)
    
    return charts

def generate_yearly_charts(transactions, year):
    """
    Gera gráficos para o dashboard anual
    
    Args:
        transactions: Lista de transações
        year: Ano selecionado
        
    Returns:
        Dicionário com os gráficos em formato JSON
    """
    charts = {}
    
    # Converter transações para DataFrame
    data = []
    for t in transactions:
        data.append({
            'data': pd.to_datetime(t.date),  # Convertendo para datetime64
            'mês': t.date.month,
            'descrição': t.description,
            'valor': t.amount,
            'categoria': t.category.name,
            'tipo': t.category.type
        })
    
    if not data:
        # Retornar gráficos vazios se não houver dados
        return {
            'line_monthly': '{}',
            'bar_categories': '{}',
            'heatmap_categories': '{}'
        }
    
    df = pd.DataFrame(data)
    
    # Gráfico de linha para evolução mensal
    monthly_data = df.groupby('mês').agg({
        'valor': ['sum', lambda x: sum(i for i in x if i > 0), lambda x: sum(i for i in x if i < 0)]
    }).reset_index()
    monthly_data.columns = ['mês', 'saldo', 'receitas', 'despesas']
    monthly_data['despesas'] = monthly_data['despesas'].abs()
    
    # Garantir que todos os meses estejam presentes
    all_months = pd.DataFrame({'mês': range(1, 13)})
    monthly_data = all_months.merge(monthly_data, on='mês', how='left').fillna(0)
    
    # Nomes dos meses
    month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    monthly_data['mês_nome'] = monthly_data['mês'].apply(lambda x: month_names[int(x)-1])
    
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Scatter(
        x=monthly_data['mês_nome'],
        y=monthly_data['receitas'],
        name='Receitas',
        line=dict(color='green', width=2)
    ))
    fig_monthly.add_trace(go.Scatter(
        x=monthly_data['mês_nome'],
        y=monthly_data['despesas'],
        name='Despesas',
        line=dict(color='red', width=2)
    ))
    fig_monthly.add_trace(go.Scatter(
        x=monthly_data['mês_nome'],
        y=monthly_data['saldo'],
        name='Saldo',
        line=dict(color='blue', width=2)
    ))
    fig_monthly.update_layout(
        title=f'Evolução Mensal - {year}',
        xaxis_title='Mês',
        yaxis_title='Valor (R$)',
        legend=dict(x=0.01, y=0.99, orientation='h')
    )
    charts['line_monthly'] = json.dumps(fig_monthly, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Gráfico de barras para categorias
    category_data = df.groupby(['categoria', 'tipo']).agg({
        'valor': 'sum'
    }).reset_index()
    
    # Separar por tipo
    expenses_cat = category_data[category_data['tipo'] == 'expense'].copy()
    expenses_cat['valor'] = expenses_cat['valor'].abs()
    
    income_cat = category_data[category_data['tipo'] == 'income']
    
    fig_categories = go.Figure()
    
    if not expenses_cat.empty:
        fig_categories.add_trace(go.Bar(
            x=expenses_cat['categoria'],
            y=expenses_cat['valor'],
            name='Despesas',
            marker_color='red'
        ))
    
    if not income_cat.empty:
        fig_categories.add_trace(go.Bar(
            x=income_cat['categoria'],
            y=income_cat['valor'],
            name='Receitas',
            marker_color='green'
        ))
    
    fig_categories.update_layout(
        title=f'Total por Categoria - {year}',
        xaxis_title='Categoria',
        yaxis_title='Valor (R$)',
        barmode='group'
    )
    charts['bar_categories'] = json.dumps(fig_categories, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Heatmap de categorias por mês
    heatmap_data = df.groupby(['mês', 'categoria']).agg({
        'valor': 'sum'
    }).reset_index()
    
    # Criar matriz para o heatmap
    heatmap_matrix = pd.pivot_table(
        heatmap_data,
        values='valor',
        index='categoria',
        columns='mês',
        fill_value=0
    )
    
    # Garantir que todos os meses estejam presentes
    for m in range(1, 13):
        if m not in heatmap_matrix.columns:
            heatmap_matrix[m] = 0
    
    heatmap_matrix = heatmap_matrix.reindex(columns=range(1, 13))
    
    # Renomear colunas para nomes dos meses
    heatmap_matrix.columns = month_names
    
    # Criar heatmap
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_matrix.values,
        x=heatmap_matrix.columns,
        y=heatmap_matrix.index,
        colorscale='RdBu_r',
        zmid=0
    ))
    fig_heatmap.update_layout(
        title=f'Categorias por Mês - {year}',
        xaxis_title='Mês',
        yaxis_title='Categoria'
    )
    charts['heatmap_categories'] = json.dumps(fig_heatmap, cls=plotly.utils.PlotlyJSONEncoder)
    
    return charts
