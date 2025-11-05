from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from calendar import month_name

import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from django.http import HttpResponse

from .models import Income, Expense, ExpenseCategory, Budget


@login_required
def dashboard_view(request):
    """Main dashboard showing selected month summary. Future months show zeros."""
    now = timezone.now()

    # Read selected month/year from GET (fall back to current)
    try:
        selected_month = int(request.GET.get('month', now.month))
    except (TypeError, ValueError):
        selected_month = now.month

    try:
        selected_year = int(request.GET.get('year', now.year))
    except (TypeError, ValueError):
        selected_year = now.year

    # Determine if selected is in the future
    is_future = (selected_year > now.year) or (selected_year == now.year and selected_month > now.month)

    if is_future:
        current_income = Decimal('0.00')
        current_expenses = Decimal('0.00')
        remaining = Decimal('0.00')
        expenses_by_category = []
        recent_expenses = Expense.objects.none()
        recent_incomes = Income.objects.none()
    else:
        # Query selected month/year
        current_income = Income.objects.filter(
            user=request.user,
            date__month=selected_month,
            date__year=selected_year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        current_expenses = Expense.objects.filter(
            user=request.user,
            date__month=selected_month,
            date__year=selected_year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        remaining = current_income - current_expenses

        expenses_by_category = Expense.objects.filter(
            user=request.user,
            date__month=selected_month,
            date__year=selected_year
        ).values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total')

        recent_expenses = Expense.objects.filter(
            user=request.user,
            date__month=selected_month,
            date__year=selected_year
        ).order_by('-date', '-id')

        recent_incomes = Income.objects.filter(
            user=request.user,
            date__month=selected_month,
            date__year=selected_year
        ).order_by('-date')[:5]

    # Available years from both incomes and expenses
    income_years = {d.year for d in Income.objects.filter(user=request.user).dates('date', 'year')}
    expense_years = {d.year for d in Expense.objects.filter(user=request.user).dates('date', 'year')}
    years_set = sorted(list(income_years.union(expense_years)))
    if not years_set:
        years_set = [now.year]

    context = {
        'current_month': month_name[selected_month],
        'current_month_num': selected_month,
        'current_year': selected_year,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'total_income': current_income,
        'total_expenses': current_expenses,
        'remaining': remaining,
        'expenses_by_category': expenses_by_category,
        'recent_expenses': recent_expenses,
        'recent_incomes': recent_incomes,
        # months and years for the report selector
        'months': [(i, month_name[i]) for i in range(1, 13)],
        'available_years': years_set,
    }

    return render(request, 'budgets/dashboard.html', context)


@login_required
def monthly_report_pdf(request):
    """Generate a PDF monthly report for the selected month/year and return as attachment."""
    # Accept month and year via GET parameters
    try:
        month = int(request.GET.get('month', timezone.now().month))
    except (TypeError, ValueError):
        month = timezone.now().month

    try:
        year = int(request.GET.get('year', timezone.now().year))
    except (TypeError, ValueError):
        year = timezone.now().year

    # Query data
    incomes = Income.objects.filter(user=request.user, date__month=month, date__year=year).order_by('-date')
    expenses = Expense.objects.filter(user=request.user, date__month=month, date__year=year).order_by('-date')

    total_income = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    balance = total_income - total_expenses

    # Create PDF using ReportLab Platypus for clean tables
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph(f"Monthly Report - {month_name[month]} {year}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))

    # Summary table
    summary_data = [
        ['User', request.user.username],
        ['Total Income', f'₹{total_income:,.2f}'],
        ['Total Expenses', f'₹{total_expenses:,.2f}'],
        ['Balance', f'₹{balance:,.2f}'],
    ]
    summary_table = Table(summary_data, colWidths=[4*cm, 10*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # Incomes table
    story.append(Paragraph('Incomes', styles['Heading3']))
    inc_table_data = [['Date', 'Source', 'Amount']]
    for inc in incomes:
        inc_table_data.append([inc.date.strftime('%d %b %Y'), inc.source or '', f'₹{inc.amount:,.2f}'])
    if len(inc_table_data) == 1:
        inc_table_data.append(['-', 'No incomes for this month.', '-'])

    inc_table = Table(inc_table_data, colWidths=[3*cm, 8*cm, 3*cm])
    inc_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(inc_table)
    story.append(Spacer(1, 12))

    # Expenses table
    story.append(Paragraph('Expenses', styles['Heading3']))
    exp_table_data = [['Date', 'Category / Title', 'Amount']]
    for exp in expenses:
        cat = exp.category.name if getattr(exp, 'category', None) else exp.title
        exp_table_data.append([exp.date.strftime('%d %b %Y'), cat, f'₹{exp.amount:,.2f}'])
    if len(exp_table_data) == 1:
        exp_table_data.append(['-', 'No expenses for this month.', '-'])

    exp_table = Table(exp_table_data, colWidths=[3*cm, 8*cm, 3*cm])
    exp_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(exp_table)

    # Build PDF
    doc.build(story)

    buffer.seek(0)
    filename = f"monthly_report_{year}_{month}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def add_income_view(request):
    """Add new income"""
    if request.method == 'POST':
        amount = request.POST.get('amount')
        source = request.POST.get('source')
        description = request.POST.get('description', '')
        date = request.POST.get('date')
        
        Income.objects.create(
            user=request.user,
            amount=Decimal(amount),
            source=source,
            description=description,
            date=date or timezone.now()
        )
        messages.success(request, 'Income added successfully!')
        return redirect('dashboard')
    
    # Get context for the page
    now = timezone.now()
    
    # Get current month data for summary card
    total_income = Income.objects.filter(
        user=request.user,
        date__month=now.month,
        date__year=now.year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_expenses = Expense.objects.filter(
        user=request.user,
        date__month=now.month,
        date__year=now.year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    recent_incomes = Income.objects.filter(user=request.user)[:5]
    
    context = {
        'current_month': month_name[now.month],
        'total_income': total_income,
        'total_expenses': total_expenses,
        'remaining': total_income - total_expenses,
        'recent_incomes': recent_incomes,
    }
    
    return render(request, 'budgets/add_income.html', context)


@login_required
def add_expense_view(request):
    """Add new expense"""
    categories = ExpenseCategory.objects.all()
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        description = request.POST.get('description', '')
        date = request.POST.get('date')
        
        category = get_object_or_404(ExpenseCategory, id=category_id)
        
        Expense.objects.create(
            user=request.user,
            amount=Decimal(amount),
            title=title,
            category=category,
            description=description,
            date=date or timezone.now()
        )
        messages.success(request, 'Expense added successfully!')
        return redirect('dashboard')
    
    # Get recent expenses for sidebar
    recent_expenses = Expense.objects.filter(user=request.user)[:5]
    
    now = timezone.now()
    
    context = {
        'categories': categories,
        'recent_expenses': recent_expenses,
        'current_month': month_name[now.month],
    }
    
    return render(request, 'budgets/add_expense.html', context)


@login_required
def all_expenses_view(request):
    """View all expenses"""
    expenses = Expense.objects.filter(user=request.user)
    
    # Get total
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
    }
    
    return render(request, 'budgets/all_expenses.html', context)


@login_required
def all_incomes_view(request):
    """View all incomes"""
    # Show newest incomes first
    incomes = Income.objects.filter(user=request.user).order_by('-date', '-id')
    
    # Get total
    total_incomes = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'incomes': incomes,
        'total_incomes': total_incomes,
    }
    
    return render(request, 'budgets/all_incomes.html', context)


@login_required
def delete_expense_view(request, expense_id):
    """Delete an expense"""
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    expense.delete()
    messages.success(request, 'Expense deleted successfully!')
    return redirect('all_expenses')


@login_required
def delete_income_view(request, income_id):
    """Delete an income"""
    income = get_object_or_404(Income, id=income_id, user=request.user)
    income.delete()
    messages.success(request, 'Income deleted successfully!')
    return redirect('all_incomes')


@login_required
def compare_months_view(request):
    """Compare current month with last month - Shows Last Month List"""
    now = timezone.now()
    current_month = now.month
    current_year = now.year
    
    # Calculate last month
    if current_month == 1:
        last_month = 12
        last_year = current_year - 1
    else:
        last_month = current_month - 1
        last_year = current_year
    
    # Current month data
    current_income = Income.objects.filter(
        user=request.user,
        date__month=current_month,
        date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    current_expenses = Expense.objects.filter(
        user=request.user,
        date__month=current_month,
        date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    current_by_category = Expense.objects.filter(
        user=request.user,
        date__month=current_month,
        date__year=current_year
    ).values('category__name', 'category__id').annotate(
        total=Sum('amount')
    )
    
    # Last month data
    last_income = Income.objects.filter(
        user=request.user,
        date__month=last_month,
        date__year=last_year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    last_expenses = Expense.objects.filter(
        user=request.user,
        date__month=last_month,
        date__year=last_year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    last_by_category = Expense.objects.filter(
        user=request.user,
        date__month=last_month,
        date__year=last_year
    ).values('category__name', 'category__id').annotate(
        total=Sum('amount')
    )
    
    # Get all last month expenses for the list
    last_month_expenses = Expense.objects.filter(
        user=request.user,
        date__month=last_month,
        date__year=last_year
    ).order_by('-date')
    
    # Create category comparison
    categories = ExpenseCategory.objects.all()
    category_comparison = []
    
    for category in categories:
        current_cat_expense = next(
            (item['total'] for item in current_by_category if item['category__name'] == category.name),
            Decimal('0.00')
        )
        last_cat_expense = next(
            (item['total'] for item in last_by_category if item['category__name'] == category.name),
            Decimal('0.00')
        )
        
        difference = current_cat_expense - last_cat_expense
        if last_cat_expense > 0:
            percentage_change = (difference / last_cat_expense) * 100
        else:
            percentage_change = 100 if current_cat_expense > 0 else 0
        
        category_comparison.append({
            'category': category.get_name_display(),
            'current': current_cat_expense,
            'last': last_cat_expense,
            'difference': difference,
            'percentage_change': percentage_change
        })
    
    context = {
        'current_month': month_name[current_month],
        'current_year': current_year,
        'last_month': month_name[last_month],
        'last_year': last_year,
        'current_income': current_income,
        'current_expenses': current_expenses,
        'current_balance': current_income - current_expenses,
        'last_income': last_income,
        'last_expenses': last_expenses,
        'last_balance': last_income - last_expenses,
        'category_comparison': category_comparison,
        'last_month_expenses': last_month_expenses,  # For the list
    }
    
    return render(request, 'budgets/compare_months.html', context)


@login_required
def yearly_report_view(request, year=None):
    """View yearly expenses report"""
    if year is None:
        year = timezone.now().year
    
    # Get total income for the year
    yearly_income = Income.objects.filter(
        user=request.user,
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Get total expenses for the year
    yearly_expenses = Expense.objects.filter(
        user=request.user,
        date__year=year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Get expenses by category
    expenses_by_category = Expense.objects.filter(
        user=request.user,
        date__year=year
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Get monthly breakdown
    monthly_data = []
    for month in range(1, 13):
        month_income = Income.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        month_expenses = Expense.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        monthly_data.append({
            'month': month_name[month],
            'month_num': month,
            'income': month_income,
            'expenses': month_expenses,
            'balance': month_income - month_expenses
        })
    
    # Available years for dropdown
    available_years = Expense.objects.filter(user=request.user).dates('date', 'year')
    years_list = [d.year for d in available_years]
    if not years_list:
        years_list = [timezone.now().year]
    
    context = {
        'year': year,
        'yearly_income': yearly_income,
        'yearly_expenses': yearly_expenses,
        'yearly_balance': yearly_income - yearly_expenses,
        'expenses_by_category': expenses_by_category,
        'monthly_data': monthly_data,
        'available_years': years_list,
    }
    
    return render(request, 'budgets/yearly_report.html', context)
