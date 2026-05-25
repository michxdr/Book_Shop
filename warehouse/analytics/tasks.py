import logging
from datetime import date, timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum

logger = logging.getLogger('analytics')


@shared_task
def generate_weekly_stock_report():
    """Generate a weekly snapshot of warehouse state every Monday."""
    from inventory.models import StockItem, StockMovement
    from .models import WeeklyStockReport

    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # This Monday
    week_end = week_start + timedelta(days=6)

    if WeeklyStockReport.objects.filter(week_start=week_start).exists():
        logger.info('Weekly report for %s already exists, skipping', week_start)
        return

    items = list(StockItem.objects.all())
    low_stock_items = [i for i in items if i.is_low_stock]
    out_of_stock_items = [i for i in items if i.is_out_of_stock]

    movements_this_week = StockMovement.objects.filter(
        created_at__date__gte=week_start,
        created_at__date__lte=week_end,
    )
    incoming = movements_this_week.filter(quantity__gt=0).aggregate(total=Sum('quantity'))['total'] or 0
    outgoing = abs(movements_this_week.filter(quantity__lt=0).aggregate(total=Sum('quantity'))['total'] or 0)

    inventory_value = sum(i.quantity * i.unit_cost for i in items)

    report_data = {
        'low_stock_books': [
            {'book_id': i.book_id, 'title': i.book_title, 'available': i.available_quantity}
            for i in low_stock_items
        ],
        'out_of_stock_books': [
            {'book_id': i.book_id, 'title': i.book_title}
            for i in out_of_stock_items
        ],
    }

    report = WeeklyStockReport.objects.create(
        week_start=week_start,
        week_end=week_end,
        total_items=len(items),
        total_quantity=sum(i.quantity for i in items),
        low_stock_count=len(low_stock_items),
        out_of_stock_count=len(out_of_stock_items),
        total_movements_in=incoming,
        total_movements_out=outgoing,
        total_inventory_value=inventory_value,
        report_data=report_data,
    )

    try:
        send_mail(
            subject=f'Weekly Warehouse Report {week_start}',
            message=(
                f'Weekly warehouse report for {week_start} to {week_end}:\n\n'
                f'Total items: {report.total_items}\n'
                f'Total quantity: {report.total_quantity}\n'
                f'Low stock: {report.low_stock_count}\n'
                f'Out of stock: {report.out_of_stock_count}\n'
                f'Inventory value: ${report.total_inventory_value}\n'
                f'Incoming: {incoming} units\n'
                f'Outgoing: {outgoing} units\n'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.WAREHOUSE_MANAGER_EMAIL],
            fail_silently=True,
        )
    except Exception as exc:
        logger.error('Failed to send weekly report email: %s', exc)

    logger.info('Weekly stock report generated: id=%s', report.pk)
    return report.pk
