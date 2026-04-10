from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth.authentication import CookieJWTAuthentication
from .models import Quiz, Question
from .serializers import QuizSerializer
from .services import extract_video_id, get_transcript, generate_quiz_from_transcript


class QuizCreateView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def post(self, request):
        url = request.data.get('url', '').strip()
        if not url:
            return Response({'detail': 'URL is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not extract_video_id(url):
            return Response({'detail': 'Invalid YouTube URL.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transcript = get_transcript(url)                          # yt-dlp + Whisper
            quiz_data  = generate_quiz_from_transcript(transcript, url)  # GPT
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