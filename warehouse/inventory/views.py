import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import StockItemFilter, StockMovementFilter, WarehouseAlertFilter
from .models import StockItem, StockMovement, WarehouseAlert
from .permissions import IsInternalService, IsManagerOrReadOnly, IsWarehouseManager
from .serializers import (
    ReleaseStockSerializer,
    ReserveStockSerializer,
    StockAdjustSerializer,
    StockItemSerializer,
    StockItemSyncSerializer,
    StockMovementSerializer,
    WarehouseAlertSerializer,
)

logger = logging.getLogger('inventory')


# ──────────────────────────────────────────────
# Django CBV views (Bootstrap UI)
# ──────────────────────────────────────────────

class StockListView(LoginRequiredMixin, ListView):
    model = StockItem
    template_name = 'inventory/stock_list.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_queryset(self):
        qs = StockItem.objects.all()
        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(book_title__icontains=search)
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'low':
            qs = qs.filter(quantity__lte=F('low_stock_threshold') + F('reserved_quantity'))
        elif status_filter == 'out':
            qs = qs.filter(quantity__lte=F('reserved_quantity'))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get('q', '')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['total_items'] = StockItem.objects.count()
        ctx['low_stock_count'] = sum(1 for i in StockItem.objects.all() if i.is_low_stock)
        return ctx


class StockDetailView(LoginRequiredMixin, DetailView):
    model = StockItem
    template_name = 'inventory/stock_detail.html'
    context_object_name = 'item'

    def get_object(self):
        pk = self.kwargs['pk']
        cache_key = f'stock_detail_{pk}'
        obj = cache.get(cache_key)
        if obj is None:
            obj = get_object_or_404(StockItem, pk=pk)
            cache.set(cache_key, obj, 60 * 15)
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['movements'] = self.object.movements.select_related('created_by').order_by('-created_at')[:20]
        ctx['alerts'] = self.object.alerts.filter(is_resolved=False)
        return ctx


class StockCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = StockItem
    fields = ('book_id', 'book_title', 'book_isbn', 'quantity', 'low_stock_threshold', 'location', 'unit_cost')
    template_name = 'inventory/stock_form.html'
    success_url = reverse_lazy('inventory:stock_list')
    permission_required = 'inventory.add_stockitem'

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info('StockItem created: book_id=%s by user=%s', self.object.book_id, self.request.user)
        return response


class StockUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = StockItem
    fields = ('book_title', 'book_isbn', 'quantity', 'low_stock_threshold', 'location', 'unit_cost')
    template_name = 'inventory/stock_form.html'
    permission_required = 'inventory.change_stockitem'

    def get_success_url(self):
        return reverse_lazy('inventory:stock_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        cache.delete(f'stock_detail_{self.object.pk}')
        logger.info('StockItem updated: pk=%s by user=%s', self.object.pk, self.request.user)
        return super().form_valid(form)


class AlertListView(LoginRequiredMixin, ListView):
    model = WarehouseAlert
    template_name = 'inventory/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20

    def get_queryset(self):
        qs = WarehouseAlert.objects.select_related('stock_item').order_by('-created_at')
        show_resolved = self.request.GET.get('resolved', '')
        if not show_resolved:
            qs = qs.filter(is_resolved=False)
        return qs


# ──────────────────────────────────────────────
# DRF ViewSets (REST API)
# ──────────────────────────────────────────────

class StockItemViewSet(viewsets.ModelViewSet):
    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer
    permission_classes = [IsManagerOrReadOnly]
    filterset_class = StockItemFilter
    search_fields = ['book_title', 'book_isbn', 'location']
    ordering_fields = ['book_title', 'quantity', 'updated_at']
    ordering = ['book_title']

    def get_object_by_book_id(self, book_id):
        return get_object_or_404(StockItem, book_id=book_id)

    @action(detail=False, url_path='by-book/(?P<book_id>[0-9]+)', methods=['get'])
    def by_book(self, request, book_id=None):
        item = self.get_object_by_book_id(book_id)
        return Response(StockItemSerializer(item).data)

    @action(
        detail=False,
        url_path='by-book/(?P<book_id>[0-9]+)/reserve',
        methods=['post'],
        permission_classes=[IsAuthenticated | IsInternalService],
    )
    def reserve(self, request, book_id=None):
        item = self.get_object_by_book_id(book_id)
        serializer = ReserveStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qty = serializer.validated_data['quantity']
        order_id = serializer.validated_data['order_id']

        if item.available_quantity < qty:
            return Response(
                {'error': _('Недостатньо товару на складі'), 'available': item.available_quantity},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            item.reserved_quantity = F('reserved_quantity') + qty
            item.save(update_fields=['reserved_quantity', 'updated_at'])
            StockMovement.objects.create(
                stock_item=item,
                movement_type=StockMovement.TYPE_RESERVATION,
                quantity=-qty,
                reference_id=str(order_id),
                note=f'Reserved for order {order_id}',
                created_by=request.user if request.user.is_authenticated else None,
            )

        item.refresh_from_db()
        cache.delete(f'stock_detail_{item.pk}')
        logger.info('Reserved %s units of book_id=%s for order %s', qty, book_id, order_id)
        return Response(StockItemSerializer(item).data)

    @action(
        detail=False,
        url_path='by-book/(?P<book_id>[0-9]+)/release',
        methods=['post'],
        permission_classes=[IsAuthenticated | IsInternalService],
    )
    def release(self, request, book_id=None):
        item = self.get_object_by_book_id(book_id)
        serializer = ReleaseStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qty = serializer.validated_data['quantity']
        order_id = serializer.validated_data['order_id']

        with transaction.atomic():
            item.reserved_quantity = F('reserved_quantity') - qty
            item.save(update_fields=['reserved_quantity', 'updated_at'])
            StockMovement.objects.create(
                stock_item=item,
                movement_type=StockMovement.TYPE_RELEASE,
                quantity=qty,
                reference_id=str(order_id),
                note=f'Released reservation for order {order_id}',
                created_by=request.user if request.user.is_authenticated else None,
            )

        item.refresh_from_db()
        cache.delete(f'stock_detail_{item.pk}')
        logger.info('Released %s units of book_id=%s for order %s', qty, book_id, order_id)
        return Response(StockItemSerializer(item).data)

    @action(
        detail=False,
        url_path='by-book/(?P<book_id>[0-9]+)/adjust',
        methods=['post'],
        permission_classes=[IsWarehouseManager],
    )
    def adjust(self, request, book_id=None):
        item = self.get_object_by_book_id(book_id)
        serializer = StockAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delta = serializer.validated_data['quantity_delta']
        note = serializer.validated_data.get('note', '')

        new_qty = item.quantity + delta
        if new_qty < 0:
            return Response({'error': _('Кількість не може бути від\'ємною')}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            item.quantity = new_qty
            item.save(update_fields=['quantity', 'updated_at'])
            StockMovement.objects.create(
                stock_item=item,
                movement_type=StockMovement.TYPE_ADJUSTMENT,
                quantity=delta,
                note=note or f'Manual adjustment by {request.user}',
                created_by=request.user,
            )

        cache.delete(f'stock_detail_{item.pk}')
        logger.info('Adjusted stock for book_id=%s delta=%s by %s', book_id, delta, request.user)
        return Response(StockItemSerializer(item).data)

    @action(
        detail=False,
        url_path='sync',
        methods=['post'],
        permission_classes=[IsInternalService],
    )
    def sync(self, request):
        """Called by ProjectA to sync book catalogue data (book_id, title, isbn)."""
        serializer = StockItemSyncSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        updated = 0
        for book_data in serializer.validated_data:
            _, created = StockItem.objects.update_or_create(
                book_id=book_data['book_id'],
                defaults={
                    'book_title': book_data['book_title'],
                    'book_isbn': book_data.get('book_isbn', ''),
                    'last_synced_at': timezone.now(),
                },
            )
            updated += 1
        return Response({'synced': updated})


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related('stock_item', 'created_by').all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = StockMovementFilter
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']


class WarehouseAlertViewSet(viewsets.ModelViewSet):
    queryset = WarehouseAlert.objects.select_related('stock_item').all()
    serializer_class = WarehouseAlertSerializer
    permission_classes = [IsWarehouseManager]
    filterset_class = WarehouseAlertFilter
    http_method_names = ['get', 'patch', 'head', 'options']
