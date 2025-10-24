import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.openai_assistant.models import Assistant, Tool
from apps.openai_assistant.services import AssistantService


assistant_service = AssistantService()

# --------------------------
# 🌐 WEB VIEWS
# --------------------------

@login_required
def assistant_list(request):
    assistants = Assistant.objects.filter(is_active=True)
    return render(request, "openai_assistant/assistant_list.html", {"assistants": assistants})


@login_required
def assistant_detail(request, assistant_id):
    assistant = get_object_or_404(Assistant, pk=assistant_id, is_active=True)
    return render(request, "openai_assistant/assistant_detail.html", {
        "assistant": assistant,
        "tools": assistant.tools.all()
    })


@login_required
def assistant_create(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                assistant = Assistant.objects.create(
                    name=request.POST.get("name"),
                    description=request.POST.get("description", ""),
                    instructions=request.POST.get("instructions"),
                    model=request.POST.get("model", "gpt-4o"),
                    created_by=request.user,
                )

                tools_data = json.loads(request.POST.get("tools", "[]"))
                for tool_data in tools_data:
                    Tool.objects.create(
                        assistant=assistant,
                        name=tool_data.get("name"),
                        type=tool_data.get("type"),
                        description=tool_data.get("description", ""),
                        parameters=tool_data.get("parameters", {}),
                    )

                assistant_service.create_assistant(assistant)
                messages.success(request, _("Assistant creado correctamente."))
                return redirect("assistant_detail", assistant_id=assistant.id)
        except Exception as e:
            messages.error(request, f"Error al crear assistant: {str(e)}")

    return render(request, "openai_assistant/assistant_form.html")


@login_required
def assistant_update(request, assistant_id):
    assistant = get_object_or_404(Assistant, pk=assistant_id, is_active=True)
    if request.method == "POST":
        try:
            with transaction.atomic():
                assistant.name = request.POST.get("name")
                assistant.description = request.POST.get("description", "")
                assistant.instructions = request.POST.get("instructions")
                assistant.model = request.POST.get("model", "gpt-4o")
                assistant.save()

                assistant.tools.all().delete()
                tools_data = json.loads(request.POST.get("tools", "[]"))
                for tool_data in tools_data:
                    Tool.objects.create(
                        assistant=assistant,
                        name=tool_data.get("name"),
                        type=tool_data.get("type"),
                        description=tool_data.get("description", ""),
                        parameters=tool_data.get("parameters", {}),
                    )

                assistant_service.update_assistant(assistant)
                messages.success(request, _("Assistant actualizado correctamente."))
                return redirect("assistant_detail", assistant_id=assistant.id)
        except Exception as e:
            messages.error(request, f"Error al actualizar assistant: {str(e)}")

    return render(request, "openai_assistant/assistant_form.html", {"assistant": assistant})


@login_required
def assistant_delete(request, assistant_id):
    assistant = get_object_or_404(Assistant, pk=assistant_id)
    if request.method == "POST":
        try:
            assistant_service.delete_assistant(assistant)
            assistant.is_active = False
            assistant.save()
            messages.success(request, _("Assistant eliminado correctamente."))
            return redirect("assistant_list")
        except Exception as e:
            messages.error(request, f"Error al eliminar assistant: {str(e)}")

    return render(request, "openai_assistant/assistant_confirm_delete.html", {"assistant": assistant})


# --------------------------
# 🧩 API VIEWS (DRF)
# --------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_assistant_list(request):
    assistants = Assistant.objects.filter(is_active=True)
    return Response([
        {
            "id": str(a.id),
            "name": a.name,
            "description": a.description,
            "model": a.model,
            "created_at": a.created_at.isoformat(),
        }
        for a in assistants
    ])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_assistant_detail(request, assistant_id):
    try:
        a = Assistant.objects.get(pk=assistant_id, is_active=True)
        return Response({
            "id": str(a.id),
            "name": a.name,
            "description": a.description,
            "instructions": a.instructions,
            "model": a.model,
            "tools": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "type": t.type,
                    "description": t.description,
                    "parameters": t.parameters,
                }
                for t in a.tools.all()
            ],
        })
    except Assistant.DoesNotExist:
        return Response({"error": "Assistant not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_assistant_create(request):
    try:
        with transaction.atomic():
            assistant = Assistant.objects.create(
                name=request.data.get("name"),
                description=request.data.get("description", ""),
                instructions=request.data.get("instructions"),
                model=request.data.get("model", "gpt-4o"),
                created_by=request.user,
            )

            for tool_data in request.data.get("tools", []):
                Tool.objects.create(
                    assistant=assistant,
                    name=tool_data.get("name"),
                    type=tool_data.get("type"),
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("parameters", {}),
                )

            assistant_service.create_assistant(assistant)
            return Response({
                "id": str(assistant.id),
                "name": assistant.name,
                "model": assistant.model,
            }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
