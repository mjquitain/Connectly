from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from singletons.logger_singleton import LoggerSingleton
from .models import Post, Comment, Like, GoogleSocialAccount
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    PostSerializer,
    CommentSerializer,
    LikeSerializer,
    GoogleLoginSerializer,
)
from .permissions import IsPostAuthor, IsCommentAuthor, IsAdminOrReadOnly
from factories.post_factory import PostFactory
from .google_auth import verify_google_token, GoogleAuthError

logger = LoggerSingleton().get_logger()
logger.info("API views initialized successfully.")


# ---------------------------------------------------------------------------
# Auth Views
# ---------------------------------------------------------------------------

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                token, _ = Token.objects.get_or_create(user=user)
                logger.info(f"New user registered: {user.username} (ID: {user.id})")
                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.key,
                    'message': 'User registered successfully.'
                }, status=status.HTTP_201_CREATED)

            logger.warning(f"Registration validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error during user registration")
            return Response({'error': 'Internal server error'}, status=500)


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Please provide both username and password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)
        if user is not None:
            token, _ = Token.objects.get_or_create(user=user)
            logger.info(f"User logged in: {username}")
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Authentication successful!'
            }, status=status.HTTP_200_OK)

        logger.error(f"Failed login attempt for username: {username}")
        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


class UserLogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        logger.info(f"User logged out: {request.user.username}")
        return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Google OAuth View  (NEW)
# ---------------------------------------------------------------------------

