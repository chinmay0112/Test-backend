# core/urls.py
from django.urls import path
from .views import TestSeriesListView,TestDetailView,SubmitTestView

urlpatterns = [
    path('test-series/', TestSeriesListView.as_view()),
    path('tests/<int:pk>/submit/', SubmitTestView.as_view(), name='submit-test'),
    path('tests/<int:pk>/', TestDetailView.as_view()),
        





]