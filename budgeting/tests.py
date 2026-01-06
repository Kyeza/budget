from django.test import TestCase
from django.contrib.auth.models import User
from budgeting.models import (
    MonthBudget, MonthCategory, MonthStatus, create_month_with_defaults, 
    MonthExpense, ExpenseType, RecurringExpenseTemplate
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
        exp = MonthExpense.objects.create(
            month_budget=mb,
            month_category=cat, 
            name="Test", 
            amount=Decimal("10.00"),
            expense_type=ExpenseType.VARIABLE
        )
        
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
        new_exp = MonthExpense(
            month_budget=mb,
            month_category=cat, 
            name="New", 
            amount=Decimal("20.00"),
            expense_type=ExpenseType.VARIABLE
        )
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
        
        MonthExpense.objects.create(
            month_budget=mb, 
            month_category=cat, 
            name="Rent", 
            amount=Decimal("600.00"),
            expense_type=ExpenseType.RECURRING
        )
        MonthExpense.objects.create(
            month_budget=mb,
            month_category=cat, 
            name="Food", 
            amount=Decimal("50.00"),
            expense_type=ExpenseType.VARIABLE
        )
        MonthExpense.objects.create(
            month_budget=mb,
            month_category=cat, 
            name="Gas", 
            amount=Decimal("30.00"),
            expense_type=ExpenseType.VARIABLE
        )
        
        self.assertEqual(mb.total_recurring, Decimal("600.00"))
        self.assertEqual(mb.total_variable, Decimal("80.00"))
        self.assertEqual(mb.total_expenses, Decimal("680.00"))
        self.assertEqual(mb.balance, Decimal("320.00"))

    def test_expense_carry_forward(self):
        # Test that all expenses carry forward to the next month
        m1 = MonthBudget.objects.create(user=self.user, month=date(2024, 1, 1), net_income=Decimal("2000.00"))
        cat = MonthCategory.objects.create(month_budget=m1, name="Bills")
        
        MonthExpense.objects.create(
            month_budget=m1, 
            month_category=cat, 
            name="Internet", 
            amount=Decimal("50.00"),
            expense_type=ExpenseType.RECURRING
        )
        MonthExpense.objects.create(
            month_budget=m1,
            month_category=cat, 
            name="Gift", 
            amount=Decimal("20.00"),
            expense_type=ExpenseType.VARIABLE
        )
        
        m2 = create_month_with_defaults(month=date(2024, 2, 1), user=self.user)
        
        self.assertEqual(m2.monthexpense_set.count(), 2)
        self.assertEqual(m2.total_recurring, Decimal("50.00"))
        self.assertEqual(m2.total_variable, Decimal("20.00"))
        
        # Internet should still be recurring
        internet = m2.monthexpense_set.get(name="Internet")
        self.assertEqual(internet.expense_type, ExpenseType.RECURRING)
        
        # Gift should still be variable
        gift = m2.monthexpense_set.get(name="Gift")
        self.assertEqual(gift.expense_type, ExpenseType.VARIABLE)
        self.assertEqual(gift.date, date(2024, 2, 1))

class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")
        self.mb = create_month_with_defaults(month=date(2024, 1, 1), user=self.user)
        self.cat = self.mb.monthcategory_set.first()
        if not self.cat:
            self.cat = MonthCategory.objects.create(month_budget=self.mb, name="Test Cat")

    def test_expense_add_view_renders(self):
        from django.urls import reverse
        url = reverse("budgeting:expense_add", kwargs={"month_id": self.mb.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "budgeting/expense_form.html")

    def test_expense_edit_view_renders(self):
        from django.urls import reverse
        exp = MonthExpense.objects.create(
            month_budget=self.mb,
            month_category=self.cat,
            name="Test",
            amount=Decimal("10.00"),
            expense_type=ExpenseType.VARIABLE
        )
        url = reverse("budgeting:expense_edit", kwargs={"pk": exp.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "budgeting/expense_form.html")
