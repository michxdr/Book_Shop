import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from inventory.models import StockItem, StockMovement, WarehouseAlert
from analytics.models import WeeklyStockReport

User = get_user_model()


# ── CustomUser ──────────────────────────────────────────

@pytest.mark.django_db
class TestCustomUser:
    def test_create_user(self):
        user = User.objects.create_user(username='alice', password='pass', role='staff', department='Shipping')
        assert user.username == 'alice'
        assert user.role == 'staff'
        assert user.department == 'Shipping'
        assert not user.is_manager

    def test_manager_role(self):
        user = User.objects.create_user(username='bob', password='pass', role='manager')
        assert user.is_manager

    def test_admin_role_is_manager(self):
        user = User.objects.create_user(username='carol', password='pass', role='admin')
        assert user.is_manager

    def test_staff_role_is_not_manager(self):
        user = User.objects.create_user(username='dave', password='pass', role='staff')
        assert not user.is_manager

    def test_str_full_name(self):
        user = User.objects.create_user(username='eve', password='pass', first_name='Eve', last_name='Smith')
        assert str(user) == 'Eve Smith'

    def test_str_username_fallback(self):
        user = User.objects.create_user(username='frank', password='pass')
        assert str(user) == 'frank'


# ── StockItem ────────────────────────────────────────────

@pytest.mark.django_db
class TestStockItem:
    def test_available_quantity(self, stock_item):
        assert stock_item.available_quantity == 45  # 50 - 5

    def test_is_low_stock_false_when_enough(self, stock_item):
        assert not stock_item.is_low_stock

    def test_is_low_stock_true(self, low_stock_item):
        assert low_stock_item.is_low_stock

    def test_is_out_of_stock_false(self, stock_item):
        assert not stock_item.is_out_of_stock

    def test_is_out_of_stock_true(self, out_of_stock_item):
        assert out_of_stock_item.is_out_of_stock

    def test_available_never_negative(self, db):
        item = StockItem.objects.create(
            book_id=99, book_title='Test', quantity=2, reserved_quantity=5
        )
        assert item.available_quantity == 0

    def test_str_repr(self, stock_item):
        assert 'Test Book' in str(stock_item)
        assert '45' in str(stock_item)

    def test_unique_book_id(self, stock_item):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            StockItem.objects.create(book_id=1, book_title='Duplicate')

    def test_default_low_stock_threshold(self, db):
        item = StockItem.objects.create(book_id=100, book_title='New')
        assert item.low_stock_threshold == 5


# ── StockMovement ────────────────────────────────────────

@pytest.mark.django_db
class TestStockMovement:
    def test_create_movement(self, stock_item, manager_user):
        mv = StockMovement.objects.create(
            stock_item=stock_item,
            movement_type=StockMovement.TYPE_RECEIPT,
            quantity=20,
            note='Supplier delivery',
            created_by=manager_user,
        )
        assert mv.pk is not None
        assert mv.quantity == 20
        assert mv.movement_type == 'receipt'

    def test_str_positive(self, stock_item):
        mv = StockMovement.objects.create(
            stock_item=stock_item, movement_type=StockMovement.TYPE_RECEIPT, quantity=10
        )
        assert '+10' in str(mv)

    def test_str_negative(self, stock_item):
        mv = StockMovement.objects.create(
            stock_item=stock_item, movement_type=StockMovement.TYPE_SALE, quantity=-3
        )
        assert '-3' in str(mv)

    def test_ordering_newest_first(self, stock_item):
        StockMovement.objects.create(stock_item=stock_item, movement_type=StockMovement.TYPE_RECEIPT, quantity=1)
        StockMovement.objects.create(stock_item=stock_item, movement_type=StockMovement.TYPE_SALE, quantity=-1)
        movements = list(StockMovement.objects.filter(stock_item=stock_item))
        assert movements[0].created_at >= movements[1].created_at


# ── WarehouseAlert ───────────────────────────────────────

@pytest.mark.django_db
class TestWarehouseAlert:
    def test_create_alert(self, low_stock_item):
        alert = WarehouseAlert.objects.create(
            stock_item=low_stock_item,
            alert_type=WarehouseAlert.ALERT_LOW_STOCK,
            message='Low stock!',
        )
        assert not alert.is_resolved
        assert alert.resolved_at is None

    def test_str_open(self, low_stock_item):
        alert = WarehouseAlert.objects.create(
            stock_item=low_stock_item, alert_type=WarehouseAlert.ALERT_LOW_STOCK, message='!'
        )
        assert '[OPEN]' in str(alert)

    def test_str_resolved(self, low_stock_item):
        alert = WarehouseAlert.objects.create(
            stock_item=low_stock_item, alert_type=WarehouseAlert.ALERT_LOW_STOCK,
            message='!', is_resolved=True,
        )
        assert '[RESOLVED]' in str(alert)


# ── WeeklyStockReport ────────────────────────────────────

@pytest.mark.django_db
class TestWeeklyStockReport:
    def test_create_report(self):
        from datetime import date
        report = WeeklyStockReport.objects.create(
            week_start=date(2025, 1, 6),
            week_end=date(2025, 1, 12),
            total_items=100,
            total_quantity=1500,
        )
        assert report.pk is not None
        assert '2025-01-06' in str(report)
