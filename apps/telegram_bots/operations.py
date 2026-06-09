import json
from datetime import datetime, time, timedelta

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
                    client_name = operation_data.get('cliente', '').strip().upper()

                    if client_name != 'BARA':
                        existing_operation = check_existing_operation(operation_data)
                        if existing_operation:
                            continue

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


def check_existing_operation(operation_data):
    try:
        # Obtener los datos clave para la comparación
        client_name = operation_data.get('cliente', '').strip()
        destino = operation_data.get('destino', '').strip()
        fecha = operation_data.get('fecha', '')
        operador = operation_data.get('operador', '').strip()

        # Verificar que tenemos los datos mínimos necesarios
        if not client_name or not destino or not fecha or not operador:
            print(
                f"Datos insuficientes para verificar duplicado: cliente='{client_name}', destino='{destino}', fecha='{fecha}', operador='{operador}'")
            return None

        # Parsear la fecha
        operation_date = parse_date(fecha)

        # Buscar cliente
        client = Client.get_or_create_by_str(client_name)
        if not client:
            print(f"No se pudo encontrar o crear cliente: {client_name}")
            return None

        # Buscar operador/conductor
        driver = Driver.get_or_create_by_str(operador)
        if not driver:
            print(f"No se pudo encontrar o crear operador: {operador}")
            return None

        # Buscar operaciones que coincidan con los 4 criterios principales
        potential_duplicates = Operation.objects.filter(
            client=client,
            driver=driver,
            operation_date=operation_date
        )

        # Verificar coincidencias de destino en raw_payload
        for operation in potential_duplicates:
            if operation.raw_payload:
                raw_destino = operation.raw_payload.get('destino', '').strip()

                # Verificar si el destino coincide (ignorando mayúsculas/minúsculas)
                if destino.lower() == raw_destino.lower():
                    print(
                        f"Operación duplicada encontrada: ID={operation.id}, Cliente={client_name}, Destino={destino}, Fecha={fecha}, Operador={operador}")
                    return operation

        print(
            f"No se encontró duplicado para: Cliente={client_name}, Destino={destino}, Fecha={fecha}, Operador={operador}")
        return None

    except Exception as e:
        print(f"Error checking existing operation: {str(e)}")
        return None


def create_operation_from_data_respaldo(data):
    # Find or create related entities
    client = Client.get_or_create_by_str(data.get('cliente'))
    route = look_for_route(data.get('destino'))

    supplier = Supplier.get_or_create_by_str(data.get('proveedor'))
    driver = Driver.get_or_create_by_str(data.get('operador'))
    vehicle = Vehicle.get_or_create_by_plate(data.get('placas'), data.get('unidad'))
    accessories = True if data.get('accesorios', "").strip().lower() == "maniobra" else False

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
        raw_payload=data,  # Store the original data for auditing
        accessories=accessories,  # Store the original data for auditing
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
        if shipment_type.lower() == shipment_type.ASTURIANO:
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
        deliveries = data.get('repartos', [])
        if deliveries:
            for delivery in deliveries:
                delivery_location = DeliveryLocation.get_or_create_by_str(delivery)
                if delivery_location:
                    route.route_stops.add(delivery_location)
                    route.save()
        operation.route = route
        operation.save()
    else:
        print("Ruta en proceso de duplicacion")
        # 2. Guardar temporalmente los stops
        original_stops = list(route.route_stops.all())

        # 3. Duplicar la ruta
        route.pk = None
        route.id = None  # opcional, pero explícito
        route.name = f"{route.name} - copia"
        route.published = False  # opcional
        route.save()
        route.name = f"OPERATION-{operation.id}"
        route.save()

        # 4. Copiar los ManyToMany
        route.route_stops.set(original_stops)

        operation.route = route
        operation.save()
        print("Ruta duplicada")


    return operation



def create_operation_from_data(data):
    # Find or create related entities
    client = Client.get_or_create_by_str(data.get('cliente'))
    route = look_for_route(data.get('destino'))

    supplier = Supplier.get_or_create_by_str(data.get('proveedor'))
    driver = Driver.get_or_create_by_str(data.get('operador'))
    vehicle = Vehicle.get_or_create_by_plate(data.get('placas'), data.get('unidad'))
    accessories = True if data.get('accesorios', "").strip().lower() == "maniobra" else False

    # Parse date
    operation_date = parse_date(data.get('fecha'))

    # Logistica inversa
    is_inverse_logistic = bool(data.get("log_inv", False))

    # Hora de carga
    cargo_time = data.get("cargo_time", -1)

    cargo_appointment = None
    scheduled_departure_time = None
    download_appointment = None

    if cargo_time not in [None, "", -1, "-1"]:
        try:
            cargo_hour = int(cargo_time)

            if 0 <= cargo_hour <= 23:
                cargo_appointment = datetime.combine(
                    operation_date,
                    time(hour=cargo_hour, minute=0)
                )

                scheduled_departure_time = cargo_appointment
                download_appointment = cargo_appointment + timedelta(hours=10)

        except (ValueError, TypeError):
            cargo_appointment = None
            scheduled_departure_time = None
            download_appointment = None

    shipment_type = data.get('type')
    if shipment_type.lower() == '3b':
        shipment_type = ShipmentType.THREE_B
    elif shipment_type.lower() == 'asturiano':
        shipment_type = ShipmentType.ASTURIANO
    elif shipment_type.lower() == 'chem':
        shipment_type = ShipmentType.CHEM
    else:
        shipment_type = ShipmentType.GENERAL

    # Create the operation
    operation = Operation.objects.create(
        client=client,
        route=route,
        supplier=supplier,
        driver=driver,
        vehicle=vehicle,
        operation_date=operation_date,
        shipment_type=shipment_type,
        status=OperationStatus.PENDING,
        vehicle_type=vehicle.unit_type if vehicle else None,
        raw_payload=data,
        accessories=accessories,

        # Nuevos campos
        is_inverse_logistic=is_inverse_logistic,
        cargo_appointment=cargo_appointment,
        scheduled_departure_time=scheduled_departure_time,
        download_appointment=download_appointment,
    )

    if not route:
        origin = DeliveryLocation.get_or_create_by_str(data.get('origen'))
        destination = DeliveryLocation.get_or_create_by_str(data.get('destino'))

        route = Route.objects.create(
            name="OPERATION-" + str(operation.id),
            initial_location=origin,
            destination_location=destination,
        )

        deliveries = data.get('repartos', [])

        if deliveries:
            for delivery in deliveries:
                delivery_location = DeliveryLocation.get_or_create_by_str(delivery)
                if delivery_location:
                    route.route_stops.add(delivery_location)
                    route.save()

        operation.route = route
        operation.save()

    else:
        print("Ruta en proceso de duplicacion")

        original_stops = list(route.route_stops.all())

        route.pk = None
        route.id = None
        route.name = f"{route.name} - copia"
        route.published = False
        route.save()

        route.name = f"OPERATION-{operation.id}"
        route.save()

        route.route_stops.set(original_stops)

        operation.route = route
        operation.save()

        print("Ruta duplicada")

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



