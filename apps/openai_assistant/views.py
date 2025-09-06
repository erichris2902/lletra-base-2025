from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db import transaction
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

import json
import logging

from .models import Assistant, Chat, Message, Tool, ToolExecution
from .services import OpenAIService

logger = logging.getLogger(__name__)
openai_service = OpenAIService()

# Web views for UI
@login_required
def assistant_list(request):
    """View to list all assistants."""
    assistants = Assistant.objects.filter(is_active=True)
    return render(request, 'openai_assistant/assistant_list.html', {
        'assistants': assistants
    })

@login_required
def assistant_detail(request, assistant_id):
    """View to show assistant details."""
    assistant = get_object_or_404(Assistant, pk=assistant_id, is_active=True)
    tools = assistant.tools.all()
    return render(request, 'openai_assistant/assistant_detail.html', {
        'assistant': assistant,
        'tools': tools
    })

@login_required
def assistant_create(request):
    """View to create a new assistant."""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Create assistant
                assistant = Assistant.objects.create(
                    name=request.POST.get('name'),
                    description=request.POST.get('description', ''),
                    instructions=request.POST.get('instructions'),
                    model=request.POST.get('model', 'gpt-4o'),
                    created_by=request.user
                )
                
                # Create tools if provided
                tools_data = request.POST.get('tools', '[]')
                tools = json.loads(tools_data)
                
                for tool_data in tools:
                    Tool.objects.create(
                        assistant=assistant,
                        name=tool_data.get('name'),
                        type=tool_data.get('type'),
                        description=tool_data.get('description', ''),
                        parameters=tool_data.get('parameters', {})
                    )
                
                # Create in OpenAI
                openai_service.create_assistant(assistant)
                
                messages.success(request, _('Assistant created successfully.'))
                return redirect('assistant_detail', assistant_id=assistant.id)
        except Exception as e:
            logger.error(f"Error creating assistant: {str(e)}")
            messages.error(request, _('Error creating assistant: {0}').format(str(e)))
    
    return render(request, 'openai_assistant/assistant_form.html')

@login_required
def assistant_update(request, assistant_id):
    """View to update an assistant."""
    assistant = get_object_or_404(Assistant, pk=assistant_id, is_active=True)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Update assistant
                assistant.name = request.POST.get('name')
                assistant.description = request.POST.get('description', '')
                assistant.instructions = request.POST.get('instructions')
                assistant.model = request.POST.get('model', 'gpt-4o')
                assistant.save()
                
                # Update tools
                tools_data = request.POST.get('tools', '[]')
                tools = json.loads(tools_data)
                
                # Delete existing tools
                assistant.tools.all().delete()
                
                # Create new tools
                for tool_data in tools:
                    Tool.objects.create(
                        assistant=assistant,
                        name=tool_data.get('name'),
                        type=tool_data.get('type'),
                        description=tool_data.get('description', ''),
                        parameters=tool_data.get('parameters', {})
                    )
                
                # Update in OpenAI
                openai_service.update_assistant(assistant)
                
                messages.success(request, _('Assistant updated successfully.'))
                return redirect('assistant_detail', assistant_id=assistant.id)
        except Exception as e:
            logger.error(f"Error updating assistant: {str(e)}")
            messages.error(request, _('Error updating assistant: {0}').format(str(e)))
    
    tools = assistant.tools.all()
    return render(request, 'openai_assistant/assistant_form.html', {
        'assistant': assistant,
        'tools': tools
    })

@login_required
def assistant_delete(request, assistant_id):
    """View to delete an assistant."""
    assistant = get_object_or_404(Assistant, pk=assistant_id)
    
    if request.method == 'POST':
        try:
            # Delete from OpenAI
            openai_service.delete_assistant(assistant)
            
            # Mark as inactive
            assistant.is_active = False
            assistant.save()
            
            messages.success(request, _('Assistant deleted successfully.'))
            return redirect('assistant_list')
        except Exception as e:
            logger.error(f"Error deleting assistant: {str(e)}")
            messages.error(request, _('Error deleting assistant: {0}').format(str(e)))
    
    return render(request, 'openai_assistant/assistant_confirm_delete.html', {
        'assistant': assistant
    })

@login_required
def chat_list(request):
    """View to list all chats for the current user."""
    chats = Chat.objects.filter(user=request.user, is_active=True)
    return render(request, 'openai_assistant/chat_list.html', {
        'chats': chats
    })

@login_required
def chat_detail(request, chat_id):
    """View to show chat details and messages."""
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user, is_active=True)
    messages_list = chat.messages.all()
    return render(request, 'openai_assistant/chat_detail.html', {
        'chat': chat,
        'messages': messages_list
    })

@login_required
def chat_create(request, assistant_id=None):
    """View to create a new chat."""
    if assistant_id:
        assistant = get_object_or_404(Assistant, pk=assistant_id, is_active=True)
    else:
        assistants = Assistant.objects.filter(is_active=True)
        return render(request, 'openai_assistant/chat_create.html', {
            'assistants': assistants
        })
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title', '')
            
            # Create chat
            chat = Chat.objects.create(
                user=request.user,
                assistant=assistant,
                title=title or f"Chat with {assistant.name}"
            )
            
            # Create thread in OpenAI
            chat.openai_thread_id = openai_service.create_thread()
            chat.save()
            
            messages.success(request, _('Chat created successfully.'))
            return redirect('chat_detail', chat_id=chat.id)
        except Exception as e:
            logger.error(f"Error creating chat: {str(e)}")
            messages.error(request, _('Error creating chat: {0}').format(str(e)))
    
    return render(request, 'openai_assistant/chat_create.html', {
        'assistant': assistant
    })

