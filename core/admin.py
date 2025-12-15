# core/admin.py
from django.contrib import admin
from .models import CustomUser, PhoneOTP,ExamName, TestSeries, Test, Section, Question, UserResponse, TestResult, TestStage
from import_export.admin import ImportExportModelAdmin
from .resources import QuestionResource
from django import forms
from .ai_utils import generate_questions_from_ai
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
class AIQuestionForm(forms.Form):
    topic = forms.CharField(
        max_length=200, 
        help_text="e.g. 'Indian History - Mughal Empire' or paste a paragraph.",
        widget=forms.Textarea(attrs={'rows': 3})
    )
    count = forms.IntegerField(
        min_value=1, 
        max_value=20, 
        initial=5, 
        help_text="Number of questions to generate (Max 20 at a time)."
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        help_text="Which section should these questions belong to?"
    )
    difficulty = forms.ChoiceField(
        choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')],
        initial='Medium'
    )


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'test', 'number_of_questions')
    search_fields = ('name', 'test__title') 



# --- Notice we are inheriting from admin.ModelAdmin ---
@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin): # <-- Corrected here
    resource_class = QuestionResource
    change_list_template = "admin/question_changelist.html" # Use custom template
    
    # Display columns
    list_display = ('id', 'question_text', 'section', 'correct_option')
    
    # Clickable links
    list_display_links = ('id', 'question_text')
    
    # Filters sidebar
    list_filter = ('section__test__test_series', 'section__test', 'section')
    
    # Search bar
    search_fields = ('question_text', 'explanation')
    
    # Searchable dropdown for Section (prevents freezing)
    autocomplete_fields = ['section']

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('generate-ai/', self.admin_site.admin_view(self.generate_ai_view), name='question_generate_ai'),
        ]
        return my_urls + urls

    def generate_ai_view(self, request):
        if request.method == "POST":
            form = AIQuestionForm(request.POST)
            if form.is_valid():
                topic = form.cleaned_data['topic']
                count = form.cleaned_data['count']
                section = form.cleaned_data['section']
                difficulty = form.cleaned_data['difficulty']

                # 1. Call AI
                questions_data = generate_questions_from_ai(topic, count, difficulty)
                
                if not questions_data:
                    messages.error(request, "AI failed to generate questions. Try a simpler topic.")
                    return redirect("..")

                # 2. Save to DB
                created_count = 0
                for q in questions_data:
                    Question.objects.create(
                        section=section,
                        question_text=q['question_text'],
                        option_a=q['option_a'],
                        option_b=q['option_b'],
                        option_c=q['option_c'],
                        option_d=q['option_d'],
                        correct_option=q['correct_option'].lower(),
                        explanation=q['explanation']
                    )
                    created_count += 1
                
                messages.success(request, f"Successfully created {created_count} questions from AI!")
                return redirect("..") # Go back to question list
        else:
            form = AIQuestionForm()

        context = dict(
           self.admin_site.each_context(request),
           form=form,
           title="Generate Questions with AI"
        )
        return render(request, "admin/ai_generate_form.html", context)
  


class UserResponseInline(admin.TabularInline):
    model = UserResponse
    fields = ('question', 'selected_answer', 'is_correct', 'marked_for_review')
    readonly_fields = ('question', 'selected_answer', 'is_correct', 'marked_for_review')
    extra = 0
    can_delete = False


# --- And here we are inheriting from admin.ModelAdmin ---
@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin): # <-- Corrected here
    list_display = ('id', 'submission_summary', 'score', 'completed_at')
    list_filter = ('test', 'user')
    search_fields = ('user__email', 'test__title')
    list_display_links = ('submission_summary',)
    inlines = [UserResponseInline]

    # This custom method is correct
    def submission_summary(self, obj):
        return f"{obj.user.first_name} - {obj.test.title}"
    submission_summary.short_description = 'Submission'


# --- These simple registrations are fine ---
admin.site.register(ExamName)
admin.site.register(TestSeries)
admin.site.register(TestStage)
admin.site.register(PhoneOTP)
admin.site.register(CustomUser)



@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_minutes', 'is_free')
    list_filter = ('test_series', 'is_free')
    search_fields = ('title',)