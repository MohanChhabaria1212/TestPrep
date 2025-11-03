from datetime import timedelta

from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from testprep.celery import app
from tests.enums import MultipleChoiceQuestionType, DifficultyType, ExamType
from tests.model_mixins import HashModelMixin, ActiveModelMixin

class Topic(HashModelMixin, ActiveModelMixin):
    title = models.CharField(max_length=128,unique=True,  db_index=True)
    created_by = models.ForeignKey(User, related_name='created_topics', blank=True, null=True,
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


class Exam(HashModelMixin, models.Model):
    title = models.CharField(max_length=128)
    duration = models.PositiveIntegerField(help_text='Duration in minutes')
    max_marks = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    exam_type = models.PositiveIntegerField(ExamType.choices, default=ExamType.CAT)
    start_timestamp = models.DateTimeField()
    end_timestamp = models.DateTimeField()
    topics = models.ManyToManyField(
        Topic,
        related_name='exams',
        through='ExamTopicMapping',
    )
    multiple_choice_questions = models.ManyToManyField(
        'MultipleChoiceQuestion',
        related_name='exams',
        through='ExamMultipleChoiceQuestionMapping',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    complete_exam_celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    completed = models.BooleanField(default=False)

    def clean(self):
        errors = {}

        if self.end_timestamp < self.start_timestamp:
            errors.setdefault('end_timestamp', []).append('End timestamp cannot be earlier than start timestamp.')

        if self.start_timestamp + timedelta(minutes=self.duration) > self.end_timestamp:
            errors.setdefault('duration', []).append('Duration exceeds the time between start and end timestamps.')

        if errors:
            raise ValidationError(errors)

@receiver(pre_save, sender=Exam)
def exam_pre_save(instance, **kwargs):
    exam = None
    if instance.id:
        try:
            exam = Exam.objects.get(pk=instance.pk)
        except Exam.DoesNotExist:
            pass
    else:
        exam = None
    instance.__old_instance = exam


@receiver(post_save,sender=Exam)
def exam_post_save(instance, created, **kwargs):
    from tests.tasks import compute_exam_leaderboard

    old_instance = getattr(instance,  '__old_instance', None)
    if not old_instance:
        complete_exam_celery_task = compute_exam_leaderboard.apply_async(
            (instance.id,),
            eta=instance.end_timestamp + timedelta(minutes=5)
        )
        instance.complete_exam_celery_task_id = complete_exam_celery_task.id
        instance.save(update_fields=['complete_exam_celery_task_id'])
    else:
        if old_instance.end_timestamp != instance.end_timestamp:
            if old_instance.complete_exam_celery_task_id:
                app.control.revoke(instance.end_video_session_celery_task_id, terminate=True)
            complete_exam_celery_task = compute_exam_leaderboard.apply_async(
                (instance.id,),
                eta=instance.end_timestamp + timedelta(minutes=5)
            )
            instance.complete_exam_celery_task_id = complete_exam_celery_task.id
            instance.save(update_fields=['complete_exam_celery_task_id'])




class ExamTopicMapping(models.Model):
    exam = models.ForeignKey(Exam,related_name='exam_topic_mapping', on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic,related_name='exam_topic_mapping', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('topic', 'exam')


class ExamMultipleChoiceQuestionMapping(models.Model):
    exam = models.ForeignKey(Exam, related_name='exam_multiple_choice_question_mappings', on_delete=models.CASCADE)
    multiple_choice_question = models.ForeignKey('MultipleChoiceQuestion',related_name='exam_multiple_choice_question_mappings', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('multiple_choice_question', 'exam')


class MultipleChoiceQuestion(ActiveModelMixin, models.Model):
    CHOICE_A = 1
    CHOICE_B = 2
    CHOICE_C = 3
    CHOICE_D = 4
    ANSWER_CHOICES = ((CHOICE_A, 'A'), (CHOICE_B, 'B'), (CHOICE_C, 'C'), (CHOICE_D, 'D'),)

    hash = models.CharField(max_length=15, null=True, blank=True, db_index=True)
    question_text = RichTextUploadingField(blank=True, null=True)

    question_type = models.PositiveIntegerField(
            choices=MultipleChoiceQuestionType.choices,
            default=MultipleChoiceQuestionType.MULTIPLE_CHOICE_QUESTION
    )

    choice_A_text = models.TextField(blank=True, null=True)
    choice_A_image = models.ImageField(upload_to='tests/questions/images', null=True, blank=True)
    choice_B_text = models.TextField(blank=True, null=True)
    choice_B_image = models.ImageField(upload_to='tests/questions/images', null=True, blank=True)
    choice_C_text = models.TextField(blank=True, null=True)
    choice_C_image = models.ImageField(upload_to='tests/questions/images', null=True, blank=True)
    choice_D_text = models.TextField(blank=True, null=True)
    choice_D_image = models.ImageField(upload_to='tests/questions/images', null=True, blank=True)
    correct_choice = models.PositiveIntegerField(choices=ANSWER_CHOICES, null=True, blank=True)
    correct_choice_explanation = models.TextField(blank=True, null=True)

    correct_puzzle_answer = models.CharField(max_length=255, null=True, blank=True)

    difficulty_level = models.PositiveIntegerField(choices=DifficultyType.choices, default=DifficultyType.EASY)
    topic = models.ForeignKey(
        Topic, related_name='multiple_choice_questions',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)


class ExamUserMapping(ActiveModelMixin, HashModelMixin, models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_timestamp = models.DateTimeField(auto_now_add=True)
    end_timestamp = models.DateTimeField(null=True, blank=True)
    total_score = models.PositiveIntegerField(null=True, blank=True)
    overall_percentile = models.DecimalField(null=True, blank=True, max_digits = 5, decimal_places=2)
    overall_rank = models.PositiveIntegerField(null=True, blank=True)
    subject_scores = models.JSONField(default=dict)
    subject_percentiles = models.JSONField(default=dict)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('exam', 'user')
        indexes = [
            models.Index(fields=['exam', 'user']),
            models.Index(fields=['user', 'exam']),
            models.Index(fields=['exam', 'completed']),
            models.Index(fields=['exam', '-total_score']),
            models.Index(fields=['exam', 'overall_percentile']),
            models.Index(fields=['exam', 'overall_rank']),
        ]

    def clean(self):
        errors = {}

        if self.end_timestamp and self.end_timestamp < self.start_timestamp:
            errors.setdefault('end_timestamp', []).append('End timestamp cannot be earlier than start timestamp.')

        if self.exam and self.start_timestamp < self.exam.start_timestamp:
            errors.setdefault('start_timestamp', []).append('End timestamp cannot be earlier than start timestamp.')

        if self.exam and self.end_timestamp and self.end_timestamp > self.exam.end_timestamp:
            errors.setdefault('end_timestamp', []).append('End timestamp cannot be earlier than start timestamp.')

        if errors:
            raise ValidationError(errors)


@receiver(pre_save, sender=ExamUserMapping)
def exam_user_mapping_pre_save(instance, **kwargs):
    exam_user_mapping = None
    if instance.id:
        try:
            exam_user_mapping = ExamUserMapping.objects.get(pk=instance.pk)
        except ExamUserMapping.DoesNotExist:
            pass
    else:
        exam_user_mapping = None
    instance.__old_instance = exam_user_mapping


@receiver(post_save, sender=ExamUserMapping)
def exam_user_mapping_post_save(instance=None, **kwargs):
    from tests.utils import update_score_for_exam_user_mapping, create_exam_user_multiple_choice_question_mappings

    old_instance = getattr(instance, '__old_instance', None)
    if old_instance:
        if not old_instance.completed and instance.completed:
            update_score_for_exam_user_mapping(instance)
    else:
        create_exam_user_multiple_choice_question_mappings(instance)


class ExamUserMultipleChoiceQuestionMapping(HashModelMixin, models.Model):
    exam_user_mapping = models.ForeignKey(ExamUserMapping,related_name='exam_user_multiple_choice_question_mappings', on_delete=models.CASCADE)
    multiple_choice_question = models.ForeignKey(MultipleChoiceQuestion,related_name='exam_user_multiple_choice_question_mappings', on_delete=models.CASCADE)
    selected_choice = models.PositiveIntegerField(choices=MultipleChoiceQuestion.ANSWER_CHOICES, null=True, blank=True)
    input_puzzle_answer = models.CharField(max_length=255, null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('exam_user_mapping', 'multiple_choice_question')
        indexes = [
            models.Index(fields=['exam_user_mapping', 'is_correct']),
            models.Index(fields=['exam_user_mapping', 'is_completed'])
        ]

    def get_is_correct(self):
        if not self.selected_choice and not self.input_puzzle_answer:
            return None
        if self.multiple_choice_question.question_type == MultipleChoiceQuestionType.MULTIPLE_CHOICE_QUESTION:
            return self.selected_choice == self.multiple_choice_question.correct_choice
        elif self.multiple_choice_question.question_type == MultipleChoiceQuestionType.PUZZLE_QUESTION:
            return (
                    (self.input_puzzle_answer or '').strip().lower() == (self.multiple_choice_question.correct_puzzle_answer or '').strip().lower()
            )
        return False


class UserExamTypeProfile(HashModelMixin, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam_type = models.PositiveIntegerField(choices=ExamType.choices, default=ExamType.CAT)
    total_tests_taken = models.PositiveIntegerField(default=0)
    average_percentile = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2)
    average_score = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2)
    highest_score = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'exam_type')


class UserTopicPerformanceProfile(HashModelMixin, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    total_questions_attempted = models.PositiveIntegerField(null=True, blank=True)
    correct_answers = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'topic')

    @property
    def accuracy(self):
        if self.correct_answers and self.total_questions_attempted:
            return (self.correct_answers / self.total_questions_attempted) * 100
        return 0


class PastExamStats(HashModelMixin, models.Model):
    exam_type = models.PositiveIntegerField(choices=ExamType.choices, default=ExamType.CAT)
    year = models.PositiveIntegerField()
    rank_vs_percentile_json = models.JSONField(default=dict)
    rank_vs_score_json = models.JSONField(default=dict)

