from flask import render_template, request, redirect, url_for, jsonify, send_file

# Importação relativa para evitar problemas com o nome do pacote
import sys
import os

# Adiciona o diretório raiz ao caminho de busca do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importa app e db do módulo principal
from app import app, db

# Importação dos modelos e utilitários
from app.models.models import Transaction, Category, Goal
from app.utils.import_data import process_excel_file, process_csv_file
from app.utils.export_data import generate_pdf_report, export_to_excel, export_to_csv
from app.utils.dashboard import generate_monthly_charts, generate_yearly_charts
import pandas as pd
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import plotly
import plotly.express as px
from sqlalchemy import extract, func

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Context processor para adicionar variáveis globais a todos os templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Home page - Dashboard
@app.route('/')
def index():
    return render_template('index.html')

# Monthly Dashboard
@app.route('/dashboard/monthly')
def monthly_dashboard():
    month = request.args.get('month', datetime.now().month)
    year = request.args.get('year', datetime.now().year)
    
    # Get transactions for the selected month
    transactions = Transaction.query.filter(
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).all()
    
    # Generate charts
    charts = generate_monthly_charts(transactions, month, year)
    
    return render_template('monthly_dashboard.html', 
                          charts=charts, 
                          month=month, 
                          year=year,
                          transactions=[t.to_dict() for t in transactions])

# Yearly Dashboard
@app.route('/dashboard/yearly')
def yearly_dashboard():
    year = request.args.get('year', datetime.now().year)
    
    # Get transactions for the selected year
    transactions = Transaction.query.filter(
        extract('year', Transaction.date) == year
    ).all()
    
    # Generate charts
    charts = generate_yearly_charts(transactions, year)
    
    return render_template('yearly_dashboard.html', 
                          charts=charts, 
                          year=year)

# Transactions management
@app.route('/transactions')
def transactions():
    month = request.args.get('month', datetime.now().month)
    year = request.args.get('year', datetime.now().year)
    
    transactions = Transaction.query.filter(
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).order_by(Transaction.date.desc()).all()
    
    categories = Category.query.all()
    
    return render_template('transactions.html', 
                          transactions=[t.to_dict() for t in transactions],
                          categories=[c.to_dict() for c in categories],
                          month=month,
                          year=year)

# Add transaction
@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    if request.method == 'POST':
        data = request.form
        
        # Create new transaction
        transaction = Transaction(
            date=datetime.strptime(data['date'], '%Y-%m-%d'),
            description=data['description'],
            amount=float(data['amount']),
            category_id=int(data['category_id']),
            recurring=bool(data.get('recurring', False)),
            recurring_period=data.get('recurring_period')
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        # Handle recurring transactions if needed
        if transaction.recurring and transaction.recurring_period == 'monthly':
            # Logic to create recurring transactions for future months
            pass
        
        return redirect(url_for('transactions'))

# Edit transaction
@app.route('/transactions/edit/<int:id>', methods=['POST'])
def edit_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    
    if request.method == 'POST':
        data = request.form
        
        transaction.date = datetime.strptime(data['date'], '%Y-%m-%d')
        transaction.description = data['description']
        transaction.amount = float(data['amount'])
        transaction.category_id = int(data['category_id'])
        transaction.recurring = bool(data.get('recurring', False))
        transaction.recurring_period = data.get('recurring_period')
        
        db.session.commit()
        
        return redirect(url_for('transactions'))

# Delete transaction
@app.route('/transactions/delete/<int:id>', methods=['POST'])
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    
    db.session.delete(transaction)
    db.session.commit()
    
    return redirect(url_for('transactions'))

# Categories management
@app.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=[c.to_dict() for c in categories])

# Add category
@app.route('/categories/add', methods=['POST'])
def add_category():
    if request.method == 'POST':
        data = request.form
        
        category = Category(
            name=data['name'],
            type=data['type'],
            color=data.get('color', '#3498db')
        )
        
        db.session.add(category)
        db.session.commit()
        
        return redirect(url_for('categories'))

# Edit category
@app.route('/categories/edit/<int:id>', methods=['POST'])
def edit_category(id):
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        data = request.form
        
        category.name = data['name']
        category.type = data['type']
        category.color = data.get('color', category.color)
        
        db.session.commit()
        
        return redirect(url_for('categories'))

# Delete category
@app.route('/categories/delete/<int:id>', methods=['POST'])
def delete_category(id):
    category = Category.query.get_or_404(id)
    
    # Check if category has transactions
    if len(category.transactions) > 0:
        # Return error
        return jsonify({'error': 'Não é possível excluir categoria com transações associadas'}), 400
    
    db.session.delete(category)
    db.session.commit()
    
    return redirect(url_for('categories'))

# Import data
@app.route('/import', methods=['GET', 'POST'])
def import_data():
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process file based on extension
            if filename.endswith('.csv'):
                # Show mapping page
                return render_template('import_mapping.html', 
                                      filename=filename, 
                                      filetype='csv')
            else:  # Excel file
                # Show mapping page
                return render_template('import_mapping.html', 
                                      filename=filename, 
                                      filetype='excel')
    
    return render_template('import.html')

