from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from knox.views import LoginView as KnoxLoginView
from rest_framework import status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializer

__all__ = [
    "LoginAPI",
    "SessionLoginAPI",
    "UserDetailAPI",
]


class LoginAPI(KnoxLoginView):
    """Login API view that uses Knox for token-based authentication."""

    permission_classes = [AllowAny]

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return super().post(request, format=None)


class SessionLoginAPI(APIView):
    """Login API view that uses Django's session authentication."""

    permission_classes = [AllowAny]

    def post(self, request):
        form = AuthenticationForm(request, data=request.data)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailAPI(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
