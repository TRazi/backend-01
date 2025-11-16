from rest_framework.routers import DefaultRouter
from .viewsets import BudgetViewSet, BudgetItemViewSet

router = DefaultRouter()
router.register("budgets", BudgetViewSet, basename="budget")
router.register("budget-items", BudgetItemViewSet, basename="budget-item")

urlpatterns = router.urls
