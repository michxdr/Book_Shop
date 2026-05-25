"""
HTTP client for communicating with ProjectA (Book Shop).

All methods raise BookShopClientError on network/HTTP failures.
Callers should handle this exception for graceful degradation.
"""

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger('services')

DEFAULT_TIMEOUT = 10  # seconds


class BookShopClientError(Exception):
    """Raised when the Book Shop API is unreachable or returns an error."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class BookShopClient:
    """Client for the Book Shop REST API (ProjectA)."""

    def __init__(self):
        self.base_url = settings.BOOK_SHOP_API_URL.rstrip('/')
        self.token = settings.BOOK_SHOP_API_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Service-Name': 'warehouse',
        })
        if self.token:
            self.session.headers['Authorization'] = f'Bearer {self.token}'

    def _get(self, path: str, params: dict = None) -> Any:
        url = f'{self.base_url}{path}'
        try:
            response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error('BookShop API timeout: GET %s', path)
            raise BookShopClientError(f'Timeout calling BookShop GET {path}')
        except requests.exceptions.ConnectionError as exc:
            logger.error('BookShop API connection error: GET %s — %s', path, exc)
            raise BookShopClientError(f'Connection error calling BookShop GET {path}')
        except requests.exceptions.HTTPError as exc:
            logger.error('BookShop API HTTP error: GET %s — %s', path, exc.response.status_code)
            raise BookShopClientError(
                f'BookShop returned {exc.response.status_code} for GET {path}',
                status_code=exc.response.status_code,
            )

    def _post(self, path: str, data: dict) -> Any:
        url = f'{self.base_url}{path}'
        try:
            response = self.session.post(url, json=data, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error('BookShop API timeout: POST %s', path)
            raise BookShopClientError(f'Timeout calling BookShop POST {path}')
        except requests.exceptions.ConnectionError as exc:
            logger.error('BookShop API connection error: POST %s — %s', path, exc)
            raise BookShopClientError(f'Connection error calling BookShop POST {path}')
        except requests.exceptions.HTTPError as exc:
            logger.error('BookShop API HTTP error: POST %s — %s', path, exc.response.status_code)
            raise BookShopClientError(
                f'BookShop returned {exc.response.status_code} for POST {path}',
                status_code=exc.response.status_code,
            )

    # ────────────────────────────────
    # Public API methods
    # ────────────────────────────────

    def get_books(self, page_size: int = 1000) -> list[dict]:
        """Fetch all books from ProjectA (paginated)."""
        all_books = []
        page = 1
        while True:
            data = self._get('/api/books/', params={'page': page, 'page_size': page_size})
            results = data.get('results', data) if isinstance(data, dict) else data
            all_books.extend(results)
            if not data.get('next'):
                break
            page += 1
        logger.info('Fetched %d books from BookShop', len(all_books))
        return all_books

    def get_book(self, book_id: int) -> dict:
        """Fetch a single book by ID."""
        return self._get(f'/api/books/{book_id}/')

    def notify_low_stock(self, book_ids: list[int]) -> dict:
        """
        Notify ProjectA about books with critically low/zero stock
        so it can mark them as unavailable.
        """
        webhook_secret = settings.WEBHOOK_SECRET
        self.session.headers['X-Warehouse-Secret'] = webhook_secret
        try:
            result = self._post('/api/webhooks/stock-alert/', {'book_ids': book_ids})
            logger.info('Sent low-stock alert to BookShop for %d books', len(book_ids))
            return result
        finally:
            self.session.headers.pop('X-Warehouse-Secret', None)

    def get_order(self, order_id: int) -> dict:
        """Fetch order details from ProjectA."""
        return self._get(f'/api/orders/{order_id}/')
