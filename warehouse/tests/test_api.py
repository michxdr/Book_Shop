import pytest
from django.urls import reverse
from rest_framework import status

from inventory.models import StockItem, StockMovement, WarehouseAlert


@pytest.mark.django_db
class TestJWTAuth:
    def test_obtain_token(self, api_client, manager_user):
        resp = api_client.post('/api/auth/token/', {'username': 'manager', 'password': 'testpass123'})
        assert resp.status_code == status.HTTP_200_OK
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_invalid_credentials(self, api_client):
        resp = api_client.post('/api/auth/token/', {'username': 'bad', 'password': 'wrong'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client, manager_user):
        resp = api_client.post('/api/auth/token/', {'username': 'manager', 'password': 'testpass123'})
        refresh = resp.data['refresh']
        resp2 = api_client.post('/api/auth/token/refresh/', {'refresh': refresh})
        assert resp2.status_code == status.HTTP_200_OK
        assert 'access' in resp2.data


@pytest.mark.django_db
class TestStockItemAPI:
    def test_list_requires_auth(self, api_client):
        resp = api_client.get('/api/stock/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, auth_client, stock_item):
        resp = auth_client.get('/api/stock/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] >= 1

    def test_retrieve_by_pk(self, auth_client, stock_item):
        resp = auth_client.get(f'/api/stock/{stock_item.pk}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['book_title'] == 'Test Book'
        assert 'available_quantity' in resp.data

    def test_retrieve_by_book_id(self, auth_client, stock_item):
        resp = auth_client.get(f'/api/stock/by-book/{stock_item.book_id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['book_id'] == stock_item.book_id

    def test_create_requires_manager(self, staff_api_client):
        resp = staff_api_client.post('/api/stock/', {
            'book_id': 99, 'book_title': 'New Book', 'quantity': 10,
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_as_manager(self, auth_client):
        resp = auth_client.post('/api/stock/', {
            'book_id': 50, 'book_title': 'Created Book',
            'quantity': 25, 'low_stock_threshold': 5,
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert StockItem.objects.filter(book_id=50).exists()

    def test_update_stock(self, auth_client, stock_item):
        resp = auth_client.patch(f'/api/stock/{stock_item.pk}/', {'location': 'Z9-99'})
        assert resp.status_code == status.HTTP_200_OK
        stock_item.refresh_from_db()
        assert stock_item.location == 'Z9-99'

    def test_filter_by_title(self, auth_client, stock_item, low_stock_item):
        resp = auth_client.get('/api/stock/', {'book_title': 'Low'})
        assert resp.status_code == status.HTTP_200_OK
        assert all('Low' in item['book_title'] for item in resp.data['results'])

    def test_search(self, auth_client, stock_item):
        resp = auth_client.get('/api/stock/', {'search': 'Test'})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] >= 1


@pytest.mark.django_db
class TestReserveReleaseAPI:
    def test_reserve_stock(self, auth_client, stock_item):
        resp = auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/reserve/',
            {'quantity': 5, 'order_id': 'ORD-001'},
        )
        assert resp.status_code == status.HTTP_200_OK
        stock_item.refresh_from_db()
        assert stock_item.reserved_quantity == 10  # was 5, now 10

    def test_reserve_insufficient_stock(self, auth_client, stock_item):
        resp = auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/reserve/',
            {'quantity': 1000, 'order_id': 'ORD-002'},
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert 'available' in resp.data

    def test_release_stock(self, auth_client, stock_item):
        initial_reserved = stock_item.reserved_quantity
        resp = auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/release/',
            {'quantity': 3, 'order_id': 'ORD-001'},
        )
        assert resp.status_code == status.HTTP_200_OK
        stock_item.refresh_from_db()
        assert stock_item.reserved_quantity == initial_reserved - 3

    def test_reserve_creates_movement(self, auth_client, stock_item):
        initial_count = StockMovement.objects.filter(stock_item=stock_item).count()
        auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/reserve/',
            {'quantity': 2, 'order_id': 'ORD-003'},
        )
        assert StockMovement.objects.filter(stock_item=stock_item).count() == initial_count + 1

    def test_adjust_stock(self, auth_client, stock_item):
        resp = auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/adjust/',
            {'quantity_delta': 10, 'note': 'Restock'},
        )
        assert resp.status_code == status.HTTP_200_OK
        stock_item.refresh_from_db()
        assert stock_item.quantity == 60

    def test_adjust_negative_not_below_zero(self, auth_client, stock_item):
        resp = auth_client.post(
            f'/api/stock/by-book/{stock_item.book_id}/adjust/',
            {'quantity_delta': -9999},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestStockSyncAPI:
    def test_sync_requires_internal_secret(self, api_client):
        # No X-Warehouse-Secret → DRF rejects (401 for unauthenticated, 403 for wrong secret)
        resp = api_client.post('/api/stock/sync/', [
            {'book_id': 1, 'book_title': 'Book 1'},
        ], format='json')
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_sync_with_secret(self, api_client):
        api_client.credentials(HTTP_X_WAREHOUSE_SECRET='test-webhook-secret')
        resp = api_client.post('/api/stock/sync/', [
            {'book_id': 10, 'book_title': 'Synced Book', 'book_isbn': '000'},
        ], format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['synced'] == 1
        assert StockItem.objects.filter(book_id=10).exists()


@pytest.mark.django_db
class TestMovementsAPI:
    def test_list_movements(self, auth_client, stock_item):
        StockMovement.objects.create(
            stock_item=stock_item, movement_type=StockMovement.TYPE_RECEIPT, quantity=5
        )
        resp = auth_client.get('/api/movements/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] >= 1

    def test_movements_are_readonly(self, auth_client):
        resp = auth_client.post('/api/movements/', {})
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestAlertsAPI:
    def test_list_alerts(self, auth_client, low_stock_item):
        WarehouseAlert.objects.create(
            stock_item=low_stock_item,
            alert_type=WarehouseAlert.ALERT_LOW_STOCK,
            message='Low!',
        )
        resp = auth_client.get('/api/alerts/')
        assert resp.status_code == status.HTTP_200_OK

    def test_resolve_alert(self, auth_client, low_stock_item):
        alert = WarehouseAlert.objects.create(
            stock_item=low_stock_item, alert_type=WarehouseAlert.ALERT_LOW_STOCK, message='!'
        )
        resp = auth_client.patch(f'/api/alerts/{alert.pk}/', {'is_resolved': True})
        assert resp.status_code == status.HTTP_200_OK
        alert.refresh_from_db()
        assert alert.is_resolved
        assert alert.resolved_at is not None

    def test_analytics_summary(self, auth_client, stock_item, low_stock_item):
        resp = auth_client.get('/api/analytics/reports/summary/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'total_items' in resp.data
        assert 'low_stock_count' in resp.data
