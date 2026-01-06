from decimal import Decimal

from django import forms

from .models import MonthBudget, MonthExpense, MonthCategory, MonthStatus, ExpenseType


class MonthBudgetIncomeForm(forms.ModelForm):
    class Meta:
        model = MonthBudget
        fields = ["net_income"]

    def clean(self):
        cleaned = super().clean()
        mb: MonthBudget = self.instance
        if mb and mb.status == MonthStatus.CLOSED:
            raise forms.ValidationError("Month is closed; income cannot be changed.")
        return cleaned


class MonthExpenseForm(forms.ModelForm):
    class Meta:
        model = MonthExpense
        fields = ["month_category", "name", "amount", "expense_type", "date", "enabled", "notes"]

    def __init__(self, *args, **kwargs):
        month_budget = kwargs.pop("month_budget", None)
        super().__init__(*args, **kwargs)
        if month_budget:
            self.fields["month_category"].queryset = MonthCategory.objects.filter(month_budget=month_budget)

        if self.instance and self.instance.pk:
            mb = self.instance.month_category.month_budget
            if mb.status == MonthStatus.CLOSED:
                for field in self.fields:
                    self.fields[field].disabled = True

    def clean_amount(self):
        amt = self.cleaned_data.get("amount")
        if amt is None:
            return amt
        return Decimal(amt).quantize(Decimal("0.01"))


class MonthCategoryForm(forms.ModelForm):
    class Meta:
        model = MonthCategory
        fields = ["name", "sort_order"]