@login_required
def chat_delete(request, chat_id):
    """View to delete a chat."""
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Mark as inactive
            chat.is_active = False
            chat.save()
            
            messages.success(request, _('Chat deleted successfully.'))
            return redirect('chat_list')
        except Exception as e:
            logger.error(f"Error deleting chat: {str(e)}")
            messages.error(request, _('Error deleting chat: {0}').format(str(e)))
    
    return render(request, 'openai_assistant/chat_confirm_delete.html', {
        'chat': chat
    })

@login_required
@require_POST
def send_message(request, chat_id):
    """View to send a message to a chat."""
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user, is_active=True)
    
    try:
        content = request.POST.get('content')
        if not content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        # Send message and get response
        new_messages = openai_service.send_message_and_get_response(chat, content)
        
        # Return the new messages
        return JsonResponse({
            'success': True,
            'messages': [
                {
                    'id': str(msg.id),
                    'role': msg.role,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat()
                }
                for msg in new_messages
            ]
        })
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

# API views for programmatic access
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_assistant_list(request):
    """API endpoint to list all assistants."""
    assistants = Assistant.objects.filter(is_active=True)
    return Response([
        {
            'id': str(assistant.id),
            'name': assistant.name,
            'description': assistant.description,
            'model': assistant.model,
            'created_at': assistant.created_at.isoformat()
        }
        for assistant in assistants
    ])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_assistant_detail(request, assistant_id):
    """API endpoint to get assistant details."""
    try:
        assistant = Assistant.objects.get(pk=assistant_id, is_active=True)
        tools = assistant.tools.all()
        
        return Response({
            'id': str(assistant.id),
            'name': assistant.name,
            'description': assistant.description,
            'instructions': assistant.instructions,
            'model': assistant.model,
            'created_at': assistant.created_at.isoformat(),
            'tools': [
                {
                    'id': str(tool.id),
                    'name': tool.name,
                    'type': tool.type,
                    'description': tool.description,
                    'parameters': tool.parameters
                }
                for tool in tools
            ]
        })
    except Assistant.DoesNotExist:
        return Response({'error': 'Assistant not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_assistant_create(request):
    """API endpoint to create a new assistant."""
    try:
        with transaction.atomic():
            # Create assistant
            assistant = Assistant.objects.create(
                name=request.data.get('name'),
                description=request.data.get('description', ''),
                instructions=request.data.get('instructions'),
                model=request.data.get('model', 'gpt-4o'),
                created_by=request.user
            )
            
            # Create tools if provided
            tools_data = request.data.get('tools', [])
            
            for tool_data in tools_data:
                Tool.objects.create(
                    assistant=assistant,
                    name=tool_data.get('name'),
                    type=tool_data.get('type'),
                    description=tool_data.get('description', ''),
                    parameters=tool_data.get('parameters', {})
                )
            
            # Create in OpenAI
            openai_service.create_assistant(assistant)
            
            return Response({
                'id': str(assistant.id),
                'name': assistant.name,
                'description': assistant.description,
                'instructions': assistant.instructions,
                'model': assistant.model,
                'created_at': assistant.created_at.isoformat()
            }, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Error creating assistant: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_chat_list(request):
    """API endpoint to list all chats for the current user."""
    chats = Chat.objects.filter(user=request.user, is_active=True)
    return Response([
        {
            'id': str(chat.id),
            'title': chat.title,
            'assistant': {
                'id': str(chat.assistant.id),
                'name': chat.assistant.name
            },
            'created_at': chat.created_at.isoformat(),
            'updated_at': chat.updated_at.isoformat()
        }
        for chat in chats
    ])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_chat_detail(request, chat_id):
    """API endpoint to get chat details and messages."""
    try:
        chat = Chat.objects.get(pk=chat_id, user=request.user, is_active=True)
        messages_list = chat.messages.all()
        
        return Response({
            'id': str(chat.id),
            'title': chat.title,
            'assistant': {
                'id': str(chat.assistant.id),
                'name': chat.assistant.name
            },
            'created_at': chat.created_at.isoformat(),
            'updated_at': chat.updated_at.isoformat(),
            'messages': [
                {
                    'id': str(msg.id),
                    'role': msg.role,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat()
                }
                for msg in messages_list
            ]
        })
    except Chat.DoesNotExist:
        return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_chat_create(request):
    """API endpoint to create a new chat."""
    try:
        assistant_id = request.data.get('assistant_id')
        if not assistant_id:
            return Response({'error': 'Assistant ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        assistant = Assistant.objects.get(pk=assistant_id, is_active=True)
        title = request.data.get('title', '')
        
        # Create chat
        chat = Chat.objects.create(
            user=request.user,
            assistant=assistant,
            title=title or f"Chat with {assistant.name}"
        )
        
        # Create thread in OpenAI
        chat.openai_thread_id = openai_service.create_thread()
        chat.save()
        
        return Response({
            'id': str(chat.id),
            'title': chat.title,
            'assistant': {
                'id': str(chat.assistant.id),
                'name': chat.assistant.name
            },
            'created_at': chat.created_at.isoformat()
        }, status=status.HTTP_201_CREATED)
    except Assistant.DoesNotExist:
        return Response({'error': 'Assistant not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error creating chat: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_send_message(request, chat_id):
    """API endpoint to send a message to a chat."""
    try:
        chat = Chat.objects.get(pk=chat_id, user=request.user, is_active=True)
        
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Send message and get response
        new_messages = openai_service.send_message_and_get_response(chat, content)
        
        # Return the new messages
        return Response({
            'messages': [
                {
                    'id': str(msg.id),
                    'role': msg.role,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat()
                }
                for msg in new_messages
            ]
        })
    except Chat.DoesNotExist:
        return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)