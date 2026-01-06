from django.urls import path

from . import views


app_name = "budgeting"

urlpatterns = [
    path("", views.MonthListView.as_view(), name="month_list"),
    path("month/create/", views.create_month_view, name="month_create"),
    path("month/<int:pk>/", views.MonthDetailView.as_view(), name="month_detail"),
    path("month/<int:pk>/close/", views.close_month_view, name="month_close"),
    path("recurring/<int:pk>/edit/", views.recurring_edit_view, name="recurring_edit"),
    path("variable/add/<int:month_id>/", views.variable_add_view, name="variable_add"),
    path("category/add/<int:month_id>/", views.category_add_view, name="category_add"),
    path("category/<int:pk>/edit/", views.category_edit_view, name="category_edit"),
    path("category/<int:pk>/delete/", views.category_delete_view, name="category_delete"),
    path("dashboards/", views.DashboardsView.as_view(), name="dashboards"),
]
