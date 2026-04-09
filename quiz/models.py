from django.contrib.auth.models import User
from django.db import models


class Quiz(models.Model):
    owner      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quizzes')
    title      = models.CharField(max_length=255)
    description = models.TextField()
    video_url  = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz             = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_title   = models.CharField(max_length=500)
    question_options = models.JSONField()   # ["Option A", "Option B", "Option C", "Option D"]
    answer           = models.CharField(max_length=255)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question_title