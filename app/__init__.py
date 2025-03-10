from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Get the absolute path for the project root
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Initialize Flask app
app = Flask(__name__)

# Configure the Flask app
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "financial_data.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['TEMPLATE_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app.config['STATIC_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), exist_ok=True)

# Initialize database
db = SQLAlchemy()
db.init_app(app)

# Push an application context
app.app_context().push()

# Import models after db initialization to avoid circular imports
from app.models.models import Transaction, Category, Goal

# Create database tables
with app.app_context():
    db.create_all()

# Import and register blueprints
from app.controllers.routes import *
from app.controllers.financial_flow import bp as financial_flow_bp

app.register_blueprint(financial_flow_bp)

# Make sure to export both app and db
__all__ = ['app', 'db']
