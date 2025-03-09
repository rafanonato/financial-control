from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import numpy as np
import os
import json
import sqlite3
import datetime
from werkzeug.utils import secure_filename
import plotly
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import csv

# Initialize Flask app
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///financial_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy()
db.init_app(app)

# Import models after db initialization to avoid circular imports
# Usando importação relativa para evitar problemas com o nome do pacote
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models.models import Transaction, Category, Goal

# Create database tables
with app.app_context():
    db.create_all()

# Import routes
from app.controllers.routes import *

if __name__ == '__main__':
    app.run(debug=True, port=5000)
