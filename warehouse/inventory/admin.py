from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import StockItem, StockMovement, WarehouseAlert


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = ('created_at', 'created_by')
    fields = ('movement_type', 'quantity', 'reference_id', 'note', 'created_by', 'created_at')


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = (
        'book_title', 'book_id', 'quantity', 'reserved_quantity',
        'available_quantity', 'is_low_stock', 'location',
    )
    list_filter = ('location',)
    search_fields = ('book_title', 'book_isbn')
    readonly_fields = ('available_quantity', 'is_low_stock', 'is_out_of_stock', 'last_synced_at')
    inlines = [StockMovementInline]

    @admin.display(boolean=True, description=_('Низький запас'))
    def is_low_stock(self, obj):
        return obj.is_low_stock

    @admin.display(description=_('Доступно'))
    def available_quantity(self, obj):
        return obj.available_quantity


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('stock_item', 'movement_type', 'quantity', 'reference_id', 'created_by', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('stock_item__book_title', 'reference_id')
    readonly_fields = ('created_at',)


@admin.register(WarehouseAlert)
class WarehouseAlertAdmin(admin.ModelAdmin):
    list_display = ('stock_item', 'alert_type', 'is_resolved', 'created_at')
    list_filter = ('alert_type', 'is_resolved')
    search_fields = ('stock_item__book_title',)
    actions = ['mark_resolved']

    @admin.action(description=_('Позначити як вирішені'))
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_resolved=True, resolved_at=timezone.now())
