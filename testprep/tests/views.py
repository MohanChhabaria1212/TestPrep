from datetime import timedelta

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from tests.models import Exam, ExamUserMapping, ExamUserMultipleChoiceQuestionMapping, Topic
from tests.serializers import ExamUserMappingFullSerializer, ExamUserMappingMinimumSerializer, \
    ExamLeaderboardSerializer
from tests.utils import get_subject_leaderboard_queryset

from tests.models import PastExamStats
from tests.utils import predict_rank_from_score_and_percentile


class ExamBaseView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        exam_hash = kwargs.get('hash_exam')
        try:
            exam = Exam.objects.get(hash=exam_hash)
        except Exam.DoesNotExist:
            exam = None

        request.exam = exam


class ExamUserMappingBaseView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        exam_user_mapping_hash = kwargs.get('hash_exam_user_mapping')
        try:
            exam_user_mapping = ExamUserMapping.objects.get(hash=exam_user_mapping_hash)
        except ExamUserMapping.DoesNotExist:
            exam_user_mapping = None
        request.exam_user_mapping = exam_user_mapping


class ExamUserMappingCreateView(ExamBaseView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        exam = request.exam

        if not exam:
            raise NotFound(detail="Exam not found.")
        now = timezone.now()
        if exam.completed or exam.end_timestamp <= now:
            raise ValidationError({
                "exam": "Cannot start mapping for a completed or expired exam."
            })

        try:
            exam_user_mapping = ExamUserMapping.objects.get(
                exam=exam,
                user=request.user
            )
        except ExamUserMapping.DoesNotExist:
            exam_user_mapping = None

        request.exam_user_mapping = exam_user_mapping

    @staticmethod
    def post(request, *args, **kwargs):
        exam_user_mapping = request.exam_user_mapping

        now = timezone.now()
        if exam_user_mapping:
            return Response(ExamUserMappingMinimumSerializer(exam_user_mapping).data, status=200)


        duration = request.exam.duration
        start_timestamp = now + timedelta(minutes=1)
        end_timestamp = start_timestamp + timedelta(minutes=duration) + timedelta(seconds=30)
        exam_user_mapping = ExamUserMapping.objects.create(
            exam = request.exam,
            user = request.user,
            start_timestamp = start_timestamp,
            end_timestamp = end_timestamp,
        )
        return Response(ExamUserMappingMinimumSerializer(exam_user_mapping).data, status=201)


class ExamUserMappingDetailView(ExamUserMappingBaseView):
    @staticmethod
    def get(request, *args, **kwargs):
        exam_user_mapping = request.exam_user_mapping

        if not exam_user_mapping:
            raise NotFound(detail="Exam user mapping not found.")

        include_answers = bool(exam_user_mapping.completed)
        serializer = ExamUserMappingFullSerializer(
            exam_user_mapping,
            context={
                'request': request,
                'include_answers': include_answers,
            }
        )
        return Response(serializer.data, status=200)

    @staticmethod
    def put(request, *args, **kwargs):
        exam_user_mapping = request.exam_user_mapping

        if not exam_user_mapping:
            raise NotFound(detail="Exam user mapping not found.")

        if exam_user_mapping.completed:
            return Response(
                {
                    "message": "Exam already marked as completed.",
                    "status": 400
                },
                status=400
            )

        with transaction.atomic():
            exam_user_mapping.refresh_from_db()
            now = timezone.now()
            exam_user_mapping.completed = True
            exam_user_mapping.completed_at = now
            exam_user_mapping.save(update_fields=['completed', 'completed_at'])

        return Response(
            {
                "message": "Exam marked as completed.",
                "status": 200
            },
            status=200
        )


class ExamUserMultipleChoiceQuestionMappingSubmitView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        exam_user_multiple_choice_question_mapping_hash = kwargs.get('hash_exam_user_multiple_choice_question_mapping')
        try:
            exam_user_multiple_choice_question_mapping = ExamUserMultipleChoiceQuestionMapping.objects.get(
                hash=exam_user_multiple_choice_question_mapping_hash
            )
        except ExamUserMapping.DoesNotExist:
            raise ValidationError({
                "message": "Exam user multiple choice question mapping not found."
            })
        now = timezone.now()
        if exam_user_multiple_choice_question_mapping.exam_user_mapping.completed or \
           exam_user_multiple_choice_question_mapping.exam_user_mapping.end_timestamp <= now:
            raise ValidationError({
                "message": "Cannot submit answer for a completed or expired exam."
            })

        request.exam_user_multiple_choice_question_mapping = exam_user_multiple_choice_question_mapping

    @staticmethod
    def put(request, *args, **kwargs):
        exam_user_multiple_choice_question_mapping = request.exam_user_multiple_choice_question_mapping
        selected_choice = request.data.get('selected_choice')
        if not selected_choice:
            return Response({
                "message": "Selected choice is required."
            }, status=400)

        exam_user_multiple_choice_question_mapping.selected_choice = selected_choice
        exam_user_multiple_choice_question_mapping.is_completed = True
        exam_user_multiple_choice_question_mapping.completed_at = timezone.now()
        exam_user_multiple_choice_question_mapping.is_correct = exam_user_multiple_choice_question_mapping.get_is_correct()
        exam_user_multiple_choice_question_mapping.save(
            update_fields=['selected_choice', 'is_completed', 'completed_at', 'is_correct']
        )

        return Response(
            {
                "message": "Answer submitted successfully.",
            },status=200
        )


class LeaderboardPagination(LimitOffsetPagination):
    default_limit = 100
    max_limit = 500


class ExamLeaderboardView(ListAPIView, ExamBaseView):
    serializer_class = ExamLeaderboardSerializer
    pagination_class = LeaderboardPagination

    def initial(self, request, *args, **kwargs):
        exam = self.request.exam
        if not exam or not exam.completed:
            raise NotFound(detail="Exam not found or leaderboard not available.")

        try:
            exam_user_mapping = ExamUserMapping.objects.filter(exam=exam)
        except ExamUserMapping.DoesNotExist:
            return PermissionDenied()

        request.exam_user_mapping = exam_user_mapping

    def get_queryset(self):
        request = self.request
        exam = request.exam

        percentile = self.request.query_params.get("percentile", False)
        subject_hash = self.request.query_params.get("subject_hash")

        queryset = ExamUserMapping.objects.filter(exam=exam).select_related("user")

        if subject_hash:
            try:
                topic = Topic.objects.get(hash=subject_hash)
                request.topic = topic
            except Topic.DoesNotExist:

                return ExamUserMapping.objects.none()

            queryset = get_subject_leaderboard_queryset(exam.id, topic.title)
            return queryset
        else:
            request.topic = None

        order_field = "-overall_percentile" if percentile else "overall_rank"
        return queryset.order_by(order_field)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["topic"] = getattr(self.request, "topic", None)
        return context


class ExamResultPredictView(ExamUserMappingBaseView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        exam_user_mapping = request.exam_user_mapping

        if not exam_user_mapping or not exam_user_mapping.completed:
            raise NotFound(detail="Exam user mapping not found or exam not completed.")

    @staticmethod
    def get(request, *args, **kwargs):
        exam_user_mapping = request.exam_user_mapping
        exam_year = exam_user_mapping.exam.year

        prediction_year = exam_year - 1
        try:
            prediction_stats = PastExamStats.objects.get(
                    exam_year = prediction_year,
                    exam_type = exam_user_mapping.exam.exam_type
            )
        except PastExamStats.DoesNotExist:
            return Response({
                "message": "Prediction data not available for the given exam year and type."
            }, status=404)

        exam = exam_user_mapping.exam
        score = exam_user_mapping.total_score or 0
        prediction = predict_rank_from_score_and_percentile(score, prediction_stats)

        return Response(
            {
                "exam": exam.title,
                "exam_year": exam.year,
                "prediction_based_on": exam.year - 1,
                "user_score": score,
                **prediction
            },
            status=200,
        )



