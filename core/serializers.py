# core/serializers.py
from rest_framework import serializers
# Make sure to import all your models, including Section
from .models import CustomUser,  TestSeries, Test, Section, Question
from dj_rest_auth.registration.serializers import RegisterSerializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username', 'phone', 'full_name', 'password')
        extra_kwargs={
            'password':{'write_only':True}
        }
    def create(self, validated_data):
        # Call the special create_user method from your CustomUserManager
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            phone=validated_data['phone'],
            full_name=validated_data['full_name'],
            password=validated_data['password']
        )
        return user


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
            username = serializers.CharField(max_length=150)
            full_name = serializers.CharField(max_length=255)
            phone = serializers.CharField(max_length=15)

    # This method is the "magic" that connects your new fields
    # to your CustomUser model's create_user method.
            def get_cleaned_data(self):
        # Get the default data (email, password)
                data = super().get_cleaned_data()

        # Add your custom fields from the validated data
                data['username'] = self.validated_data.get('username', '')
                data['full_name'] = self.validated_data.get('full_name', '')
                data['phone'] = self.validated_data.get('phone', '')

                return data