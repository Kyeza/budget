from datetime import date as date_cls

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, DetailView

from django.db import models
from .forms import MonthBudgetIncomeForm, MonthExpenseForm, MonthCategoryForm
from .models import (
    MonthBudget,
    MonthCategory,
    MonthExpense,
    ExpenseType,
    MonthStatus,
    create_month_with_defaults,
    forecast_months,
)


@method_decorator(login_required, name="dispatch")
class MonthListView(ListView):
    model = MonthBudget
    context_object_name = "months"
    template_name = "budgeting/month_list.html"

    def get_queryset(self):
        return MonthBudget.objects.filter(user=self.request.user).order_by("-month")


@method_decorator(login_required, name="dispatch")
class MonthDetailView(DetailView):
    model = MonthBudget
    context_object_name = "month"
    template_name = "budgeting/month_detail.html"

    def get_queryset(self):
        return MonthBudget.objects.filter(user=self.request.user)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.object = self.get_object()
        if self.object.status == MonthStatus.CLOSED:
            return HttpResponseForbidden("Month is closed")
        form = MonthBudgetIncomeForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            messages.success(request, "Income updated.")
            return redirect("budgeting:month_detail", pk=self.object.pk)
        context = self.get_context_data(object=self.object)
        context["income_form"] = form
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        month: MonthBudget = self.object
        ctx["income_form"] = MonthBudgetIncomeForm(instance=month)
        # Group data by category
        categories = MonthCategory.objects.filter(month_budget=month).order_by("sort_order", "name")
        
        expenses = MonthExpense.objects.filter(month_category__month_budget=month).order_by(
            "month_category__sort_order", "expense_type", "name"
        )
        
        recurring_by_cat = {}
        variable_by_cat = {}
        for e in expenses:
            if e.expense_type == ExpenseType.RECURRING:
                recurring_by_cat.setdefault(e.month_category_id, []).append(e)
            else:
                variable_by_cat.setdefault(e.month_category_id, []).append(e)

        rows = []
        for c in categories:
            rows.append({
                "category": c,
                "recurring": recurring_by_cat.get(c.id, []),
                "variable": variable_by_cat.get(c.id, []),
                "recurring_total": sum([x.amount for x in recurring_by_cat.get(c.id, [])]) if recurring_by_cat.get(c.id) else 0,
                "variable_total": sum([x.amount for x in variable_by_cat.get(c.id, [])]) if variable_by_cat.get(c.id) else 0,
            })
        ctx["category_rows"] = rows
        return ctx


@login_required
def create_month_view(request: HttpRequest) -> HttpResponse:
    month_str = request.GET.get("month")
    if month_str:
        try:
            year, mon = month_str.split("-")
            m = date_cls(int(year), int(mon), 1)
        except Exception:
            messages.error(request, "Invalid month format. Use YYYY-MM")
            return redirect("budgeting:month_list")
    else:
        now = timezone.now().date()
        m = now.replace(day=1)
    mb = create_month_with_defaults(month=m, user=request.user)
    messages.success(request, f"Month {mb} ready.")
    return redirect("budgeting:month_detail", pk=mb.pk)


@login_required
def close_month_view(request: HttpRequest, pk: int) -> HttpResponse:
    mb = get_object_or_404(MonthBudget, pk=pk, user=request.user)
    if request.method == "POST":
        mb.close()
        messages.success(request, "Month closed.")
        return redirect("budgeting:month_detail", pk=pk)
    return render(request, "budgeting/confirm_close.html", {"month": mb})


@login_required
def expense_add_view(request: HttpRequest, month_id: int) -> HttpResponse:
    mb = get_object_or_404(MonthBudget, pk=month_id, user=request.user)
    if mb.status == MonthStatus.CLOSED:
        return HttpResponseForbidden("Month is closed")
    if request.method == "POST":
        form = MonthExpenseForm(request.POST, month_budget=mb)
        if form.is_valid():
            v = form.save(commit=False)
            v.month_budget = mb
            # Ensure chosen category belongs to this month
            if v.month_category.month_budget_id != mb.id:
                messages.error(request, "Invalid category selection")
            else:
                v.save()
                messages.success(request, f"{v.get_expense_type_display()} expense added.")
                return redirect("budgeting:month_detail", pk=mb.pk)
    else:
        initial = {}
        if request.GET.get('type') == 'variable':
            initial['expense_type'] = ExpenseType.VARIABLE
        cat_id = request.GET.get('category')
        if cat_id:
            initial['month_category'] = cat_id
        form = MonthExpenseForm(month_budget=mb, initial=initial)
    return render(request, "budgeting/expense_form.html", {"form": form, "month": mb})


@login_required
def expense_edit_view(request: HttpRequest, pk: int) -> HttpResponse:
    e = get_object_or_404(MonthExpense, pk=pk, month_category__month_budget__user=request.user)
    mb = e.month_category.month_budget
    if mb.status == MonthStatus.CLOSED:
        return HttpResponseForbidden("Month is closed")
    if request.method == "POST":
        form = MonthExpenseForm(request.POST, instance=e)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated.")
            return redirect("budgeting:month_detail", pk=mb.pk)
    else:
        form = MonthExpenseForm(instance=e)
    return render(request, "budgeting/expense_form.html", {"form": form, "item": e, "month": mb})


