# apps/users/views_mfa.py
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers_mfa import (
    MFABeginSetupSerializer,
    MFAConfirmSetupSerializer,
    MFABackupCodeVerifySerializer,
)
from .services.mfa import generate_provisioning_uri


class MFABeginSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Optionally restrict to certain roles or staff
        provisioning_uri = generate_provisioning_uri(request.user)
        serializer = MFABeginSetupSerializer({"provisioning_uri": provisioning_uri})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MFAConfirmSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MFAConfirmSetupSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)


class MFABackupCodeVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MFABackupCodeVerifySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
