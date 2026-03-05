from django.urls import path
from .views import (
    AdminOnlyView,
    PostDetailView,
    ProtectedView,
    PostListCreate,
    CommentListCreate,
    UserListCreateView,
    UserLoginView,
    UserLogoutView,
    UserRegistrationView,
    LikePostView,
    PostCommentListCreate,
    GoogleLoginView,         # NEW
)

urlpatterns = [
    # --- Auth (standard) ---
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),

    # --- Auth (Google OAuth) NEW ---
    path('auth/google/login/', GoogleLoginView.as_view(), name='google-login'),

    # --- Users ---
    path('users/', UserListCreateView.as_view(), name='user-list-create'),

    # --- Posts ---
    path('posts/', PostListCreate.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),

    # --- Likes ---
    path('posts/<int:pk>/like/', LikePostView.as_view(), name='post-like'),

    # --- Comments ---
    path('posts/<int:pk>/comments/', PostCommentListCreate.as_view(), name='post-comments'),
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),

    # --- Utility ---
    path('protected/', ProtectedView.as_view(), name='protected'),
    path('admin-only/', AdminOnlyView.as_view(), name='admin-only'),
]