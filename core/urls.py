# core/urls.py
from django.urls import path, include
from .views import MarkNotificationReadView,ClearNotificationsView , NotificationListView, DashboardViewSet, SendOTPView,VerifyOTPView,TestLeaderboardView, UserDetailView,TestResultDetailView,TestResultListView ,SaveTestProgressView,TestSeriesDetailView, TestSeriesListView,TestDetailView,SubmitTestView, QuestionListView, CompleteProfile, VerifyPaymentView,CreateOrderView, ExamNameListView
from dj_rest_auth.registration.views import VerifyEmailView  # <--- IMPORT THIS
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
urlpatterns = [
    path('exam-names/', ExamNameListView.as_view()),
    path('test-series/', TestSeriesListView.as_view()),
    path('test-series/<int:pk>/', TestSeriesDetailView.as_view(),name='series-detail'),
    path('tests/<int:pk>/submit/', SubmitTestView.as_view(), name='submit-test'),
    path('tests/<int:pk>/', TestDetailView.as_view()),
    path('users/me/', UserDetailView.as_view(), name = 'user-detail'),
# path('tests/<int:test_id>/questions/', QuestionListView.as_view(), name='question-list'),
path("auth/complete-profile/", CompleteProfile.as_view()),
path('payments/create-order/', CreateOrderView.as_view(), name='create-order'),
    path('payments/verify/', VerifyPaymentView.as_view(), name='verify-payment'),
        path('auth/registration/verify-email/', VerifyEmailView.as_view(), name='rest_verify_email'),

    path('tests/<int:pk>/save-progress/', SaveTestProgressView.as_view(), name='save-progress'),
    path('notifications/', NotificationListView.as_view(), name='notifications-list'),
    path('notifications/mark-read/',MarkNotificationReadView.as_view(), name='notifications-mark-read'),
    path('notifications/clear/', ClearNotificationsView.as_view(), name='notifications-clear'),
    path('results/<int:pk>/', TestResultDetailView.as_view()),
        path('results/', TestResultListView.as_view(), name='result-list'),  
        path('tests/<int:pk>/leaderboard/', TestLeaderboardView.as_view(), name='test-leaderboard'), 
            path('auth/send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),  
        path('', include(router.urls)),   # <--- ADDED THIS


]
