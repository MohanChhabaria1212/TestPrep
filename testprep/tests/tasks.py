from collections import defaultdict

import redis
from django.db import transaction
from django.utils import timezone

from testprep.celery import app
from tests.models import Exam, ExamUserMapping

@app.task(name="compute_exam_leaderboard")
def compute_exam_leaderboard(exam_id):
    lock_id = f''
    redis_cache = redis.StrictRedis()
    lock = redis_cache.lock(lock_id, blocking_timeout=0, timeout=60)

    if not lock.acquire():
        return False

    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        return False

    with transaction.atomic():
        incomplete_exam_user_mappings = ExamUserMapping.objects.filter(
            exam_id=exam_id, completed=False
        )
        for exam_user_mapping in incomplete_exam_user_mappings:
            exam_user_mapping.completed = True
            exam_user_mapping.completed_at = exam.end_timestamp
            exam_user_mapping.save(update_fields=['completed', 'completed_at'])

        exam_user_mappings = (
            ExamUserMapping.objects.filter(exam_id=exam.id)
            .exclude(total_score__isnull=True)
            .order_by("-total_score", "completed_at")
            .values("id", "total_score")
        )
        total_users = len(exam_user_mappings)
        now = timezone.now()

        for rank, exam_user_mapping in enumerate(exam_user_mappings, start=1):
            exam_user_mapping.overall_rank = rank
            exam_user_mapping.overall_percentile = round(100 * (1 - ((rank - 1) / total_users)), 2)


        subject_scores_map = defaultdict(list)
        for exam_user_mapping in exam_user_mappings:
            for subject, score in exam_user_mapping.subject_scores.items():
                subject_scores_map[subject].append(score)

        for subject in subject_scores_map:
            subject_scores_map[subject].sort(reverse=True)


        for exam_user_mapping in exam_user_mappings:
            subject_percentiles = {}
            for subject, score in exam_user_mapping.subject_scores.items():
                scores = subject_scores_map[subject]
                rank = scores.index(score) + 1
                percentile = round(100 * (1 - ((rank - 1) / len(scores))), 2)
                subject_percentiles[subject] = percentile

            exam_user_mapping.subject_percentiles = subject_percentiles

        ExamUserMapping.objects.bulk_update(
            exam_user_mappings,
            ["overall_rank", "overall_percentile", "subject_percentiles"],
            batch_size=5000,
        )

        exam.completed = True
        exam.save(update_fields=["completed",])
