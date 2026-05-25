from django.urls import path

from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.StockListView.as_view(), name='stock_list'),
    path('stock/<int:pk>/', views.StockDetailView.as_view(), name='stock_detail'),
    path('stock/create/', views.StockCreateView.as_view(), name='stock_create'),
    path('stock/<int:pk>/edit/', views.StockUpdateView.as_view(), name='stock_edit'),
    path('alerts/', views.AlertListView.as_view(), name='alert_list'),
]
