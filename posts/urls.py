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
    GoogleLoginView,
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('auth/google/login/', GoogleLoginView.as_view(), name='google-login'),
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('posts/', PostListCreate.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('protected/', ProtectedView.as_view(), name='protected'),
    path('admin-only/', AdminOnlyView.as_view(), name='admin-only'),
]
