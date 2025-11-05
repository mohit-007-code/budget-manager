from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class ExpenseCategory(models.Model):
    """Categories for expenses"""
    ENTERTAINMENT = 'entertainment'
    EATING_OUT = 'eating_out'
    CLOTHING = 'clothing'
    TRAVEL = 'travel'
    BILLS_RENT = 'bills_rent'
    PERSONAL_CARE = 'personal_care'
    OTHERS = 'others'
    
    CATEGORY_CHOICES = [
        (ENTERTAINMENT, 'Entertainment'),
        (EATING_OUT, 'Eating Out'),
        (CLOTHING, 'Clothing & Shoes'),
        (TRAVEL, 'Travel'),
        (BILLS_RENT, 'Bills & Rent'),
        (PERSONAL_CARE, 'Personal Care'),
        (OTHERS, 'Others'),
    ]
    
    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.get_name_display()
    
    class Meta:
        verbose_name_plural = "Expense Categories"


class Income(models.Model):
    """User's income records"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.source} - ₹{self.amount}"
    
    class Meta:
        ordering = ['-date']


class Expense(models.Model):
    """User's expense records"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.title} - ₹{self.amount}"
    
    class Meta:
        ordering = ['-date']


class Budget(models.Model):
    """Monthly budget for each category"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.IntegerField()  # 1-12
    year = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.month}/{self.year}"
    
    class Meta:
        unique_together = ['user', 'category', 'month', 'year']
        ordering = ['-year', '-month']
