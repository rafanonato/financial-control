from app import db
from app.models.models import Transaction, Category
import pandas as pd
import numpy as np
from datetime import datetime
import os

def process_excel_file(filepath, date_col, desc_col, amount_col, category_col=None):
    """
    Processa um arquivo Excel para importação de dados financeiros
    
    Args:
        filepath: Caminho para o arquivo Excel
        date_col: Nome da coluna de data
        desc_col: Nome da coluna de descrição
        amount_col: Nome da coluna de valor
        category_col: Nome da coluna de categoria (opcional)
        
    Returns:
        Lista de dicionários com os dados processados
    """
    try:
        # Ler o arquivo Excel
        df = pd.read_excel(filepath)
        
        # Verificar se as colunas existem
        required_cols = [date_col, desc_col, amount_col]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Coluna {col} não encontrada no arquivo")
        
        # Processar os dados
        transactions = []
        
        for _, row in df.iterrows():
            # Processar a data
            date_value = row[date_col]
            if isinstance(date_value, str):
                try:
                    # Tentar diferentes formatos de data
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                        try:
                            date_obj = datetime.strptime(date_value, fmt)
                            break
                        except ValueError:
                            continue
                except:
                    # Se falhar, usar a data atual
                    date_obj = datetime.now()
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                # Se não for string nem datetime, usar a data atual
                date_obj = datetime.now()
            
            # Processar o valor
            amount = float(row[amount_col])
            
            # Criar transação
            transaction = {
                'date': date_obj,
                'description': str(row[desc_col]),
                'amount': amount
            }
            
            # Adicionar categoria se existir
            if category_col and category_col in df.columns:
                transaction['category'] = str(row[category_col])
            
            transactions.append(transaction)
        
        return transactions
    
    except Exception as e:
        print(f"Erro ao processar arquivo Excel: {str(e)}")
        return []

def process_csv_file(filepath, date_col, desc_col, amount_col, category_col=None):
    """
    Processa um arquivo CSV para importação de dados financeiros
    
    Args:
        filepath: Caminho para o arquivo CSV
        date_col: Nome da coluna de data
        desc_col: Nome da coluna de descrição
        amount_col: Nome da coluna de valor
        category_col: Nome da coluna de categoria (opcional)
        
    Returns:
        Lista de dicionários com os dados processados
    """
    try:
        # Ler o arquivo CSV
        df = pd.read_csv(filepath)
        
        # Verificar se as colunas existem
        required_cols = [date_col, desc_col, amount_col]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Coluna {col} não encontrada no arquivo")
        
        # Processar os dados
        transactions = []
        
        for _, row in df.iterrows():
            # Processar a data
            date_value = row[date_col]
            if isinstance(date_value, str):
                try:
                    # Tentar diferentes formatos de data
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                        try:
                            date_obj = datetime.strptime(date_value, fmt)
                            break
                        except ValueError:
                            continue
                except:
                    # Se falhar, usar a data atual
                    date_obj = datetime.now()
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                # Se não for string nem datetime, usar a data atual
                date_obj = datetime.now()
            
            # Processar o valor
            amount = float(row[amount_col])
            
            # Criar transação
            transaction = {
                'date': date_obj,
                'description': str(row[desc_col]),
                'amount': amount
            }
            
            # Adicionar categoria se existir
            if category_col and category_col in df.columns:
                transaction['category'] = str(row[category_col])
            
            transactions.append(transaction)
        
        return transactions
    
    except Exception as e:
        print(f"Erro ao processar arquivo CSV: {str(e)}")
        return []

def map_categories(transactions, categories):
    """
    Mapeia categorias para transações baseado em palavras-chave
    
    Args:
        transactions: Lista de transações
        categories: Lista de categorias disponíveis
        
    Returns:
        Transações com categorias mapeadas
    """
    # Dicionário de palavras-chave para categorias
    keywords = {
        'Alimentação': ['mercado', 'supermercado', 'restaurante', 'ifood', 'comida'],
        'Transporte': ['uber', '99', 'táxi', 'combustível', 'gasolina', 'estacionamento'],
        'Moradia': ['aluguel', 'condomínio', 'iptu', 'água', 'luz', 'energia', 'gás'],
        'Saúde': ['farmácia', 'médico', 'consulta', 'exame', 'hospital'],
        'Educação': ['escola', 'faculdade', 'curso', 'livro'],
        'Lazer': ['cinema', 'teatro', 'show', 'viagem', 'hotel'],
        'Investimentos': ['tesouro', 'ações', 'fii', 'cdb', 'poupança']
    }
    
    # Mapear categorias
    for transaction in transactions:
        if 'category' not in transaction:
            desc = transaction['description'].lower()
            
            # Verificar palavras-chave
            for cat_name, words in keywords.items():
                for word in words:
                    if word in desc:
                        # Encontrar categoria correspondente
                        for category in categories:
                            if category.name == cat_name:
                                transaction['category_id'] = category.id
                                break
                        break
            
            # Se não encontrou categoria, usar a primeira disponível
            if 'category_id' not in transaction and categories:
                transaction['category_id'] = categories[0].id
    
    return transactions
