# messaging_app/chats/auth.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from .models import User


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication to use our custom User model
    """

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token.get('user_id')
            if user_id is None:
                raise exceptions.AuthenticationError(
                    'Token contained no recognizable user identification')

            user = User.objects.get(user_id=user_id)
            return user
        except User.DoesNotExist:
            raise exceptions.AuthenticationError('User not found')
        except Exception:
            raise exceptions.AuthenticationError('User lookup failed')

# Alternative authentication classes if needed


class QueryParamJWTAuthentication(JWTAuthentication):
    """
    JWT authentication that also checks for token in query parameters
    """

    def authenticate(self, request):
        # First try the header-based authentication
        header_auth = super().authenticate(request)
        if header_auth is not None:
            return header_auth

        # Then try query parameter authentication
        token = request.query_params.get('token')
        if token:
            return self.authenticate_credentials(token)

        return None

# Utility functions for authentication


def get_user_from_token(token):
    """
    Utility function to get user from JWT token
    """
    from rest_framework_simplejwt.tokens import AccessToken
    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        return User.objects.get(user_id=user_id)
    except (User.DoesNotExist, KeyError, Exception):
        return None


def validate_jwt_token(token):
    """
    Validate JWT token and return user if valid
    """
    from rest_framework_simplejwt.tokens import AccessToken
    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        user = User.objects.get(user_id=user_id)
        return user, access_token
    except (User.DoesNotExist, KeyError, Exception):
        return None, None
