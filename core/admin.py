# core/admin.py
from django.contrib import admin
from .models import CustomUser, ExamName, TestSeries, Test, Section, Question, UserResponse, TestResult
from import_export.admin import ImportExportModelAdmin
from .resources import QuestionResource
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'test', 'number_of_questions')
    search_fields = ('name', 'test__title') 



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
admin.site.register(Test)

admin.site.register(CustomUser)

class UserResponseInline(admin.TabularInline):
    model = UserResponse
    fields = ('question', 'selected_answer', 'is_correct', 'marked_for_review')
    readonly_fields = ('question', 'selected_answer', 'is_correct', 'marked_for_review')
    extra = 0
    can_delete = False

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_minutes', 'is_free')
    list_filter = ('test_series', 'is_free')
    search_fields = ('title',)