from django.db import models


class MultipleChoiceQuestionType(models.IntegerChoices):
    MULTIPLE_CHOICE_QUESTION = 1, 'Multiple Choice Question'
    PUZZLE_QUESTION = 2, 'Puzzle Question'

class DifficultyType(models.IntegerChoices):
    EASY = 1, 'Easy'
    MEDIUM = 2, 'Medium'
    HARD = 3, 'Hard'

class ExamType(models.IntegerChoices):
    CAT = 1, 'CAT'
    GATE = 2, 'GATE'
    JEE_MAIN = 3, 'JEE Main'
    JEE_ADVANCED = 4, 'JEE Advanced'
    NEET = 5, 'NEET'

    @staticmethod
    def get_marks_per_correct(exam_type):
        marks_mapping = {
            ExamType.CAT: 5,
            ExamType.GATE: 4,
            ExamType.JEE_MAIN: 4,
            ExamType.JEE_ADVANCED: 4,
            ExamType.NEET: 4,
        }
        return marks_mapping.get(exam_type, 0)

    @staticmethod
    def get_negative_marks_per_wrong(exam_type):
        negative_marks_mapping = {
            ExamType.CAT: 1,
            ExamType.GATE: 1,
            ExamType.JEE_MAIN: 1,
            ExamType.JEE_ADVANCED: 1,
            ExamType.NEET: 1,
        }
        return negative_marks_mapping.get(exam_type, 0)



