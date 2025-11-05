from django.contrib import admin
from .models import ExpenseCategory, Income, Expense, Budget


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['user', 'source', 'amount', 'date', 'created_at']
    list_filter = ['date', 'user']
    search_fields = ['source', 'description']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'category', 'amount', 'date', 'created_at']
    list_filter = ['category', 'date', 'user']
    search_fields = ['title', 'description']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'amount', 'month', 'year']
    list_filter = ['category', 'month', 'year', 'user']
    readonly_fields = ['created_at', 'updated_at']
