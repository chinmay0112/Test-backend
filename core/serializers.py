# core/serializers.py
from rest_framework import serializers
# Make sure to import all your models, including Section
from .models import CustomUser,  TestSeries, Test, Section, Question
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework.validators import UniqueValidator
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # These are the "safe" fields to show to a logged-in user
        fields = ('id', 'email', 'phone', 'first_name', 'last_name')
        # We DO NOT include 'password' here


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

class CustomRegisterSerializer(RegisterSerializer):
    # These are the extra fields your form will send
            first_name = serializers.CharField(max_length=255)
            last_name = serializers.CharField(max_length=255)
            phone = serializers.CharField(
        max_length=15,
        validators=[
            UniqueValidator(
                queryset=CustomUser.objects.all(),
                message="A user with this phone number already exists."
            )
        ]
    )
            email = serializers.CharField(
        max_length=255,
        validators=[
            UniqueValidator(
                queryset=CustomUser.objects.all(),
                message="A user with this email already exists."
            )
        ]
    )
            
    # This method is the "magic" that connects your new fields
    # to your CustomUser model's create_user method.
            def get_cleaned_data(self):
        # Get the default data (email, password)
                data = super().get_cleaned_data()

        # Add your custom fields from the validated data
                data['first_name'] = self.validated_data.get('first_name', '')
                data['last_name'] = self.validated_data.get('last_name', '')
                data['phone'] = self.validated_data.get('phone', ''),
                data['email'] = self.validated_data.get('email', '')


                return data