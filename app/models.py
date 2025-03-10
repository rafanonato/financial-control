from app import db
from datetime import datetime

class Category(db.Model):
    """Modelo para categorias de transações."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # receita, despesa, investimento, reserva
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    goals = db.relationship('Goal', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

class Transaction(db.Model):
    """Modelo para transações financeiras."""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(256), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.description} {self.amount}>'

class Goal(db.Model):
    """Modelo para metas financeiras."""
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(256))
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0.0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    deadline = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='em_andamento')  # em_andamento, concluida, cancelada
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Goal {self.name}>'

    @property
    def progress(self):
        """Retorna o progresso da meta em porcentagem."""
        if self.target_amount == 0:
            return 0
        return (self.current_amount / self.target_amount) * 100

    def update_status(self):
        """Atualiza o status da meta com base no progresso e prazo."""
        if self.current_amount >= self.target_amount:
            self.status = 'concluida'
        elif self.deadline and self.deadline < datetime.utcnow():
            self.status = 'cancelada'
        else:
            self.status = 'em_andamento' 