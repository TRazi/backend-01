from rest_framework import viewsets, permissions
from .models import Reward
from .serializers import RewardSerializer
from .permissions import IsRewardOwnerOrAdmin


class RewardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    READ-ONLY rewards API.
    Users only see their own earned rewards.
    """

    serializer_class = RewardSerializer
    permission_classes = [permissions.IsAuthenticated, IsRewardOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Reward.objects.all()

        # Normal users only see their own rewards
        return Reward.objects.filter(user=user).order_by("-earned_on")

        # Optional future filters:
        #   reward_type=milestone
        #   reward_type=savings
        #   is_visible=true
