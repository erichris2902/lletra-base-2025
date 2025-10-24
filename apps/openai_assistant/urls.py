from django.urls import path

from apps.openai_assistant import views

app_name = 'openai_assistant'

urlpatterns = [
    # Web UI URLs
    path('assistants/', views.assistant_list, name='assistant_list'),
    path('assistants/create/', views.assistant_create, name='assistant_create'),
    path('assistants/<uuid:assistant_id>/', views.assistant_detail, name='assistant_detail'),
    path('assistants/<uuid:assistant_id>/update/', views.assistant_update, name='assistant_update'),
    path('assistants/<uuid:assistant_id>/delete/', views.assistant_delete, name='assistant_delete'),
    
    path('chats/', views.chat_list, name='chat_list'),
    path('chats/create/', views.chat_create, name='chat_create'),
    path('chats/create/<uuid:assistant_id>/', views.chat_create, name='chat_create_with_assistant'),
    path('chats/<uuid:chat_id>/', views.chat_detail, name='chat_detail'),
    path('chats/<uuid:chat_id>/delete/', views.chat_delete, name='chat_delete'),

    # API URLs
    path('api/assistants/', views.api_assistant_list, name='api_assistant_list'),
    path('api/assistants/<uuid:assistant_id>/', views.api_assistant_detail, name='api_assistant_detail'),
    path('api/assistants/create/', views.api_assistant_create, name='api_assistant_create'),
    
    path('api/chats/', views.api_chat_list, name='api_chat_list'),
    path('api/chats/<uuid:chat_id>/', views.api_chat_detail, name='api_chat_detail'),
    path('api/chats/create/', views.chat_create, name='api_chat_create'),
    path('api/chats/<uuid:chat_id>/send/', views.api_send_message, name='api_send_message'),
]