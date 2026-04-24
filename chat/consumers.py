import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, Group, GroupMessage

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for 1-on-1 real-time messaging."""

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        self.other_username = self.scope['url_route']['kwargs']['username']
        usernames = sorted([self.user.username, self.other_username])
        self.room_name = f'chat_{"_".join(usernames)}'
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
        await self.mark_messages_read()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        # ── File / Voice message ──
        # FIX: The file is already saved to DB by the upload view (upload_file_view /
        # upload_voice_view). Here we only need to broadcast it over WebSocket so the
        # RECEIVER sees it instantly without refreshing. We also notify the receiver's
        # home-page notification channel.
        if data.get('file_message'):
            avatar = await self.get_avatar()
            ts = data.get('timestamp', '')

            # Broadcast inside the chat room so the receiver's room.html picks it up
            await self.channel_layer.group_send(self.room_name, {
                'type': 'chat_message',
                'file_message': True,
                'file_url': data.get('file_url', ''),
                'file_name': data.get('file_name', ''),
                'file_type': data.get('file_type', 'document'),
                'file_size': data.get('file_size', ''),
                'message': data.get('caption', ''),
                'sender': self.user.username,
                'sender_avatar': avatar,
                'timestamp': ts,
                'message_id': data.get('message_id', -1),
            })

            # FIX: Also push to the receiver's notification channel so their home
            # page updates in real time (was missing for file/voice messages before).
            file_type = data.get('file_type', 'document')
            preview_map = {
                'image': '📷 Image',
                'video': '🎬 Video',
                'voice': '🎤 Voice message',
                'audio': '🎵 Audio',
                'pdf':   '📄 PDF',
                'archive': '🗜 Archive',
            }
            preview = preview_map.get(file_type, f'📎 {data.get("file_name", "File")}')
            chat_url = f'/chat/room/{self.user.username}/'

            await self.channel_layer.group_send(
                f'notif_{self.other_username}',
                {
                    'type': 'new_message',
                    'sender': self.user.username,
                    'sender_avatar': avatar,
                    'preview': preview,
                    'timestamp': ts,
                    'chat_url': chat_url,
                    'is_group': False,
                }
            )
            return

        # ── Text message ──
        message_content = data.get('message', '').strip()
        if not message_content:
            return
        message = await self.save_message(message_content)
        avatar = await self.get_avatar()
        ts = timezone.localtime(message.timestamp).strftime('%I:%M %p')
        chat_url = f'/chat/room/{self.user.username}/'

        await self.channel_layer.group_send(self.room_name, {
            'type': 'chat_message',
            'message': message_content,
            'sender': self.user.username,
            'sender_avatar': avatar,
            'timestamp': ts,
            'message_id': message.id,
        })

        # Notify receiver's home page in real time
        await self.channel_layer.group_send(
            f'notif_{self.other_username}',
            {
                'type': 'new_message',
                'sender': self.user.username,
                'sender_avatar': avatar,
                'preview': message_content[:60],
                'timestamp': ts,
                'chat_url': chat_url,
                'is_group': False,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event.get('message', ''),
            'sender': event['sender'],
            'sender_avatar': event.get('sender_avatar', ''),
            'timestamp': event.get('timestamp', ''),
            'message_id': event.get('message_id', -1),
            'file_message': event.get('file_message', False),
            'file_url': event.get('file_url', ''),
            'file_name': event.get('file_name', ''),
            'file_type': event.get('file_type', ''),
            'file_size': event.get('file_size', ''),
        }))

    @database_sync_to_async
    def save_message(self, content):
        other_user = User.objects.get(username=self.other_username)
        return Message.objects.create(sender=self.user, receiver=other_user, message_content=content)

    @database_sync_to_async
    def mark_messages_read(self):
        try:
            other_user = User.objects.get(username=self.other_username)
            Message.objects.filter(sender=other_user, receiver=self.user, is_read=False).update(is_read=True)
        except User.DoesNotExist:
            pass

    @database_sync_to_async
    def get_avatar(self):
        # Re-fetch from DB to get fresh avatar URL
        try:
            u = User.objects.only('avatar').get(pk=self.user.pk)
            return u.avatar.url if u.avatar else ''
        except Exception:
            return ''


class GroupChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for group chat rooms."""

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_name = f'group_{self.group_id}'
        if not await self.check_membership():
            await self.close()
            return
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('file_message'):
            avatar = await self.get_avatar()
            ts = data.get('timestamp', '')
            file_type = data.get('file_type', 'document')

            await self.channel_layer.group_send(self.room_name, {
                'type': 'group_message',
                'file_message': True,
                'file_url': data.get('file_url', ''),
                'file_name': data.get('file_name', ''),
                'file_type': file_type,
                'file_size': data.get('file_size', ''),
                'message': '',
                'sender': self.user.username,
                'sender_avatar': avatar,
                'timestamp': ts,
                'message_id': data.get('message_id', -1),
            })

            # FIX: Notify all group members' home pages for file messages too
            preview_map = {
                'image': '📷 Image',
                'video': '🎬 Video',
                'voice': '🎤 Voice message',
                'audio': '🎵 Audio',
                'pdf':   '📄 PDF',
                'archive': '🗜 Archive',
            }
            preview = preview_map.get(file_type, f'📎 {data.get("file_name", "File")}')
            group_name = await self.get_group_name()
            member_usernames = await self.get_member_usernames()
            for uname in member_usernames:
                if uname != self.user.username:
                    await self.channel_layer.group_send(
                        f'notif_{uname}',
                        {
                            'type': 'new_message',
                            'sender': self.user.username,
                            'sender_avatar': avatar,
                            'preview': preview,
                            'timestamp': ts,
                            'chat_url': f'/chat/group/{self.group_id}/',
                            'is_group': True,
                            'group_name': group_name,
                        }
                    )
            return

        message_content = data.get('message', '').strip()
        if not message_content:
            return
        msg = await self.save_group_message(message_content)
        avatar = await self.get_avatar()
        ts = timezone.localtime(msg.timestamp).strftime('%I:%M %p')
        group_name = await self.get_group_name()

        await self.channel_layer.group_send(self.room_name, {
            'type': 'group_message',
            'message': message_content,
            'sender': self.user.username,
            'sender_avatar': avatar,
            'timestamp': ts,
            'message_id': msg.id,
            'file_message': False,
        })

        # Notify all group members' home pages
        member_usernames = await self.get_member_usernames()
        for uname in member_usernames:
            if uname != self.user.username:
                await self.channel_layer.group_send(
                    f'notif_{uname}',
                    {
                        'type': 'new_message',
                        'sender': self.user.username,
                        'sender_avatar': avatar,
                        'preview': message_content[:60],
                        'timestamp': ts,
                        'chat_url': f'/chat/group/{self.group_id}/',
                        'is_group': True,
                        'group_name': group_name,
                    }
                )

    async def group_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event.get('message', ''),
            'sender': event['sender'],
            'sender_avatar': event.get('sender_avatar', ''),
            'timestamp': event.get('timestamp', ''),
            'message_id': event.get('message_id', -1),
            'file_message': event.get('file_message', False),
            'file_url': event.get('file_url', ''),
            'file_name': event.get('file_name', ''),
            'file_type': event.get('file_type', ''),
            'file_size': event.get('file_size', ''),
        }))

    @database_sync_to_async
    def check_membership(self):
        try:
            group = Group.objects.get(id=self.group_id)
            return group.members.filter(id=self.user.id).exists()
        except Group.DoesNotExist:
            return False

    @database_sync_to_async
    def save_group_message(self, content):
        group = Group.objects.get(id=self.group_id)
        return GroupMessage.objects.create(group=group, sender=self.user, message_content=content)

    @database_sync_to_async
    def get_avatar(self):
        try:
            u = User.objects.only('avatar').get(pk=self.user.pk)
            return u.avatar.url if u.avatar else ''
        except Exception:
            return ''

    @database_sync_to_async
    def get_group_name(self):
        try:
            return Group.objects.get(id=self.group_id).name
        except Group.DoesNotExist:
            return 'Group'

    @database_sync_to_async
    def get_member_usernames(self):
        try:
            return list(Group.objects.get(id=self.group_id).members.values_list('username', flat=True))
        except Group.DoesNotExist:
            return []


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Global consumer — one per logged-in user.
    Receives new message notifications from any chat/group
    so the home page updates in real time without refresh.
    """

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        self.group_name = f'notif_{self.user.username}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass  # client never sends to this socket

    async def new_message(self, event):
        """Push a new-message event to this user's home page."""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'sender': event['sender'],
            'sender_avatar': event.get('sender_avatar', ''),
            'preview': event.get('preview', ''),
            'timestamp': event.get('timestamp', ''),
            'chat_url': event.get('chat_url', ''),
            'is_group': event.get('is_group', False),
            'group_name': event.get('group_name', ''),
        }))
