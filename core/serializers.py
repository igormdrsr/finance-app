from rest_framework import serializers
from core.models import Transaction, Category, Goal, Budget


class TransactionSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    goal = serializers.StringRelatedField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user",
            "amount",
            "transaction_type",
            "description",
            "date",
            "created_at",
            "category",
            "goal",
        ]
        read_only_fields = ["id", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "user", "name"]
        read_only_fields = ["id"]


class GoalSerializer(serializers.ModelSerializer):
    current_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    current_amount_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = Goal
        fields = [
            "id",
            "user",
            "name",
            "target_amount",
            "current_amount",
            "current_amount_percentage",
        ]
        read_only_fields = ["id", "user"]


class BudgetSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Budget
        fields = ["id", "user", "category", "amount", "active"]
        read_only_fields = ["id", "user"]


class BudgetStreakSerializer(serializers.Serializer):
    month = serializers.DateField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
