# core/views.py
from rest_framework import generics
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from .models import CustomUser,Test, TestSeries, Question, TestResult, UserResponse, ExamName
from .serializers import ExamNameSerializer,TestResultListSerializer, TestSeriesListSerializer,TestResultDetailSerializer,QuestionSerializer, TestSectionSerializer, UserSerializer, LeaderboardSerializer,TestSeriesDetailSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import razorpay
import requests,os
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
        return Response(serializer.data) 
    

class SubmitTestView(APIView):
    """This API will save timer state every minute"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, format=None):
        test = get_object_or_404(Test,pk=pk)
        user = request.user
        answers = request.data.get('responses',[])
        score =0.0
        correct_count=0
        incorrect_count=0
        answered_count=0
        unanswered_count=0
        all_test_questions = Question.objects.filter(section__test=test)
        correct_answers = {q.id: q.correct_option for q in all_test_questions}
        user_answers_map={ans['question_id']:ans for ans in answers}
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
        responses_to_create=[]
        for question in all_test_questions:
            is_correct=False
            selected_answer=None
            marked_for_review=False
            if question.id in user_answers_map:
                user_answer_data=user_answers_map[question.id]
                selected_answer = user_answer_data.get('selected_answer')
                marked_for_review = user_answer_data.get('marked_for_review', False)
                if selected_answer:
                    answered_count +=1
                    if selected_answer.lower() == correct_answers[question.id]:
                        is_correct=True
                        correct_count += 1
                        score += float(test.marks_correct)
                    else:
                        incorrect_count += 1
                        score -= float(test.marks_incorrect)
                else:
                    unanswered_count += 1
            else:
                unanswered_count += 1
            responses_to_create.append(UserResponse(test_result=test_result, 
                question=question,
                selected_answer=selected_answer,
                marked_for_review=marked_for_review,
                is_correct=is_correct ))
        UserResponse.objects.filter(test_result=test_result).delete()
        UserResponse.objects.bulk_create(responses_to_create)
        TestResult.objects.filter(
            user=user, 
            test=test, 
            is_completed=False
        ).exclude(id=test_result.id).delete()

        test_result.score = score
        test_result.is_completed=True
        test_result.time_remaining=0
        test_result.save()
       
        # --- BUILD THE FINAL RESPONSE ---
        serializer = TestResultDetailSerializer(test_result)
      
        
        return Response(serializer.data, status=status.HTTP_200_OK)

class SaveTestProgressView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self, request, pk):
        time_remaining = request.data.get('time_remaining')
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
        ).order_by('-score', '-time_remaining')[:50]