@login_required
def expense_toggle_type_view(request: HttpRequest, pk: int) -> HttpResponse:
    expense = get_object_or_404(MonthExpense, pk=pk, month_category__month_budget__user=request.user)
    month = expense.month_category.month_budget
    if month.status == MonthStatus.CLOSED:
        return HttpResponseForbidden("Month is closed")

    if expense.expense_type == ExpenseType.RECURRING:
        expense.expense_type = ExpenseType.VARIABLE
        expense.date = month.month
    else:
        expense.expense_type = ExpenseType.RECURRING
        expense.date = None

    expense.save()
    messages.success(request, f"Item '{expense.name}' changed to {expense.get_expense_type_display()}.")
    return redirect("budgeting:month_detail", pk=month.id)


@login_required
def category_add_view(request: HttpRequest, month_id: int) -> HttpResponse:
    mb = get_object_or_404(MonthBudget, pk=month_id, user=request.user)
    if mb.status == MonthStatus.CLOSED:
        return HttpResponseForbidden("Month is closed")
    if request.method == "POST":
        form = MonthCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.month_budget = mb
            cat.save()
            messages.success(request, "Category added.")
            return redirect("budgeting:month_detail", pk=mb.pk)
    else:
        form = MonthCategoryForm()
    return render(request, "budgeting/category_form.html", {"form": form, "month": mb})


@login_required
def category_edit_view(request: HttpRequest, pk: int) -> HttpResponse:
    cat = get_object_or_404(MonthCategory, pk=pk, month_budget__user=request.user)
    mb = cat.month_budget
    if mb.status == MonthStatus.CLOSED:
        return HttpResponseForbidden("Month is closed")
    if request.method == "POST":
        form = MonthCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return redirect("budgeting:month_detail", pk=mb.pk)
    else:
        form = MonthCategoryForm(instance=cat)
    return render(request, "budgeting/category_form.html", {"form": form, "month": mb, "category": cat})


@login_required
def category_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    cat = get_object_or_404(MonthCategory, pk=pk, month_budget__user=request.user)
    mb = cat.month_budget
    if mb.status == MonthStatus.CLOSED:
        return HttpResponseForbidden("Month is closed")
    
    # Check if there are expenses in this category
    has_expenses = cat.monthexpense_set.exists()
    
    if request.method == "POST":
        reassign_to_id = request.POST.get("reassign_to")
        if has_expenses and not reassign_to_id:
            messages.error(request, "You must reassign expenses before deleting this category.")
        else:
            if reassign_to_id:
                target_cat = get_object_or_404(MonthCategory, pk=reassign_to_id, month_budget=mb)
                cat.monthexpense_set.update(month_category=target_cat)
            cat.delete()
            messages.success(request, "Category deleted.")
            return redirect("budgeting:month_detail", pk=mb.pk)
            
    other_categories = mb.monthcategory_set.exclude(pk=cat.pk)
    return render(request, "budgeting/category_confirm_delete.html", {
        "category": cat, 
        "month": mb,
        "has_expenses": has_expenses,
        "other_categories": other_categories
    })


@method_decorator(login_required, name="dispatch")
class DashboardsView(View):
    template_name = "budgeting/dashboards.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        # Last 6 months trend
        months = MonthBudget.objects.filter(user=request.user).order_by("-month")[:6]
        trend = [
            {
                "month": m,
                "income": m.net_income,
                "recurring": m.total_recurring,
                "variable": m.total_variable,
                "total": m.total_expenses,
                "balance": m.balance,
            }
            for m in reversed(list(months))
        ]
        # Forecast next 3 months based on latest month
        now_month = timezone.now().date().replace(day=1)
        forecast = forecast_months(request.user, now_month, horizon=3)

        # Top spending items (variable)
        top_variable = (
            MonthExpense.objects.filter(
                month_category__month_budget__user=request.user,
                expense_type=ExpenseType.VARIABLE
            )
            .values("name")
            .annotate(total=models.Sum("amount"))
            .order_by("-total")[:10]
        )

        # Breakdown by category (current month or latest)
        latest = months.first()
        category_breakdown = []
        if latest:
            for cat in latest.monthcategory_set.all():
                rec = (
                    cat.monthexpense_set.filter(enabled=True, expense_type=ExpenseType.RECURRING)
                    .aggregate(s=models.Sum("amount"))
                    .get("s")
                    or 0
                )
                var = (
                    cat.monthexpense_set.filter(expense_type=ExpenseType.VARIABLE)
                    .aggregate(s=models.Sum("amount"))
                    .get("s")
                    or 0
                )
                category_breakdown.append({
                    "name": cat.name,
                    "recurring": rec,
                    "variable": var,
                    "total": rec + var,
                })

        return render(request, self.template_name, {
            "trend": trend, 
            "forecast": forecast,
            "top_variable": top_variable,
            "category_breakdown": category_breakdown,
            "latest_month": latest
        })
