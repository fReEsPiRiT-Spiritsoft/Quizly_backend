from django.contrib import admin
from .models import Quiz, Question


class QuestionInline(admin.TabularInline):
    """
    Inline editor for questions, displayed within the Quiz change page.

    Questions are shown in a compact table format so they can be created,
    edited, and deleted without leaving the parent quiz form.
    """

    model = Question
    extra = 0
    fields = ('question_title', 'question_options', 'answer')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Quiz model.

    Displays quizzes with their owner and timestamps, supports full-text
    search by title and description, and embeds all related questions as
    an inline table on the quiz detail page.
    """

    list_display   = ('title', 'owner', 'created_at', 'updated_at')
    list_filter    = ('owner',)
    search_fields  = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines        = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Question model.

    Allows searching questions by their text and filtering the list by
    the parent quiz. Timestamps are read-only as they are set automatically.
    """

    list_display  = ('question_title', 'quiz', 'answer')
    list_filter   = ('quiz',)
    search_fields = ('question_title',)
    readonly_fields = ('created_at', 'updated_at')
