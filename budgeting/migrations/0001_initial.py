from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurringExpenseTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('default_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('default_category_name', models.CharField(max_length=200)),
                ('notes', models.TextField(blank=True)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='MonthBudget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField(help_text='Normalized to the first day of the month')),
                ('net_income', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-month']},
        ),
        migrations.CreateModel(
            name='MonthCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('month_budget', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budgeting.monthbudget')),
            ],
            options={'ordering': ['sort_order', 'name']},
        ),
        migrations.CreateModel(
            name='MonthRecurringExpense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('enabled', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True)),
                ('month_category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budgeting.monthcategory')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='budgeting.recurringexpensetemplate')),
            ],
            options={'ordering': ['month_category__sort_order', 'name']},
        ),
        migrations.CreateModel(
            name='MonthVariableExpense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('month_category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budgeting.monthcategory')),
            ],
            options={'ordering': ['-date', 'name']},
        ),
        migrations.CreateModel(
            name='ForecastOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('override_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('month_budget', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budgeting.monthbudget')),
                ('month_category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budgeting.monthcategory')),
            ],
        ),
        migrations.AddIndex(
            model_name='monthvariableexpense',
            index=models.Index(fields=['month_category', 'date'], name='budgeting_m_month_ca_676d07_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='recurringexpensetemplate',
            unique_together={('user', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='monthbudget',
            unique_together={('user', 'month')},
        ),
        migrations.AlterUniqueTogether(
            name='monthcategory',
            unique_together={('month_budget', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='forecastoverride',
            unique_together={('month_budget', 'month_category')},
        ),
    ]
