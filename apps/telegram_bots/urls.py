from django.urls import path
from . import views

app_name = 'telegram_bots'

urlpatterns = [
    path('webhook/<str:bot_username>/', views.telegram_webhook, name='webhook'),
    path('webapp/<str:bot_username>/', views.telegram_webapp_callback, name='webapp_callback'),
]