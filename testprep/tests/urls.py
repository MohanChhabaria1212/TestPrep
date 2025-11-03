from django.urls import path

from .views import (
    ExamLeaderboardView,
    ExamUserMappingCreateView,
    ExamUserMappingDetailView,
    ExamUserMultipleChoiceQuestionMappingSubmitView,
)

app_name = "tests"

urlpatterns = [
      path(
          "exams/<str:hash_exam>/start/",
          ExamUserMappingCreateView.as_view(),
          name="exam-user-mapping-create",
      ),
      path(
          "exam-user-mappings/<str:hash_exam_user_mapping>/",
          ExamUserMappingDetailView.as_view(),
          name="exam-user-mapping-detail",
      ),
      path(
          "exam-user-multiple-choice-question-mappings/<str:hash_exam_user_multiple_choice_question_mapping>/submit/",
          ExamUserMultipleChoiceQuestionMappingSubmitView.as_view(),
          name="exam-user-mcq-submit",
      ),
      path(
          "exams/<str:hash_exam>/leaderboard/",
          ExamLeaderboardView.as_view(),
          name="exam-leaderboard",
      ),
  ]

