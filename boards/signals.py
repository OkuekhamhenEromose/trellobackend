from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from .models import Board, List, Card, Comment


@receiver(post_save, sender=List)
def broadcast_list_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    action = 'list_created' if created else 'list_updated'
    
    async_to_sync(channel_layer.group_send)(
        f'board_{instance.board.id}',
        {
            'type': 'board_update',
            'action': action,
            'data': {
                'id': instance.id,
                'title': instance.title,
                'position': instance.position,
                'board_id': instance.board.id
            }
        }
    )


@receiver(post_save, sender=Card)
def broadcast_card_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    action = 'card_created' if created else 'card_updated'
    
    async_to_sync(channel_layer.group_send)(
        f'board_{instance.list.board.id}',
        {
            'type': 'board_update',
            'action': action,
            'data': {
                'id': instance.id,
                'title': instance.title,
                'position': instance.position,
                'list_id': instance.list.id,
                'board_id': instance.list.board.id
            }
        }
    )


@receiver(post_save, sender=Comment)
def broadcast_comment_update(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            f'board_{instance.card.list.board.id}',
            {
                'type': 'board_update',
                'action': 'comment_added',
                'data': {
                    'id': instance.id,
                    'text': instance.text,
                    'card_id': instance.card.id,
                    'author': instance.author.username if instance.author else None,
                    'created_at': instance.created_at.isoformat()
                }
            }
        )