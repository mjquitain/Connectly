from django.contrib import admin
from .models import Post, Comment, Like, GoogleSocialAccount


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'author', 'post_type', 'created_at']
    list_filter = ['post_type', 'created_at']
    search_fields = ['title', 'content', 'author__username']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'author__username']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username']


@admin.register(GoogleSocialAccount)
class GoogleSocialAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'email', 'google_id', 'created_at', 'last_login']
    search_fields = ['user__username', 'email', 'google_id']
    readonly_fields = ['google_id', 'created_at', 'last_login']