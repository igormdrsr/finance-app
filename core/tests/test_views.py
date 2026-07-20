from decimal import Decimal
from datetime import date

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Category, Transaction, Goal, Budget


class CategoryListCreateTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("category-list-create")
        self.user = User.objects.create_user(username="igor", password="1234-abc")
        self.client.force_authenticate(user=self.user)

    def test_create_category(self):
        data = {"name": "Categoria de teste"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(Category.objects.get().name, "Categoria de teste")

    def test_list_categories(self):
        Category.objects.create(user=self.user, name="Category 1")
        Category.objects.create(user=self.user, name="Category 2")
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # breakpoint()
        self.assertEqual(len(response.data["results"]), 2)


class GoalListTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("goals-list")
        self.user = User.objects.create_user(username="igor", password="1234-abc")
        self.client.force_authenticate(user=self.user)

    def test_list_goals(self):
        Goal.objects.create(user=self.user, name="Goal 1", target_amount=1000)
        Goal.objects.create(user=self.user, name="Goal 2", target_amount=2000)
        response = self.client.get(self.url, format="json")
        # breakpoint()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class ExpensesByCategoryTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="igor", password="1234-abc")

        self.cat_food = Category.objects.create(name="Alimentação", user=self.user)
        self.cat_transport = Category.objects.create(name="Transporte", user=self.user)

        self.url = reverse("expenses-by-category")

        Transaction.objects.create(
            user=self.user,
            category=self.cat_food,
            transaction_type="expense",
            amount=Decimal("100.00"),
            description="Supermercado",
            date=date(2024, 1, 5),
        )

        Transaction.objects.create(
            user=self.user,
            category=self.cat_food,
            transaction_type="expense",
            amount=Decimal("50.00"),
            description="Padaria",
            date=date(2024, 1, 10),
        )

        Transaction.objects.create(
            user=self.user,
            category=self.cat_transport,
            transaction_type="expense",
            amount=Decimal("200.00"),
            description="Uber",
            date=date(2024, 1, 15),
        )

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_expenses_grouped_by_category(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]
        self.assertEqual(len(results), 2)

        self.assertEqual(results[0]["category_name"], "Transporte")
        self.assertEqual(Decimal(results[0]["total_amount"]), Decimal("200.00"))

        self.assertEqual(results[1]["category_name"], "Alimentação")
        self.assertEqual(Decimal(results[1]["total_amount"]), Decimal("150.00"))

    def test_empty_result_when_no_expenses(self):
        empty_user = User.objects.create_user(
            username="sem_gastos", password="senha123"
        )
        self.client.force_authenticate(user=empty_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])


class BudgetStreakTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="igor", password="1234-abc")
        self.category = Category.objects.create(name="Lazer", user=self.user)
        Budget.objects.create(
            user=self.user,
            category=Category.objects.get(name="Lazer"),
            amount=Decimal("1000.00"),
            active=True,
        )

        Transaction.objects.create(
            user=self.user,
            category=Category.objects.get(name="Lazer"),
            transaction_type="expense",
            amount=Decimal("100.00"),
            description="Cinema",
            date=date(2024, 1, 5),
        )

        Transaction.objects.create(
            user=self.user,
            category=Category.objects.get(name="Lazer"),
            transaction_type="expense",
            amount=Decimal("200.00"),
            description="Show",
            date=date(2024, 1, 15),
        )

        Transaction.objects.create(
            user=self.user,
            category=Category.objects.get(name="Lazer"),
            transaction_type="expense",
            amount=Decimal("1200.00"),
            description="Restaurante",
            date=date(2024, 2, 6),
        )

        Transaction.objects.create(
            user=self.user,
            category=Category.objects.get(name="Lazer"),
            transaction_type="expense",
            amount=Decimal("300.00"),
            description="Teatro",
            date=date(2024, 3, 10),
        )

        Transaction.objects.create(
            user=self.user,
            category=Category.objects.get(name="Lazer"),
            transaction_type="expense",
            amount=Decimal("300.00"),
            description="Teatro",
            date=date(2024, 4, 10),
        )

    def test_requires_authentication(self):
        category_id = Category.objects.get(name="Lazer").id
        url = reverse("budget-streak", args=[category_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_budget_streak(self):
        self.client.force_authenticate(user=self.user)

        category_id = Category.objects.get(name="Lazer").id
        url = reverse("budget-streak", args=[category_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_streak"], 2)

    def test_get_budget_amount(self):
        self.client.force_authenticate(user=self.user)

        category_id = Category.objects.get(name="Lazer").id
        url = reverse("budget-streak", args=[category_id])
        response = self.client.get(url)

        self.assertEqual(response.data["budget"], Decimal("1000.00"))

    def test_should_return_404_for_nonexistent_category(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("budget-streak", args=[999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_should_return_404_when_active_budget_does_not_exist(self):
        self.client.force_authenticate(user=self.user)

        other_category = Category.objects.create(name="Outra Categoria", user=self.user)
        url = reverse("budget-streak", args=[other_category.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_should_return_404_when_budget_is_inactive(self):
        self.client.force_authenticate(user=self.user)

        category = Category.objects.create(name="Alimentação", user=self.user)
        Budget.objects.create(
            user=self.user, category=category, amount=Decimal("1000.00"), active=False
        )

        url = reverse("budget-streak", kwargs={"category_id": category.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DashboardTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="igor", password="1234-abc")
        # self.client.force_authenticate(user=self.user)
        self.url = reverse("dashboard-api")

    def test_should_require_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_should_return_empty_dashboard(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["total_income"], Decimal("0.00"))
        self.assertEqual(response.data["total_expense"], Decimal("0.00"))
        self.assertEqual(response.data["total_balance"], Decimal("0.00"))
        self.assertEqual(response.data["total_transactions"], 0)
        self.assertEqual(response.data["monthly_transactions_count"], 0)
        self.assertEqual(response.data["monthly_transactions_items"], [])

    def test_should_calculate_dashboard_totals(self):
        self.client.force_authenticate(self.user)

        Transaction.objects.create(
            user=self.user,
            transaction_type="income",
            amount=Decimal("1000.00"),
            description="Salário",
            date=date(2024, 1, 5),
        )

        Transaction.objects.create(
            user=self.user,
            transaction_type="expense",
            amount=Decimal("200.00"),
            description="Aluguel",
            date=date(2024, 1, 10),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_income"], Decimal("1000.00"))
        self.assertEqual(response.data["total_expense"], Decimal("200.00"))
        self.assertEqual(response.data["total_balance"], Decimal("800.00"))
        self.assertEqual(response.data["total_transactions"], 2)

    def test_should_filter_transactions_by_month_and_year(self):
        self.client.force_authenticate(self.user)

        Transaction.objects.create(
            user=self.user,
            transaction_type="expense",
            amount=Decimal("200.00"),
            description="Aluguel",
            date=date(2024, 1, 10),
        )

        Transaction.objects.create(
            user=self.user,
            transaction_type="expense",
            amount=Decimal("200.00"),
            description="Aluguel",
            date=date(2024, 2, 10),
        )

        response = self.client.get(self.url, {"month": 1, "year": 2024})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["monthly_expense"], Decimal("200.00"))
        self.assertEqual(response.data["monthly_transactions_count"], 1)

    def test_should_return_monthly_transactions(self):
        self.client.force_authenticate(self.user)

        transaction = Transaction.objects.create(
            user=self.user,
            transaction_type="expense",
            amount=Decimal("200.00"),
            description="Mercado",
            date=date.today(),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        monthly_transactions_items = response.data["monthly_transactions_items"]
        self.assertEqual(len(monthly_transactions_items), 1)

        self.assertEqual(monthly_transactions_items[0]["id"], transaction.id)

        self.assertEqual(monthly_transactions_items[0]["description"], "Mercado")

        self.assertEqual(
            Decimal(monthly_transactions_items[0]["amount"]), Decimal("200.00")
        )


class TransactionListTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="igor", password="1234-abc")

    def test_should_require_authentication(self):
        url = reverse("transactions")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_should_return_all_transactions(self):
        self.client.force_authenticate(self.user)
        url = reverse("transactions")

        Transaction.objects.create(
            user=self.user,
            transaction_type="income",
            amount=Decimal("1000.00"),
            description="Salário",
            date=date(2024, 1, 5),
        )

        Transaction.objects.create(
            user=self.user,
            transaction_type="expense",
            amount=Decimal("200.00"),
            description="Aluguel",
            date=date(2024, 1, 10),
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_should_filter_current_month(self):
        self.client.force_authenticate(self.user)
        url = reverse("transactions")

        Transaction.objects.create(
            user=self.user,
            transaction_type="income",
            amount=Decimal("1000.00"),
            description="Salário",
            date=date(2024, 1, 5),
        )

        Transaction.objects.create(
            user=self.user,
            transaction_type="expense",
            amount=Decimal("200.00"),
            description="Aluguel",
            date=date(2024, 2, 10),
        )

        response = self.client.get(url, {"month": 1, "year": 2024})
        breakpoint()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
