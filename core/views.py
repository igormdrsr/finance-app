from django.shortcuts import render
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Value
from django.db.models.functions import Coalesce, TruncMonth
from datetime import date

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status


from core.models import Transaction, Category, Goal, Budget
from core.serializers import (
    TransactionSerializer,
    CategorySerializer,
    GoalSerializer,
    BudgetSerializer,
    BudgetStreakSerializer,
)
from decimal import Decimal


class HomeView(View):
    def get(self, request):
        context = {"message": "Hello, world!"}
        return render(request, "home.html", context)


class CategoryListCreate(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = Category.objects.filter(user=request.user)
        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(categories, request)
        serializer = CategorySerializer(result_page, many=True)

        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    # TODO: Orçamento Mensal
    # Objetivo
    # Controlar limites de gastos.

    # Funcionalidades
    # Definir orçamento por categoria
    # Acompanhar consumo do orçamento
    # Alertar quando o limite estiver próximo
    # Exemplo
    # Alimentação: R$ 800/mês


class GoalListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        goals = (
            Goal.objects.filter(user=request.user)
            .annotate(
                current_amount=Coalesce(Sum("transactions__amount"), Decimal("0.00"))
            )
            .annotate(
                current_amount_percentage=ExpressionWrapper(
                    F("current_amount") * Value(100) / F("target_amount"),
                    output_field=DecimalField(max_digits=5, decimal_places=2),
                )
            )
            .order_by("-current_amount_percentage")
        )

        serializer = GoalSerializer(goals, many=True)
        return Response(serializer.data)


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()

        month = int(request.query_params.get("month", today.month))
        year = int(request.query_params.get("year", today.year))

        transactions = Transaction.objects.filter(user=request.user)

        total_income = transactions.filter(transaction_type="income").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        total_expense = transactions.filter(transaction_type="expense").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        monthly_expense = transactions.filter(
            transaction_type="expense", date__year=year, date__month=month
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        monthly_income = transactions.filter(
            transaction_type="income", date__year=year, date__month=month
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        monthly_transactions = transactions.filter(date__year=year, date__month=month)

        monthly_transactions_items = TransactionSerializer(
            monthly_transactions, many=True
        )

        data = {
            "total_balance": total_income - total_expense,
            "total_income": total_income,
            "total_expense": total_expense,
            "total_transactions": transactions.count(),
            "monthly_income": monthly_income,
            "monthly_expense": monthly_expense,
            "monthly_transactions_count": monthly_transactions.count(),
            "monthly_transactions_items": monthly_transactions_items.data,
        }

        return Response(data)


class ExpenseByCategoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user)

        expenses_by_category = (
            transactions.filter(transaction_type="expense")
            .values(category_name=F("category__name"))
            .annotate(total_amount=Sum("amount"))
            .order_by("-total_amount")
        )

        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(expenses_by_category, request)

        return paginator.get_paginated_response(result_page)


# isso, só que em sequência
# exemplo: a meta é 1000 reais em alimentação
# - dezembro: 900
# - janeiro: 1400
# - fevereiro: 950
# - março: 700
# - abril: 800

# nesse caso, ele está a 3 meses em sequência batendo a meta, já que janeiro resetou a sequência por estar acima do limite

# TODO: Filtros e Pesquisas
# Objetivo
# Facilitar a consulta das movimentações.

# Filtros
# Período personalizado
# Mês atual
# Últimos 3 meses
# Últimos 6 meses
# Ano atual
# Categoria
# Tipo de transação

# Observação: Somente um filtro deve ser aplicado por vez.


class BudgetListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        budgets = Budget.objects.filter(user=request.user, active=True).order_by(
            "-created_at"
        )
        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(budgets, request)
        serializer = BudgetSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


class BudgetStreakAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id, user=request.user)
            budget_amount = category.budgets.get(active=True).amount
            current_streak = 0

            data = (
                category.transactions.filter(transaction_type="expense")
                .annotate(month=TruncMonth("date"))
                .values("month")
                .annotate(amount=Sum("amount"))
                .order_by("month")
            )

            for obj in data:
                if obj["amount"] <= budget_amount:
                    current_streak += 1
                else:
                    current_streak = 0

            data = {"category": category.name, "current_streak": current_streak}
            return Response(data)

        except Category.DoesNotExist:
            return Response({"error": "Categoria não encontrada."}, status=404)
