import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('inventory')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_low_stock_levels(self):
    """Check all stock items and create alerts for low/out-of-stock items."""
    from .models import StockItem, WarehouseAlert

    low_items = [item for item in StockItem.objects.all() if item.is_low_stock]
    alert_count = 0

    for item in low_items:
        alert_type = WarehouseAlert.ALERT_OUT_OF_STOCK if item.is_out_of_stock else WarehouseAlert.ALERT_LOW_STOCK
        # Only create if no unresolved alert of same type exists
        exists = WarehouseAlert.objects.filter(
            stock_item=item, alert_type=alert_type, is_resolved=False
        ).exists()
        if not exists:
            msg = (
                f'Book "{item.book_title}" is out of stock.' if item.is_out_of_stock
                else f'Book "{item.book_title}" has only {item.available_quantity} units left '
                     f'(threshold: {item.low_stock_threshold}).'
            )
            WarehouseAlert.objects.create(
                stock_item=item,
                alert_type=alert_type,
                message=msg,
            )
            alert_count += 1
            logger.warning('Stock alert created: %s', msg)

    if low_items:
        try:
            _notify_bookshop_low_stock.delay([item.book_id for item in low_items])
        except Exception as exc:
            logger.error('Failed to schedule book shop notification: %s', exc)

    logger.info('check_low_stock_levels: %d alerts created', alert_count)
    return alert_count


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def _notify_bookshop_low_stock(self, book_ids):
    """Notify ProjectA about books with low/out stock so it can update availability."""
    from services.book_shop_client import BookShopClient

    client = BookShopClient()
    try:
        result = client.notify_low_stock(book_ids)
        logger.info('Notified BookShop about low stock for %d books: %s', len(book_ids), result)
    except Exception as exc:
        logger.error('Failed to notify BookShop: %s', exc)
        raise self.retry(exc=exc)


@shared_task
def sync_book_catalog():
    """Pull book catalogue from ProjectA and ensure all books have StockItem entries."""
    from services.book_shop_client import BookShopClient
    from .models import StockItem

    client = BookShopClient()
    try:
        books = client.get_books()
    except Exception as exc:
        logger.error('Failed to fetch books from BookShop: %s', exc)
        return {'error': str(exc)}

    created = 0
    for book in books:
        _, was_created = StockItem.objects.get_or_create(
            book_id=book['id'],
            defaults={
                'book_title': book.get('title', f'Book #{book["id"]}'),
                'book_isbn': book.get('isbn', ''),
                'last_synced_at': timezone.now(),
            },
        )
        if was_created:
            created += 1

    logger.info('sync_book_catalog: %d new StockItems created from %d books', created, len(books))
    return {'total': len(books), 'created': created}


@shared_task
def fulfill_order_stock(order_id, items):
    """
    Called when ProjectA marks an order as PAID.
    Converts reservations into actual sales (decrements quantity).
    `items` = [{'book_id': int, 'quantity': int}, ...]
    """
    from .models import StockItem, StockMovement
    from django.db import transaction

    fulfilled = []
    errors = []
    for item_data in items:
        book_id = item_data['book_id']
        qty = item_data['quantity']
        try:
            with transaction.atomic():
                stock = StockItem.objects.select_for_update().get(book_id=book_id)
                stock.quantity = F('quantity') - qty
                stock.reserved_quantity = F('reserved_quantity') - qty
                stock.save(update_fields=['quantity', 'reserved_quantity', 'updated_at'])
                StockMovement.objects.create(
                    stock_item=stock,
                    movement_type=StockMovement.TYPE_SALE,
                    quantity=-qty,
                    reference_id=str(order_id),
                    note=f'Fulfilled for order {order_id}',
                )
                fulfilled.append(book_id)
        except StockItem.DoesNotExist:
            logger.error('StockItem not found for book_id=%s during order %s fulfillment', book_id, order_id)
            errors.append({'book_id': book_id, 'error': 'not found'})
        except Exception as exc:
            logger.error('Error fulfilling book_id=%s order %s: %s', book_id, order_id, exc)
            errors.append({'book_id': book_id, 'error': str(exc)})

    logger.info('fulfill_order_stock: order=%s fulfilled=%s errors=%s', order_id, fulfilled, errors)
    return {'fulfilled': fulfilled, 'errors': errors}
