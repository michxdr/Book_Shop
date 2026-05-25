from rest_framework.routers import DefaultRouter

from .views import WeeklyReportViewSet

router = DefaultRouter()
router.register('reports', WeeklyReportViewSet, basename='report')

urlpatterns = router.urls
