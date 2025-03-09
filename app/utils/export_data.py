from app import app
from app.models.models import Transaction, Category
import pandas as pd
import numpy as np
from datetime import datetime
import os
from io import BytesIO
import pdfkit
from jinja2 import Environment, FileSystemLoader
import csv

def generate_pdf_report(transactions, start_date, end_date):
    """
    Gera um relatório PDF com os dados financeiros
    
    Args:
        transactions: Lista de transações
        start_date: Data inicial do período
        end_date: Data final do período
        
    Returns:
        BytesIO contendo o arquivo PDF
    """
    # Converter transações para DataFrame
    data = []
    for t in transactions:
        data.append({
            'data': t.date.strftime('%d/%m/%Y'),
            'descrição': t.description,
            'valor': f"R$ {t.amount:.2f}",
            'categoria': t.category.name
        })
    
    df = pd.DataFrame(data)
    
    # Calcular totais
    total_receitas = sum([t.amount for t in transactions if t.amount > 0])
    total_despesas = sum([t.amount for t in transactions if t.amount < 0])
    saldo = total_receitas + total_despesas
    
    # Criar HTML para o relatório
    env = Environment(loader=FileSystemLoader('app/templates'))
    template = env.get_template('report_template.html')
    
    html = template.render(
        transactions=data,
        start_date=start_date.strftime('%d/%m/%Y'),
        end_date=end_date.strftime('%d/%m/%Y'),
        total_receitas=f"R$ {total_receitas:.2f}",
        total_despesas=f"R$ {total_despesas:.2f}",
        saldo=f"R$ {saldo:.2f}"
    )
    
    # Converter HTML para PDF
    pdf_options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None
    }
    
    pdf = pdfkit.from_string(html, False, options=pdf_options)
    
    # Retornar como BytesIO
    pdf_io = BytesIO(pdf)
    pdf_io.seek(0)
    
    return pdf_io

def export_to_excel(transactions):
    """
    Exporta transações para um arquivo Excel
    
    Args:
        transactions: Lista de transações
        
    Returns:
        BytesIO contendo o arquivo Excel
    """
    # Converter transações para DataFrame
    data = []
    for t in transactions:
        data.append({
            'Data': t.date,
            'Descrição': t.description,
            'Valor': t.amount,
            'Categoria': t.category.name,
            'Tipo': t.category.type
        })
    
    df = pd.DataFrame(data)
    
    # Criar arquivo Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transações')
        
        # Adicionar planilha de resumo
        summary = pd.DataFrame({
            'Categoria': [t.category.name for t in transactions],
            'Valor': [t.amount for t in transactions]
        }).groupby('Categoria').sum().reset_index()
        
        summary.to_excel(writer, index=False, sheet_name='Resumo por Categoria')
    
    output.seek(0)
    return output

def export_to_csv(transactions):
    """
    Exporta transações para um arquivo CSV
    
    Args:
        transactions: Lista de transações
        
    Returns:
        BytesIO contendo o arquivo CSV
    """
    # Criar arquivo CSV
    output = BytesIO()
    
    # Escrever dados
    writer = csv.writer(output)
    
    # Escrever cabeçalho
    writer.writerow(['Data', 'Descrição', 'Valor', 'Categoria', 'Tipo'])
    
    # Escrever transações
    for t in transactions:
        writer.writerow([
            t.date.strftime('%Y-%m-%d'),
            t.description,
            t.amount,
            t.category.name,
            t.category.type
        ])
    
    output.seek(0)
    return output
