from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("health/", views.HealthView.as_view()),
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("documents/", views.DocumentListView.as_view()),
    path("documents/upload/", views.UploadView.as_view()),
    path("documents/<int:pk>/", views.DocumentDetailView.as_view()),
    path("ask/", views.AskView.as_view()),
]