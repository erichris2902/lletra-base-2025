import json
from datetime import datetime

from django.db import transaction
from apps.telegram_bots.models import TelegramGroup
from apps.telegram_bots.services.services import send_telegram_message
from core.operations_panel.choices import ShipmentType, OperationStatus, UnitType
from core.operations_panel.models import Operation, Route, Client, DeliveryLocation, Supplier, Driver, Vehicle
from core.system.functions import extract_best_coincidence_from_field_in_model


@transaction.atomic
def register_operations(tool_input):
    print("REGISTER OPERATIONS")
    try:
        # Parse the input JSON
        input_data = json.loads(tool_input)
        operations_data = input_data.get('operations', [])

        if not operations_data:
            return {"error": "No operations found in input data"}

        results = []

        # Process each operation
        for operation_data in operations_data:
            print(operation_data)
            try:
                with transaction.atomic():
                    # Create the operation
                    operation = create_operation_from_data(operation_data)

                    # Send notification to Telegram group
                    operation.notify_operation_created()

                    results.append({
                        "status": "success",
                        "operation": operation_data,
                        "message": "se genero exitosamente la operacion"
                    })
            except Exception as e:
                print("ERROR")
                print(e)
                results.append({
                    "status": "error",
                    "error": str(e),
                    "data": operation_data
                })
            print("----------------")
            print(results)
        return {"results": results}

    except Exception as e:
        print(e)
        return {"error": str(e)}


def create_operation_from_data(data):
    """
    Create an Operation record from the data provided by the Assistant.

    Args:
        data (dict): Operation data from Assistant

    Returns:
        Operation: The created Operation instance
    """
    # Find or create related entities
    client = Client.get_or_create_by_str(data.get('cliente'))
    route = look_for_route(data.get('destino'))

    supplier = Supplier.get_or_create_by_str(data.get('proveedor'))
    driver = Driver.get_or_create_by_str(data.get('operador'))
    vehicle = Vehicle.get_or_create_by_plate(data.get('placas'), data.get('unidad'))

    # Parse date
    operation_date = parse_date(data.get('fecha'))

    shipment_type = data.get('type')
    if shipment_type.lower() == '3b':
        shipment_type = ShipmentType.THREE_B
    elif shipment_type.lower() == 'asturiano':
        shipment_type = ShipmentType.ASTURIANO
    elif shipment_type.lower() == 'chem':
        shipment_type = ShipmentType.CHEM
    else:
        shipment_type = ShipmentType.GENERAL

    print(client)
    print(route)
    print(supplier)
    print(driver)
    print(vehicle)
    print(operation_date)
    print(shipment_type)

    # Create the operation
    operation = Operation.objects.create(
        client=client,
        route=route,
        supplier=supplier,
        driver=driver,
        vehicle=vehicle,
        operation_date=operation_date,
        shipment_type=shipment_type,  # Default to 3B as per the issue description
        status=OperationStatus.PENDING,
        vehicle_type=vehicle.unit_type if vehicle else None,
        raw_payload=data  # Store the original data for auditing
    )

    print(operation)

    if not route:
        print("ROUTE NOT FOUND")
        print(data)
        print(1)
        origin = DeliveryLocation.get_or_create_by_str(data.get('origen'))
        print(2)
        #destination = get_or_create_delivery_location(data.get('destino'))
        destination = DeliveryLocation.get_or_create_by_str(data.get('destino'))
        print(3)
        print(origin)
        print(destination)
        if shipment_type.ASTURIANO:
            route = Route.objects.create(
                name="OPERATION-" + str(operation.id),
                initial_location=origin,
                destination_location=destination,
            )
        else:
            route = Route.objects.create(
                name="OPERATION-" + str(operation.id),
                initial_location=origin,
                destination_location=destination,
            )
        print(route)
        deliveries = data.get('repartos', [])
        print(deliveries)
        if deliveries:
            for delivery in deliveries:
                delivery_location = DeliveryLocation.get_or_create_by_str(delivery)
                if delivery_location:
                    route.route_stops.add(delivery_location)
                    route.save()
        operation.route = route
        operation.save()

    return operation


