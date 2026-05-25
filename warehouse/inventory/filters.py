import django_filters
from django.utils.translation import gettext_lazy as _

from .models import StockItem, StockMovement, WarehouseAlert


class StockItemFilter(django_filters.FilterSet):
    book_title = django_filters.CharFilter(lookup_expr='icontains', label=_('Назва книги'))
    low_stock = django_filters.BooleanFilter(method='filter_low_stock', label=_('Тільки низький запас'))
    out_of_stock = django_filters.BooleanFilter(method='filter_out_of_stock', label=_('Тільки відсутні'))
    min_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    max_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='lte')

    class Meta:
        model = StockItem
        fields = ['book_title', 'location']

    def filter_low_stock(self, queryset, name, value):
        if value:
            from django.db.models import F
            return queryset.filter(quantity__lte=F('low_stock_threshold') + F('reserved_quantity'))
        return queryset

    def filter_out_of_stock(self, queryset, name, value):
        if value:
            from django.db.models import F
            return queryset.filter(quantity__lte=F('reserved_quantity'))
        return queryset


class StockMovementFilter(django_filters.FilterSet):
    movement_type = django_filters.ChoiceFilter(choices=StockMovement.TYPE_CHOICES)
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    reference_id = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockMovement
        fields = ['movement_type', 'stock_item', 'reference_id']


class WarehouseAlertFilter(django_filters.FilterSet):
    alert_type = django_filters.ChoiceFilter(choices=WarehouseAlert.ALERT_CHOICES)
    is_resolved = django_filters.BooleanFilter()

    class Meta:
        model = WarehouseAlert
        fields = ['alert_type', 'is_resolved']
