# core/views.py
from rest_framework import generics
from rest_framework.decorators import action
from django.db.models import Avg, Count, Sum
from django.db.models import Count, Q, Case, When, IntegerField
from .models import CustomUser,Test, TestSeries, Question, TestResult, UserResponse, ExamName
from .serializers import ExamNameSerializer,TestResultListSerializer, TestSeriesListSerializer,TestResultDetailSerializer,QuestionSerializer, TestSectionSerializer, UserSerializer, LeaderboardSerializer,TestSeriesDetailSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions,viewsets
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import razorpay
import requests,os
from django.db import transaction
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
class ExamNameListView(generics.ListAPIView):
    """
    Returns a list of all Exam Categories (e.g. SSC, Banking, Railways).
    Used for populating filter dropdowns on the frontend.
    """
    queryset = ExamName.objects.all()
    serializer_class = ExamNameSerializer

class TestSeriesListView(generics.ListAPIView):
    queryset = TestSeries.objects.all()
    serializer_class = TestSeriesListSerializer

class TestSeriesDetailView(generics.RetrieveAPIView):
    '''Returns specific list of test series like ssc mock1, ssc mock2'''
    queryset = TestSeries.objects.all()
    serializer_class = TestSeriesDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

class QuestionListView(generics.ListAPIView):
    serializer_class = QuestionSerializer

    def get_queryset(self):
        test_id = self.kwargs['test_id']
        return Question.objects.filter(section__test__id=test_id)
    
