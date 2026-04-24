from django.db import models
from django.conf import settings
import os


def message_file_path(instance, filename):
    return f'chat_files/{instance.sender.username}/{filename}'


def group_icon_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1]
    return f'group_icons/{instance.id}.{ext}'


class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, max_length=300)
    icon = models.ImageField(upload_to=group_icon_path, blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_groups',
        on_delete=models.CASCADE
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='group_memberships',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_icon_url(self):
        if self.icon:
            return self.icon.url
        return None


class GroupMessage(models.Model):
    group = models.ForeignKey(Group, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='group_messages_sent',
        on_delete=models.CASCADE
    )
    message_content = models.TextField(blank=True)
    file = models.FileField(upload_to='group_files/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'[{self.group.name}] {self.sender.username}: {self.message_content[:40]}'


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_messages',
        on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_messages',
        on_delete=models.CASCADE
    )
    message_content = models.TextField(blank=True)
    file = models.FileField(upload_to=message_file_path, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['sender', 'receiver']),
            models.Index(fields=['receiver', 'sender']),        # FIX: reverse index for inbox queries
            models.Index(fields=['timestamp']),
            models.Index(fields=['receiver', 'is_read']),       # FIX: fast unread-count queries
        ]

    def __str__(self):
        return f'{self.sender.username} → {self.receiver.username}: {self.message_content[:40]}'

    def get_file_type(self):
        if not self.file:
            return None
        ext = os.path.splitext(self.file_name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return 'image'
        elif ext in ['.mp4', '.webm', '.mov']:
            return 'video'
        elif ext in ['.pdf']:
            return 'pdf'
        else:
            return 'document'
