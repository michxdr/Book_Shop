from rest_framework.permissions import BasePermission, IsAdminUser, SAFE_METHODS


class IsManagerOrReadOnly(BasePermission):
    """Allow read-only to all authenticated users; write only to managers/admins."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_manager or request.user.is_staff)
        )


class IsWarehouseManager(BasePermission):
    """Allow access only to warehouse managers and admins."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_manager or request.user.is_staff)
        )


class IsInternalService(BasePermission):
    """Allows access only to internal service-to-service calls authenticated by a shared secret."""

    def has_permission(self, request, view):
        from django.conf import settings
        token = request.headers.get('X-Warehouse-Secret', '')
        return token == settings.WEBHOOK_SECRET
