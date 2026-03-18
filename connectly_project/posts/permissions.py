from rest_framework.permissions import BasePermission
from .models import ConnectlyUser


def get_connectly_user_from_request(request):
    if not request.user or not request.user.is_authenticated:
        return None

    return ConnectlyUser.objects.filter(username=request.user.username).first()

class IsPostAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        return obj.author == request.user


class IsCommentAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        return obj.author == request.user


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        return request.user and request.user.is_staff


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        ):
            return True

        connectly_user = get_connectly_user_from_request(request)
        return bool(connectly_user and connectly_user.role == 'admin')