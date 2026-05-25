from django.db import models
from django.utils.translation import gettext_lazy as _


class WeeklyStockReport(models.Model):
    """Auto-generated weekly snapshot of warehouse state."""

    week_start = models.DateField(_('Початок тижня'), unique=True)
    week_end = models.DateField(_('Кінець тижня'))
    total_items = models.PositiveIntegerField(_('Всього позицій'), default=0)
    total_quantity = models.PositiveIntegerField(_('Загальна кількість'), default=0)
    low_stock_count = models.PositiveIntegerField(_('Позицій з низьким запасом'), default=0)
    out_of_stock_count = models.PositiveIntegerField(_('Відсутніх позицій'), default=0)
    total_movements_in = models.PositiveIntegerField(_('Надходжень (шт.)'), default=0)
    total_movements_out = models.PositiveIntegerField(_('Видатків (шт.)'), default=0)
    total_inventory_value = models.DecimalField(
        _('Загальна вартість запасів'), max_digits=14, decimal_places=2, default=0
    )
    report_data = models.JSONField(_('Деталі звіту'), default=dict)
    generated_at = models.DateTimeField(_('Згенеровано'), auto_now_add=True)

    class Meta:
        verbose_name = _('Тижневий звіт складу')
        verbose_name_plural = _('Тижневі звіти складу')
        ordering = ['-week_start']

    def __str__(self):
        return f'Звіт {self.week_start} — {self.week_end}'
