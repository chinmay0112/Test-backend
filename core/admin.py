from django.contrib import admin
from .models import ExamName,TestSeries,Test, Section, Question
# Register your models here.

admin.site.register(ExamName)
admin.site.register(TestSeries)
admin.site.register(Test)
admin.site.register(Section)
admin.site.register(Question)