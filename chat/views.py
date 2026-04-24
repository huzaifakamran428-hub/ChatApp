import json
import os
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Prefetch, Max
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages as django_messages
from .models import Message, Group, GroupMessage

User = get_user_model()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB (reduced from 5 GB to be practical)


def get_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']:
        return 'image'
    elif ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v']:
        return 'video'
    elif ext in ['.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a']:
        return 'audio'
    elif ext in ['.pdf']:
        return 'pdf'
    elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
        return 'archive'
    else:
        return 'document'


def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 ** 2:
        return f'{size_bytes / 1024:.1f} KB'
    elif size_bytes < 1024 ** 3:
        return f'{size_bytes / (1024**2):.1f} MB'
    else:
        return f'{size_bytes / (1024**3):.2f} GB'


@login_required
def home_view(request):
    # FIX: Use a single optimised query instead of N+1 queries per conversation.
    # Get all user IDs the current user has chatted with.
    sent_to = Message.objects.filter(sender=request.user).values_list('receiver_id', flat=True)
    received_from = Message.objects.filter(receiver=request.user).values_list('sender_id', flat=True)
    chatted_user_ids = set(list(sent_to) + list(received_from))

    # Fetch all chatted users in ONE query (with avatar via select_related)
    chatted_users = {u.pk: u for u in User.objects.filter(pk__in=chatted_user_ids)}

    # Fetch last message per conversation in ONE query using subquery
    conversations = []
    for uid in chatted_user_ids:
        other_user = chatted_users.get(uid)
        if not other_user:
            continue
        last_msg = Message.objects.filter(
            Q(sender=request.user, receiver_id=uid) |
            Q(sender_id=uid, receiver=request.user)
        ).order_by('-timestamp').first()
        unread_count = Message.objects.filter(
            sender_id=uid, receiver=request.user, is_read=False
        ).count()
        conversations.append({
            'user': other_user,
            'last_message': last_msg,
            'unread_count': unread_count,
        })

    conversations.sort(
        key=lambda x: x['last_message'].timestamp if x['last_message'] else timezone.datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    all_users = User.objects.exclude(pk=request.user.pk).exclude(pk__in=chatted_user_ids)
    user_groups = request.user.group_memberships.select_related('created_by').prefetch_related('members').order_by('-created_at')

    return render(request, 'chat/home.html', {
        'conversations': conversations,
        'all_users': all_users,
        'user_groups': user_groups,
    })


@login_required
def chat_room_view(request, username):
    other_user = get_object_or_404(User, username=username)
    if other_user == request.user:
        return redirect('chat:home')
    # FIX: select_related('sender', 'sender__avatar') to avoid repeated avatar DB hits
    messages_qs = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).select_related('sender', 'receiver').order_by('timestamp')
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    return render(request, 'chat/room.html', {'other_user': other_user, 'messages': messages_qs})


@login_required
def search_users_view(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = User.objects.filter(username__icontains=query).exclude(pk=request.user.pk)
    return render(request, 'chat/search.html', {'results': results, 'query': query})


# ── Group Views ────────────────────────────────────────────────────────────────

@login_required
def create_group_view(request):
    all_users = User.objects.exclude(pk=request.user.pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        member_ids = request.POST.getlist('members')
        icon = request.FILES.get('icon')

        if not name:
            django_messages.error(request, 'Group name is required.')
            return render(request, 'chat/create_group.html', {'all_users': all_users})

        group = Group.objects.create(name=name, description=description, created_by=request.user)
        if icon:
            group.icon = icon
            group.save()

        group.members.add(request.user)
        for uid in member_ids:
            try:
                group.members.add(User.objects.get(pk=uid))
            except User.DoesNotExist:
                pass

        django_messages.success(request, f'Group "{name}" created!')
        return redirect('chat:group_room', group_id=group.id)

    return render(request, 'chat/create_group.html', {'all_users': all_users})


@login_required
def group_room_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not group.members.filter(id=request.user.id).exists():
        django_messages.error(request, 'You are not a member of this group.')
        return redirect('chat:home')
    # FIX: select_related to avoid N+1 avatar queries
    group_messages = GroupMessage.objects.filter(group=group).select_related('sender').order_by('timestamp')
    members = group.members.all()
    return render(request, 'chat/group_room.html', {
        'group': group,
        'messages': group_messages,
        'members': members,
        'is_admin': group.created_by == request.user,
    })


@login_required
@require_POST
def group_upload_file_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not group.members.filter(id=request.user.id).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'error': 'No file provided'}, status=400)
    if uploaded_file.size > MAX_FILE_SIZE:
        return JsonResponse({'error': f'File exceeds {format_file_size(MAX_FILE_SIZE)} limit'}, status=400)

    file_name = uploaded_file.name
    file_type = get_file_type(file_name)
    file_size = format_file_size(uploaded_file.size)

    msg = GroupMessage.objects.create(
        group=group, sender=request.user,
        message_content='', file=uploaded_file,
        file_name=file_name, file_type=file_type,
    )
    return JsonResponse({
        'ok': True, 'message_id': msg.id,
        'sender': request.user.username,
        'sender_avatar': request.user.avatar.url if request.user.avatar else '',
        'timestamp': timezone.localtime(msg.timestamp).strftime('%I:%M %p'),
        'file_url': msg.file.url,
        'file_name': file_name,
        'file_type': file_type,
        'file_size': file_size,
    })


