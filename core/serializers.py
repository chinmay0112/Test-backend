# core/serializers.py
from rest_framework import serializers
# Make sure to import all your models, including Section
from .models import  TestSeries, Test, Section, Question
from django.contrib.auth.models import User


class TestSeriesListSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = TestSeries
        fields = ['id', 'name', 'description', 'category']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d']


# LEVEL 2: A Section, which contains a list of Questions.
class SectionSerializer(serializers.ModelSerializer):
    # This line uses the simple QuestionSerializer to create a nested list.
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ['id', 'name', 'number_of_questions', 'questions']


# LEVEL 1: The main serializer for a Test, containing its Sections.
class TestDetailSerializer(serializers.ModelSerializer):
    # This line uses the SectionSerializer to create the final nested structure.
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = ['id', 'title', 'duration_minutes', 'sections']


from .models import UserResponse

class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserResponse
        fields = ['user', 'test', 'question', 'selected_answer', 'marked_for_review']

class QuestionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option','explanation']