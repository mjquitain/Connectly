from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.db.models import Q, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from singletons.logger_singleton import LoggerSingleton
from .models import ConnectlyUser, Post, Comment, Like, GoogleSocialAccount
from .serializers import (
    GoogleLoginSerializer,
    UserSerializer, 
    UserRegistrationSerializer,
    PostSerializer, 
    CommentSerializer
)
from .permissions import IsAdminRole, get_connectly_user_from_request
from factories.post_factory import PostFactory
from django.core.paginator import Paginator, EmptyPage
from .google_auth import verify_google_token, GoogleAuthError

# def get_users(request):
#     try:
#         users = list(User.objects.values('id', 'username', 'email', 'created_at'))
#         return JsonResponse(users, safe=False)
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
   
# @csrf_exempt
# def create_user(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             user = User.objects.create(username=data['username'], email=data['email']) 
#             return JsonResponse({'id': user.id, 'message': 'User created successfully'}, status=201)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=400)
        
# def get_posts(request):
#     try:
#         posts = list(Post.objects.values('id', 'content', 'author_id', 'created_at'))
#         return JsonResponse(posts, safe=False)
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
    
# @csrf_exempt
# def create_post(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             author = User.objects.get(id=data['author'])
#             post = Post.objects.create(content=data['content'], author=author) 
#             return JsonResponse({'id': post.id, 'message': 'Post created successfully'}, status=201)
#         except User.DoesNotExist:
#             return JsonResponse({'error': 'Author not found'}, status=400)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=400)

logger = LoggerSingleton().get_logger()
logger.info("API views initialized successfully.")

DEFAULT_FEED_PAGE_SIZE = 10
MAX_FEED_PAGE_SIZE = 50
FEED_CACHE_TIMEOUT_SECONDS = 60
FEED_CACHE_VERSION_KEY = 'feed_cache_version'


def get_feed_cache_version():
    return cache.get_or_set(FEED_CACHE_VERSION_KEY, 1)


def bump_feed_cache_version():
    try:
        cache.incr(FEED_CACHE_VERSION_KEY)
    except ValueError:
        cache.set(FEED_CACHE_VERSION_KEY, 2)


