import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import F, Sum
from django.views.generic import ListView, TemplateView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inventory.models import StockItem
from inventory.permissions import IsWarehouseManager
from .models import WeeklyStockReport
from .serializers import StockSummarySerializer, WeeklyStockReportSerializer

logger = logging.getLogger('analytics')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cache_key = 'analytics_dashboard'
        data = cache.get(cache_key)
        if data is None:
            items = list(StockItem.objects.all())
            data = {
                'total_items': len(items),
                'total_quantity': sum(i.quantity for i in items),
                'low_stock_items': [i for i in items if i.is_low_stock],
                'out_of_stock_items': [i for i in items if i.is_out_of_stock],
                'inventory_value': sum(i.quantity * i.unit_cost for i in items),
            }
            cache.set(cache_key, data, 60 * 5)
        ctx.update(data)
        ctx['recent_reports'] = WeeklyStockReport.objects.order_by('-week_start')[:5]
        return ctx


class ReportListView(LoginRequiredMixin, ListView):
    model = WeeklyStockReport
    template_name = 'analytics/report_list.html'
    context_object_name = 'reports'
    paginate_by = 10


class WeeklyReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WeeklyStockReport.objects.all()
    serializer_class = WeeklyStockReportSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-week_start']

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        cache_key = 'api_stock_summary'
        data = cache.get(cache_key)
        if data is None:
            items = list(StockItem.objects.all())
            low_stock = [i for i in items if i.is_low_stock]
            out_of_stock = [i for i in items if i.is_out_of_stock]
            data = {
                'total_items': len(items),
                'total_quantity': sum(i.quantity for i in items),
                'low_stock_count': len(low_stock),
                'out_of_stock_count': len(out_of_stock),
                'total_inventory_value': float(sum(i.quantity * i.unit_cost for i in items)),
                'top_low_stock': [
                    {'book_id': i.book_id, 'book_title': i.book_title, 'available': i.available_quantity}
                    for i in sorted(low_stock, key=lambda x: x.available_quantity)[:10]
                ],
            }
            cache.set(cache_key, data, 60 * 5)
        return Response(data)
