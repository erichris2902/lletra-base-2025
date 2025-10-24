

class InlineQueryHandler:
    """
    Maneja consultas inline (@Bot en modo inline).
    """
    def __init__(self, bot):
        self.bot = bot

    def handle(self, inline_query_data):
        query = inline_query_data.get('query', '')
        from_user = inline_query_data.get('from', {}).get('username', 'unknown')
        print(f"[InlineQueryHandler] Inline query de @{from_user}: {query}")

        # Aquí podrías responder con resultados inline
        # (actualmente solo registramos la acción)
        return {"status": "inline_query_processed", "query": query}