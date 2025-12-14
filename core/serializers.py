# core/serializers.py
from rest_framework import serializers
# Make sure to import all your models, including Section
from .models import CustomUser, TestResult, TestSeries, Test, Section, Question, ExamName, TestStage
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework.validators import UniqueValidator
from django.core.validators import RegexValidator
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate

class ExamNameSerializer(serializers.ModelSerializer):
    class Meta:
        model=ExamName
        fields=['id','name']
class UserSerializer(serializers.ModelSerializer):
    is_pro_active = serializers.BooleanField(read_only=True)
    streak = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        # These are the "safe" fields to show to a logged-in user
        fields = ('id', 'email', 'phone', 'first_name', 'last_name','is_pro_member','pro_expiry_date', 'is_pro_active', 'streak')
        
        def get_streak(self, obj):
        # Get all completed tests for this user
            completed_results = TestResult.objects.filter(user=obj, is_completed=True).order_by('-completed_at')
        
        # Get distinct dates of activity
            activity_dates = completed_results.annotate(
            date=TruncDate('completed_at')
            ).values_list('date', flat=True).distinct()

            current_streak = 0
            if activity_dates:
                today = timezone.now().date()
            last_activity = activity_dates[0]

            # Check if active today or yesterday
            if last_activity == today or last_activity == (today - timedelta(days=1)):
                current_streak = 1
                previous_date = last_activity
                
                # Count backwards
                for date in activity_dates[1:]:
                    if date == previous_date - timedelta(days=1):
                        current_streak += 1
                        previous_date = date
                    else:
                        break
            else:
                current_streak = 0
                
            return current_streak


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
    saved_time_remaining=serializers.SerializerMethodField()
    class Meta:
        model = Test
        fields = ['id', 'title', 'duration_minutes', 'sections','saved_time_remaining']
    
    def get_saved_time_remaining(self, obj):
        user = self.context.get('request').user
        if user and user.is_authenticated:
            active_attempt = TestResult.objects.filter(user=user, test=obj, is_completed=False).first()
            if active_attempt:
                return active_attempt.time_remaining
            return None


from .models import UserResponse

class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserResponse
        fields = ['user', 'test', 'question', 'selected_answer', 'marked_for_review']

class QuestionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option','explanation','section']

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
                return TestResult.objects.filter(user=user, test=obj, is_completed=True).order_by('-completed_at').first()
            return None

    def get_status(self, obj):
        user = self.context.get('request').user
        if not user or not user.is_authenticated:
            return 'Not Started'
        active = TestResult.objects.filter(user=user, test=obj, is_completed=False).order_by('-last_updated').first()
        if active:
            return 'Continue'
        completed = TestResult.objects.filter(user=user, test=obj, is_completed=True).order_by('-last_updated').first()
        if completed:
            return 'Completed'

        return 'Not Started'

        

    def get_resultId(self, obj):
        result = self.get_user_result(obj)
        if result:
            return result.id
        return None

class TestStageSerializer(serializers.ModelSerializer):
    # This fetches the tests linked to this stage
    tests = TestStatusSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestStage
        fields = ['id', 'name', 'tests']

class TestSeriesDetailSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    # This is the line you asked about:
    # tests = TestStatusSerializer(many=True, read_only=True,source='test_set') 
    stages = TestStageSerializer(many=True, read_only=True)
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
            'stages'
        ]

    def get_testsTotal(self, obj):
        return obj.test_set.count()

    def get_testsCompleted(self, obj):
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return TestResult.objects.filter(user=user, test__test_series=obj, is_completed=True).values('test').distinct().count()
        return 0


# Result and analysis serializers
class UserResponseDetailSerializer(serializers.ModelSerializer):
    question = QuestionResultSerializer(read_only=True) # Nested question details
    
    class Meta:
        model = UserResponse
        fields = ['id', 'question', 'selected_answer', 'is_correct', 'marked_for_review']
