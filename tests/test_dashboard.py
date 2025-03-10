import unittest
from app import create_app, db
from app.models import Transaction, Category, Goal
from datetime import datetime, timedelta
import json

class TestDashboard(unittest.TestCase):
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.app = create_app('config.TestConfig')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Criar categorias de teste
        self.categories = {
            'receita': Category(name='Receita', type='receita'),
            'despesa_fixa': Category(name='Despesa Fixa', type='despesa'),
            'despesa_variavel': Category(name='Despesa Variável', type='despesa'),
            'investimento': Category(name='Investimento', type='investimento'),
            'reserva': Category(name='Reserva de Emergência', type='reserva')
        }
        for category in self.categories.values():
            db.session.add(category)
        db.session.commit()

        # Criar transações de teste
        self.create_test_transactions()
        self.create_test_goals()

    def tearDown(self):
        """Limpeza após cada teste."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_test_transactions(self):
        """Criar transações de teste."""
        now = datetime.now()
        transactions = [
            # Receitas
            Transaction(
                description='Salário',
                amount=5000.00,
                date=now,
                category=self.categories['receita']
            ),
            # Despesas Fixas
            Transaction(
                description='Aluguel',
                amount=-1500.00,
                date=now,
                category=self.categories['despesa_fixa']
            ),
            # Despesas Variáveis
            Transaction(
                description='Alimentação',
                amount=-800.00,
                date=now,
                category=self.categories['despesa_variavel']
            ),
            # Investimentos
            Transaction(
                description='Tesouro Direto',
                amount=-1000.00,
                date=now,
                category=self.categories['investimento']
            ),
            # Reserva de Emergência
            Transaction(
                description='Reserva',
                amount=-500.00,
                date=now,
                category=self.categories['reserva']
            )
        ]

        # Criar transações para os últimos 12 meses
        for i in range(1, 12):
            date = now - timedelta(days=30*i)
            for t in transactions:
                db.session.add(Transaction(
                    description=t.description,
                    amount=t.amount,
                    date=date,
                    category=t.category
                ))

        db.session.add_all(transactions)
        db.session.commit()

    def create_test_goals(self):
        """Criar metas de teste."""
        goals = [
            Goal(
                name='Meta de Economia',
                target_amount=2000.00,
                current_amount=1500.00,
                category=self.categories['reserva'],
                deadline=datetime.now() + timedelta(days=30)
            ),
            Goal(
                name='Meta de Investimento',
                target_amount=10000.00,
                current_amount=8000.00,
                category=self.categories['investimento'],
                deadline=datetime.now() + timedelta(days=365)
            )
        ]
        db.session.add_all(goals)
        db.session.commit()

    def test_monthly_dashboard_page(self):
        """Testar se a página do dashboard mensal é carregada corretamente."""
        response = self.client.get('/dashboard/monthly')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard Mensal', response.data)

    def test_yearly_dashboard_page(self):
        """Testar se a página do dashboard anual é carregada corretamente."""
        response = self.client.get('/dashboard/yearly')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard Anual', response.data)

    def test_dashboard_api_monthly_data(self):
        """Testar se a API retorna os dados mensais corretamente."""
        response = self.client.get('/dashboard/api/data?period=monthly')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        # Verificar estrutura dos dados
        self.assertIn('receita_vs_despesa', data)
        self.assertIn('fechamento_mensal', data)
        self.assertIn('despesas_categoria', data)
        self.assertIn('investimentos', data)
        self.assertIn('metas_realizado', data)
        self.assertIn('saving_rate', data)
        self.assertIn('projecao_mensal', data)

        # Verificar valores
        self.assertEqual(data['receita_vs_despesa']['receitas'], 5000.00)
        self.assertEqual(data['receita_vs_despesa']['despesas'], -2300.00)
        self.assertEqual(data['investimentos']['reserva_emergencia'], -500.00)
        self.assertEqual(data['investimentos']['investimentos'], -1000.00)

    def test_dashboard_api_yearly_data(self):
        """Testar se a API retorna os dados anuais corretamente."""
        response = self.client.get('/dashboard/api/data?period=yearly')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        # Verificar estrutura dos dados
        self.assertIn('receita_vs_despesa', data)
        self.assertIn('fechamento_mensal', data)
        self.assertIn('despesas_categoria', data)
        self.assertIn('investimentos', data)
        self.assertIn('metas_realizado', data)
        self.assertIn('saving_rate', data)
        self.assertIn('cash_flow', data)
        self.assertIn('projecao_mensal', data)

        # Verificar se há dados para 12 meses
        self.assertEqual(len(data['months']), 12)
        self.assertEqual(len(data['fechamento_mensal']), 12)
        self.assertEqual(len(data['saving_rate']), 12)

    def test_dashboard_api_with_date_range(self):
        """Testar se a API filtra corretamente por período."""
        now = datetime.now()
        start_date = (now - timedelta(days=90)).strftime('%Y-%m')
        end_date = now.strftime('%Y-%m')

        response = self.client.get(
            f'/dashboard/api/data?period=monthly&start_date={start_date}&end_date={end_date}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        # Verificar se há dados apenas para o período especificado
        self.assertEqual(len(data['months']), 3)

if __name__ == '__main__':
    unittest.main() 