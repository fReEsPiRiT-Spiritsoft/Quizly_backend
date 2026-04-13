from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth.authentication import CookieJWTAuthentication
from .models import Quiz, Question
from .serializers import QuizSerializer
from .services import extract_video_id, get_transcript, generate_quiz_from_transcript


class QuizListCreateView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        """Gibt alle Quizzes des eingeloggten Users zurück."""
        quizzes = Quiz.objects.filter(owner=request.user).prefetch_related('questions')
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Erstellt ein neues Quiz aus einer YouTube-URL."""
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
        except Exception:
            return Response({'detail': 'Internal server error.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        """Gibt ein spezifisches Quiz zurück — nur wenn es dem User gehört."""
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
        """Partielle Aktualisierung eines Quiz — nur eigene Quizzes."""
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
        """Löscht ein Quiz — nur eigene Quizzes."""
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