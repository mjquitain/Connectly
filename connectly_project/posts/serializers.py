from rest_framework import serializers
from .models import User, Post, Comment

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'created_at']
        
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