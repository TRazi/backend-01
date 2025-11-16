# apps/users/views_auth.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers_auth import MFATokenObtainPairSerializer


class MFATokenObtainPairView(TokenObtainPairView):
    serializer_class = MFATokenObtainPairSerializer
