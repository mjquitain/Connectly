from rest_framework import serializers
from .models import User, Post, Comment
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']
        read_only_fields = ['id', 'date_joined']
        
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']
        
        def create(self,validated_data):
            validated_data.pop('password_confirm')
            
            return User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password']
            )
        
class PostSerializer(serializers.ModelSerializer):
    comments = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = Post
        fields = ['id', 'content', 'author', 'created_at', 'comments']
        
class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'text', 'author', 'post', 'created_at']
        
    def validate_post(self, value):
        if not isinstance(value, Post):
            raise serializers.ValidationError("Post does not exist")
        return value
    
    def validate_author(self, value):
        if not isinstance(value, User):
            raise serializers.ValidationError("Author does not exist")
        return value