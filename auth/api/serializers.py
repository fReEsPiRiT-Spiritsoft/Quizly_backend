from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for new user registration.

    Validates that both password fields match, that the email address is not
    already registered, and applies Django's built-in password strength
    validators before creating the new user.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirmed_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'confirmed_password')

    def validate(self, data):
        """
        Cross-field validation: ensures both password fields match and that
        the provided email address is not already associated with an account.
        """
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError({'confirmed_password': 'Passwords do not match.'})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'Email already in use.'})
        return data

    def create(self, validated_data):
        """
        Creates and returns a new User instance.

        Uses Django's create_user helper so the password is hashed correctly
        before being stored. The confirmed_password field is removed beforehand
        as it is not part of the User model.
        """
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """
    Serializer for validating login credentials.

    Only validates the format of the incoming data. Actual credential
    verification is performed by Django's authenticate() in the view.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)