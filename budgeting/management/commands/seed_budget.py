import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from budgeting.models import RecurringExpenseTemplate, create_month_with_defaults
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

        data_file = os.path.join(settings.BASE_DIR, 'seed_data.json')
        example_file = os.path.join(settings.BASE_DIR, 'seed_data.example.json')

        if os.path.exists(data_file):
            path = data_file
            self.stdout.write(self.style.SUCCESS(f'Using {path} for seeding'))
        elif os.path.exists(example_file):
            path = example_file
            self.stdout.write(self.style.WARNING(f'seed_data.json not found, using example data from {path}'))
        else:
            self.stdout.write(self.style.ERROR('No seed data file found (seed_data.json or seed_data.example.json)'))
            return

        with open(path, 'r') as f:
            data = json.load(f)

        for cat_data in data.get('categories', []):
            cat_name = cat_data.get('name')
            for item in cat_data.get('items', []):
                RecurringExpenseTemplate.objects.get_or_create(
                    user=user,
                    name=item.get('name'),
                    defaults={
                        'default_amount': Decimal(str(item.get('amount'))),
                        'default_category_name': cat_name,
                        'active': True
                    }
                )

        # Create an example month budget
        today = date.today().replace(day=1)
        mb = create_month_with_defaults(month=today, user=user)
        mb.net_income = Decimal(str(data.get('net_income', "0.00")))
        mb.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded budget data from {os.path.basename(path)}'))
