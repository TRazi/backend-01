# config/views/session.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from config.utils.ratelimit import ratelimit  # you already have this helper


class SessionPingView(APIView):
    permission_classes = [IsAuthenticated]

    @ratelimit(key="user_or_ip", rate="30/m", method="POST")
    def post(self, request):
        # Simply bump last_activity
        request.session["last_activity"] = int(__import__("time").time())
        return Response(status=status.HTTP_204_NO_CONTENT)
