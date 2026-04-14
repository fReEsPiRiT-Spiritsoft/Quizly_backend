from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication backend that reads the access token from an
    HTTP-only cookie instead of the Authorization header.

    This allows the frontend to authenticate without exposing tokens to
    JavaScript, since HTTP-only cookies are not accessible via document.cookie.
    """

    def authenticate(self, request):
        """
        Extracts the JWT access token from the 'access_token' cookie,
        validates it, and returns the corresponding (user, token) pair.

        Returns None if no token cookie is present, which allows Django REST
        Framework to fall through to other configured authentication backends.
        """
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token