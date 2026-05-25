from rest_framework import serializers

from .models import WeeklyStockReport


class WeeklyStockReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyStockReport
        fields = '__all__'
        read_only_fields = ('id', 'generated_at')


class StockSummarySerializer(serializers.Serializer):
    total_items = serializers.IntegerField()
    total_quantity = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    total_inventory_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    top_low_stock = serializers.ListField(child=serializers.DictField())
