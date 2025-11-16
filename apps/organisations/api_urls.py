from rest_framework.routers import DefaultRouter
from .viewsets import OrganisationViewSet

router = DefaultRouter()
router.register("organisations", OrganisationViewSet, basename="organisation")

urlpatterns = router.urls
