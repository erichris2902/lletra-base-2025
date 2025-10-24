from datetime import datetime


class ChatDomain:

    def __init__(self, user_id, assistant_id, title=None, thread_id=None):
        self.user_id = user_id
        self.assistant_id = assistant_id
        self.title = title or "Chat"
        self.thread_id = thread_id
        self.created_at = datetime.now()
        self.messages = []

    def add_message(self, role, content):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })

    def get_history(self, limit=None):
        if limit:
            return self.messages[-limit:]
        return self.messages

    def summary(self):
        return {
            "assistant_id": self.assistant_id,
            "user_id": self.user_id,
            "messages_count": len(self.messages),
            "title": self.title,
            "thread_id": self.thread_id
        }
