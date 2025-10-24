from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.openai_assistant.models import Chat, Assistant
from apps.openai_assistant.services import ChatService


chat_service = ChatService()

# --------------------------
# 🌐 WEB VIEWS
# --------------------------

@login_required
def chat_list(request):
    chats = Chat.objects.filter(user=request.user, is_active=True)
    return render(request, "openai_assistant/chat_list.html", {"chats": chats})


@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user, is_active=True)
    return render(request, "openai_assistant/chat_detail.html", {
        "chat": chat,
        "messages": chat.messages.all(),
    })


@login_required
def chat_create(request, assistant_id=None):
    if assistant_id:
        assistant = get_object_or_404(Assistant, pk=assistant_id, is_active=True)
    else:
        assistants = Assistant.objects.filter(is_active=True)
        return render(request, "openai_assistant/chat_create.html", {"assistants": assistants})

    if request.method == "POST":
        try:
            chat = Chat.objects.create(
                user=request.user,
                assistant=assistant,
                title=request.POST.get("title", f"Chat with {assistant.name}"),
            )
            chat_service.client.create_thread()  # crea thread en OpenAI
            messages.success(request, _("Chat creado correctamente."))
            return redirect("chat_detail", chat_id=chat.id)
        except Exception as e:
            messages.error(request, f"Error al crear chat: {str(e)}")

    return render(request, "openai_assistant/chat_create.html", {"assistant": assistant})


@login_required
def chat_delete(request, chat_id):
    chat = get_object_or_404(Chat, pk=chat_id, user=request.user)
    if request.method == "POST":
        chat.is_active = False
        chat.save()
        messages.success(request, _("Chat eliminado correctamente."))
        return redirect("chat_list")
    return render(request, "openai_assistant/chat_confirm_delete.html", {"chat": chat})


# --------------------------
# 🧩 API VIEWS (DRF)
# --------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_chat_list(request):
    chats = Chat.objects.filter(user=request.user, is_active=True)
    return Response([
        {
            "id": str(c.id),
            "title": c.title,
            "assistant": {"id": str(c.assistant.id), "name": c.assistant.name},
            "updated_at": c.updated_at.isoformat(),
        }
        for c in chats
    ])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_chat_detail(request, chat_id):
    try:
        chat = Chat.objects.get(pk=chat_id, user=request.user, is_active=True)
        return Response({
            "id": str(chat.id),
            "title": chat.title,
            "assistant": {"id": str(chat.assistant.id), "name": chat.assistant.name},
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
                for m in chat.messages.all()
            ]
        })
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_send_message(request, chat_id):
    try:
        chat = Chat.objects.get(pk=chat_id, user=request.user, is_active=True)
        content = request.data.get("content")
        if not content:
            return Response({"error": "Message content is required"}, status=status.HTTP_400_BAD_REQUEST)

        new_messages = chat_service.send_message(chat, content)
        return Response({
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
                for m in new_messages
            ]
        })
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
