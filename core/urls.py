# core/urls.py
from django.urls import path
from .views import UserDetailView, RegisterView, TestSeriesListView,TestDetailView,SubmitTestView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('test-series/', TestSeriesListView.as_view()),
    path('tests/<int:pk>/submit/', SubmitTestView.as_view(), name='submit-test'),
    path('tests/<int:pk>/', TestDetailView.as_view()),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
path('users/name/', UserDetailView.as_view(), name = 'user-detail')




]