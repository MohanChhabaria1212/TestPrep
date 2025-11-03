from collections import defaultdict

from numpy import interp
from cacheops import cached_as
from django.db import transaction
from django.db.models import FloatField, F, Window
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Rank

from tests.enums import ExamType
from tests.models import ExamUserMapping, ExamUserMultipleChoiceQuestionMapping, Topic

from tests.models import UserExamTypeProfile, UserTopicPerformanceProfile


def update_score_for_exam_user_mapping(exam_user_mapping: ExamUserMapping):
    exam = exam_user_mapping.exam
    exam_user_multiple_choice_question_mappings = ExamUserMultipleChoiceQuestionMapping.objects.filter(
        exam_user_mapping=exam_user_mapping,
        completed=True
    ).select_related('multiple_choice_question__topic')

    correct_answer_multiplier = ExamType.get_marks_per_correct(exam.exam_type)
    incorrect_answer_multiplier = ExamType.get_negative_marks_per_wrong(exam.exam_type)

    score_dict = defaultdict(lambda: {'correct': 0, 'incorrect': 0})
    total_score = 0
    for exam_user_multiple_choice_question_mapping in exam_user_multiple_choice_question_mappings:
        topic = exam_user_multiple_choice_question_mapping.multiple_choice_question.topic
        correct = exam_user_multiple_choice_question_mapping.get_is_correct()
        if correct is True:
            score_dict[topic.title]['correct']  += 1
            total_score += correct_answer_multiplier
        elif correct is False:
            score_dict[topic.title]['incorrect']  += 1
            total_score -= incorrect_answer_multiplier

    subject_scores = {}
    for topic_title in score_dict:
        correct_count = score_dict[topic_title].get('correct', 0)
        incorrect_count = score_dict[topic_title].get('incorrect', 0)
        score = correct_count * correct_answer_multiplier - incorrect_count * incorrect_answer_multiplier
        subject_scores[topic_title] = score

        topic = Topic.objects.get(title=topic_title)
        user_topic_performance_profile, _ = UserTopicPerformanceProfile.objects.get_or_create(
            user=exam_user_mapping.user,
            topic=topic
        )
        user_topic_performance_profile.total_questions_attempted = correct_count + incorrect_count + (user_topic_performance_profile.total_questions_attempted or 0)
        user_topic_performance_profile.correct_answers = correct_count + (user_topic_performance_profile.correct_answers or 0)
        user_topic_performance_profile.save(update_fields=['total_questions_attempted', 'correct_answers'])


    user_exam_type_profile, _ = UserExamTypeProfile.objects.get_or_create(
        user=exam_user_mapping.user,
        exam_type=exam.exam_type
    )
    user_exam_type_profile.total_tests_taken = (user_exam_type_profile.total_tests_taken or 0) + 1
    previous_average_score = user_exam_type_profile.average_score or 0
    user_exam_type_profile.average_score = (
        (previous_average_score * (user_exam_type_profile.total_tests_taken - 1)) + total_score
    ) / user_exam_type_profile.total_tests_taken
    if user_exam_type_profile.highest_score is None or total_score > user_exam_type_profile.highest_score:
        user_exam_type_profile.highest_score = total_score
    user_exam_type_profile.save(update_fields=['total_tests_taken', 'average_score', 'highest_score'])




def create_exam_user_multiple_choice_question_mappings(exam_user_mapping: ExamUserMapping):
    exam = exam_user_mapping.exam

    multiple_choice_question_ids = exam.exam_multiple_choice_question_mappings.values_list('multiple_choice_question_id', flat=True)
    exam_user_multiple_choice_question_mappings = []

    with transaction.atomic():
        for multiple_choice_question_id in multiple_choice_question_ids:
            exam_user_multiple_choice_question_mapping = ExamUserMultipleChoiceQuestionMapping.objects.create(
                exam_user_mapping=exam_user_mapping,
                multiple_choice_question_id=multiple_choice_question_id
            )
            exam_user_multiple_choice_question_mappings.append(exam_user_multiple_choice_question_mapping)

    UserExamTypeProfile.objects.get_or_create(
        user=exam_user_mapping.user,
        exam_type=exam.exam_type
    )

    topic_ids = exam.exam_topic_mappings.values_list('topic_id', flat=True)
    for topic_id in topic_ids:
        UserTopicPerformanceProfile.objects.get_or_create(
            user=exam_user_mapping.user,
            topic_id=topic_id
        )



def get_subject_leaderboard_queryset(exam_id: int, topic_title: str):

    @cached_as(ExamUserMapping.objects.filter(exam_id=exam_id))
    def _get_subject_leaderboard_queryset(exam_id: int, topic_title: str):
        return (
            ExamUserMapping.objects.filter(exam_id=exam_id)
            .exclude(subject_percentiles__isnull=True)
            .annotate(
                subj_percentile=Cast(
                    KeyTextTransform(topic_title, F("subject_percentiles")),
                    FloatField(),
                )
            )
            .annotate(
                rank=Window(
                    expression=Rank(),
                    order_by=F("subj_percentile").desc(),
                )
            )
            .select_related("user")
            .order_by("subj_rank")
        )

    return _get_subject_leaderboard_queryset(exam_id, topic_title)


def _interpolate(x, x_points, y_points):

    if not x_points or not y_points:
        return None

    x_points = list(map(float, x_points))
    y_points = list(map(float, y_points))
    x_points, y_points = zip(*sorted(zip(x_points, y_points)))

    if x <= x_points[0]:
        slope = (y_points[1] - y_points[0]) / (x_points[1] - x_points[0])
        return y_points[0] + slope * (x - x_points[0])
    elif x >= x_points[-1]:
        slope = (y_points[-1] - y_points[-2]) / (x_points[-1] - x_points[-2])
        return y_points[-1] + slope * (x - x_points[-1])
    else:
        return float(interp(x, x_points, y_points))


def predict_rank_from_score_and_percentile(score , past_stats):

    score_map = past_stats.rank_vs_score_json or {}
    rank_map = past_stats.rank_vs_percentile_json or {}

    if score_map:
        score_points = list(score_map.keys())
        percentile_points = list(score_map.values())
        predicted_percentile = _interpolate(score, score_points, percentile_points)
    else:
        predicted_percentile = None


    predicted_rank = None
    if predicted_percentile and rank_map:
        rank_points = list(rank_map.keys())
        rank_percentiles = list(rank_map.values())
        predicted_rank = _interpolate(predicted_percentile, rank_percentiles[::-1], rank_points[::-1])

    if predicted_rank is None and predicted_percentile:
        predicted_rank = int(max(1, (100 - predicted_percentile) * 100))

    if predicted_percentile is None and rank_map:
        rank_points = sorted(map(int, rank_map.keys()))
        predicted_rank = rank_points[len(rank_points) // 2]

    return {
        "predicted_percentile": round(predicted_percentile or 0.0, 2),
        "predicted_rank": int(round(predicted_rank or 0))
    }