def parse_positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def is_post_visible_to_user(post, connectly_user):
    if post.privacy == 'public':
        return True

    if connectly_user is None:
        return False

    return post.author_id == connectly_user.id

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            ConnectlyUser.objects.get_or_create(username=user.username, email=user.email)
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                "user": UserSerializer(user).data,
                "token": token.key,
                "message": "User registered successfully"
            }, status=201)

        return Response(serializer.errors, status=400)
    
    
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
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"User logged in: {username}")
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Authentication successful!'
            }, status=status.HTTP_200_OK)
        else:
            logger.error(f"Failed login attempt for username: {username}")
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
class UserLogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        request.user.auth_token.delete()
        return Response(
            {'message': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )
        
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({'error': str(first_error)}, status=status.HTTP_400_BAD_REQUEST)

        id_token_str = serializer.validated_data['id_token']

        try:
            payload = verify_google_token(id_token_str)
        except GoogleAuthError as e:
            logger.warning(f"Google token verification failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        google_id   = payload['sub']
        email       = payload['email']
        name        = payload.get('name', '')
        picture_url = payload.get('picture', '')

        try:
            social_account = GoogleSocialAccount.objects.get(google_id=google_id)
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
            pass

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
            
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        new_user = User.objects.create_user(
            username=username,
            email=email,
            password=None,
        )
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
            connectly_user = ConnectlyUser.objects.get(username=request.user.username)
            post = PostFactory.create_post(
                author=connectly_user,
                post_type=data['post_type'],
                title=data['title'],
                content=data.get('content', ''),
                privacy=data.get('privacy', 'public'),
                metadata=data.get('metadata', {})
            )
            bump_feed_cache_version()
            return Response ({'message': 'Post created successfully!', 'post_id': post.id}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
class CommentListCreate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        comments = Comment.objects.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PostDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return None
    
    def get(self, request, pk):
        post = self.get_object(pk)
        if post is None:
            return Response(
                {'error': 'Post not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        connectly_user = get_connectly_user_from_request(request)
        if not is_post_visible_to_user(post, connectly_user):
            return Response(
                {'error': 'You do not have permission to view this private post'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PostSerializer(post)
        return Response(serializer.data)
    
    def put(self, request, pk):
        post = self.get_object(pk)
        if post is None:
            logger.warning(f"Update failed: Post {pk} not found.")
            return Response(
                {'error': 'Post not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        connectly_user = get_connectly_user_from_request(request)
        if connectly_user is None or post.author_id != connectly_user.id:
            return Response(
                {'error': 'Only the post owner can update this post'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            bump_feed_cache_version()
            logger.info(f"Post {pk} updated by {request.user.username}")
            return Response(serializer.data)
        
        logger.warning(f"Validation failed for Post {pk} update: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not IsAdminRole().has_permission(request, self):
            return Response(
                {'error': 'Admin role required to delete posts'},
                status=status.HTTP_403_FORBIDDEN
            )

        post = self.get_object(pk)
        if post:
            post_id = post.id
            post.delete()
            bump_feed_cache_version()
            logger.info(f"Post {post_id} deleted by user {request.user.username}")
            return Response({'message': 'Post deleted'}, status=status.HTTP_204_NO_CONTENT)
        
        logger.warning(f"DELETE FAILED: Post {pk} not found for user {request.user.username}")
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        
class ProtectedView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'message': 'Authenticated!',
            'user': request.user.username
        })
        
class AdminOnlyView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def get(self, request):
        logger.info(f"Admin dashboard accessed by: {request.user.username}")
        return Response({
            'message': 'Welcome, Admin!',
            'stats': {'users': User.objects.count(), 'posts': Post.objects.count(), 'comments': Comment.objects.count()}
        })
        

class LikePostView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

        connectly_user = get_connectly_user_from_request(request)
        if connectly_user is None:
            return Response({"error": "Connectly user profile not found"}, status=404)

        like, created = Like.objects.get_or_create(
            user=connectly_user,
            post=post
        )

        if not created:
            return Response({"error": "Already liked"}, status=400)

        bump_feed_cache_version()
        return Response({"message": "Post liked"}, status=201)
    
class PostCommentView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

        connectly_user = get_connectly_user_from_request(request)
        if connectly_user is None:
            return Response({"error": "Connectly user profile not found"}, status=404)

        text = request.data.get("text")

        if not text:
            return Response({"error": "Comment cannot be empty"}, status=400)

        comment = Comment.objects.create(
            author=connectly_user,
            post=post,
            text=text
        )
        bump_feed_cache_version()

        return Response(
            {
                "message": "Comment added",
                "comment": {
                    "id": comment.id,
                    "post_id": post.id,
                    "author": comment.author.username,
                    "text": comment.text,
                    "created_at": comment.created_at,
                },
            },
            status=201,
        )


class CommentDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    def delete(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)

        comment.delete()
        bump_feed_cache_version()
        return Response({"message": "Comment deleted"}, status=status.HTTP_204_NO_CONTENT)


class PostCommentDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    def delete(self, request, post_pk, comment_pk):
        try:
            comment = Comment.objects.get(pk=comment_pk, post_id=post_pk)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found for this post"}, status=404)

        comment.delete()
        bump_feed_cache_version()
        return Response({"message": "Comment deleted"}, status=status.HTTP_204_NO_CONTENT)
    
class PostCommentsListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)

        comments = Comment.objects.filter(post=post)

        data = [
            {
                "id": c.id,
                "author": c.author.username,
                "text": c.text,
                "created_at": c.created_at
            }
            for c in comments
        ]

        return Response(data)
    
class NewsFeedView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        connectly_user = get_connectly_user_from_request(request)
        page_number = parse_positive_int(request.query_params.get('page', 1), 1)
        requested_page_size = parse_positive_int(
            request.query_params.get('page_size', DEFAULT_FEED_PAGE_SIZE),
            DEFAULT_FEED_PAGE_SIZE,
        )
        page_size = min(requested_page_size, MAX_FEED_PAGE_SIZE)
        cache_version = get_feed_cache_version()
        user_key = connectly_user.id if connectly_user else 'anonymous'
        feed_cache_key = f'feed:{cache_version}:user:{user_key}:page:{page_number}:size:{page_size}'

        cached_payload = cache.get(feed_cache_key)
        if cached_payload is not None:
            return Response(cached_payload, status=status.HTTP_200_OK)

        user_filter = Q(author=connectly_user) if connectly_user else Q(pk__in=[])
        posts_list = Post.objects.filter(
            Q(privacy='public') | user_filter
        ).select_related('author').annotate(
            like_count_annotated=Count('likes', distinct=True),
            comment_count_annotated=Count('comments', distinct=True),
        ).order_by('-created_at')
        paginator = Paginator(posts_list, page_size)
        
        try:
            page_obj = paginator.page(page_number)
        except (EmptyPage, ValueError):
            return Response({"error": "Invalid page number"}, status=400)
        
        serializer = PostSerializer(page_obj.object_list, many=True)

        payload = {
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_number,
            "results": serializer.data
        }
        cache.set(feed_cache_key, payload, FEED_CACHE_TIMEOUT_SECONDS)

        return Response(payload, status=status.HTTP_200_OK)