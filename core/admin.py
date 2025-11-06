# core/admin.py
from django.contrib import admin
from .models import CustomUser, ExamName, TestSeries, Test, Section, Question, UserResponse, TestResult

# --- Notice we are inheriting from admin.ModelAdmin ---
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin): # <-- Corrected here
    list_display = ('id', 'question_text', 'section')
    list_filter = ('section__test', 'section')
    search_fields = ('question_text', 'explanation')


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
admin.site.register(Section)
admin.site.register(CustomUser)