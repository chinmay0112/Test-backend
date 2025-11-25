# core/views.py
from rest_framework import generics
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from .models import CustomUser,Test, TestSeries, Question, TestResult, UserResponse
from .serializers import TestSeriesListSerializer,QuestionResultSerializer,QuestionSerializer, TestDetailSerializer, UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import razorpay
import requests,os
from django.conf import settings
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

class SubmitTestView(APIView):
    # permission_classes = [permissions.IsAuthenticated] # Good to add this back later

    def post(self, request, pk, format=None):
        test = get_object_or_404(Test,pk=pk)
        # user = request.user ##use when using production
        user = CustomUser.objects.get(pk=1) # Use the hardcoded admin user
        answers = request.data.get('responses',[])
        score =0.0
        correct_count=0
        incorrect_count=0
        answered_count=0
        unanswered_count=0
        all_test_questions = Question.objects.filter(section__test=test)
        correct_answers = {q.id: q.correct_option for q in all_test_questions}
        user_answers_map={ans['question_id']:ans for ans in answers}
        test_result = TestResult.objects.create(user=user, test=test, score=score)
# Now we will loop user answers and calculate score
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
            
            UserResponse.objects.create(
                test_result=test_result, 
                question=question,
                selected_answer=selected_answer,
                marked_for_review=marked_for_review,
                is_correct=is_correct  # <-- Pylance warning is now fixed
            )

        test_result.score = score
        test_result.save()
        question_details = QuestionResultSerializer(all_test_questions, many=True).data
        for question_data in question_details:
            q_id = question_data['id']
            if q_id in user_answers_map:
                question_data['user_answer'] = user_answers_map[q_id].get('selected_answer')
                if question_data['user_answer']:
                    question_data['is_correct'] = (user_answers_map[q_id].get('selected_answer', '').lower() == correct_answers[q_id])
            else:
                question_data['user_answer'] = None
                question_data['is_correct'] = False

        # --- BUILD THE FINAL RESPONSE ---
        final_report = {
            "score": score,
            "total_questions": all_test_questions.count(),
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "unanswered_count": unanswered_count,
            "test_details": {
                "title": test.title,
                "marks_correct": test.marks_correct,
                "marks_incorrect": test.marks_incorrect,
            },
            "full_results": question_details,
        }
        
        return Response(final_report, status=status.HTTP_200_OK)


# class RegisterView(generics.CreateAPIView):
#     queryset = CustomUser.objects.all()
#     serializer_class = UserSerializer         
      

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
        if plan_id == 'pro_monthly':
            amount = 29900
        elif plan_id == 'pro_yearly':
            amount = 249900
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