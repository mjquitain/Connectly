from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment, Like


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )


class PostSerializer(serializers.ModelSerializer):
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'author', 'post_type',
            'metadata', 'created_at', 'like_count', 'comment_count'
        ]
        read_only_fields = ['author', 'created_at', 'like_count', 'comment_count']

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_comment_count(self, obj):
        return obj.comments.count()


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Comment
        fields = ['id', 'text', 'author', 'author_username', 'post', 'created_at']
        read_only_fields = ['author', 'created_at']

    def validate_text(self, value):
        """Ensure comment text is not blank."""
        if not value or not value.strip():
            raise serializers.ValidationError("Comment text cannot be empty.")
        if len(value.strip()) < 1:
            raise serializers.ValidationError("Comment text must have at least 1 character.")
        return value.strip()

    def validate_post(self, value):
        if not isinstance(value, Post):
            raise serializers.ValidationError("Post does not exist.")
        return value

    def validate_author(self, value):
        if not isinstance(value, User):
            raise serializers.ValidationError("Author does not exist.")
        return value


class LikeSerializer(serializers.ModelSerializer):
    user_username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Like
        fields = ['id', 'user', 'user_username', 'post', 'created_at']
        read_only_fields = ['user', 'created_at']


class GoogleSocialAccountSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for GoogleSocialAccount.
    Used to expose linked Google profile info on user-facing endpoints.
    """
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        from .models import GoogleSocialAccount
        model = GoogleSocialAccount
        fields = ['id', 'username', 'google_id', 'email', 'name', 'picture_url', 'created_at', 'last_login']
        read_only_fields = fields


class GoogleLoginSerializer(serializers.Serializer):
    """
    Validates the incoming payload for POST /auth/google/login/.
    Ensures id_token is present and is a non-empty string.

    Note: DRF raises 'required' before 'blank' when a field is required=True,
    so the blank case is handled explicitly in validate_id_token() instead.
    """
    id_token = serializers.CharField(
        required=True,
        allow_blank=True,   # allow_blank=True so DRF passes the value to validate_id_token
        error_messages={
            'required': 'id_token is required.',
        }
    )

    def validate_id_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('id_token must not be blank.')
        return value