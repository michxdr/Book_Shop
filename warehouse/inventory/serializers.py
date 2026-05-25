from django.utils import timezone
from rest_framework import serializers

from .models import StockItem, StockMovement, WarehouseAlert


class StockItemSerializer(serializers.ModelSerializer):
    available_quantity = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    is_out_of_stock = serializers.ReadOnlyField()

    class Meta:
        model = StockItem
        fields = (
            'id', 'book_id', 'book_title', 'book_isbn',
            'quantity', 'reserved_quantity', 'available_quantity',
            'low_stock_threshold', 'is_low_stock', 'is_out_of_stock',
            'location', 'unit_cost', 'last_synced_at',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_synced_at')


class StockItemSyncSerializer(serializers.ModelSerializer):
    """Used by ProjectA to sync book data."""

    class Meta:
        model = StockItem
        fields = ('book_id', 'book_title', 'book_isbn')


class StockMovementSerializer(serializers.ModelSerializer):
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            'id', 'stock_item', 'movement_type', 'movement_type_display',
            'quantity', 'reference_id', 'note',
            'created_by', 'created_by_username', 'created_at',
        )
        read_only_fields = ('id', 'created_at', 'created_by')


class StockAdjustSerializer(serializers.Serializer):
    """POST /api/stock/{book_id}/adjust/ — manual stock correction."""
    quantity_delta = serializers.IntegerField(help_text='Positive to add, negative to remove')
    note = serializers.CharField(required=False, allow_blank=True)


class ReserveStockSerializer(serializers.Serializer):
    """POST /api/stock/{book_id}/reserve/ — reserve stock for an order."""
    quantity = serializers.IntegerField(min_value=1)
    order_id = serializers.CharField()


class ReleaseStockSerializer(serializers.Serializer):
    """POST /api/stock/{book_id}/release/ — release reserved stock."""
    quantity = serializers.IntegerField(min_value=1)
    order_id = serializers.CharField()


class WarehouseAlertSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    book_title = serializers.CharField(source='stock_item.book_title', read_only=True)

    class Meta:
        model = WarehouseAlert
        fields = (
            'id', 'stock_item', 'book_title',
            'alert_type', 'alert_type_display',
            'message', 'is_resolved', 'resolved_at', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def update(self, instance, validated_data):
        if validated_data.get('is_resolved') and not instance.is_resolved:
            validated_data['resolved_at'] = timezone.now()
        return super().update(instance, validated_data)
