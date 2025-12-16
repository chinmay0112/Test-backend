# core/admin.py
from django.contrib import admin
from .models import CustomUser, PhoneOTP,ExamName, TestSeries, Test, Section, Question, UserResponse, TestResult, TestStage
from import_export.admin import ImportExportModelAdmin
from .resources import QuestionResource
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import render, redirect
from .ai_utils import generate_questions_from_ai
from .forms import AIQuestionForm
from django.contrib import messages
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'test', 'number_of_questions', 'ai_actions')
    search_fields = ('name', 'test__title')
    
    # 1. Register the custom URL
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:section_id>/generate-questions/',
                self.admin_site.admin_view(self.generate_questions_view),
                name='section-generate-ai',
            ),
        ]
        return custom_urls + urls

    # 2. Add the Button to the List View
    def ai_actions(self, obj):
        return format_html(
            '<a class="button" style="background-color: #28a745; color: white;" href="{}">Generate AI Questions</a>',
            f"{obj.id}/generate-questions/"
        )
    ai_actions.short_description = "AI Tools"
    ai_actions.allow_tags = True

    # 3. The View Logic
    def generate_questions_view(self, request, section_id):
        # Get the section or 404
        section = Section.objects.get(pk=section_id)
        
        if request.method == 'POST':
            form = AIQuestionForm(request.POST)
            if form.is_valid():
                topic = form.cleaned_data['topic']
                count = form.cleaned_data['num_questions']
                difficulty = form.cleaned_data['difficulty']

                # Notify user
                self.message_user(request, "AI is generating questions, please wait...", level=messages.INFO)
                
                try:
                    questions_data = generate_questions_from_ai(topic, count, difficulty)
                    
                    if questions_data:
                        count_created = 0
                        for q in questions_data:
                            # CREATE QUESTION OBJECT
                            Question.objects.create(
                                section=section,
                                question_text=q.get('question_text'),
                                option_a=q.get('option_a'), # Updated keys
                                option_b=q.get('option_b'),
                                option_c=q.get('option_c'),
                                option_d=q.get('option_d'),
                                # This will now save 'option_a', 'option_b' etc. as the correct answer
                                correct_option=q.get('correct_option'), 
                                explanation=q.get('explanation')
                            )
                            count_created += 1
                        
                        self.message_user(request, f"Success! Added {count_created} questions about '{topic}'.", level=messages.SUCCESS)
                        return redirect('admin:core_section_change', section_id)
                    else:
                        self.message_user(request, "AI returned empty data. Please try again.", level=messages.ERROR)
                
                except Exception as e:
                    self.message_user(request, f"Error: {str(e)}", level=messages.ERROR)

        else:
            form = AIQuestionForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'section': section,
            'opts': self.model._meta,
            'title': f"Generate Questions for {section.name}"
        }
        
        # CRITICAL FIX: Render the correct template, NOT 'question_changelist.html'
        return render(request, 'admin/question_changelist.html', context)



# --- Notice we are inheriting from admin.ModelAdmin ---
@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin): # <-- Corrected here
    resource_class = QuestionResource
    
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