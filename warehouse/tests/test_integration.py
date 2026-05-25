"""
Integration tests: full flows across models + views + tasks.
"""
import pytest
from unittest.mock import MagicMock, patch

from inventory.models import StockItem, StockMovement, WarehouseAlert


@pytest.mark.django_db
class TestOrderFulfillmentFlow:
    """Simulate: order placed → reserve → paid → fulfill → stock decremented."""

    def test_reserve_then_fulfill(self, auth_client, stock_item):
        initial_qty = stock_item.quantity  # 50
        initial_reserved = stock_item.reserved_quantity  # 5

        # Step 1: Reserve stock (called by ProjectA when order is created)
        resp = auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/reserve/',
            {'quantity': 3, 'order_id': 'ORD-INTEG-001'},
        )
        assert resp.status_code == 200
        stock_item.refresh_from_db()
        assert stock_item.reserved_quantity == initial_reserved + 3

        # Step 2: Fulfill order (called by Celery task when order is paid)
        from inventory.tasks import fulfill_order_stock
        result = fulfill_order_stock(
            order_id='ORD-INTEG-001',
            items=[{'book_id': stock_item.book_id, 'quantity': 3}]
        )
        assert result['fulfilled'] == [stock_item.book_id]
        assert result['errors'] == []

        stock_item.refresh_from_db()
        assert stock_item.quantity == initial_qty - 3
        assert stock_item.reserved_quantity == initial_reserved  # back to original

        # Verify movement audit trail
        movements = StockMovement.objects.filter(
            stock_item=stock_item, reference_id='ORD-INTEG-001'
        )
        assert movements.count() == 2  # reservation + sale

    def test_reserve_cancel_release(self, auth_client, stock_item):
        initial_reserved = stock_item.reserved_quantity

        # Reserve
        auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/reserve/',
            {'quantity': 5, 'order_id': 'ORD-CANCEL-001'},
        )

        # Cancel (release reservation)
        resp = auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/release/',
            {'quantity': 5, 'order_id': 'ORD-CANCEL-001'},
        )
        assert resp.status_code == 200
        stock_item.refresh_from_db()
        assert stock_item.reserved_quantity == initial_reserved

    def test_fulfill_nonexistent_book(self):
        from inventory.tasks import fulfill_order_stock
        result = fulfill_order_stock(
            order_id='ORD-999',
            items=[{'book_id': 99999, 'quantity': 1}]
        )
        assert result['fulfilled'] == []
        assert len(result['errors']) == 1
        assert result['errors'][0]['error'] == 'not found'


@pytest.mark.django_db
class TestLowStockAlertFlow:
    def test_check_low_stock_creates_alert(self, low_stock_item):
        from inventory.tasks import check_low_stock_levels
        with patch('inventory.tasks._notify_bookshop_low_stock.delay') as mock_notify:
            result = check_low_stock_levels()
            assert result >= 1
            assert WarehouseAlert.objects.filter(
                stock_item=low_stock_item, alert_type=WarehouseAlert.ALERT_LOW_STOCK
            ).exists()
            mock_notify.assert_called_once()

    def test_check_low_stock_no_duplicate_alerts(self, low_stock_item):
        from inventory.tasks import check_low_stock_levels
        # Create existing unresolved alert
        WarehouseAlert.objects.create(
            stock_item=low_stock_item,
            alert_type=WarehouseAlert.ALERT_LOW_STOCK,
            message='existing',
        )
        with patch('inventory.tasks._notify_bookshop_low_stock.delay'):
            check_low_stock_levels()
        # Should still be only 1 alert of this type
        assert WarehouseAlert.objects.filter(
            stock_item=low_stock_item,
            alert_type=WarehouseAlert.ALERT_LOW_STOCK,
            is_resolved=False,
        ).count() == 1

    def test_out_of_stock_creates_out_alert(self, out_of_stock_item):
        from inventory.tasks import check_low_stock_levels
        with patch('inventory.tasks._notify_bookshop_low_stock.delay'):
            check_low_stock_levels()
        assert WarehouseAlert.objects.filter(
            stock_item=out_of_stock_item, alert_type=WarehouseAlert.ALERT_OUT_OF_STOCK
        ).exists()


@pytest.mark.django_db
class TestBookShopClientErrorHandling:
    def test_client_handles_connection_error(self):
        from services.book_shop_client import BookShopClient, BookShopClientError
        client = BookShopClient()
        with patch.object(client.session, 'get', side_effect=__import__('requests').exceptions.ConnectionError):
            with pytest.raises(BookShopClientError) as exc_info:
                client.get_books()
            assert 'Connection error' in str(exc_info.value)

    def test_client_handles_timeout(self):
        from services.book_shop_client import BookShopClient, BookShopClientError
        client = BookShopClient()
        with patch.object(client.session, 'get', side_effect=__import__('requests').exceptions.Timeout):
            with pytest.raises(BookShopClientError) as exc_info:
                client.get_book(1)
            assert 'Timeout' in str(exc_info.value)

    def test_sync_book_catalog_handles_client_error(self):
        from inventory.tasks import sync_book_catalog
        from services.book_shop_client import BookShopClientError
        # The task imports BookShopClient locally, so patch at the source module
        with patch('services.book_shop_client.BookShopClient') as MockClient:
            MockClient.return_value.get_books.side_effect = BookShopClientError('Connection refused')
            result = sync_book_catalog()
            assert 'error' in result

    def test_sync_creates_missing_stock_items(self, db):
        from inventory.tasks import sync_book_catalog
        with patch('services.book_shop_client.BookShopClient') as MockClient:
            MockClient.return_value.get_books.return_value = [
                {'id': 1, 'title': 'Book A', 'isbn': '111'},
                {'id': 2, 'title': 'Book B', 'isbn': '222'},
            ]
            result = sync_book_catalog()
        assert result['created'] == 2
        assert StockItem.objects.filter(book_id=1).exists()
        assert StockItem.objects.filter(book_id=2).exists()


@pytest.mark.django_db
class TestWeeklyReportGeneration:
    def test_generate_weekly_report(self, stock_item, low_stock_item):
        from analytics.tasks import generate_weekly_stock_report
        from analytics.models import WeeklyStockReport
        pk = generate_weekly_stock_report()
        assert pk is not None
        report = WeeklyStockReport.objects.get(pk=pk)
        assert report.total_items == 2
        assert report.low_stock_count >= 1

    def test_no_duplicate_reports(self, stock_item):
        from analytics.tasks import generate_weekly_stock_report
        from analytics.models import WeeklyStockReport
        generate_weekly_stock_report()
        initial_count = WeeklyStockReport.objects.count()
        generate_weekly_stock_report()  # should skip
        assert WeeklyStockReport.objects.count() == initial_count
