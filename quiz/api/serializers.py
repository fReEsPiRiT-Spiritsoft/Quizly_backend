from rest_framework import serializers
from quiz.models import Quiz, Question


class QuestionSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for individual quiz questions.

    Exposes the question text, all four answer options, the correct answer,
    and creation / update timestamps.
    """

    class Meta:
        model  = Question
        fields = ('id', 'question_title', 'question_options', 'answer', 'created_at', 'updated_at')


class QuizSerializer(serializers.ModelSerializer):
    """
    Serializer for a complete quiz, including all nested questions.

    Questions are embedded as a read-only nested list using QuestionSerializer,
    so every quiz response already contains its full set of questions.
    """

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model  = Quiz
        fields = ('id', 'title', 'description', 'created_at', 'updated_at', 'video_url', 'questions')