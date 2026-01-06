# 💰 Monthly Budgeting App

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Django Version](https://img.shields.io/badge/django-6.0-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust, production-ready Django web application for personal budgeting. This app replicates and extends the behavior of a traditional "Monthly Budget" spreadsheet with powerful snapshotting and forecasting features.

## ✨ Features

- **📂 Month-Specific Versioning**: Edit, add, or delete categories for a specific month without affecting historical data.
- **🔄 Monthly Recurring Expenses**: Grouped by categories and seeded from global templates.
- **💸 Variable Expense Tracking**: Easily add ad-hoc expenses for any month.
- **📊 Real-time Dashboard**: 
  - 6-month historical trends.
  - Category breakdown (recurring vs variable).
  - Top spending items analysis.
- **📈 Smart Forecasting**: 3-month forecast based on recurring templates and trailing averages of variable spend.
- **🔒 Data Integrity**: Lock months to prevent accidental edits of historical data.
- **💰 Balance Management**: Real-time calculation of totals and remaining balance.

## 🏗️ Architecture: Category Snapshotting

To prevent retroactive changes, the app uses a **snapshotting** approach:
- `MonthCategory` is tied to a `MonthBudget`. When a new month is created, the category structure is cloned from the most recent month.
- This design ensures that renaming or reordering categories in "February" does not change how "January" looks.
- Deleting a category for a month requires reassigning its expenses to another category in that same month, ensuring data integrity.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Django 6.0

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/yourusername/budget-app.git
cd budget-app
pip install -r requirements.txt
```

### 3. Setup Database
Run the migrations and seed default data:
```bash
python manage.py migrate
python manage.py seed_budget
```
*The `seed_budget` command creates a default admin user (`admin`/`admin123`) and populates global templates.*

### 4. Run the App
```bash
python manage.py runserver
```
Access the application at `http://127.0.0.1:8000/`.

## 🧪 Testing
Maintain code quality by running the test suite:
```bash
python manage.py test budgeting
```

## 🔭 Forecasting Logic
The app uses a hybrid forecasting strategy:
- **Recurring Spend**: Sum of all enabled recurring items from the latest month.
- **Variable Spend**: Trailing 3-month average of variable expenses per category.
- **Extensibility**: The logic resides in `budgeting/models.py` and can be easily extended with custom strategies.

## 📁 Project Structure
```text
.
├── budget/             # Project configuration
├── budgeting/          # Core budgeting application
├── templates/          # Global HTML templates
├── manage.py           # Django management script
└── db.sqlite3          # Local database (development)
```

## 🛠️ Tech Stack
- **Backend**: Django (Python)
- **Database**: SQLite (default) / PostgreSQL (supported via environment variables)
- **Frontend**: Django Templates & CSS

## 📜 License
This project is licensed under the MIT License.
