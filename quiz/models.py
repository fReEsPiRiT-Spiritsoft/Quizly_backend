from django.contrib.auth.models import User
from django.db import models


class Quiz(models.Model):
    """
    Represents a quiz generated from a YouTube video.

    Each quiz belongs to a single user (owner) and holds a title, a short
    description, the original video URL, and a set of related questions.
    """

    owner       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quizzes')
    title       = models.CharField(max_length=255)
    description = models.TextField()
    video_url   = models.URLField()
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Returns the quiz title as its string representation."""
        return self.title


class Question(models.Model):
    """
    Represents a single multiple-choice question belonging to a Quiz.

    The answer options are stored as a JSON array of exactly four strings.
    The correct answer must be one of the entries in question_options.
    """

    quiz             = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_title   = models.CharField(max_length=500)
    question_options = models.JSONField()   # ["Option A", "Option B", "Option C", "Option D"]
    answer           = models.CharField(max_length=255)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Returns the question text as its string representation."""
        return self.question_title