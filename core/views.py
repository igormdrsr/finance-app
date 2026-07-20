from django.shortcuts import render, get_object_or_404
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
from django.utils.dateparse import parse_date
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
)

from decimal import Decimal
from dateutil.relativedelta import relativedelta


class HomeView(View):
    def get(self, request):
        context = {"message": "Hello, world!"}
        return render(request, "home.html", context)


class CategoryListCreate(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = Category.objects.filter(user=request.user).order_by("name")
        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(categories, request)
        serializer = CategorySerializer(result_page, many=True)

        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
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

        transactions = Transaction.objects.filter(user=request.user)

        month = int(request.query_params.get("month", today.month))
        year = int(request.query_params.get("year", today.year))

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

        monthly_transactions = transactions.filter(
            date__year=year, date__month=month
        ).select_related("category", "goal")

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


class TransactionList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        transactions = (
            Transaction.objects.filter(user=request.user)
            .select_related("category", "goal")
            .order_by("-date")
        )

        period = request.query_params.get("period")

        valid_period = {
            "current_month",
            "last_3_months",
            "last_6_months",
            "current_year",
            "custom",
        }

        if period is not None:
            period = period.strip()

            # ?period= pode retornar uma string vazia e eu optei por tratar isso como inválido.
            if not period:
                return Response(
                    {"detail": "Period cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if period not in valid_period:
                return Response(
                    {"detail": "Invalid filter."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if period == "current_month":
                transactions = transactions.filter(
                    date__year=today.year, date__month=today.month
                )

            elif period == "last_3_months":
                transactions = transactions.filter(
                    date__gte=today - relativedelta(months=3)
                )

            elif period == "last_6_months":
                transactions = transactions.filter(
                    date__gte=today - relativedelta(months=6)
                )

            elif period == "current_year":
                transactions = transactions.filter(date__year=today.year)

            elif period == "custom":
                start_date = request.query_params.get("start_date")
                end_date = request.query_params.get("end_date")

                if not start_date or not end_date:
                    return Response(
                        {"detail": "start_date and end_date are required."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                start_date = parse_date(start_date)
                end_date = parse_date(end_date)
                if start_date is None or end_date is None:
                    return Response(
                        {
                            "detail": "start_date and end_date must be in YYYY-MM-DD format."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if start_date > end_date:
                    return Response(
                        {
                            "detail": "start_date must be less than or equal to end_date."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                transactions = transactions.filter(date__range=[start_date, end_date])

        category_id = request.query_params.get("category_id")
        if category_id is not None:
            category_id = category_id.strip()

            if not category_id:
                return Response(
                    {"detail": "Category ID cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            transactions = transactions.filter(category_id=category_id)

        transaction_type = request.query_params.get("transaction_type")
        if transaction_type is not None:
            transaction_type = transaction_type.strip()
            if not transaction_type:
                return Response(
                    {"detail": "transaction_type cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            valid_types = dict(Transaction.TRANSACTION_TYPES).keys()

            if transaction_type not in valid_types:
                return Response(
                    {"detail": "transaction_type must be 'income' or 'expense'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            transactions = transactions.filter(transaction_type=transaction_type)

        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class BudgetListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        budgets = (
            Budget.objects.filter(user=request.user, active=True)
            .order_by("-created_at")
            .select_related("category")
        )
        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(budgets, request)
        serializer = BudgetSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


class BudgetStreakAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id, user=request.user)
        budget = get_object_or_404(Budget, category=category, active=True)

        current_streak = 0

        monthly_expenses = (
            category.transactions.filter(transaction_type="expense")
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(amount=Sum("amount"))
            .order_by("month")
        )

        for expense in monthly_expenses:
            if expense["amount"] <= budget.amount:
                current_streak += 1
            else:
                current_streak = 0

        data = {
            "category": category.name,
            "budget": budget.amount,
            "current_streak": current_streak,
        }
        return Response(data)
