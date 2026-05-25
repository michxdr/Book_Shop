from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('reports/', views.ReportListView.as_view(), name='report_list'),
]
