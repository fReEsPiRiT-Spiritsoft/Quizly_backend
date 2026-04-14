from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from auth.authentication import CookieJWTAuthentication
from auth.api.serializers import RegisterSerializer, LoginSerializer


def _set_auth_cookies(response, refresh):
    """
    Attaches JWT access and refresh tokens as HTTP-only cookies to the response.

    Cookie attributes (secure, httponly, samesite, max_age) are read from
    the SIMPLE_JWT settings block, keeping cookie configuration in one place.
    """
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
    """
    Public endpoint for creating a new user account.

    POST /api/register/
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """
        Validates the registration payload and creates a new user.

        Expects: username, email, password, confirmed_password.
        Returns 201 on success, 400 if validation fails.
        """
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({'detail': 'User created successfully!'}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Public endpoint for authenticating an existing user.

    POST /api/login/
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """
        Authenticates the user and issues JWT tokens via HTTP-only cookies.

        Expects: username, password.
        Returns 200 with basic user info and sets access_token / refresh_token cookies.
        Returns 401 if credentials are invalid.
        """
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
    """
    Protected endpoint that invalidates the current session.

    POST /api/logout/
    Requires authentication via the access_token cookie.
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Blacklists the refresh token server-side and deletes both auth cookies.

        The refresh token is revoked so it cannot be used to obtain new tokens.
        Both cookies are deleted regardless of whether the token is still valid
        (e.g. already expired tokens are silently ignored).
        """
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
    """
    Public endpoint for issuing a new access token using a valid refresh token.

    POST /api/token/refresh/
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """
        Reads the refresh token from the cookie, rotates it, and sets fresh tokens.

        If BLACKLIST_AFTER_ROTATION is enabled, the old refresh token is
        blacklisted and a brand-new pair of tokens is written as HTTP-only cookies.
        Returns 401 if the refresh token is missing, invalid, or expired.
        """
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