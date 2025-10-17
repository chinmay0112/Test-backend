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
    option_a = models.CharField(max_length=10)
    option_b = models.CharField(max_length=10)
    option_c = models.CharField(max_length=10)
    option_d = models.CharField(max_length=10)
    correct_option = models.CharField(max_length=1,choices=[('a','A'), ('b','B'), ('c','C'), ('d','D')])
    explanation = models.TextField(blank=True)

    # class Meta:
    #     ordering =['id']

    def __str__(self):
        return f"{self.section.test} - {self.section.name} - {self.question_text[:30]}..."