from rest_framework.routers import DefaultRouter
from .viewsets import TransactionViewSet
from .views_ocr import ReceiptOCRViewSet, BillOCRViewSet

router = DefaultRouter()
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("receipts", ReceiptOCRViewSet, basename="receipt")
router.register("bills", BillOCRViewSet, basename="bill")

urlpatterns = router.urls
