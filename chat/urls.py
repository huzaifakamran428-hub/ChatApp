from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('room/<str:username>/', views.chat_room_view, name='room'),
    path('search/', views.search_users_view, name='search'),
    path('send/', views.send_message_view, name='send'),
    path('upload/', views.upload_file_view, name='upload'),
    path('upload/voice/', views.upload_voice_view, name='upload_voice'),
    path('group/create/', views.create_group_view, name='create_group'),
    path('group/<int:group_id>/', views.group_room_view, name='group_room'),
    path('group/<int:group_id>/upload/', views.group_upload_file_view, name='group_upload'),
    path('group/<int:group_id>/upload/voice/', views.upload_group_voice_view, name='group_upload_voice'),
    path('group/<int:group_id>/add-member/', views.add_member_view, name='add_member'),
    path('group/<int:group_id>/leave/', views.leave_group_view, name='leave_group'),
]
