from flask import Blueprint, render_template, jsonify, request
from app.controllers.dashboard import DashboardController

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/monthly')
def monthly():
    """Rota para exibir o dashboard mensal."""
    return render_template('dashboard/monthly.html')

@bp.route('/yearly')
def yearly():
    """Rota para exibir o dashboard anual."""
    return render_template('dashboard/yearly.html')

@bp.route('/api/data')
def get_data():
    """Rota para obter os dados do dashboard."""
    period = request.args.get('period', 'monthly')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    controller = DashboardController()
    data = controller.get_dashboard_data(period, start_date, end_date)
    return jsonify(data) 