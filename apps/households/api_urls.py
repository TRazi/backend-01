from django.urls import path
from .apis import (
    HouseholdListCreateApi,
    HouseholdDetailApi,
    MembershipListApi,
    MembershipCreateApi,
)

urlpatterns = [
    path("households/", HouseholdListCreateApi.as_view()),
    path("households/<uuid:uuid>/", HouseholdDetailApi.as_view()),
    path("memberships/", MembershipListApi.as_view()),
    path("memberships/create/", MembershipCreateApi.as_view()),
]
