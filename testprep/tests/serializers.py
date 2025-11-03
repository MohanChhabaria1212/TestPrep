from django.contrib.auth.models import User
from rest_framework import serializers

from tests.models import ExamUserMapping, Exam, ExamUserMultipleChoiceQuestionMapping, MultipleChoiceQuestion


class MultipleChoiceQuestionFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = MultipleChoiceQuestion
        fields = (
            'hash','question_text','question_type','choice_A_text','choice_A_image','choice_B_text','choice_B_image',
            'choice_C_text','choice_C_image','choice_D_text','choice_D_image','correct_choice',
            'correct_choice_explanation','correct_puzzle_answer','difficulty_level','topic','created_at',
        )


class MultipleChoiceQuestionWithoutAnswerSerializer(MultipleChoiceQuestionFullSerializer):
    class Meta:
        model = MultipleChoiceQuestion
        fields = (
            'hash', 'question_text', 'question_type', 'choice_A_text', 'choice_A_image', 'choice_B_text',
            'choice_B_image','choice_C_text', 'choice_C_image', 'choice_D_text', 'choice_D_image','difficulty_level',
            'topic', 'created_at',
        )


class ExamUserMultipleChoiceQuestionMappingSerializer(serializers.ModelSerializer):
    multiple_choice_question = MultipleChoiceQuestionWithoutAnswerSerializer()

    class Meta:
        model = ExamUserMultipleChoiceQuestionMapping
        fields = (
            'hash',
            'multiple_choice_question',
            'selected_choice',
            'input_puzzle_answer',
            'created_at',
            'completed_at',
            'is_completed',
        )


class ExamUserMultipleChoiceQuestionMappingFullSerializer(ExamUserMultipleChoiceQuestionMappingSerializer):
    multiple_choice_question = MultipleChoiceQuestionFullSerializer()

    class Meta(ExamUserMultipleChoiceQuestionMappingSerializer.Meta):
        fields = ExamUserMultipleChoiceQuestionMappingSerializer.Meta.fields + ('is_correct',)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')


class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ('title','duration','max_marks','year','exam_type','start_timestamp','end_timestamp')



class ExamUserMappingFullSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    exam = ExamSerializer()
    exam_user_multiple_choice_question_mappings = serializers.SerializerMethodField()

    class Meta:
        model = ExamUserMapping
        fields =  (
            'user', 'exam','hash', 'start_timestamp', 'end_timestamp', 'total_score', 'overall_percentile','overall_rank',
            'subject_scores','subject_percentiles','completed', 'exam_user_multiple_choice_question_mappings'
        )

    def get_exam_user_multiple_choice_question_mappings(self, obj):
        exam_user_multiple_choice_question_mappings = obj.exam_user_multiple_choice_question_mappings.select_related(
            'multiple_choice_question'
        ).all()
        include_answers = self.context.get(
            'include_answers',bool(obj.completed)
        )
        serializer_class = ExamUserMultipleChoiceQuestionMappingFullSerializer if include_answers else ExamUserMultipleChoiceQuestionMappingSerializer
        serializer = serializer_class(
            exam_user_multiple_choice_question_mappings,
            many=True,
            context=self.context
        )
        return serializer.data

class ExamUserMappingMinimumSerializer(ExamUserMappingFullSerializer):

    class Meta:
        model = ExamUserMapping
        fields = ('user','exam','start_timestamp', 'end_timestamp', 'hash')


class ExamLeaderboardSerializer(ExamUserMappingFullSerializer):
    subject_score = serializers.SerializerMethodField()
    subject_percentile = serializers.SerializerMethodField()
    subject_rank = serializers.SerializerMethodField()

    class Meta:
        model = ExamUserMapping
        fields = (
            'user', 'exam', 'hash', 'start_timestamp', 'end_timestamp', 'total_score', 'overall_percentile',
            'subject_score','subject_percentile','subject_rank','overall_rank',
        )

    def get_subject_score(self, obj):
        topic = self.context.get("topic")
        if not topic:
            return None
        return obj.subject_scores.get(topic.title, None)

    def get_subject_percentile(self, obj):
        topic = self.context.get("topic")
        if not topic:
            return None
        return obj.subject_percentiles.get(topic.title, None)

    def get_subject_rank(self, obj):
        topic = self.context.get("topic")
        if not topic:
            return None
        return getattr(obj,'rank', None)
