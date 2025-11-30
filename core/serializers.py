# core/serializers.py
from rest_framework import serializers
# Make sure to import all your models, including Section
from .models import CustomUser, TestResult, TestSeries, Test, Section, Question
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework.validators import UniqueValidator
from django.core.validators import RegexValidator
from django.db.models import Sum
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # These are the "safe" fields to show to a logged-in user
        fields = ('id', 'email', 'phone', 'first_name', 'last_name','is_pro_member')
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
class TestSectionSerializer(serializers.ModelSerializer):
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
    first_name = serializers.CharField(max_length=255, required=True)
    last_name = serializers.CharField(max_length=255, required=True)

    phone = serializers.CharField(
        max_length=15,
       required=True,
        validators=[
            RegexValidator(
                regex=r'^\+?\d{7,15}$',
                message="Enter a valid phone number (7–15 digits, optional +)."
            ),
            UniqueValidator(
                queryset=CustomUser.objects.all(),
                message="A user with this phone number already exists."
            ),
        ],
    )

    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=CustomUser.objects.all(),
                message="A user with this email already exists."
            ),
        ],
    )

    def validate_phone(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Phone number is required.")
        return str(value).strip()

    def get_cleaned_data(self):
        """
        Combine parent cleaned data with our custom fields.
        """
        data = super().get_cleaned_data()
        data.update({
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'phone': self.validated_data.get('phone', None),
            'email': self.validated_data.get('email', ''),
        })
        return data

    def save(self, request):
        """
        Create user and assign extra fields.
        """
        user = super().save(request)
        user.first_name = self.validated_data.get('first_name', '')
        user.last_name = self.validated_data.get('last_name', '')
        phone = self.validated_data.get('phone', None)

        # Store NULL (not '') for phone if not provided
        user.phone = phone if phone else None
        user.email = self.validated_data.get('email', user.email)
        user.save()
        return user
    
class TestStatusSerializer(serializers.ModelSerializer):
    status=serializers.SerializerMethodField()
    resultId=serializers.SerializerMethodField()
    number_of_questions=serializers.SerializerMethodField()

    class Meta:
        model=Test
        fields=['id',
                'title',
                'duration_minutes',
                'number_of_questions',
                'marks_correct',
                'status',
                'resultId']
        def get_number_of_questions(self,obj):
            total = obj.sections.aggregate(total_q = Sum('number_of_questions'))['total_q']
            return total or 0
        def get_user_result(self, obj):
            user = self.context.get('request').user
            if user and user.is_authenticated:
                return TestResult.objects.filter(user=user, test=obj).first()
            return None

    def get_status(self, obj):
        result = self.get_user_result(obj)
        if result:
            return 'Completed'
        return 'Not Started'

    def get_resultId(self, obj):
        result = self.get_user_result(obj)
        if result:
            return result.id
        return None

class TestSeriesDetailSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    # This is the line you asked about:
    tests = TestStatusSerializer(many=True, read_only=True) 
    testsCompleted = serializers.SerializerMethodField()
    testsTotal = serializers.SerializerMethodField()

    class Meta:
        model = TestSeries
        fields = [
            'id', 
            'name', 
            'category', 
            'description', 
            'testsCompleted', 
            'testsTotal', 
            'tests'
        ]

    def get_testsTotal(self, obj):
        return obj.tests.count()

    def get_testsCompleted(self, obj):
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return TestResult.objects.filter(user=user, test__series=obj).count()
        return 0