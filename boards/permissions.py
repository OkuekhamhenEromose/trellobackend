from rest_framework import permissions


class IsBoardMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the board.
    """
    def has_object_permission(self, request, view, obj):
        # Handle different object types
        if hasattr(obj, 'board'):
            board = obj.board
        elif hasattr(obj, 'list'):
            board = obj.list.board
        elif hasattr(obj, 'card'):
            board = obj.card.list.board
        else:
            board = obj
        
        return board.owner == request.user or board.members.filter(id=request.user.id).exists()


class IsBoardOwnerOrMember(permissions.BasePermission):
    """
    Permission to check if user is owner or member of the board.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Allow read-only access for members
            return obj.owner == request.user or obj.members.filter(id=request.user.id).exists()
        else:
            # Allow write access only for owner
            return obj.owner == request.user