import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import StockItem

logger = logging.getLogger('inventory')


@receiver(post_save, sender=StockItem)
def invalidate_stock_cache(sender, instance, **kwargs):
    from django.core.cache import cache
    cache.delete(f'stock_detail_{instance.pk}')


@receiver(post_save, sender=StockItem)
def auto_create_low_stock_alert(sender, instance, created, **kwargs):
    """Automatically queue a low-stock check when a StockItem is saved."""
    if not created and instance.is_low_stock:
        from .tasks import check_low_stock_levels
        try:
            check_low_stock_levels.apply_async(countdown=5)
        except Exception as exc:
            logger.warning('Could not schedule low_stock check: %s', exc)
