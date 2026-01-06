from django.contrib import admin

from .models import (
    MonthBudget,
    MonthCategory,
    MonthExpense,
    RecurringExpenseTemplate,
    ForecastOverride,
    MonthStatus,
)


class MonthExpenseInline(admin.TabularInline):
    model = MonthExpense
    extra = 0


@admin.register(MonthCategory)
class MonthCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "month_budget", "sort_order")
    list_filter = ("month_budget",)
    search_fields = ("name",)
    inlines = [MonthExpenseInline]


@admin.register(MonthBudget)
class MonthBudgetAdmin(admin.ModelAdmin):
    list_display = ("month", "user", "status", "net_income", "total_recurring", "total_variable", "balance")
    list_filter = ("status", "user")
    date_hierarchy = "month"
    readonly_fields = ("created_at", "updated_at")


@admin.register(MonthExpense)
class MonthExpenseAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "expense_type", "enabled", "month_category")
    list_filter = ("expense_type", "enabled", "month_category__month_budget")
    search_fields = ("name",)


@admin.register(RecurringExpenseTemplate)
class RecurringExpenseTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "default_amount", "default_category_name", "active", "user")
    list_filter = ("active",)
    search_fields = ("name", "default_category_name")


@admin.register(ForecastOverride)
class ForecastOverrideAdmin(admin.ModelAdmin):
    list_display = ("month_budget", "month_category", "override_amount")
    list_filter = ("month_budget",)
