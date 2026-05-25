import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestInventoryViews:
    def test_stock_list_redirects_unauthenticated(self, client):
        resp = client.get('/inventory/')
        assert resp.status_code == 302
        assert '/accounts/login/' in resp['Location']

    def test_stock_list_authenticated(self, client, manager_user, stock_item):
        client.force_login(manager_user)
        resp = client.get('/inventory/')
        assert resp.status_code == 200
        assert b'Test Book' in resp.content

    def test_stock_list_search(self, client, manager_user, stock_item, low_stock_item):
        client.force_login(manager_user)
        resp = client.get('/inventory/?q=Low')
        assert resp.status_code == 200
        assert b'Low Stock Book' in resp.content

    def test_stock_detail(self, client, manager_user, stock_item):
        client.force_login(manager_user)
        resp = client.get(f'/inventory/stock/{stock_item.pk}/')
        assert resp.status_code == 200
        assert b'Test Book' in resp.content
        assert b'A1-01' in resp.content

    def test_stock_detail_404(self, client, manager_user):
        client.force_login(manager_user)
        resp = client.get('/inventory/stock/99999/')
        assert resp.status_code == 404

    def test_stock_create_requires_permission(self, client, staff_user):
        client.force_login(staff_user)
        resp = client.get('/inventory/stock/create/')
        assert resp.status_code == 403

    def test_stock_create_as_manager(self, client, manager_user):
        from inventory.models import StockItem
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename='add_stockitem')
        manager_user.user_permissions.add(perm)
        client.force_login(manager_user)
        resp = client.post('/inventory/stock/create/', {
            'book_id': 77,
            'book_title': 'New Book',
            'book_isbn': '',
            'quantity': 30,
            'low_stock_threshold': 5,
            'location': 'D4-01',
            'unit_cost': '15.00',
        })
        assert resp.status_code == 302
        assert StockItem.objects.filter(book_id=77).exists()

    def test_stock_filter_low_stock(self, client, manager_user, stock_item, low_stock_item):
        client.force_login(manager_user)
        resp = client.get('/inventory/?status=low')
        assert resp.status_code == 200
        assert b'Low Stock Book' in resp.content

    def test_alert_list(self, client, manager_user, low_stock_item):
        from inventory.models import WarehouseAlert
        WarehouseAlert.objects.create(
            stock_item=low_stock_item, alert_type=WarehouseAlert.ALERT_LOW_STOCK, message='Low!'
        )
        client.force_login(manager_user)
        resp = client.get('/inventory/alerts/')
        assert resp.status_code == 200
        assert b'Low!' in resp.content


@pytest.mark.django_db
class TestAnalyticsViews:
    def test_dashboard_requires_login(self, client):
        resp = client.get('/analytics/')
        assert resp.status_code == 302

    def test_dashboard_renders(self, client, manager_user, stock_item):
        client.force_login(manager_user)
        resp = client.get('/analytics/')
        assert resp.status_code == 200
        assert b'Analytics' in resp.content

    def test_report_list(self, client, manager_user):
        client.force_login(manager_user)
        resp = client.get('/analytics/reports/')
        assert resp.status_code == 200


@pytest.mark.django_db
class TestAccountViews:
    def test_login_page(self, client):
        resp = client.get('/accounts/login/')
        assert resp.status_code == 200

    def test_login_success(self, client, manager_user):
        resp = client.post('/accounts/login/', {'username': 'manager', 'password': 'testpass123'})
        assert resp.status_code == 302

    def test_login_invalid(self, client):
        resp = client.post('/accounts/login/', {'username': 'bad', 'password': 'wrong'})
        assert resp.status_code == 200  # re-renders form

    def test_profile_requires_login(self, client):
        resp = client.get('/accounts/profile/')
        assert resp.status_code == 302

    def test_profile_view(self, client, manager_user):
        client.force_login(manager_user)
        resp = client.get('/accounts/profile/')
        assert resp.status_code == 200

    def test_health_check(self, client):
        resp = client.get('/health/')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'ok'
        assert resp.json()['service'] == 'warehouse'
