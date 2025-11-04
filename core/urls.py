# core/urls.py
from django.urls import path
from .views import UserDetailView,  TestSeriesListView,TestDetailView,SubmitTestView, QuestionListView

urlpatterns = [
    path('test-series/', TestSeriesListView.as_view()),
    path('tests/<int:pk>/submit/', SubmitTestView.as_view(), name='submit-test'),
    path('tests/<int:pk>/', TestDetailView.as_view()),
    path('users/me/', UserDetailView.as_view(), name = 'user-detail'),
path('tests/<int:test_id>/questions/', QuestionListView.as_view(), name='question-list'),


]