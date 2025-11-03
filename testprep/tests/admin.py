from django.contrib import admin

from .models import (
    Exam,
    ExamMultipleChoiceQuestionMapping,
    ExamTopicMapping,
    ExamUserMapping,
    ExamUserMultipleChoiceQuestionMapping,
    MultipleChoiceQuestion,
    Topic,
    UserExamTypeProfile,
    UserTopicPerformanceProfile,
)


class ExamTopicMappingInline(admin.TabularInline):
    model = ExamTopicMapping
    extra = 1
    autocomplete_fields = ("topic",)


class ExamMultipleChoiceQuestionMappingInline(admin.TabularInline):
    model = ExamMultipleChoiceQuestionMapping
    extra = 1
    autocomplete_fields = ("multiple_choice_question",)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "created_by__username")
    readonly_fields = ("hash", "created_at")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "exam_type",
        "start_timestamp",
        "end_timestamp",
        "duration",
        "max_marks",
    )
    list_filter = ("exam_type", "start_timestamp", "end_timestamp", "completed")
    search_fields = ("title", "topics__title")
    inlines = [ExamTopicMappingInline, ExamMultipleChoiceQuestionMappingInline]
    readonly_fields = ("hash", "created_at", "complete_exam_celery_task_id")


@admin.register(MultipleChoiceQuestion)
class MultipleChoiceQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "question_type", "difficulty_level", "is_active")
    list_filter = ("question_type", "difficulty_level", "is_active")
    search_fields = ("question_text", "topic__title", "hash")
    readonly_fields = ("hash", "created_at")


@admin.register(ExamUserMapping)
class ExamUserMappingAdmin(admin.ModelAdmin):
    list_display = (
        "exam",
        "user",
        "start_timestamp",
        "end_timestamp",
        "total_score",
        "completed",
    )
    list_filter = ("completed", "exam")
    search_fields = (
        "exam__title",
        "user__username",
        "user__email",
    )
    readonly_fields = ("start_timestamp",)
    autocomplete_fields = ("exam", "user")


@admin.register(ExamTopicMapping)
class ExamTopicMappingAdmin(admin.ModelAdmin):
    list_display = ("exam", "topic", "created_at")
    list_filter = ("exam", "topic")
    search_fields = ("exam__title", "topic__title")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("exam", "topic")


@admin.register(ExamMultipleChoiceQuestionMapping)
class ExamMultipleChoiceQuestionMappingAdmin(admin.ModelAdmin):
    list_display = ("exam", "multiple_choice_question", "created_at")
    list_filter = ("exam",)
    search_fields = ("exam__title", "multiple_choice_question__hash")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("exam", "multiple_choice_question")


@admin.register(ExamUserMultipleChoiceQuestionMapping)
class ExamUserMultipleChoiceQuestionMappingAdmin(admin.ModelAdmin):
    list_display = (
        "exam_user_mapping",
        "multiple_choice_question",
        "selected_choice",
        "is_correct",
        "is_completed",
        "completed_at",
    )
    list_filter = ("is_correct", "is_completed")
    search_fields = (
        "exam_user_mapping__exam__title",
        "exam_user_mapping__user__username",
        "multiple_choice_question__hash",
    )
    readonly_fields = ("hash", "created_at")
    autocomplete_fields = ("exam_user_mapping", "multiple_choice_question")


@admin.register(UserExamTypeProfile)
class UserExamTypeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "exam_type", "total_tests_taken", "average_percentile")
    list_filter = ("exam_type",)
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user",)


@admin.register(UserTopicPerformanceProfile)
class UserTopicPerformanceProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "topic",
        "total_questions_attempted",
        "correct_answers",
        "accuracy",
    )
    list_filter = ("topic",)
    search_fields = ("user__username", "user__email", "topic__title")
    autocomplete_fields = ("user", "topic")