# This is the view that will serve our nested data
class TestDetailView(generics.RetrieveAPIView):
    """Returns the actual Exam Paper (Questions & Sections).
    SECURE: Checks if the user is allowed to access this specific test."""
    
    queryset = Test.objects.all()
    serializer_class = TestSectionSerializer
    permission_classes=[permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user=request.user
        if not instance.is_free and not getattr(user, 'is_pro_member', False):
            return Response(
                {"detail": "Access Denied: This test is locked for free users."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(instance)
        data = serializer.data

        # --- NEW LOGIC: INJECT SAVED PROGRESS ---
        # Check if there is an ongoing (incomplete) test for this user
        ongoing_result = TestResult.objects.filter(
            user=user, 
            test=instance, 
            is_completed=False
        ).first()

        if ongoing_result:
            # 1. Add Saved Time
            data['saved_time_remaining'] = ongoing_result.time_remaining
            
            # 2. Add Saved Responses
            saved_responses = UserResponse.objects.filter(test_result=ongoing_result).values(
                'question_id', 'selected_answer', 'marked_for_review'
            )
            data['saved_responses'] = list(saved_responses)
        else:
            data['saved_time_remaining'] = None
            data['saved_responses'] = []
        return Response(data) 
    

class SubmitTestView(APIView):
    """This API will save timer state every minute"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, format=None):
        # Start the atomic transaction block
        with transaction.atomic():
            test = get_object_or_404(Test, pk=pk)
            user = request.user
            answers = request.data.get('responses', [])
            score = 0.0
            correct_count = 0
            incorrect_count = 0
            answered_count = 0
            unanswered_count = 0
            
            all_test_questions = Question.objects.filter(section__test=test)
            correct_answers = {q.id: q.correct_option for q in all_test_questions}
            user_answers_map = {ans['question_id']: ans for ans in answers}

            # Get or Create TestResult
            test_result = TestResult.objects.filter(
                user=user, 
                test=test, 
                is_completed=False
            ).last()

            if not test_result:
                test_result = TestResult.objects.create(
                    user=user, 
                    test=test, 
                    is_completed=False,
                    score=0
                )

            # Now we will loop user answers and calculate score
            responses_to_create = []
            
            for question in all_test_questions:
                is_correct = False
                selected_answer = None
                marked_for_review = False

                if question.id in user_answers_map:
                    user_answer_data = user_answers_map[question.id]
                    selected_answer = user_answer_data.get('selected_answer')
                    marked_for_review = user_answer_data.get('marked_for_review', False)

                    if selected_answer:
                        answered_count += 1
                        if selected_answer.lower() == correct_answers[question.id]:
                            is_correct = True
                            correct_count += 1
                            score += float(test.marks_correct)
                        else:
                            incorrect_count += 1
                            score -= float(test.marks_incorrect)
                    else:
                        unanswered_count += 1
                else:
                    unanswered_count += 1

                # Add to bulk list
                responses_to_create.append(UserResponse(
                    test_result=test_result, 
                    question=question,
                    selected_answer=selected_answer,
                    marked_for_review=marked_for_review,
                    is_correct=is_correct
                ))

            # Database operations (Safe inside atomic block)
            # 1. Delete old responses for this result to avoid duplicates
            UserResponse.objects.filter(test_result=test_result).delete()
            
            # 2. Bulk create new responses
            UserResponse.objects.bulk_create(responses_to_create)
            
            # 3. Cleanup other incomplete attempts for this test/user
            TestResult.objects.filter(
                user=user, 
                test=test, 
                is_completed=False
            ).exclude(id=test_result.id).delete()

            # 4. Finalize Test Result
            test_result.score = score
            test_result.is_completed = True
            test_result.time_remaining = 0
            test_result.save()
       
        # --- BUILD THE FINAL RESPONSE (Outside atomic block) ---
        serializer = TestResultDetailSerializer(test_result)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SaveTestProgressView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self, request, pk):
        time_remaining = request.data.get('time_remaining')
        responses = request.data.get('responses', [])
        test=get_object_or_404(Test,pk=pk)
        test_result, created = TestResult.objects.get_or_create(
            user=request.user,
            test=test,
            is_completed=False,
            defaults={'time_remaining': test.duration_minutes * 60,'score':0.0}
        )
        if time_remaining is not None:
            test_result.time_remaining = time_remaining
            test_result.save()
        
        for resp in responses:
            question_id = resp.get('question_id')
            selected_answer = resp.get('selected_answer')
            marked_for_review = resp.get('marked_for_review', False)
            
            if question_id:
                # Update existing response or create new one
                UserResponse.objects.update_or_create(
                    test_result=test_result,
                    question_id=question_id,
                    defaults={
                        'selected_answer': selected_answer,
                        'marked_for_review': marked_for_review,
                        'is_correct': False # We don't grade yet
                    }
                )

        return Response({"status": "saved"}, status=status.HTTP_200_OK)


class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes=[permissions.IsAuthenticated]
    queryset = CustomUser.objects.all() 

    def get_object(self):
       return self.request.user 



User = get_user_model()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET =os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = "https://examprepare.netlify.app/google-callback"
class GoogleLogin(APIView):
    def post(self, request):
        code = request.data.get("code")

        if not code:
            return Response({"error": "No code provided"}, status=400)

        # 1. Exchange the authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        token_res = requests.post(token_url, data=token_data)
        token_json = token_res.json()

        if "id_token" not in token_json:
            return Response({"error": "Google token exchange failed", "details": token_json}, status=400)

        id_token = token_json["id_token"]

        # 2. Get Google user info
        user_info_url = f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={id_token}"
        user_info = requests.get(user_info_url).json()

        email = user_info.get("email")
        first_name = user_info.get("given_name", "")
        last_name = user_info.get("family_name", "")

        if not email:
            return Response({"error": "Google login failed (no email)"}, status=400)

        # 3. Create or fetch user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"first_name": first_name, "last_name": last_name},
        )

        # 4. Issue Django JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone":user.phone,
                "is_pro_member": user.is_pro_member,
            },"needs_profile": (
        user.phone is None or
        not user.first_name or
        not user.last_name
    )
        })
    
class CompleteProfile(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        phone = request.data.get("phone")

        if not first_name or not last_name or not phone:
            return Response({"error": "All fields are required"}, status=400)

        if User.objects.exclude(id=user.id).filter(phone=phone).exists():
            return Response({"error": "Phone already exists"}, status=400)

        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone
        user.save()

        return Response({"message": "Profile completed successfully"})

class CreateOrderView(APIView):
    permission_classes =[permissions.IsAuthenticated]

    def post(self,request):
        user = request.user
        plan_id = request.data.get('plan_id')
        amount = 0
        if plan_id == 'pro_yearly':
            amount = 29900
       
        else:
            return Response({'error':'Invalid plan ID'}, status = status.HTTP_400_BAD_REQUEST)
        
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            order=client.order.create({
                "amount":amount,
                "currency":"INR",
                "receipt":f"receipt_user_{user.id}_{plan_id}",
                "payment_capture":1
            })
            return Response({
                "order_id":order['id'],
                "amount":amount,
                "currency":"INR",
                'key_id': settings.RAZORPAY_KEY_ID, # Frontend needs this public key
                'user_email': user.email,

            },status=status.HTTP_200_OK)
        except Exception as e:
            return Response ({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class VerifyPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data

        # 1. Get the 3 pieces of payment data sent from the Angular client
        payment_id = data.get('razorpay_payment_id')
        order_id = data.get('razorpay_order_id')
        signature = data.get('razorpay_signature')

        if not all([payment_id, order_id, signature]):
            return Response({"error": "Missing payment details"}, status=status.HTTP_400_BAD_REQUEST)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # 2. CRUCIAL SECURITY CHECK: Verify the signature
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Invalid payment signature"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. If signature is valid, grant the user access
        user = request.user
        user.is_pro_member = True # This grants the Pro status
        user.pro_expiry_date = timezone.now() + timedelta(days=365)
        user.save()

        return Response({"status": "success", "message": "Payment verified and user upgraded!"}, status=status.HTTP_200_OK)
    

class TestResultListView(generics.ListAPIView):
    """
    Returns history of all completed tests (for Dashboard).
    """
    serializer_class = TestResultListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TestResult.objects.filter(
            user=self.request.user, 
            is_completed=True
        ).order_by('-completed_at')


class TestResultDetailView(generics.RetrieveAPIView):
    """
    Returns the detailed report card for a specific result.
    """
    serializer_class = TestResultDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TestResult.objects.filter(user=self.request.user)

class TestLeaderboardView(generics.ListAPIView):
    """
    Returns the top 50 students for a specific test.
    Sorted by Score (Desc) -> Time Remaining (Desc).
    """
    serializer_class = LeaderboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # getting test_id from URL: /api/tests/<pk>/leaderboard/
        test_id = self.kwargs['pk']
        
        return TestResult.objects.filter(
            test_id=test_id, 
            is_completed=True
        ).order_by('user','-score', '-time_remaining').distinct('user')
    def list(self, request, *args, **kwargs):
        test_id = self.kwargs['pk']
        
        queryset = TestResult.objects.filter(test_id=test_id, is_completed=True)\
            .order_by('user', '-score')\
            .distinct('user')
        sorted_results = sorted(
            queryset, 
            key=lambda x: (-x.score, -x.time_remaining)
        )[:50]

        for index, result in enumerate(sorted_results):
            result.rank = index + 1  # 1st item = Rank 1

        # 3. Serialize
        serializer = self.get_serializer(sorted_results, many=True)
        return Response(serializer.data)
    
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import PhoneOTP, CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
import random

# Helper to send OTP
def send_sms(phone, otp):
    # For Dev: Print to console
    print("-------------------------------------")
    print(f" OTP for {phone} is: {otp}")
    print("-------------------------------------")
    # For Prod: Use Twilio / MSG91 API here
    return True

class SendOTPView(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        if not phone:
            return Response({"error": "Phone number is required"}, status=400)

        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Save to DB (Update if exists, Create if new)
        obj, created = PhoneOTP.objects.update_or_create(
            phone_number=phone,
            defaults={'otp': otp}
        )
        
        # Increment count (optional spam protection)
        obj.count += 1
        obj.save()

        # Send
        send_sms(phone, otp)
        
        return Response({"message": "OTP sent successfully", "otp": otp}, status=200) # Remove "otp" from response in production!

class VerifyOTPView(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        otp = request.data.get('otp')

        if not phone or not otp:
            return Response({"error": "Phone and OTP are required"}, status=400)

        # 1. Verify OTP
        try:
            record = PhoneOTP.objects.get(phone_number=phone)
        except PhoneOTP.DoesNotExist:
            return Response({"error": "Invalid phone number"}, status=400)

        if record.otp != otp:
            return Response({"error": "Invalid OTP"}, status=400)

        # 2. Login or Create User
        user, created = CustomUser.objects.get_or_create(
            phone=phone,
            defaults={
                'username': phone, # Use phone as username if needed
                'email': f"{phone}@example.com" # Placeholder email
            }
        )
        
        # 3. Generate Token
        refresh = RefreshToken.for_user(user)
        
        # Clear OTP after success
        record.otp = "" 
        record.save()

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': user.id,
            'is_new_user': created
        })

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
  # 1. Performance Stats & Overall Accuracy (Top Row + Doughnut Chart)
    @action(detail=False, methods=['get'])
    def stats(self, request):
        user = request.user
        
        # Get all COMPLETED results
        completed_results = TestResult.objects.filter(user=user, is_completed=True)
        
        # 1. Tests Taken
        tests_taken = completed_results.count()

        # 2. Average Score
        avg_score = completed_results.aggregate(Avg('score'))['score__avg'] or 0
        
        # 3. Aggregated Counts for Accuracy Chart
        # We need to sum up correct/incorrect across ALL tests.
        # Efficient way: Filter UserResponse objects linked to completed tests.
        
        all_responses = UserResponse.objects.filter(
            test_result__user=user, 
            test_result__is_completed=True
        )
        
        # Correct Answers
        total_correct = all_responses.filter(is_correct=True).count()
        
        # Incorrect Answers (Attempted but wrong)
        # Note: We assume 'selected_answer' is not null for attempted questions
        total_incorrect = all_responses.filter(is_correct=False).exclude(selected_answer__isnull=True).count()
        
        # Questions Attempted
        questions_attempted = total_correct + total_incorrect

        # Skipped Questions Logic
        # This is harder to get from UserResponse if we don't save skipped rows.
        # But wait! Your SubmitTestView DOES save skipped rows (as None).
        # So we can just count them.
        total_skipped = all_responses.filter(selected_answer__isnull=True).count()
        
        # Total Questions Seen (Correct + Incorrect + Skipped)
        total_questions_seen = questions_attempted + total_skipped

        # 4. Overall Accuracy Calculation
        # Formula: (Total Correct / Total Questions Seen) * 100
        # OR: (Total Correct / Total Attempted) * 100 ? 
        # Usually "Accuracy" implies (Correct / Attempted). 
        # "Score Percentage" implies (Correct / Total Questions).
        # Let's stick to Accuracy (Correct / Attempted) for the stat card, 
        # but send all counts for the Pie Chart.
        
        overall_accuracy = 0
        if questions_attempted > 0:
            overall_accuracy = round((total_correct / questions_attempted) * 100, 1)

        return Response({
            "tests_taken": tests_taken,
            "avg_score": round(avg_score, 1),
            "questions_attempted": questions_attempted,
            "accuracy": overall_accuracy,
            "total_questions": total_questions_seen,
            
            # Extra data for Charts
            "chart_data": {
                "correct": total_correct,
                "incorrect": total_incorrect,
                "skipped": total_skipped
            }
        })
        # 2. Performance Trend (Line Chart)
    @action(detail=False, methods=['get'])
    def trend(self, request):
        user=request.user
        recent_results = TestResult.objects.filter(user=user, is_completed=True).order_by('-completed_at')[:10]
        data = []
        for result in reversed(recent_results):
            data.append({
                "test_title": result.test.title,
                "score": result.score,
                "date": result.completed_at.strftime("%b %d") # e.g. "Oct 18"
            })
            
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def resume(self, request):
        user = request.user
        # Find the most recently updated INCOMPLETE test
        pending_test = TestResult.objects.filter(user=user, is_completed=False).order_by('-last_updated').first()
        
        if pending_test:
            return Response({
                "id": pending_test.test.id,
                "name": pending_test.test.title,
                "category": pending_test.test.test_series.category.name, # Assuming relations exist
                "description": pending_test.test.test_series.description[:100] + "...", # Truncate description
                "lastActive": pending_test.last_updated.strftime("%b %d, %I:%M %p"), # "Oct 18, 10:30 AM"
                "progress_time": pending_test.time_remaining # You might use this to calculate % if needed
            })
        return Response("Yayy, you have no pending tests") # No pending test
    
    # 4. Recent Activity (Table)
    @action(detail=False, methods=['get'])
    def recent(self, request):
        user = request.user
        recent_results = TestResult.objects.filter(user=user, is_completed=True).order_by('-completed_at')[:5]
        
        data = []
        for result in recent_results:
            # Calculate accuracy for this specific test
            total_attempted = result.responses.exclude(selected_answer__isnull=True).count()
            correct = result.responses.filter(is_correct=True).count()
            accuracy = round((correct / total_attempted * 100), 1) if total_attempted > 0 else 0

            data.append({
                "id": result.id, # Result ID for navigation
                "name": result.test.title,
                "category": result.test.test_series.category.name,
                "score": result.score,
                "accuracy": accuracy,
                "date": result.completed_at.strftime("%b %d, %Y")
            })
            
        return Response(data)

    # 5. My Series (Sidebar) - Simplified for now
    # Ideally, this should calculate progress % for each series


    @action(detail=False, methods=['get'])
    def my_series(self, request):
        user = request.user
        
        # 1. THE OPTIMIZED QUERY
        # We fetch Series + Category + Counts in a single DB hit.
        all_series = TestSeries.objects.select_related('category').annotate(
            # Count total tests in this series
            total_tests_count=Count('test', distinct=True),
            
            # Count unique tests completed by THIS user in this series
            # We use filter=Q(...) to count only the relevant rows
            completed_tests_count=Count(
                'test__testresult',
                filter=Q(test__testresult__user=user, test__testresult__is_completed=True),
                distinct=True
            )
        )
        
        data = []
        
        # 2. THE LOOP (Pure Python Math, No DB Queries)
        for series in all_series:
            total = series.total_tests_count
            if total == 0: continue
            
            completed = series.completed_tests_count
            progress = round((completed / total) * 100)
            
            data.append({
                "id": series.id,
                "name": series.name,
                "category": series.category.name, # Already fetched via select_related
                "progress": progress,
                "icon": series.name[0]
            })
            
        return Response(data)
    