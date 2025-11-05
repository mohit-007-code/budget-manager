from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Income & Expenses
    path('add-income/', views.add_income_view, name='add_income'),
    path('add-expense/', views.add_expense_view, name='add_expense'),
    path('expenses/', views.all_expenses_view, name='all_expenses'),
    path('incomes/', views.all_incomes_view, name='all_incomes'),
    
    # Delete operations
    path('expense/delete/<int:expense_id>/', views.delete_expense_view, name='delete_expense'),
    path('income/delete/<int:income_id>/', views.delete_income_view, name='delete_income'),
    
    # Reports
    path('yearly-report/', views.yearly_report_view, name='yearly_report'),
    path('yearly-report/<int:year>/', views.yearly_report_view, name='yearly_report_year'),
    path('compare-months/', views.compare_months_view, name='compare_months'),
    path('monthly-report/download/', views.monthly_report_pdf, name='monthly_report_pdf'),
]
