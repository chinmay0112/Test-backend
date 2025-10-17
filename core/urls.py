# core/urls.py
from django.urls import path
from .views import TestSeriesListView,TestDetailView

urlpatterns = [
    path('test-series/', TestSeriesListView.as_view()),
    path('tests/<int:pk>/', TestDetailView.as_view()),




]