@login_required
@require_POST
def add_member_view(request, group_id):
    group = get_object_or_404(Group, id=group_id, created_by=request.user)
    username = request.POST.get('username', '').strip()
    try:
        user = User.objects.get(username=username)
        group.members.add(user)
        django_messages.success(request, f'{username} added to the group.')
    except User.DoesNotExist:
        django_messages.error(request, f'User "{username}" not found.')
    return redirect('chat:group_room', group_id=group_id)


@login_required
@require_POST
def leave_group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    group.members.remove(request.user)
    django_messages.success(request, f'You left "{group.name}".')
    return redirect('chat:home')


# ── HTTP fallbacks ─────────────────────────────────────────────────────────────

@login_required
@require_POST
@csrf_protect
def send_message_view(request):
    try:
        data = json.loads(request.body)
        content = data.get('message', '').strip()
        receiver_username = data.get('receiver', '')
        if not content or not receiver_username:
            return JsonResponse({'error': 'Missing message or receiver'}, status=400)
        receiver = get_object_or_404(User, username=receiver_username)
        msg = Message.objects.create(sender=request.user, receiver=receiver, message_content=content)
        return JsonResponse({
            'ok': True, 'message': msg.message_content, 'sender': request.user.username,
            'timestamp': timezone.localtime(msg.timestamp).strftime('%I:%M %p'), 'message_id': msg.id,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def upload_file_view(request):
    receiver_username = request.POST.get('receiver', '')
    if not receiver_username:
        return JsonResponse({'error': 'No receiver'}, status=400)
    receiver = get_object_or_404(User, username=receiver_username)
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'error': 'No file provided'}, status=400)
    if uploaded_file.size > MAX_FILE_SIZE:
        return JsonResponse({'error': f'File exceeds {format_file_size(MAX_FILE_SIZE)} limit'}, status=400)

    file_name = uploaded_file.name
    file_type = get_file_type(file_name)
    file_size = format_file_size(uploaded_file.size)

    msg = Message.objects.create(
        sender=request.user, receiver=receiver,
        message_content='', file=uploaded_file,
        file_name=file_name, file_type=file_type,
    )
    return JsonResponse({
        'ok': True, 'message_id': msg.id,
        'sender': request.user.username,
        'sender_avatar': request.user.avatar.url if request.user.avatar else '',
        'timestamp': timezone.localtime(msg.timestamp).strftime('%I:%M %p'),
        'file_url': msg.file.url,
        'file_name': file_name,
        'file_type': file_type,
        'file_size': file_size,
    })


@login_required
@require_POST
def upload_voice_view(request):
    """Upload a recorded voice message (WebM/OGG blob from MediaRecorder)."""
    receiver_username = request.POST.get('receiver', '')
    if not receiver_username:
        return JsonResponse({'error': 'No receiver'}, status=400)
    receiver = get_object_or_404(User, username=receiver_username)
    voice_blob = request.FILES.get('voice')
    if not voice_blob:
        return JsonResponse({'error': 'No audio'}, status=400)

    import uuid
    voice_blob.name = f'voice_{uuid.uuid4().hex}.webm'

    msg = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        message_content='',
        file=voice_blob,
        file_name=voice_blob.name,
        file_type='voice',
    )
    return JsonResponse({
        'ok': True,
        'message_id': msg.id,
        'sender': request.user.username,
        'sender_avatar': request.user.avatar.url if request.user.avatar else '',
        'timestamp': timezone.localtime(msg.timestamp).strftime('%I:%M %p'),
        'file_url': msg.file.url,
        'file_name': voice_blob.name,
        'file_type': 'voice',
        'file_size': '',
    })


@login_required
@require_POST
def upload_group_voice_view(request, group_id):
    """Upload a voice message to a group."""
    group = get_object_or_404(Group, id=group_id)
    if not group.members.filter(id=request.user.id).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)
    voice_blob = request.FILES.get('voice')
    if not voice_blob:
        return JsonResponse({'error': 'No audio'}, status=400)

    import uuid
    voice_blob.name = f'voice_{uuid.uuid4().hex}.webm'

    msg = GroupMessage.objects.create(
        group=group,
        sender=request.user,
        message_content='',
        file=voice_blob,
        file_name=voice_blob.name,
        file_type='voice',
    )
    return JsonResponse({
        'ok': True,
        'message_id': msg.id,
        'sender': request.user.username,
        'sender_avatar': request.user.avatar.url if request.user.avatar else '',
        'timestamp': timezone.localtime(msg.timestamp).strftime('%I:%M %p'),
        'file_url': msg.file.url,
        'file_name': voice_blob.name,
        'file_type': 'voice',
        'file_size': '',
    })
