from rest_framework.routers import DefaultRouter
from .viewsets import GoalViewSet, GoalProgressViewSet

router = DefaultRouter()
router.register("goals", GoalViewSet, basename="goal")
router.register("goal-progress", GoalProgressViewSet, basename="goal-progress")

urlpatterns = router.urls
