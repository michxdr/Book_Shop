import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username='staff',
        password='testpass123',
        role='staff',
        department='General',
    )


@pytest.fixture
def manager_user(db):
    return User.objects.create_user(
        username='manager',
        password='testpass123',
        role='manager',
        department='Warehouse',
        is_staff=True,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin',
        password='testpass123',
        role='admin',
    )


@pytest.fixture
def stock_item(db):
    from inventory.models import StockItem
    return StockItem.objects.create(
        book_id=1,
        book_title='Test Book',
        book_isbn='978-0-000-00000-0',
        quantity=50,
        reserved_quantity=5,
        low_stock_threshold=10,
        location='A1-01',
        unit_cost='9.99',
    )


@pytest.fixture
def low_stock_item(db):
    from inventory.models import StockItem
    return StockItem.objects.create(
        book_id=2,
        book_title='Low Stock Book',
        quantity=3,
        reserved_quantity=0,
        low_stock_threshold=10,
        location='B2-05',
        unit_cost='12.50',
    )


@pytest.fixture
def out_of_stock_item(db):
    from inventory.models import StockItem
    return StockItem.objects.create(
        book_id=3,
        book_title='Out of Stock Book',
        quantity=0,
        reserved_quantity=0,
        low_stock_threshold=5,
        location='C3-01',
        unit_cost='7.99',
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def auth_client(api_client, manager_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(manager_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return api_client


@pytest.fixture
def staff_api_client(api_client, staff_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return api_client
