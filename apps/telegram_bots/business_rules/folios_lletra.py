from apps.telegram_bots.models import TelegramMessage, TelegramReaction
from apps.telegram_bots.services.telegram_api import TelegramAPI


class FoliosLletraRule:
    @staticmethod
    def execute(bot, chat, message):
        """
        Maneja mensajes dentro del grupo 'Folios Lletra'.
        Ejemplo: comando 'Asignar folios'.
        """
        text = (message.text or "").strip().lower()
        api = TelegramAPI(bot.token)

        if text == "asignar folios":
            from core.operations_panel.models import Operation
            from core.operations_panel.choices import OperationStatus

            operations = Operation.objects.filter(
                pre_folio__isnull=False,
                folio__isnull=True,
                status=OperationStatus.APPROVED
            )

            count = 0
            for op in operations:
                op.assign_folio()
                count += 1

            reply = f"✅ {count} pre-folios convertidos." if count else "ℹ️ No hay pre-folios pendientes."
            api.send_message(chat.telegram_id, reply, reply_to=message.telegram_id)
            print(f"[FoliosLletra] {count} pre-folios convertidos por {bot.username}")
            return {"status": "folios_assigned", "count": count}

        return {"status": "no_action"}

    # 💥 Aquí la parte que faltaba
    @staticmethod
    def handle_reaction(bot, chat, user, reaction_data):
        """
        Maneja reacciones (👍 o 👎) en mensajes del grupo 'Folios Lletra'.
        """
        api = TelegramAPI(bot.token)
        message_id = reaction_data.get('message_id')
        new_reactions = reaction_data.get('new_reaction', [])
        old_reactions = reaction_data.get('old_reaction', [])

        # 1️⃣ Buscar mensaje original
        try:
            message = TelegramMessage.objects.get(telegram_id=message_id, chat=chat)
        except TelegramMessage.DoesNotExist:
            print(f"[FoliosLletra] Mensaje no encontrado para reacción: {message_id}")
            return {"status": "message_not_found"}

        # 2️⃣ Procesar nuevas reacciones
        for emoji in new_reactions:
            emoji_value = emoji.get('emoji', '')

            # Crear o registrar la reacción
            TelegramReaction.objects.get_or_create(
                message=message,
                user=user,
                emoji=emoji_value
            )

            # Validar si el mensaje está vinculado a una operación
            operation = getattr(message, "operation", None)
            if not operation:
                continue

            # 👍 Aprobar operación → asigna pre-folio
            if emoji_value == '👍':
                pre_folio = operation.approve()
                if pre_folio:
                    reply_text = f"✅ Pre-folio asignado: {pre_folio}"
                    api.send_message(
                        chat.telegram_id,
                        reply_text,
                        reply_to=message.telegram_id
                    )
                    print(f"[FoliosLletra] Pre-folio {pre_folio} asignado en operación {operation.id}")
                else:
                    api.send_message(
                        chat.telegram_id,
                        "⚠️ No se pudo asignar el pre-folio.",
                        reply_to=message.telegram_id
                    )

            # 👎 Cancelar operación
            elif emoji_value == '👎':
                operation.status = 'CANCELED'
                operation.folio = None
                operation.pre_folio = None
                operation.save()

                api.send_message(
                    chat.telegram_id,
                    "❌ Operación cancelada",
                    reply_to=message.telegram_id
                )
                logger.info(f"[FoliosLletra] Operación {operation.id} cancelada")

        # 3️⃣ Eliminar reacciones antiguas si se retiraron
        for emoji in old_reactions:
            TelegramReaction.objects.filter(
                message=message,
                user=user,
                emoji=emoji.get('emoji', '')
            ).delete()

        return {"status": "reaction_processed", "message_id": str(message.id)}
