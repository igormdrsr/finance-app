from django.urls import path
from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("categories/", views.CategoryListCreate.as_view(), name="category-list-create"),
    path("budgets/", views.BudgetListAPIView.as_view(), name="budgets"),
    path("dashboard/", views.DashboardAPIView.as_view(), name="dashboard-api"),
    path("goals/", views.GoalListAPIView.as_view(), name="goals-list"),
    path("expenses-by-category/", views.ExpenseByCategoryAPIView.as_view(), name="expenses-by-category"),
    path("category/<int:category_id>/statistics/", views.BudgetStreakAPIView.as_view(), name="budget-streak"),
    path("transactions/", views.TransactionList.as_view(), name="transactions")
]

# GET /budgets/5/statistics/