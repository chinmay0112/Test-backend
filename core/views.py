# core/views.py
from rest_framework import generics
from .models import Test, TestSeries, Question, User
from .serializers import TestSeriesListSerializer,QuestionSerializer, TestDetailSerializer
class TestSeriesListView(generics.ListAPIView):
    queryset = TestSeries.objects.all()
    serializer_class = TestSeriesListSerializer

class QuestionListView(generics.ListAPIView):
    serializer_class = QuestionSerializer

    def get_queryset(self):
        test_id = self.kwargs['test_id']
        return Question.objects.filter(section__test__id=test_id)
    
# This is the view that will serve our nested data
class TestDetailView(generics.RetrieveAPIView):
    queryset = Test.objects.all()
    serializer_class = TestDetailSerializer