from django.test import TestCase
from django.contrib.auth.models import User
from budgeting.models import (
    MonthBudget, MonthCategory, MonthStatus, create_month_with_defaults, 
    MonthRecurringExpense, MonthVariableExpense, RecurringExpenseTemplate
)
from decimal import Decimal
from datetime import date
from django.core.exceptions import PermissionDenied

class BudgetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

    def test_month_closing_prevents_edits(self):
        mb = create_month_with_defaults(month=date(2024, 1, 1), user=self.user)
        cat = mb.monthcategory_set.first()
        if not cat:
            cat = MonthCategory.objects.create(month_budget=mb, name="Test Cat")
        
        # Open month - can add expense
        exp = MonthVariableExpense.objects.create(month_category=cat, name="Test", amount=Decimal("10.00"))
        
        # Close month
        mb.status = MonthStatus.CLOSED
        mb.save()
        
        # Try to modify existing expense
        exp.name = "Modified"
        with self.assertRaises(PermissionDenied):
            exp.save()
            
        # Try to delete expense
        with self.assertRaises(PermissionDenied):
            exp.delete()
            
        # Try to add new expense
        new_exp = MonthVariableExpense(month_category=cat, name="New", amount=Decimal("20.00"))
        with self.assertRaises(PermissionDenied):
            new_exp.save()

    def test_category_snapshot_isolation(self):
        # Create templates so that create_month_with_defaults has categories to copy
        cat_name = "Isolation Test Cat"
        RecurringExpenseTemplate.objects.create(
            user=self.user,
            name="Template",
            default_amount=Decimal("100.00"),
            default_category_name=cat_name
        )
        
        m1 = create_month_with_defaults(month=date(2024, 1, 1), user=self.user)
        m2 = create_month_with_defaults(month=date(2024, 2, 1), user=self.user)
        
        # Categories should be different objects
        c1 = m1.monthcategory_set.get(name=cat_name)
        c2 = m2.monthcategory_set.get(name=cat_name)
        
        self.assertNotEqual(c1.id, c2.id)
        
        # Renaming c1 should not affect c2
        c1.name = "Renamed Category"
        c1.save()
        
        c2.refresh_from_db()
        self.assertEqual(c2.name, cat_name)

    def test_totals_correctness(self):
        mb = MonthBudget.objects.create(user=self.user, month=date(2024, 1, 1), net_income=Decimal("1000.00"))
        cat = MonthCategory.objects.create(month_budget=mb, name="General")
        
        MonthRecurringExpense.objects.create(month_budget=mb, month_category=cat, name="Rent", amount=Decimal("600.00"))
        MonthVariableExpense.objects.create(month_category=cat, name="Food", amount=Decimal("50.00"))
        MonthVariableExpense.objects.create(month_category=cat, name="Gas", amount=Decimal("30.00"))
        
        self.assertEqual(mb.total_recurring, Decimal("600.00"))
        self.assertEqual(mb.total_variable, Decimal("80.00"))
        self.assertEqual(mb.total_expenses, Decimal("680.00"))
        self.assertEqual(mb.balance, Decimal("320.00"))
