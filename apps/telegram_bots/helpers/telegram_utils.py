import requests


def get_file_path(bot_token, file_id):
    """
    Devuelve el path del archivo desde la API de Telegram.
    """
    url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get('result', {}).get('file_path', '')
    except requests.RequestException as e:
        print(f"[TelegramUtils] Error obteniendo file_path: {e}")
        return ''
