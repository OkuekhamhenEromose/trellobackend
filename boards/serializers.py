from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Board, List, Card, Comment, Checklist, ChecklistItem, Activity


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ['id', 'text', 'completed', 'position', 'created_at', 'updated_at']


class ChecklistSerializer(serializers.ModelSerializer):
    items = ChecklistItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Checklist
        fields = ['id', 'title', 'card', 'items', 'created_at', 'updated_at']


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'text', 'card', 'author', 'created_at', 'updated_at']
        read_only_fields = ['author', 'created_at', 'updated_at']


class CardSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='members',
        many=True,
        write_only=True,
        required=False
    )
    comments = CommentSerializer(many=True, read_only=True)
    checklists = ChecklistSerializer(many=True, read_only=True)
    
    class Meta:
        model = Card
        fields = [
            'id', 'title', 'description', 'list', 'position', 'due_date',
            'labels', 'members', 'member_ids', 'attachments', 'archived',
            'comments', 'checklists', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ListSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)
    
    class Meta:
        model = List
        fields = ['id', 'title', 'board', 'position', 'cards', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class BoardSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='members',
        many=True,
        write_only=True,
        required=False
    )
    lists = ListSerializer(many=True, read_only=True)
    
    class Meta:
        model = Board
        fields = [
            'id', 'title', 'description', 'owner', 'members', 'member_ids',
            'background_color', 'background_image', 'archived', 'lists',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']


class ActivitySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Activity
        fields = ['id', 'board', 'user', 'activity_type', 'description', 'data', 'created_at']
        read_only_fields = ['user', 'created_at']


# Serializers for ordering/reordering
class ReorderListsSerializer(serializers.Serializer):
    lists = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )


class ReorderCardsSerializer(serializers.Serializer):
    cards = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    source_list_id = serializers.IntegerField(required=False)
    destination_list_id = serializers.IntegerField(required=False)