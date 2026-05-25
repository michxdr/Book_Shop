from django.contrib import admin

from .models import WeeklyStockReport


@admin.register(WeeklyStockReport)
class WeeklyStockReportAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'week_end', 'total_items', 'low_stock_count', 'out_of_stock_count', 'generated_at')
    readonly_fields = ('generated_at',)
