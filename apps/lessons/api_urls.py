from rest_framework.routers import DefaultRouter
from .viewsets import FinancialLessonViewSet

router = DefaultRouter()
router.register("lessons", FinancialLessonViewSet, basename="lessons")

urlpatterns = router.urls
