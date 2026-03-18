from django.urls import path

from posts.views import GoogleLoginView
from . import views
from .views import  AdminOnlyView, PostDetailView, PostCommentDetailView, ProtectedView, PostListCreate,  CommentListCreate, CommentDetailView, UserListCreateView, UserLoginView, UserLogoutView, UserRegistrationView, LikePostView, PostCommentView, PostCommentsListView, NewsFeedView

  # path('users/', views.get_users, name='get_users'),
    # path('users/create/', views.create_user, name='create_user'),
    # path('posts/', views.get_posts, name='get_posts'),
    # path('posts/create/', views.create_post, name='create_post'),
urlpatterns = [
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('posts/', PostListCreate.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    path('protected/', ProtectedView.as_view(), name='protected'),
    path('admin-only/', AdminOnlyView.as_view(), name='admin-only'),
    path('posts/<int:pk>/like/', LikePostView.as_view(), name='post-like'),
    path('posts/<int:pk>/comment/', PostCommentView.as_view(), name='post-comment'),
    path('posts/<int:pk>/comments/', PostCommentsListView.as_view(), name='post-comments-list'),
    path('posts/<int:post_pk>/comments/<int:comment_pk>/', PostCommentDetailView.as_view(), name='post-comment-detail'),
    path('feed/', NewsFeedView.as_view(), name='news-feed'),
    path('auth/google/login/', GoogleLoginView.as_view(), name='google-login'),
]