from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models, transaction
from django.utils import timezone


class MonthStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"


class ClosedMonthGuardMixin(models.Model):
    """
    Mixin to prevent modifications to budget-affecting models when the month is closed.
    Expects a `month_budget` relation either directly or via `month_category.month_budget`.
    """

    class Meta:
        abstract = True

    def _get_month_budget(self):
        if hasattr(self, "month_budget") and isinstance(self.month_budget, MonthBudget):
            return self.month_budget
        if hasattr(self, "month_category") and isinstance(self.month_category, MonthCategory):
            return self.month_category.month_budget
        return None

    def clean(self):
        mb = self._get_month_budget()
        if mb and mb.status == MonthStatus.CLOSED:
            raise ValidationError("This month is closed and cannot be modified.")
        return super().clean()

    def save(self, *args, **kwargs):
        mb = self._get_month_budget()
        if mb and mb.status == MonthStatus.CLOSED:
            # Allow superusers via explicit override flag
            if not kwargs.pop("admin_override", False):
                raise PermissionDenied("This month is closed and cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        mb = self._get_month_budget()
        if mb and mb.status == MonthStatus.CLOSED:
            if not kwargs.pop("admin_override", False):
                raise PermissionDenied("This month is closed and cannot be modified.")
        return super().delete(*args, **kwargs)


class RecurringExpenseTemplate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200)
    default_amount = models.DecimalField(max_digits=10, decimal_places=2)
    default_category_name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (£{self.default_amount:,.2f})"


class MonthBudget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    month = models.DateField(help_text="Normalized to the first day of the month")
    net_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=MonthStatus.choices, default=MonthStatus.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "month")
        ordering = ["-month"]

    def __str__(self):
        return self.month.strftime("%Y-%m")

    def clean(self):
        # Normalize to first day of month
        if self.month:
            self.month = self.month.replace(day=1)
        return super().clean()

    def save(self, *args, **kwargs):
        if self.pk:
            prev = MonthBudget.objects.filter(pk=self.pk).only("status", "net_income").first()
            if prev and prev.status == MonthStatus.CLOSED and self.net_income != prev.net_income:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Closed month income cannot be modified.")
        return super().save(*args, **kwargs)

    @property
    def total_recurring(self) -> Decimal:
        return (
            self.monthrecurringexpense_set.filter(enabled=True)
            .aggregate(s=models.Sum("amount"))
            .get("s")
            or Decimal("0")
        )

    @property
    def total_variable(self) -> Decimal:
        return (
            MonthVariableExpense.objects.filter(month_category__month_budget=self)
            .aggregate(s=models.Sum("amount"))
            .get("s")
            or Decimal("0")
        )

    @property
    def total_expenses(self) -> Decimal:
        return (self.total_recurring or Decimal("0")) + (self.total_variable or Decimal("0"))

    @property
    def balance(self) -> Decimal:
        return (self.net_income or Decimal("0")) - self.total_expenses

    def close(self):
        self.status = MonthStatus.CLOSED
        self.save(update_fields=["status"]) 


class MonthCategory(ClosedMonthGuardMixin):
    month_budget = models.ForeignKey(MonthBudget, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("month_budget", "name")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.month_budget})"