# Process import mapping
@app.route('/import/process', methods=['POST'])
def process_import():
    data = request.form
    filename = data['filename']
    filetype = data['filetype']
    
    # Get column mappings
    date_col = data['date_column']
    desc_col = data['description_column']
    amount_col = data['amount_column']
    category_col = data.get('category_column', None)
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Process file based on type
    if filetype == 'csv':
        transactions = process_csv_file(filepath, date_col, desc_col, amount_col, category_col)
    else:  # Excel
        transactions = process_excel_file(filepath, date_col, desc_col, amount_col, category_col)
    
    # Save transactions to database
    for t in transactions:
        transaction = Transaction(
            date=t['date'],
            description=t['description'],
            amount=t['amount'],
            category_id=t.get('category_id', 1)  # Default to first category if not specified
        )
        db.session.add(transaction)
    
    db.session.commit()
    
    return redirect(url_for('transactions'))

# Export data
@app.route('/export', methods=['GET', 'POST'])
def export_data():
    if request.method == 'POST':
        data = request.form
        export_type = data['export_type']
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        
        # Get transactions for the selected period
        transactions = Transaction.query.filter(
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).order_by(Transaction.date).all()
        
        if export_type == 'pdf':
            # Generate PDF report
            pdf_file = generate_pdf_report(transactions, start_date, end_date)
            return send_file(pdf_file, as_attachment=True, download_name='financial_report.pdf')
        
        elif export_type == 'excel':
            # Export to Excel
            excel_file = export_to_excel(transactions)
            return send_file(excel_file, as_attachment=True, download_name='financial_data.xlsx')
        
        elif export_type == 'csv':
            # Export to CSV
            csv_file = export_to_csv(transactions)
            return send_file(csv_file, as_attachment=True, download_name='financial_data.csv')
    
    return render_template('export.html')

# Goals management
@app.route('/goals')
def goals():
    goals = Goal.query.all()
    categories = Category.query.all()
    
    return render_template('goals.html', 
                          goals=[g.to_dict() for g in goals],
                          categories=[c.to_dict() for c in categories])

# Add goal
@app.route('/goals/add', methods=['POST'])
def add_goal():
    if request.method == 'POST':
        data = request.form
        
        goal = Goal(
            name=data['name'],
            target_amount=float(data['target_amount']),
            current_amount=float(data.get('current_amount', 0)),
            category_id=data.get('category_id'),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d') if data.get('end_date') else None
        )
        
        db.session.add(goal)
        db.session.commit()
        
        return redirect(url_for('goals'))

# Edit goal
@app.route('/goals/edit/<int:id>', methods=['POST'])
def edit_goal(id):
    goal = Goal.query.get_or_404(id)
    
    if request.method == 'POST':
        data = request.form
        
        goal.name = data['name']
        goal.target_amount = float(data['target_amount'])
        goal.current_amount = float(data['current_amount'])
        goal.category_id = data.get('category_id')
        goal.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        goal.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d') if data.get('end_date') else None
        
        db.session.commit()
        
        return redirect(url_for('goals'))

# Delete goal
@app.route('/goals/delete/<int:id>', methods=['POST'])
def delete_goal(id):
    goal = Goal.query.get_or_404(id)
    
    db.session.delete(goal)
    db.session.commit()
    
    return redirect(url_for('goals'))

# API endpoints for AJAX requests
@app.route('/api/transactions/<int:year>/<int:month>')
def api_transactions(year, month):
    transactions = Transaction.query.filter(
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).all()
    
    return jsonify([t.to_dict() for t in transactions])

@app.route('/api/categories')
def api_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])

@app.route('/api/dashboard/monthly/<int:year>/<int:month>')
def api_monthly_dashboard(year, month):
    transactions = Transaction.query.filter(
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).all()
    
    charts = generate_monthly_charts(transactions, month, year)
    
    return jsonify(charts)

@app.route('/api/dashboard/yearly/<int:year>')
def api_yearly_dashboard(year):
    transactions = Transaction.query.filter(
        extract('year', Transaction.date) == year
    ).all()
    
    charts = generate_yearly_charts(transactions, year)
    
    return jsonify(charts)

# Backup and restore
@app.route('/backup', methods=['GET', 'POST'])
def backup():
    if request.method == 'POST':
        # Create backup of database
        from shutil import copyfile
        backup_file = f"financial_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        copyfile('financial_data.db', os.path.join(app.config['UPLOAD_FOLDER'], backup_file))
        
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], backup_file), 
                        as_attachment=True, 
                        download_name=backup_file)
    
    return render_template('backup.html')

@app.route('/restore', methods=['GET', 'POST'])
def restore():
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(request.url)
        
        if file and file.filename.endswith('.db'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Restore database
            from shutil import copyfile
            copyfile(filepath, 'financial_data.db')
            
            return redirect(url_for('index'))
    
    return render_template('restore.html')
