import requests


class TelegramAPI:
    BASE_URL = "https://api.telegram.org"

    def __init__(self, token):
        self.token = token

    def send_message(self, chat_id, text, reply_to=None, parse_mode="HTML"):
        print("SEND_MESSAGE_TELEGRAM")
        url = f"{self.BASE_URL}/bot{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_to:
            payload["reply_to_message_id"] = reply_to
        try:
            r = requests.post(url, json=payload, timeout=5)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            return None