class GoogleLoginView(APIView):
    """
    POST /auth/google/login/

    Accepts a Google ID token from a client (mobile app or SPA) and returns
    a Connectly API token, creating or linking a user account as needed.

    Request body:
        { "id_token": "<Google ID token string>" }

    Response (success 200 / 201):
        {
            "token": "<Connectly API token>",
            "user": { id, username, email, date_joined },
            "created": true | false,
            "message": "..."
        }

    Three possible account scenarios handled:
        1. Returning Google user  -> existing GoogleSocialAccount found by google_id
        2. Existing email user    -> Google account linked to their existing profile
        3. Brand new user         -> new User + GoogleSocialAccount created automatically
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # -- Step 1: Validate request body via serializer --
        serializer = GoogleLoginSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({'error': str(first_error)}, status=status.HTTP_400_BAD_REQUEST)

        id_token_str = serializer.validated_data['id_token']

        # -- Step 2: Verify token with Google --
        try:
            payload = verify_google_token(id_token_str)
        except GoogleAuthError as e:
            logger.warning(f"Google token verification failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        google_id   = payload['sub']
        email       = payload['email']
        name        = payload.get('name', '')
        picture_url = payload.get('picture', '')

        # ── Step 2: Scenario 1 — returning Google user ───────────────────
        try:
            social_account = GoogleSocialAccount.objects.get(google_id=google_id)
            # Refresh stored profile data in case it changed
            social_account.email = email
            social_account.name = name
            social_account.picture_url = picture_url
            social_account.save()

            user = social_account.user
            token, _ = Token.objects.get_or_create(user=user)
            logger.info(f"Google login (returning): {user.username} (google_id={google_id})")
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'created': False,
                'message': 'Logged in with Google successfully.'
            }, status=status.HTTP_200_OK)

        except GoogleSocialAccount.DoesNotExist:
            pass  # Continue to scenarios 2 & 3

        # ── Step 3: Scenario 2 — link to existing email account ──────────
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            GoogleSocialAccount.objects.create(
                user=existing_user,
                google_id=google_id,
                email=email,
                name=name,
                picture_url=picture_url,
            )
            token, _ = Token.objects.get_or_create(user=existing_user)
            logger.info(
                f"Google login (linked to existing): {existing_user.username} "
                f"(google_id={google_id})"
            )
            return Response({
                'token': token.key,
                'user': UserSerializer(existing_user).data,
                'created': False,
                'message': 'Google account linked to your existing Connectly account.'
            }, status=status.HTTP_200_OK)

        # ── Step 4: Scenario 3 — create brand new user ───────────────────
        # Derive a unique username from the email prefix
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        new_user = User.objects.create_user(
            username=username,
            email=email,
            password=None,       # No password — Google is the auth provider
        )
        # Store display name in first_name/last_name for convenience
        if name:
            parts = name.split(' ', 1)
            new_user.first_name = parts[0]
            new_user.last_name = parts[1] if len(parts) > 1 else ''
            new_user.save()

        GoogleSocialAccount.objects.create(
            user=new_user,
            google_id=google_id,
            email=email,
            name=name,
            picture_url=picture_url,
        )
        token, _ = Token.objects.get_or_create(user=new_user)
        logger.info(
            f"Google login (new user created): {new_user.username} "
            f"(google_id={google_id})"
        )
        return Response({
            'token': token.key,
            'user': UserSerializer(new_user).data,
            'created': True,
            'message': 'New Connectly account created via Google login.'
        }, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# User Views
# ---------------------------------------------------------------------------

class UserListCreateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Post Views
# ---------------------------------------------------------------------------

class PostListCreate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        posts = Post.objects.all()
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        try:
            post = PostFactory.create_post(
                author=request.user,
                post_type=data['post_type'],
                title=data['title'],
                content=data.get('content', ''),
                metadata=data.get('metadata', {})
            )
            return Response(
                {'message': 'Post created successfully!', 'post_id': post.id},
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsPostAuthor]

    def get_object(self, pk):
        try:
            post = Post.objects.get(pk=pk)
            self.check_object_permissions(self.request, post)
            return post
        except Post.DoesNotExist:
            return None

    def get(self, request, pk):
        post = self.get_object(pk)
        if post is None:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PostSerializer(post)
        return Response(serializer.data)

    def put(self, request, pk):
        post = self.get_object(pk)
        if post is None:
            logger.warning(f"Update failed: Post {pk} not found.")
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Post {pk} updated by {request.user.username}")
            return Response(serializer.data)

        logger.warning(f"Validation failed for Post {pk}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        post = self.get_object(pk)
        if post:
            post_id = post.id
            post.delete()
            logger.info(f"Post {post_id} deleted by {request.user.username}")
            return Response({'message': 'Post deleted'}, status=status.HTTP_204_NO_CONTENT)

        logger.warning(f"DELETE FAILED: Post {pk} not found for {request.user.username}")
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Like Views
# ---------------------------------------------------------------------------

class LikePostView(APIView):
    """
    POST /posts/{id}/like/  - Toggle like on/off
    GET  /posts/{id}/like/  - Get like count + current user like status
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_post(self, pk):
        try:
            return Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return None

    def get(self, request, pk):
        post = self.get_post(pk)
        if post is None:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'post_id': pk,
            'like_count': post.likes.count(),
            'liked_by_me': post.likes.filter(user=request.user).exists(),
        }, status=status.HTTP_200_OK)

    def post(self, request, pk):
        post = self.get_post(pk)
        if post is None:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        existing = Like.objects.filter(user=request.user, post=post).first()
        if existing:
            existing.delete()
            logger.info(f"User {request.user.username} unliked Post {pk}")
            return Response({
                'message': 'Post unliked successfully.',
                'like_count': post.likes.count(),
                'liked_by_me': False,
            }, status=status.HTTP_200_OK)

        like = Like.objects.create(user=request.user, post=post)
        logger.info(f"User {request.user.username} liked Post {pk}")
        return Response({
            'message': 'Post liked successfully.',
            'like': LikeSerializer(like).data,
            'like_count': post.likes.count(),
            'liked_by_me': True,
        }, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Comment Views
# ---------------------------------------------------------------------------

class PostCommentListCreate(APIView):
    """
    GET  /posts/{id}/comments/ - List all comments for a post
    POST /posts/{id}/comments/ - Add a comment to a post
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_post(self, pk):
        try:
            return Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return None

    def get(self, request, pk):
        post = self.get_post(pk)
        if post is None:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        comments = post.comments.all().order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response({
            'post_id': pk,
            'comment_count': comments.count(),
            'comments': serializer.data,
        }, status=status.HTTP_200_OK)

    def post(self, request, pk):
        post = self.get_post(pk)
        if post is None:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['post'] = post.id
        data['author'] = request.user.id

        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(author=request.user, post=post)
            logger.info(f"User {request.user.username} commented on Post {pk}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        logger.warning(f"Comment validation failed for Post {pk}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentListCreate(APIView):
    """Global comment endpoint — kept for backward compatibility."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        comments = Comment.objects.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['author'] = request.user.id
        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Utility Views
# ---------------------------------------------------------------------------

class ProtectedView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'message': 'Authenticated!', 'user': request.user.username})


class AdminOnlyView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            logger.warning(f"Unauthorized admin access attempt by: {request.user.username}")
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

        logger.info(f"Admin dashboard accessed by: {request.user.username}")
        return Response({
            'message': 'Welcome, Admin!',
            'stats': {
                'users': User.objects.count(),
                'posts': Post.objects.count(),
                'comments': Comment.objects.count(),
                'likes': Like.objects.count(),
            }
        })