from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from singletons.logger_singleton import LoggerSingleton
from .models import Post, Comment
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer,
    PostSerializer, 
    CommentSerializer
)
from .permissions import IsPostAuthor, IsCommentAuthor, IsAdminOrReadOnly
from factories.post_factory import PostFactory

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

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = User.objects.create_user(
                    username=serializer.validated_data['username'],
                    email=serializer.validated_data['email'],
                    password=serializer.validated_data['password']
                )
                token, created = Token.objects.get_or_create(user=user)
            
                logger.info(f"New user registered: {user.username} (ID: {user.id})")
                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.key,
                    'message': 'User registered successfully with hashed password'
                }, status=status.HTTP_201_CREATED)
            
            logger.warning(f"BAD REQUEST: Registration validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception:   
            logger.exception("CRITICAL: Unexpected error during user registration")
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
        
        
class UserListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
        
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
            post = PostFactory.create_post(
                author=request.user,
                post_type=data['post_type'],
                title=data['title'],
                content=data.get('content', ''),
                metadata=data.get('metadata', {})
            )
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
            return Response(
                {'error': 'Post not found'},
                status=status.HTTP_404_NOT_FOUND
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
        
        serializer = PostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Post {pk} updated by {request.user.username}")
            return Response(serializer.data)
        
        logger.warning(f"Validation failed for Post {pk} update: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        post = self.get_object(pk)
        if post:
            post_id = post.id
            author = post.author.username
            post.delete()
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
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_staff:
            logger.warning(f"Unauthorized Admin access attempt by user: {request.user.username}")
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        logger.info(f"Admin dashboard accessed by: {request.user.username}")
        return Response({
            'message': 'Welcome, Admin!',
            'stats': {'users': User.objects.count(), 'posts': Post.objects.count(), 'comments': Comment.objects.count()}
        })