class MonthRecurringExpense(ClosedMonthGuardMixin):
    month_budget = models.ForeignKey(MonthBudget, on_delete=models.CASCADE, null=True)
    month_category = models.ForeignKey(MonthCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    enabled = models.BooleanField(default=True)
    template = models.ForeignKey(RecurringExpenseTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["month_category__sort_order", "name"]

    def __str__(self):
        return f"{self.name} (£{self.amount:,.2f})"


class MonthVariableExpense(ClosedMonthGuardMixin):
    month_category = models.ForeignKey(MonthCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["month_category", "date"])]
        ordering = ["-date", "name"]

    def clean(self):
        if not self.date:
            # Default to the month date
            self.date = self.month_category.month_budget.month
        return super().clean()


class ForecastOverride(ClosedMonthGuardMixin):
    month_budget = models.ForeignKey(MonthBudget, on_delete=models.CASCADE)
    month_category = models.ForeignKey(MonthCategory, on_delete=models.CASCADE)
    override_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("month_budget", "month_category")


# Services
@transaction.atomic
def create_month_with_defaults(
    month: date,
    user=None,
    carry_forward_income: bool = True,
) -> MonthBudget:
    """Create a MonthBudget, copy last month categories, and seed recurring items from templates.

    If a month already exists, returns it.
    """
    month = month.replace(day=1)
    mb, created = MonthBudget.objects.get_or_create(user=user, month=month)
    if not created:
        return mb

    # Copy category structure from most recent month for this user (if any)
    prev = (
        MonthBudget.objects.filter(user=user, month__lt=month)
        .order_by("-month")
        .first()
    )
    name_to_cat: dict[str, MonthCategory] = {}
    if prev:
        if carry_forward_income:
            mb.net_income = prev.net_income
            mb.save(update_fields=["net_income"]) 
        for cat in prev.monthcategory_set.all().order_by("sort_order", "name"):
            name_to_cat[cat.name] = MonthCategory.objects.create(
                month_budget=mb, name=cat.name, sort_order=cat.sort_order
            )

    # Seed from templates
    templates = RecurringExpenseTemplate.objects.filter(active=True, user=user)
    # Ensure categories for each template exist
    for t in templates:
        cat = name_to_cat.get(t.default_category_name)
        if not cat:
            # Create at the end
            max_order = (
                MonthCategory.objects.filter(month_budget=mb).aggregate(m=models.Max("sort_order")).get("m")
                or 0
            )
            cat = MonthCategory.objects.create(
                month_budget=mb,
                name=t.default_category_name,
                sort_order=max_order + 10,
            )
            name_to_cat[t.default_category_name] = cat
        MonthRecurringExpense.objects.create(
            month_budget=mb,
            month_category=cat,
            name=t.name,
            amount=t.default_amount,
            template=t,
        )

    return mb


@dataclass
class ForecastResult:
    month: date
    recurring_total: Decimal
    variable_estimate: Decimal
    total_expenses: Decimal
    balance: Decimal


def trailing_average_variable(user, up_to_month: date, category_name: str, months: int = 3) -> Decimal:
    """Compute trailing average of variable spend for a named category up to (but not including) a month."""
    up_to = up_to_month.replace(day=1)
    qs = (
        MonthVariableExpense.objects.filter(
            month_category__month_budget__user=user,
            month_category__name=category_name,
            month_category__month_budget__month__lt=up_to,
        )
        .values("month_category__month_budget__month")
        .annotate(total=models.Sum("amount"))
        .order_by("-month_category__month_budget__month")
    )
    totals = [r["total"] for r in qs[:months]]
    if not totals:
        return Decimal("0")
    return sum(totals) / Decimal(len(totals))


def forecast_months(user, start_month: date, horizon: int = 3) -> list[ForecastResult]:
    start = start_month.replace(day=1)
    # Base recurring from latest existing month for the user
    latest = MonthBudget.objects.filter(user=user, month__lte=start).order_by("-month").first()
    recurring_by_cat: dict[str, Decimal] = {}
    if latest:
        for r in latest.monthrecurringexpense_set.filter(enabled=True):
            recurring_by_cat[r.month_category.name] = recurring_by_cat.get(r.month_category.name, Decimal("0")) + r.amount
    results: list[ForecastResult] = []
    for i in range(horizon):
        m = (start.replace(day=15) + timezone.timedelta(days=32 * i)).replace(day=1)
        recurring_total = sum(recurring_by_cat.values()) if recurring_by_cat else Decimal("0")
        # variable baseline: sum of trailing averages per category present in latest
        variable_estimate = Decimal("0")
        for cat_name in recurring_by_cat.keys():
            variable_estimate += trailing_average_variable(user, m, cat_name)
        total_expenses = recurring_total + variable_estimate
        # no income forecasted here; caller can add expected income
        results.append(
            ForecastResult(
                month=m,
                recurring_total=recurring_total,
                variable_estimate=variable_estimate,
                total_expenses=total_expenses,
                balance=Decimal("0") - total_expenses,
            )
        )
    return results
