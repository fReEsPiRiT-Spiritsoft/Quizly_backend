import traceback

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth.authentication import CookieJWTAuthentication
from quiz.models import Quiz, Question
from quiz.api.serializers import QuizSerializer
from quiz.services import extract_video_id, get_transcript, generate_quiz_from_transcript


class QuizListCreateView(APIView):
    """
    Handles listing all quizzes and creating a new quiz for the authenticated user.

    GET  /api/quizzes/  — Returns all quizzes owned by the current user.
    POST /api/quizzes/  — Accepts a YouTube URL and generates a new quiz via Gemini AI.
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        """
        Returns a list of all quizzes that belong to the authenticated user,
        with all nested questions pre-fetched in a single query.
        """
        quizzes = Quiz.objects.filter(owner=request.user).prefetch_related('questions')
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Generates and saves a new quiz from a YouTube video URL.

        Workflow:
          1. Validates that a YouTube URL was provided and is recognisable.
          2. Downloads the audio via yt-dlp and transcribes it with Gemini.
          3. Uses Gemini to produce 10 multiple-choice questions from the transcript.
          4. Persists the Quiz and all Questions to the database.

        Expects: { "url": "<youtube_url>" }
        Returns 201 with the created quiz on success.
        Returns 400 for invalid URLs or AI-related errors, 500 for unexpected failures.
        """
        url = request.data.get('url', '').strip()
        if not url:
            return Response({'detail': 'URL is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not extract_video_id(url):
            return Response({'detail': 'Invalid YouTube URL.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transcript = get_transcript(url)
            quiz_data  = generate_quiz_from_transcript(transcript, url)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()   # vollständiger Fehler im Server-Log
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        quiz = Quiz.objects.create(
            owner       = request.user,
            title       = quiz_data['title'],
            description = quiz_data['description'],
            video_url   = url,
        )
        for q in quiz_data['questions']:
            Question.objects.create(
                quiz             = quiz,
                question_title   = q['question_title'],
                question_options = q['question_options'],
                answer           = q['answer'],
            )
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuizDetailView(APIView):
    """
    Handles retrieval, partial update, and deletion of a single quiz.

    GET    /api/quizzes/<pk>/  — Returns the quiz with all its questions.
    PATCH  /api/quizzes/<pk>/  — Partially updates quiz fields.
    DELETE /api/quizzes/<pk>/  — Permanently deletes the quiz.

    All operations are restricted to the quiz owner.
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        """
        Returns a single quiz by its primary key, including all nested questions.

        Returns 404 if the quiz does not exist, 403 if the requesting user
        is not the owner.
        """
        try:
            quiz = Quiz.objects.prefetch_related('questions').get(pk=pk)
        except Quiz.DoesNotExist:
            return Response({'detail': 'Quiz not found.'}, status=status.HTTP_404_NOT_FOUND)
        if quiz.owner != request.user:
            return Response(
                {'detail': 'Access denied. You can only view your own quizzes.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """
        Partially updates a quiz (e.g. title or description).

        Only the fields provided in the request body are updated; all other
        fields remain unchanged.
        Returns 404 if not found, 403 if not the owner, 400 on validation error.
        """
        try:
            quiz = Quiz.objects.prefetch_related('questions').get(pk=pk)
        except Quiz.DoesNotExist:
            return Response({'detail': 'Quiz not found.'}, status=status.HTTP_404_NOT_FOUND)
        if quiz.owner != request.user:
            return Response(
                {'detail': 'Access denied. You can only edit your own quizzes.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = QuizSerializer(quiz, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


    def delete(self, request, pk):
        """
        Permanently deletes a quiz and all its associated questions.

        Returns 404 if the quiz does not exist, 403 if the requesting user
        is not the owner.
        """
        try:
            quiz = Quiz.objects.get(pk=pk)
        except Quiz.DoesNotExist:
            return Response({'detail': 'Quiz not found.'}, status=status.HTTP_404_NOT_FOUND)
        if quiz.owner != request.user:
            return Response(
                {'detail': 'Access denied. You can only delete your own quizzes.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        quiz.delete()
        return Response({'detail': 'Quiz deleted successfully.'}, status=status.HTTP_200_OK)