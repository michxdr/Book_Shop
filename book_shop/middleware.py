import logging
import time

logger = logging.getLogger('request')


class RequestLoggingMiddleware:
    """Логує кожен HTTP-запит: метод, шлях, статус, час виконання, користувач."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()

        response = self.get_response(request)

        elapsed_ms = (time.monotonic() - start) * 1000
        user = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous'

        logger.info(
            '%s %s → %s | %.1f ms | user=%s',
            request.method,
            request.get_full_path(),
            response.status_code,
            elapsed_ms,
            user,
        )
        return response
