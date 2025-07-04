import json
from channels.generic.websocket import AsyncWebsocketConsumer
from bookstall.models import ChatRoom, ChatMessage,CustomUser
from channels.db import database_sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        sender_id = data['sender_id']

        sender_name = await self.save_message(self.room_name, sender_id, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': sender_id,
                'sender_name': sender_name,  
            }
        )


    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],  
        }))


    @database_sync_to_async
    def save_message(self, room_name, sender_id, message):
        room, _ = ChatRoom.objects.get_or_create(room_name=room_name)
        sender = CustomUser.objects.get(id=sender_id)
        ChatMessage.objects.create(room=room, sender=sender, message=message)
        return sender.first_name 

