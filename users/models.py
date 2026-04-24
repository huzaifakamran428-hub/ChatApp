from django.db import models
from django.contrib.auth.models import AbstractUser


def avatar_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1]
    return f'avatars/{instance.username}.{ext}'


class CustomUser(AbstractUser):
    """Extended user model — uses Django's built-in auth with email added."""
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True, max_length=300)
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
