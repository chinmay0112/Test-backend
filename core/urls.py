# core/urls.py
from django.urls import path
from .views import UserDetailView,  TestSeriesListView,TestDetailView,SubmitTestView, QuestionListView, CompleteProfile, VerifyPaymentView,CreateOrderView

urlpatterns = [
    path('test-series/', TestSeriesListView.as_view()),
    path('tests/<int:pk>/submit/', SubmitTestView.as_view(), name='submit-test'),
    path('tests/<int:pk>/', TestDetailView.as_view()),
    path('users/me/', UserDetailView.as_view(), name = 'user-detail'),
# path('tests/<int:test_id>/questions/', QuestionListView.as_view(), name='question-list'),
path("auth/complete-profile/", CompleteProfile.as_view()),
path('payments/create-order/', CreateOrderView.as_view(), name='create-order'),
    path('payments/verify/', VerifyPaymentView.as_view(), name='verify-payment'),

]
