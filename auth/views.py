from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .authentication import CookieJWTAuthentication
from .serializers import RegisterSerializer, LoginSerializer


def _set_auth_cookies(response, refresh):
    jwt_settings = settings.SIMPLE_JWT
    secure   = jwt_settings.get('AUTH_COOKIE_SECURE', False)
    http_only = jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True)
    samesite = jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax')

    response.set_cookie(
        key='access_token',
        value=str(refresh.access_token),
        max_age=int(jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        secure=secure, httponly=http_only, samesite=samesite,
    )
    response.set_cookie(
        key='refresh_token',
        value=str(refresh),
        max_age=int(jwt_settings['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        secure=secure, httponly=http_only, samesite=samesite,
    )
    return response


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({'detail': 'User created successfully!'}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        response = Response({
            'detail': 'Login successfully!',
            'user': {'id': user.id, 'username': user.username, 'email': user.email},
        }, status=status.HTTP_200_OK)
        return _set_auth_cookies(response, refresh)


class LogoutView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token_str = request.COOKIES.get('refresh_token')
        if refresh_token_str:
            try:
                token = RefreshToken(refresh_token_str)
                token.blacklist()       # macht den Refresh-Token serverseitig ungültig
            except (TokenError, Exception):
                pass                    # Token schon abgelaufen → trotzdem Cookies löschen

        response = Response(
            {'detail': 'Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid.'},
            status=status.HTTP_200_OK,
        )
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response


class TokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token_str = request.COOKIES.get('refresh_token')
        if not refresh_token_str:
            return Response({'detail': 'Refresh token missing.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token_str)

            # Token rotieren: altes Token blacklisten, neues generieren
            if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION', False):
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()

        except (TokenError, Exception):
            return Response({'detail': 'Invalid or expired refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)

        response = Response({'detail': 'Token refreshed'}, status=status.HTTP_200_OK)
        return _set_auth_cookies(response, refresh)