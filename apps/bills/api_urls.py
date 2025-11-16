from rest_framework.routers import DefaultRouter
from .viewsets import BillViewSet

router = DefaultRouter()
router.register("bills", BillViewSet, basename="bill")

urlpatterns = router.urls
