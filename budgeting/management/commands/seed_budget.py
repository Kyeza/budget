from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from budgeting.models import RecurringExpenseTemplate, MonthBudget, create_month_with_defaults
from decimal import Decimal
from datetime import date

class Command(BaseCommand):
    help = 'Seeds the database with default categories and recurring expenses'

    def handle(self, *args, **options):
        # Create a default user if none exists
        user, created = User.objects.get_or_create(username='admin')
        if created:
            user.set_password('admin123')
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))

        seed_data = [
            ("House Expenses", [
                ("Rent", 675.00),
                ("No Deposit Scheme", 30.00),
                ("House Bills", 247.86),
                ("Road Tax", 17.06),
            ]),
            ("Loans", [
                ("118118 Loan", 72.04),
                ("Finio Loan", 64.74),
                ("Abound Loan", 129.75),
            ]),
            ("Personal Handouts", [
                ("Mum", 210.00),
                ("Jowi Rent", 135.00),
                ("Jowi Internet", 21.00),
                ("Jowi Upkeep", 41.00),
            ]),
            ("Other", [
                ("Admiral Car Insurance", 135.93),
                ("Phone bill", 18.91),
                ("Creation finance", 59.71),
                ("Car finance", 364.48),
            ]),
            ("Savings", [
                ("Joint Account", 200.00),
            ]),
            ("Subscriptions", [
                ("Plum", 9.99),
                ("YouTube", 20.00),
                ("Now TV HD Extra", 9.00),
                ("Now TV", 34.99),
                ("JetBrains AI", 22.34),
                ("Amazon Prime", 8.99),
                ("LinkedIn Premium", 29.99),
                ("NordVpn", 11.99),
                ("Obsidian Sync", 3.87),
                ("ChatGPT", 20.00),
            ]),
        ]

        for cat_name, items in seed_data:
            for item_name, amount in items:
                RecurringExpenseTemplate.objects.get_or_create(
                    user=user,
                    name=item_name,
                    defaults={
                        'default_amount': Decimal(str(amount)),
                        'default_category_name': cat_name,
                        'active': True
                    }
                )

        # Create an example month budget
        today = date.today().replace(day=1)
        mb = create_month_with_defaults(month=today, user=user)
        mb.net_income = Decimal("4319.38")
        mb.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded budget data'))
