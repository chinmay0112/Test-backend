# core/models.py
from django.db import models
from django.contrib.auth.models import User


class ExamName(models.Model):
    """Exam name is SSC, Bank etc"""
    name=models.CharField(max_length=100)

    def __str__(self):
        return self.name
    

class TestSeries(models.Model):
    """Like SSC CGL, SSC CHSL"""
    name=models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(ExamName,on_delete=models.CASCADE)
 
    def __str__(self):
        return self.name
    
class Test(models.Model):
    """Like SSC CGL Mock 1, SSC CGL Mock 2 etc"""
    title = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField()    
    test_series = models.ForeignKey(TestSeries,on_delete=models.CASCADE)
    marks_correct = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    marks_incorrect = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    def __str__(self):
        return self.title

class Section(models.Model):
    name=models.CharField(max_length=100)
    number_of_questions =models.PositiveIntegerField()
    test = models.ForeignKey(Test, related_name='sections', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.test.title} - {self.name}"
    

class Question(models.Model):
    section = models.ForeignKey(Section,related_name='questions',on_delete=models.CASCADE)
    question_text = models.TextField()
    option_a = models.CharField(max_length=15)
    option_b = models.CharField(max_length=15)
    option_c = models.CharField(max_length=15)
    option_d = models.CharField(max_length=15)
    correct_option = models.CharField(max_length=1,choices=[('a','A'), ('b','B'), ('c','C'), ('d','D')])
    explanation = models.TextField(blank=True)

    # class Meta:
    #     ordering =['id']

    def __str__(self):
        return f"{self.section.test} - {self.section.name} - {self.question_text[:30]}..."
    


    

# Add these two new classes to the end of your core/models.py file

class TestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    score = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.test.title}"


# --- THIS IS THE CORRECTED MODEL ---
class UserResponse(models.Model):
    # This is the new, direct parent-child link.
    test_result = models.ForeignKey(TestResult, related_name='responses', on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1, blank=True, null=True)
    marked_for_review = models.BooleanField(default=False)
    
   

    def __str__(self):
        return f"Response for Q{self.question.id}"