class TestResultDetailSerializer(serializers.ModelSerializer):
    test_title=serializers.ReadOnlyField(source='test.title')
    total_questions = serializers.SerializerMethodField()
    correct_count = serializers.SerializerMethodField()
    incorrect_count = serializers.SerializerMethodField()
    unanswered_count = serializers.SerializerMethodField()
    accuracy = serializers.SerializerMethodField()
    marks_correct = serializers.ReadOnlyField(source='test.marks_correct')
    marks_incorrect = serializers.ReadOnlyField(source='test.marks_incorrect')
    percentile=serializers.SerializerMethodField()
    # section wise breakdown
    section_analysis = serializers.SerializerMethodField()
    responses = UserResponseDetailSerializer(many=True, read_only=True)
    class Meta:
        model = TestResult
        fields = [
             'id', 'test','test_title', 'score', 'time_remaining', 'completed_at',
            'total_questions', 'correct_count', 'incorrect_count', 
            'unanswered_count', 'accuracy', 
            'section_analysis',
            'responses', 'marks_correct', 'marks_incorrect', 'percentile'
        ]
        
    def get_total_questions(self, obj):
        return obj.responses.count()
    
    def get_correct_count(self, obj):
        return obj.responses.filter(is_correct=True).count()

    def get_incorrect_count(self, obj):
        # Incorrect = Answered but is_correct is False
        return obj.responses.filter(is_correct=False).exclude(selected_answer__isnull=True).count()

    def get_unanswered_count(self, obj):
        return obj.responses.filter(selected_answer__isnull=True).count()

    def get_accuracy(self, obj):
        total_attempted = obj.responses.exclude(selected_answer__isnull=True).count()
        correct = obj.responses.filter(is_correct=True).count()
        if total_attempted > 0:
            return round((correct / total_attempted) * 100, 2)
        return 0

    def get_percentile(self, obj):
        # 'obj' is the current TestResult (for the current user)
        
        # A. Get all COMPLETED results for this specific Test ID
        # We only care about people who actually finished the test
        all_attempts = TestResult.objects.filter(test=obj.test, is_completed=True)
        best_attempts = all_attempts.order_by('user', '-score').distinct('user')
        
        total_students = best_attempts.count()
        
        if total_students <= 1:
            return 100.00 # If you are the only one, you are top 100%

        # B. Count how many people scored LESS than the current user
        # 'score__lt' means "Score Less Than"
        students_behind = sum(1 for attempt in best_attempts if attempt.score < obj.score)
        
        # 4. Formula
        percentile_val = (students_behind / total_students) * 100
        return round(percentile_val, 2)


    def get_section_analysis(self, obj):
        analysis_data = []
        
        # 1. Get all sections for this test
        sections = obj.test.sections.all()
        
        for section in sections:
            # 2. Filter user responses belonging to this section
            # We use double underscore: question__section
            section_responses = obj.responses.filter(question__section=section)
            
            # 3. Calculate Stats
            total = section.number_of_questions
            attempted = section_responses.exclude(selected_answer__isnull=True).count()
            correct = section_responses.filter(is_correct=True).count()
            incorrect = section_responses.filter(is_correct=False).exclude(selected_answer__isnull=True).count()
            skipped = total - attempted
            
            accuracy = 0
            if attempted > 0:
                accuracy = round((correct / attempted) * 100, 1)

            analysis_data.append({
                "section_name": section.name,
                "section_id": section.id,
                "total_questions": total,
                "attempted": attempted,
                "correct": correct,
                "incorrect": incorrect,
                "skipped": skipped,
                "accuracy": accuracy
            })
            
        return analysis_data

class TestResultListSerializer(serializers.ModelSerializer):
    test_title = serializers.ReadOnlyField(source='test.title')
    series_name = serializers.ReadOnlyField(source='test.test_series.name')
    
    class Meta:
        model = TestResult
        fields = ['id', 'test_title', 'series_name', 'score', 'is_completed', 'completed_at']


# core/serializers.py

class LeaderboardSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    accuracy = serializers.SerializerMethodField()
    rank = serializers.IntegerField(read_only=True) 

    class Meta:
        model = TestResult
        # Only send what is needed for the table
        fields = ['rank','student_name', 'score', 'accuracy', 'time_remaining', 'completed_at']

    def get_student_name(self, obj):
        # Combine First + Last Name. 
        # Optional: You can mask the last name for privacy (e.g. "Aniket S.")
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email.split('@')[0]

    def get_accuracy(self, obj):
        # Calculate accuracy on the fly
        total_attempted = obj.responses.exclude(selected_answer__isnull=True).count()
        if total_attempted == 0:
            return 0.0
        correct = obj.responses.filter(is_correct=True).count()
        return round((correct / total_attempted) * 100, 1)