def look_for_route(name, threshold=90):
    if not name:
        return None

    # Try exact match first
    try:
        return Route.objects.get(name__iexact=name)
    except Route.DoesNotExist:
        pass

    # Try fuzzy matching
    best_coincidence = extract_best_coincidence_from_field_in_model(Route, 'name', name, threshold)

    if best_coincidence:
        return best_coincidence






def parse_date(date_str):
    """
    Parse a date string into a datetime.date object.

    Args:
        date_str (str): Date string in YYYY-MM-DD format

    Returns:
        datetime.date: Parsed date
    """
    if not date_str:
        return datetime.now().date()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        # Try other common formats
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        # If all parsing attempts fail, return today's date
        return datetime.now().date()


def get_embarques_lletra_group_info():
    """
    Get the bot token and group chat ID for the "Embarques Lletra" group.

    Returns:
        tuple: (bot_token, group_chat_id, bot) or (None, None, None) if not found
    """
    from apps.telegram_bots.models import TelegramBot


    try:
        bot_token = TelegramBot.objects.get(username='prueba_lletra_bot').token

        # Get the "Embarques Lletra" group
        try:
            # Use filter instead of get to handle multiple groups
            groups = TelegramGroup.objects.filter(name='Embarques Lletra')
            if groups.exists():
                group_chat_id = groups.first().telegram_id
                if groups.count() > 1:
                    print(
                        f"Note: Found {groups.count()} groups with name 'Embarques Lletra'. Using the first one.")

                # Get or create the bot
                bot, created = TelegramBot.objects.get_or_create(
                    token=bot_token,
                    defaults={'name': 'Operations Notification Bot'}
                )

                return bot_token, group_chat_id, bot
            else:
                raise TelegramGroup.DoesNotExist
        except TelegramGroup.DoesNotExist:
            print("Telegram group 'Embarques Lletra' not found")
            return None, None, None

        return None, None, None
    except Exception as e:
        print(f"Error getting Embarques Lletra group info: {str(e)}")
        return None, None, None


def send_operation_missing_items(operation_id, chat_id, message_id=None):
    """
    Send a message with missing items for an operation to a Telegram chat.

    Args:
        operation_id (int): ID of the operation to check
        chat_id (str): Telegram chat ID to send the message to
        message_id (int, optional): Message ID to reply to

    Returns:
        bool: True if message was sent successfully
    """
    from apps.telegram_bots.models import TelegramBot, TelegramMessage, TelegramChat


    try:
        # Get the operation
        try:
            operation = Operation.objects.get(id=operation_id)
        except Operation.DoesNotExist:
            print(f"Operation with ID {operation_id} not found")
            return False

        # Get the bot token and group chat ID
        bot_token, group_chat_id, bot = get_embarques_lletra_group_info()

        if not bot_token or not group_chat_id or not bot:
            print("Telegram notification settings not configured")
            return False

        # Format the message
        message_text = operation.format_operation_missing_items_message()

        # Send the message
        response = send_telegram_message(
            bot,
            chat_id,
            message_text,
            reply_to_message_id=message_id
        )

        # If the message was sent successfully, link it to the operation
        if response and 'result' in response and 'message_id' in response['result']:
            message_id = response['result']['message_id']

            # Get the chat
            chat = TelegramChat.objects.get(telegram_id=chat_id)

            # Get or create the message
            telegram_message, created = TelegramMessage.objects.get_or_create(
                telegram_id=message_id,
                chat=chat,
                bot=bot,
                defaults={
                    'text': message_text,
                    'operation': operation
                }
            )

            # If the message already existed but wasn't linked to the operation, link it
            if not created and not telegram_message.operation:
                telegram_message.operation = operation
                telegram_message.save()

            print(f"Linked message {message_id} to operation {operation.id}")

        return True
    except Exception as e:
        print(f"Error sending operation missing items: {str(e)}")
        return False



