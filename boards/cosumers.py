import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Board
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


class BoardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.board_id = self.scope['url_route']['kwargs']['board_id']
        self.board_group_name = f'board_{self.board_id}'
        
        # Authenticate user via JWT token
        await self.authenticate_user()
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Check if user has access to board
        has_access = await self.check_board_access()
        if not has_access:
            await self.close()
            return
        
        # Join board group
        await self.channel_layer.group_add(
            self.board_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to board updates'
        }))

    async def disconnect(self, close_code):
        # Leave board group
        await self.channel_layer.group_discard(
            self.board_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        
        # Broadcast to board group
        await self.channel_layer.group_send(
            self.board_group_name,
            {
                'type': 'board_update',
                'action': action,
                'data': data.get('data', {}),
                'user': self.user.username
            }
        )

    async def board_update(self, event):
        # Send update to WebSocket
        await self.send(text_data=json.dumps({
            'type': event['action'],
            'data': event['data'],
            'user': event['user']
        }))

    @database_sync_to_async
    def authenticate_user(self):
        # Get token from query string
        query_string = self.scope.get('query_string', b'').decode()
        token_key = None
        
        # Parse query string for token
        if query_string:
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token_key = params.get('token')
        
        if token_key:
            try:
                token = AccessToken(token_key)
                self.user = User.objects.get(id=token['user_id'])
            except Exception:
                self.user = AnonymousUser()
        else:
            self.user = AnonymousUser()

    @database_sync_to_async
    def check_board_access(self):
        try:
            board = Board.objects.get(id=self.board_id)
            return board.owner == self.user or board.members.filter(id=self.user.id).exists()
        except Board.DoesNotExist:
            return False