from apps.telegram_bots.models import TelegramMessage, TelegramReaction
from apps.telegram_bots.services.telegram_api import TelegramAPI


class EmbarquesLletraRule:
    """
    Regla de negocio para el grupo 'Embarques Lletra'.
    Se encarga de confirmar packings y manejar reacciones tipo 🤔.
    """

    @staticmethod
    def execute(bot, chat, message):
        text = (message.text or "").strip().lower()
        api = TelegramAPI(bot.token)

        # 1️⃣ Caso: confirmar packing
        if text == "confirmar packing":
            from core.operations_panel.models.operation import Operation
            from core.operations_panel.choices import OperationStatus

            operations = Operation.objects.filter(
                is_packing_ready=False,
                invoice__isnull=True,
                status=OperationStatus.APPROVED
            )

            count = 0
            for op in operations:
                if op.is_ready_for_invoicing():
                    op.is_packing_ready = True
                    op.save()
                    count += 1

            reply = f"✅ Se han cerrado {count} packings." if count else "ℹ️ No hay packings para cerrar."
            api.send_message(chat.telegram_id, reply, reply_to=message.telegram_id)
            print(f"[EmbarquesLletra] {count} packings confirmados por {bot.username}")

            return {"status": "packing_confirmed", "count": count}

        return {"status": "no_action"}

    # 💥 Reacciones
    @staticmethod
    def handle_reaction(bot, chat, user, reaction_data):
        """
        Maneja las reacciones (por ahora 🤔) en el grupo 'Embarques Lletra'.
        """
        api = TelegramAPI(bot.token)
        message_id = reaction_data.get('message_id')
        new_reactions = reaction_data.get('new_reaction', [])
        old_reactions = reaction_data.get('old_reaction', [])

        try:
            message = TelegramMessage.objects.get(telegram_id=message_id, chat=chat)
        except TelegramMessage.DoesNotExist:
            print(f"[EmbarquesLletra] Mensaje no encontrado: {message_id}")
            return {"status": "message_not_found"}

        for emoji in new_reactions:
            emoji_value = emoji.get('emoji', '')
            TelegramReaction.objects.get_or_create(
                message=message,
                user=user,
                emoji=emoji_value
            )

            if emoji_value == '🤔':
                from apps.telegram_bots.operations import send_operation_missing_items
                from core.operations_panel.models import Operation

                latest_operation = Operation.objects.order_by('-created_at').first()
                if latest_operation:
                    send_operation_missing_items(
                        latest_operation.id,
                        chat.telegram_id,
                        message.telegram_id,
                    )
                    print(f"[EmbarquesLletra] Faltantes enviados para operación {latest_operation.id}")
                    return {"status": "missing_items_sent", "operation_id": latest_operation.id}

                api.send_message(
                    chat.telegram_id,
                    "ℹ️ No hay operaciones disponibles para mostrar faltantes.",
                    reply_to=message.telegram_id,
                )
                print("[EmbarquesLletra] No hay operaciones para faltantes")
                return {"status": "no_operations_found"}

        # Eliminar reacciones antiguas
        for emoji in old_reactions:
            TelegramReaction.objects.filter(
                message=message,
                user=user,
                emoji=emoji.get('emoji', '')
            ).delete()

        return {"status": "reaction_processed"}
