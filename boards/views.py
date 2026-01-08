from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Board, List, Card, Comment, Checklist, ChecklistItem, Activity
from .serializers import (
    BoardSerializer, ListSerializer, CardSerializer, 
    CommentSerializer, ChecklistSerializer, ChecklistItemSerializer,
    ActivitySerializer, ReorderListsSerializer, ReorderCardsSerializer
)
from .permissions import IsBoardMember, IsBoardOwnerOrMember


class BoardViewSet(viewsets.ModelViewSet):
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Return boards where user is owner or member
        return Board.objects.filter(
            archived=False
        ).filter(
            Q(owner=user) | Q(members=user)
        ).distinct()

    def perform_create(self, serializer):
        board = serializer.save(owner=self.request.user)
        # Add owner as a member
        board.members.add(self.request.user)
        # Log activity
        Activity.objects.create(
            board=board,
            user=self.request.user,
            activity_type='CREATE',
            description=f'{self.request.user.username} created board "{board.title}"'
        )

    def perform_update(self, serializer):
        board = serializer.save()
        Activity.objects.create(
            board=board,
            user=self.request.user,
            activity_type='UPDATE',
            description=f'{self.request.user.username} updated board "{board.title}"'
        )

    def perform_destroy(self, instance):
        # Soft delete (archive)
        instance.archived = True
        instance.save()
        Activity.objects.create(
            board=instance,
            user=self.request.user,
            activity_type='DELETE',
            description=f'{self.request.user.username} archived board "{instance.title}"'
        )

    @action(detail=True, methods=['post'])
    def reorder_lists(self, request, pk=None):
        board = self.get_object()
        serializer = ReorderListsSerializer(data=request.data)
        
        if serializer.is_valid():
            list_ids = serializer.validated_data['lists']
            
            # Validate that all lists belong to this board
            lists = List.objects.filter(id__in=list_ids, board=board)
            if len(lists) != len(list_ids):
                return Response(
                    {'error': 'Invalid list IDs'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update positions
            for position, list_id in enumerate(list_ids):
                List.objects.filter(id=list_id, board=board).update(position=position)
            
            # Log activity
            Activity.objects.create(
                board=board,
                user=request.user,
                activity_type='MOVE',
                description=f'{request.user.username} reordered lists'
            )
            
            return Response({'status': 'lists reordered'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        board = self.get_object()
        activities = Activity.objects.filter(board=board).order_by('-created_at')[:50]
        serializer = ActivitySerializer(activities, many=True)
        return Response(serializer.data)


class ListViewSet(viewsets.ModelViewSet):
    serializer_class = ListSerializer
    permission_classes = [IsAuthenticated, IsBoardMember]

    def get_queryset(self):
        user = self.request.user
        board_id = self.request.query_params.get('board_id')
        
        if board_id:
            board = get_object_or_404(Board, id=board_id)
            self.check_object_permissions(self.request, board)
            return List.objects.filter(board=board, board__archived=False)
        
        return List.objects.filter(board__members=user, board__archived=False)

    def perform_create(self, serializer):
        list_obj = serializer.save()
        Activity.objects.create(
            board=list_obj.board,
            user=self.request.user,
            activity_type='CREATE',
            description=f'{self.request.user.username} created list "{list_obj.title}"'
        )

    def perform_update(self, serializer):
        list_obj = serializer.save()
        Activity.objects.create(
            board=list_obj.board,
            user=self.request.user,
            activity_type='UPDATE',
            description=f'{self.request.user.username} updated list "{list_obj.title}"'
        )


class CardViewSet(viewsets.ModelViewSet):
    serializer_class = CardSerializer
    permission_classes = [IsAuthenticated, IsBoardMember]

    def get_queryset(self):
        user = self.request.user
        list_id = self.request.query_params.get('list_id')
        
        if list_id:
            list_obj = get_object_or_404(List, id=list_id)
            self.check_object_permissions(self.request, list_obj.board)
            return Card.objects.filter(list=list_obj, archived=False)
        
        return Card.objects.filter(list__board__members=user, archived=False)

    def perform_create(self, serializer):
        card = serializer.save()
        Activity.objects.create(
            board=card.list.board,
            user=self.request.user,
            activity_type='CREATE',
            description=f'{self.request.user.username} created card "{card.title}"'
        )

    def perform_update(self, serializer):
        card = serializer.save()
        Activity.objects.create(
            board=card.list.board,
            user=self.request.user,
            activity_type='UPDATE',
            description=f'{self.request.user.username} updated card "{card.title}"'
        )

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        card = self.get_object()
        serializer = ReorderCardsSerializer(data=request.data)
        
        if serializer.is_valid():
            new_list_id = serializer.validated_data.get('destination_list_id')
            new_position = serializer.validated_data.get('position', 0)
            
            if new_list_id:
                new_list = get_object_or_404(List, id=new_list_id)
                self.check_object_permissions(request, new_list.board)
                
                # Move card to new list
                old_list = card.list
                card.list = new_list
                card.position = new_position
                card.save()
                
                # Log activity
                Activity.objects.create(
                    board=new_list.board,
                    user=request.user,
                    activity_type='MOVE',
                    description=f'{request.user.username} moved card "{card.title}" from "{old_list.title}" to "{new_list.title}"'
                )
            else:
                # Reorder within same list
                card.position = new_position
                card.save()
                
                Activity.objects.create(
                    board=card.list.board,
                    user=request.user,
                    activity_type='MOVE',
                    description=f'{request.user.username} reordered card "{card.title}"'
                )
            
            return Response({'status': 'card moved'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsBoardMember]

    def get_queryset(self):
        user = self.request.user
        card_id = self.request.query_params.get('card_id')
        
        if card_id:
            card = get_object_or_404(Card, id=card_id)
            self.check_object_permissions(self.request, card.list.board)
            return Comment.objects.filter(card=card)
        
        return Comment.objects.filter(card__list__board__members=user)

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        Activity.objects.create(
            board=comment.card.list.board,
            user=self.request.user,
            activity_type='COMMENT',
            description=f'{self.request.user.username} commented on card "{comment.card.title}"'
        )


class ChecklistViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistSerializer
    permission_classes = [IsAuthenticated, IsBoardMember]

    def get_queryset(self):
        user = self.request.user
        card_id = self.request.query_params.get('card_id')
        
        if card_id:
            card = get_object_or_404(Card, id=card_id)
            self.check_object_permissions(self.request, card.list.board)
            return Checklist.objects.filter(card=card)
        
        return Checklist.objects.filter(card__list__board__members=user)


class ChecklistItemViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistItemSerializer
    permission_classes = [IsAuthenticated, IsBoardMember]

    def get_queryset(self):
        user = self.request.user
        checklist_id = self.request.query_params.get('checklist_id')
        
        if checklist_id:
            checklist = get_object_or_404(Checklist, id=checklist_id)
            self.check_object_permissions(self.request, checklist.card.list.board)
            return ChecklistItem.objects.filter(checklist=checklist)
        
        return ChecklistItem.objects.filter(checklist__card__list__board__members=user)

    def perform_update(self, serializer):
        item = serializer.save()
        if 'completed' in serializer.validated_data:
            Activity.objects.create(
                board=item.checklist.card.list.board,
                user=self.request.user,
                activity_type='COMPLETE',
                description=f'{self.request.user.username} {"completed" if item.completed else "unchecked"} "{item.text}"'
            )