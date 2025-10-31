# core/views.py
from rest_framework import generics
from .models import CustomUser,Test, TestSeries, Question, User, TestResult
from .serializers import TestSeriesListSerializer,QuestionResultSerializer,QuestionSerializer, TestDetailSerializer, UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .models import Test, Question, UserResponse # Use your UserResponse model
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



# core/views.py

# ... import other models and serializers ...

# ... keep your TestDetailView and other views ...

class SubmitTestView(APIView):
    # permission_classes = [permissions.IsAuthenticated] # Good to add this back later

    def post(self, request, pk, format=None):
        test = get_object_or_404(Test,pk=pk)
        user = User.objects.get(pk=1)
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


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer         
      


