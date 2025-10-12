import json
import logging
from urllib.request import Request
from googleapiclient.discovery import build

from apps.google_drive.services import get_credentials_from_user
from apps.telegram_bots.models import TelegramUser
from core.system.models import SystemUser

logger = logging.getLogger(__name__)


def register_event(tool_input, telegram_user: TelegramUser=None):
    """
    Process the register_operations tool call from OpenAI Assistant.

    Args:
        tool_input (str): JSON string with operations data

    Returns:
        dict: Result of the operation
    """
    try:
        # Parse the input JSON
        input_data = json.loads(tool_input)
        _user = SystemUser.objects.get(telegram_username=telegram_user.first_name.strip()) if telegram_user else None
        credentials = get_credentials_from_user(_user)  # Debes implementar esta función

        # Refrescar token si está expirado
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        # Construir servicio de Google Calendar
        service = build('calendar', 'v3', credentials=credentials)
        print(input_data)

        # Crear cuerpo del evento
        event = {
            'summary': input_data["title"],
            'description': input_data["description"],
            'start': {
                'dateTime': input_data["start_datetime"],
                'timeZone': 'America/Mexico_City',
            },
            'end': {
                'dateTime': input_data["end_datetime"],
                'timeZone': 'America/Mexico_City',
            },
            'reminders': {
                'useDefault': True,
            },
        }

        # Insertar el evento
        created_event = service.events().insert(calendarId=_user.calendar_url, body=event).execute()


        return {"results": "Evento registrado con exito"}

    except Exception as e:
        print(f"Error in register_operations: {str(e)}")
        return {"error": str(e)}

