from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, LoginSerializer


def _set_auth_cookies(response: Response, refresh: RefreshToken) -> Response:
    """ """
    jwt_settings = settings.SIMPLE_JWT
    secure = jwt_settings.get('AUTH_COOKIE_SECURE', False)
    http_only = jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True)
    samesite = jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax')

    access_lifetime = jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds()
    refresh_lifetime = jwt_settings['REFRESH_TOKEN_LIFETIME'].total_seconds()

    response.set_cookie(
        key='access_token',
        value=str(refresh.access_token),
        max_age=int(access_lifetime),
        secure=secure,
        httponly=http_only,
        samesite=samesite,
    )
    response.set_cookie(
        key='refresh_token',
        value=str(refresh),
        max_age=int(refresh_lifetime),
        secure=secure,
        httponly=http_only,
        samesite=samesite,
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
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        response = Response({
            'detail': 'Login successfully!',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
        }, status=status.HTTP_200_OK)

        return _set_auth_cookies(response, refresh)