"""
WebSocket URL configuration for ikigai2025 project.

This file defines the WebSocket URL patterns for the project.
Each application that uses WebSockets should define its own consumers and add them to this list.
"""

from django.urls import path

# Import consumers from applications
# Example: from apps.chat.consumers import ChatConsumer

websocket_urlpatterns = [
    # Define WebSocket URL patterns here
    # Example: path('ws/chat/<str:room_name>/', ChatConsumer.as_asgi()),
]