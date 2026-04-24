from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_group_groupmessage'),
    ]

    operations = [
        # Add reverse index (receiver, sender) for fast inbox queries
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['receiver', 'sender'], name='chat_msg_recv_send_idx'),
        ),
        # Add index (receiver, is_read) for fast unread-count queries
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['receiver', 'is_read'], name='chat_msg_recv_read_idx'),
        ),
    ]
