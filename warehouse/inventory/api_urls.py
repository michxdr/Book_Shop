from rest_framework.routers import DefaultRouter

from .views import StockItemViewSet, StockMovementViewSet, WarehouseAlertViewSet

router = DefaultRouter()
router.register('stock', StockItemViewSet, basename='stock')
router.register('movements', StockMovementViewSet, basename='movement')
router.register('alerts', WarehouseAlertViewSet, basename='alert')

urlpatterns = router.urls
