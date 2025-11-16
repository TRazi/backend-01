from rest_framework.routers import DefaultRouter
from .viewsets import AuditLogViewSet

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = router.urls
