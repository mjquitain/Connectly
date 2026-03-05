from rest_framework.permissions import BasePermission

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