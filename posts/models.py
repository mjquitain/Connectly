from django.db import models
from django.contrib.auth.models import User


class Post(models.Model):
    POST_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    title = models.CharField(max_length=255, default="Untitled")
    post_type = models.CharField(max_length=10, choices=POST_TYPES, default='text')
    metadata = models.JSONField(default=dict, blank=True)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post by {self.author.username} at {self.created_at}"


class Comment(models.Model):
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on Post {self.post.id}"


class Like(models.Model):
    """
    Represents a user liking a post.
    The unique_together constraint ensures a user can only like a post once.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"Like by {self.user.username} on Post {self.post.id}"


class GoogleSocialAccount(models.Model):
    """
    Links a Django User account to a Google OAuth identity.

    Flow:
      1. Client sends a Google ID token to POST /auth/google/login/
      2. API verifies the token with Google's tokeninfo endpoint
      3. If google_id already exists  -> return token for linked User
      4. If email matches existing User -> link and return token
      5. Otherwise -> create new User + GoogleSocialAccount, return token

    google_id   -- Google's immutable 'sub' claim (never changes, even if email does)
    email       -- Stored for display; not used as the primary lookup key
    picture_url -- Profile photo URL returned by Google
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='google_account'
    )
    google_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    picture_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Google Social Account'
        verbose_name_plural = 'Google Social Accounts'

    def __str__(self):
        return f"GoogleAccount({self.user.username} <-> {self.google_id})"