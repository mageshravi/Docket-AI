from django.urls import path
from knox import views as knox_views

from .views import LoginAPI, SessionLoginAPI, SessionLogoutAPI, UserDetailAPI

app_name = "core"
urlpatterns = [
    path("login/", SessionLoginAPI.as_view(), name="session_login"),
    path("logout/", SessionLogoutAPI.as_view(), name="session_logout"),
    path("knox/login/", LoginAPI.as_view(), name="login"),
    path("knox/logout/", knox_views.LogoutView.as_view(), name="logout"),
    path("knox/logout/all/", knox_views.LogoutAllView.as_view(), name="logout_all"),
    path("users/me/", UserDetailAPI.as_view(), name="user_detail"),
]
