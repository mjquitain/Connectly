from django.urls import path
from . import views
from .views import AdminOnlyView, CreatePostView, PostDetailView, ProtectedView, UserListCreate, PostListCreate, CommentListCreate, UserListCreateView, UserListView, UserLoginView, UserLogoutView, UserRegistrationView

urlpatterns = [
    # path('users/', views.get_users, name='get_users'),
    # path('users/create/', views.create_user, name='create_user'),
    # path('posts/', views.get_posts, name='get_posts'),
    # path('posts/create/', views.create_post, name='create_post'),
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('posts/', PostListCreate.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),path('protected/', ProtectedView.as_view(), name='protected'),
    path('admin-only/', AdminOnlyView.as_view(), name='admin-only'),
]