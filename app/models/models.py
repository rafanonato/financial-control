from datetime import datetime
import sys
import os
from app import db

# Adiciona o diretório raiz ao caminho de busca do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importa a instância db do app_main.py
try:
    from app_main import db
except ImportError:
    # Fallback para execução direta do arquivo
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'expense', 'income', 'investment'
    color = db.Column(db.String(20), default='#3498db')
    transactions = db.relationship('Transaction', backref='category', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'color': self.color
        }

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    recurring = db.Column(db.Boolean, default=False)
    recurring_period = db.Column(db.String(20), nullable=True)  # 'monthly', 'yearly', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'description': self.description,
            'amount': self.amount,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'category_type': self.category.type if self.category else None,
            'recurring': self.recurring,
            'recurring_period': self.recurring_period
        }

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0.0)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'target_amount': self.target_amount,
            'current_amount': self.current_amount,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category_id else None,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'progress': (self.current_amount / self.target_amount * 100) if self.target_amount > 0 else 0
        }


# Este bloco será executado apenas quando o arquivo for executado diretamente
if __name__ == "__main__":
    # Quando executado diretamente, usamos a instância de Flask e SQLAlchemy criada no bloco try/except acima
    # Isso garante que estamos usando a mesma instância de db em todo o código
    
    # Criar um contexto de aplicação
    with app.app_context():
        # Criar as tabelas no banco de dados
        db.create_all()
        
        # Verificar se já existem categorias
        if not Category.query.first():
            # Criar algumas categorias de exemplo
            categories = [
                Category(name="Moradia", type="expense", color="#e74c3c"),
                Category(name="Alimentação", type="expense", color="#3498db"),
                Category(name="Transporte", type="expense", color="#2ecc71"),
                Category(name="Lazer", type="expense", color="#f39c12"),
                Category(name="Saúde", type="expense", color="#9b59b6"),
                Category(name="Educação", type="expense", color="#1abc9c"),
                Category(name="Salário", type="income", color="#27ae60"),
                Category(name="Investimentos", type="investment", color="#2980b9")
            ]
            
            # Adicionar categorias ao banco de dados
            for category in categories:
                db.session.add(category)
            
            # Commit das alterações
            db.session.commit()
            print("Categorias de exemplo criadas com sucesso!")
        
        # Listar todas as categorias
        print("\nCategorias disponíveis:")
        for category in Category.query.all():
            print(f"ID: {category.id}, Nome: {category.name}, Tipo: {category.type}")
        
        print("\nModelo de dados configurado com sucesso!")
