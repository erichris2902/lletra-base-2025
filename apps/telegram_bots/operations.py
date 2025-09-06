import json
import logging
from datetime import datetime

from django.db import transaction
from django.utils.text import slugify
from apps.telegram_bots.models import TelegramGroup
from apps.telegram_bots.services import send_telegram_message
from core.operations_panel.choices import ShipmentType, OperationStatus, UnitType
from core.operations_panel.models import Operation, Route, Client, DeliveryLocation, Supplier, Driver, Vehicle
from core.operations_panel.models.address import Address
from core.system.functions import extract_best_coincidence_from_field_in_model

logger = logging.getLogger(__name__)


def register_operations(tool_input):
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
        operations_data = input_data.get('operations', [])

        if not operations_data:
            return {"error": "No operations found in input data"}

        results = []

        # Process each operation
        for operation_data in operations_data:
            try:
                with transaction.atomic():
                    # Create the operation
                    operation = create_operation_from_data(operation_data)

                    # Send notification to Telegram group
                    notify_operation_created(operation)

                    results.append({
                        "status": "success",
                        "operation_id": operation.id,
                        "folio": operation.pre_folio
                    })
            except Exception as e:
                logger.exception(f"Error processing operation: {str(e)}")
                results.append({
                    "status": "error",
                    "error": str(e),
                    "data": operation_data
                })

        return {"results": results}

    except Exception as e:
        logger.exception(f"Error in register_operations: {str(e)}")
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
    client = get_or_create_client(data.get('cliente'))
    route = look_for_route(data.get('destino'))

    origin = DeliveryLocation.get_or_create_by_str(data.get('origen'))
    destination = None
    if not route:
        destination = get_or_create_delivery_location(data.get('destino'))
    supplier = get_or_create_supplier(data.get('proveedor'))
    driver = get_or_create_driver(data.get('operador'))
    vehicle = get_or_create_vehicle(data.get('placas'), data.get('unidad'))

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

    # Create the operation
    operation = Operation.objects.create(
        client=client,
        origin=origin,
        destination=destination,
        supplier=supplier,
        driver=driver,
        vehicle=vehicle,
        operation_date=operation_date,
        shipment_type=shipment_type,  # Default to 3B as per the issue description
        status=OperationStatus.PENDING,
        vehicle_type=get_vehicle_type(data.get('unidad')),
        raw_payload=data  # Store the original data for auditing
    )
    if not route:
        # Add deliveries (repartos)
        repartos = data.get('repartos', [])
        if repartos:
            for reparto in repartos:
                delivery_location = get_or_create_delivery_location(reparto)
                if delivery_location:
                    operation.deliveries.add(delivery_location)

    if route:
        operation.origin = route.initial_location
        operation.destination = route.destination_location
        for stop in route.route_stops.all():
            operation.deliveries.add(stop)
        operation.save()

    return operation


def look_for_route(name):
    """
    Get or create a DeliveryLocation by name using fuzzy matching.

    Args:
        name (str): Location name

    Returns:
        Route: The found or created Route instance
    """
    if not name:
        return None

    # Try exact match first
    try:
        return Route.objects.get(name__iexact=name)
    except Route.DoesNotExist:
        pass

    # Try fuzzy matching
    best_coincidence = extract_best_coincidence_from_field_in_model(Route, 'name', name, 90)

    if best_coincidence:
        return best_coincidence


def get_or_create_client(name):
    """
    Get or create a Client by name using fuzzy matching.

    Args:
        name (str): Client name

    Returns:
        Client: The found or created Client instance
    """
    if not name:
        return None

    # Try exact match first
    try:
        return Client.objects.get(name__iexact=name)
    except Client.DoesNotExist:
        pass

    # Try fuzzy matching
    best_coincidence = extract_best_coincidence_from_field_in_model(Client, 'name', name)

    if best_coincidence:
        return best_coincidence

    # Create new client if no match found
    # First create a default address
    address = Address.objects.create(
        street="Default Street",
        exterior_number="S/N",
        colony="Default Colony",
        city="Default City",
        state="Ciudad de México",  # Valid choice from MEXICAN_STATES
        zip_code="00000"
    )

    return Client.objects.create(
        name=name,
        business_name=name,
        email=f"{slugify(name)}@example.com",  # Default email
        phone="0000000000",  # Default phone
        tax_regime="601",  # Default tax regime
        address=address
    )


def get_or_create_delivery_location(name):
    """
    Get or create a DeliveryLocation by name using fuzzy matching.

    Args:
        name (str): Location name

    Returns:
        DeliveryLocation: The found or created DeliveryLocation instance
    """



def get_or_create_supplier(name):
    """
    Get or create a Supplier by name using fuzzy matching.

    Args:
        name (str): Supplier name

    Returns:
        Supplier: The found or created Supplier instance
    """
    if not name:
        return None

    # Try exact match first
    try:
        return Supplier.objects.get(business_name__iexact=name)
    except Supplier.DoesNotExist:
        pass

    # Try fuzzy matching
    best_coincidence = extract_best_coincidence_from_field_in_model(Supplier, 'code', name, 80)
    if best_coincidence:
        return best_coincidence

    best_coincidence = extract_best_coincidence_from_field_in_model(Supplier, 'business_name', name, 80)
    if best_coincidence:
        return best_coincidence

    # Create new supplier if no match found
    # First create a default address
    address = Address.objects.create(
        street="Default Street",
        exterior_number="S/N",
        colony="Default Colony",
        city="Default City",
        state="Ciudad de México",  # Valid choice from MEXICAN_STATES
        zip_code="00000"
    )

    code = generate_supplier_code(name)
    return Supplier.objects.create(
        code=code,
        business_name=name,
        rfc="XAXX010101000",  # Default RFC for Mexico
        email=f"{slugify(name)}@example.com",  # Default email
        phone="0000000000",  # Default phone
        bank="Default Bank",
        clabe="000000000000000000",
        tax_regime="601",  # Default tax regime
        address=address
    )


def get_or_create_driver(name):
    """
    Get or create a Driver by name using fuzzy matching.

    Args:
        name (str): Driver name

    Returns:
        Driver: The found or created Driver instance
    """
    if not name:
        return None

    # Split name into parts (assuming format: First Last Mother)
    name_parts = name.split()
    if len(name_parts) >= 3:
        first_name = name_parts[0]
        last_name = name_parts[1]
        mother_last_name = ' '.join(name_parts[2:])
    elif len(name_parts) == 2:
        first_name = name_parts[0]
        last_name = name_parts[1]
        mother_last_name = ""
    else:
        first_name = name
        last_name = ""
        mother_last_name = ""

    # Try exact match first
    try:
        return Driver.objects.get(
            name__iexact=first_name,
            last_name__iexact=last_name
        )
    except Driver.DoesNotExist:
        pass

    # Try fuzzy matching
    best_coincidence = extract_best_coincidence_from_field_in_model(Driver, 'name', name, 80)
    if best_coincidence:
        return best_coincidence

    best_coincidence = extract_best_coincidence_from_field_in_model(Driver, 'last_name', name, 80)
    if best_coincidence:
        return best_coincidence

    best_coincidence = extract_best_coincidence_from_field_in_model(Driver, 'mother_last_name', name, 80)
    if best_coincidence:
        return best_coincidence

    # Create new driver if no match found
    return Driver.objects.create(
        name=first_name,
        last_name=last_name,
        mother_last_name=mother_last_name,
        rfc="XAXX010101000",  # Default RFC for Mexico
        license_number="DEFAULT",
        license_type="DEFAULT",
        license_expiration=datetime.now().date().replace(year=datetime.now().year + 5)  # 5 years from now
    )


def get_or_create_vehicle(plates, unit_type=None):
    """
    Get or create a Vehicle by plates using fuzzy matching.

    Args:
        plates (str): Vehicle plates
        unit_type (str): Vehicle type description

    Returns:
        Vehicle: The found or created Vehicle instance
    """
    if not plates:
        return None

    # Try exact match first
    try:
        return Vehicle.objects.get(license_plate__iexact=plates)
    except Vehicle.DoesNotExist:
        pass

    # Try fuzzy matching
    best_coincidence = extract_best_coincidence_from_field_in_model(Vehicle, 'license_plate', plates, 80)
    if best_coincidence:
        return best_coincidence

    # Determine unit type
    vehicle_type = get_vehicle_type(unit_type)

    # Create new vehicle if no match found
    return Vehicle.objects.create(
        econ_number=f"ECO-{plates}",
        model="DEFAULT",
        brand="DEFAULT",
        circulation_card_number="DEFAULT",
        insurance_company="DEFAULT",
        insurance_code="DEFAULT",
        serial_number="DEFAULT",
        license_plate=plates,
        year=datetime.now().year,
        sct_permit="DEFAULT",
        vehicle_config="C2",  # Default vehicle config
        unit_type=vehicle_type
    )


def get_vehicle_type(unit_description):
    """
    Map a unit description to a UnitType choice.

    Args:
        unit_description (str): Description of the unit

    Returns:
        str: UnitType choice
    """
    if not unit_description:
        return UnitType.TORTON  # Default as per issue description

    unit_description = unit_description.upper()

    # Map common descriptions to UnitType choices
    if "TORTON" in unit_description:
        return UnitType.TORTON
    elif "TRACTO" in unit_description or "TRAILER" in unit_description:
        return UnitType.TRAILER
    elif "CAJA" in unit_description:
        if "40" in unit_description:
            return UnitType.BOX_40
        elif "48" in unit_description:
            return UnitType.BOX_48
        elif "53" in unit_description:
            return UnitType.BOX_53
        else:
            return UnitType.BOX
    elif "1 TN" in unit_description or "1TN" in unit_description:
        return UnitType.UNIT_1TN
    elif "2.5 TN" in unit_description or "2.5TN" in unit_description:
        return UnitType.UNIT_25TN
    elif "3.5 TN" in unit_description or "3.5TN" in unit_description:
        return UnitType.UNIT_35TN
    elif "5 TN" in unit_description or "5TN" in unit_description:
        return UnitType.UNIT_5TN
    elif "RABON" in unit_description:
        return UnitType.RABON
    elif "PLATAFORMA" in unit_description:
        if "40" in unit_description:
            return UnitType.PLATFORM_40
        elif "48" in unit_description:
            return UnitType.PLATFORM_48
        else:
            return UnitType.PLATFORM_40
    elif "PIPA" in unit_description:
        return UnitType.TANKER
    elif "TOLVA" in unit_description:
        return UnitType.HOPPER
    elif "MADRINA" in unit_description:
        return UnitType.CARRIER
    elif "UTILITARIO" in unit_description:
        return UnitType.UTILITY
    else:
        return UnitType.TORTON  # Default


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


def generate_supplier_code(name):
    """
    Generate a unique supplier code based on the name.

    Args:
        name (str): Supplier name

    Returns:
        str: Generated code
    """
    # Create a base code from the first 3 letters of the name
    base_code = ''.join(c for c in name if c.isalnum())[:3].upper()

    # Add a number to make it unique
    existing_codes = Supplier.objects.filter(code__startswith=base_code).count()
    return f"{base_code}{existing_codes + 1:03d}"


def notify_operation_created(operation):
    """
    Send a notification to the Telegram group about a new operation.

    Args:
        operation (Operation): The created Operation instance

    Returns:
        bool: True if notification was sent successfully
    """
    from apps.telegram_bots.models import TelegramBot, TelegramMessage, TelegramChat

    try:
        # Get the notification bot and group chat ID from settings
        from django.conf import settings

        bot_token = TelegramBot.objects.get(username='prueba_lletra_bot').token
        group_chat_id = TelegramGroup.objects.get(name='Folios Lletra').telegram_id

        if not bot_token or not group_chat_id:
            logger.warning("Telegram notification settings not configured")
            return False

        # Get or create the bot
        bot, created = TelegramBot.objects.get_or_create(
            token=bot_token,
            defaults={'name': 'Operations Notification Bot'}
        )

        # Format the message
        message_text = format_operation_notification(operation)

        # Send the message
        response = send_telegram_message(bot, group_chat_id, message_text)

        # If the message was sent successfully, link it to the operation
        if response and 'result' in response and 'message_id' in response['result']:
            message_id = response['result']['message_id']

            # Get the chat
            chat = TelegramChat.objects.get(telegram_id=group_chat_id)

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

            logger.info(f"Linked message {message_id} to operation {operation.id}")

        return True
    except Exception as e:
        logger.exception(f"Error sending Telegram notification: {str(e)}")
        return False


def format_operation_notification(operation):
    """
    Format an operation notification message for Telegram.

    Args:
        operation (Operation): The Operation instance

    Returns:
        str: Formatted message
    """
    # Get the deliveries as a comma-separated list
    deliveries = ", ".join([d.name for d in operation.deliveries.all()])

    # Format the message
    message = (
        f"🚚 Nueva operación registrada:\n"
        f"Cliente: {operation.client.name if operation.client else 'N/A'}\n"
        f"Origen: {operation.origin.name if operation.origin else 'N/A'}\n"
        f"Destino: {operation.destination.name if operation.destination else 'N/A'}\n"
        f"Unidad: {operation.get_vehicle_type_display() if operation.vehicle_type else 'N/A'}\n"
        f"Proveedor: {operation.supplier.business_name if operation.supplier else 'N/A'}\n"
        f"Operador: {operation.driver.name + ' ' + operation.driver.last_name if operation.driver else 'N/A'}\n"
        f"Fecha: {operation.operation_date.strftime('%Y-%m-%d')}\n"
    )

    if deliveries:
        message += f"Repartos: {deliveries}\n"

    message += f"Folio: {operation.pre_folio or 'Pendiente'}"

    return message


def format_operation_approved_notification(operation):
    """
    Format an operation approved notification message for Telegram.

    Args:
        operation (Operation): The Operation instance with assigned folio

    Returns:
        str: Formatted message
    """
    # Get the deliveries as a comma-separated list
    deliveries = ", ".join([d.name for d in operation.deliveries.all()])

    # Format the message
    message = (
        f"✅ Operación aprobada con folio asignado:\n"
        f"Folio: {operation.folio}\n"
        f"Cliente: {operation.client.name if operation.client else 'N/A'}\n"
        f"Origen: {operation.origin.name if operation.origin else 'N/A'}\n"
        f"Destino: {operation.destination.name if operation.destination else 'N/A'}\n"
        f"Unidad: {operation.get_vehicle_type_display() if operation.vehicle_type else 'N/A'}\n"
        f"Proveedor: {operation.supplier.business_name if operation.supplier else 'N/A'}\n"
        f"Operador: {operation.driver.name + ' ' + operation.driver.last_name if operation.driver else 'N/A'}\n"
        f"Fecha: {operation.operation_date.strftime('%Y-%m-%d')}\n"
    )

    if deliveries:
        message += f"Repartos: {deliveries}\n"

    return message


def get_embarques_lletra_group_info():
    """
    Get the bot token and group chat ID for the "Embarques Lletra" group.

    Returns:
        tuple: (bot_token, group_chat_id, bot) or (None, None, None) if not found
    """
    from apps.telegram_bots.models import TelegramBot
    import logging

    logger = logging.getLogger(__name__)

    try:
        bot_token = TelegramBot.objects.get(username='prueba_lletra_bot').token

        # Get the "Embarques Lletra" group
        try:
            # Use filter instead of get to handle multiple groups
            groups = TelegramGroup.objects.filter(name='Embarques Lletra')
            if groups.exists():
                group_chat_id = groups.first().telegram_id
                if groups.count() > 1:
                    logger.info(
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
            logger.warning("Telegram group 'Embarques Lletra' not found")
            return None, None, None

        return None, None, None
    except Exception as e:
        logger.exception(f"Error getting Embarques Lletra group info: {str(e)}")
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
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Get the operation
        try:
            operation = Operation.objects.get(id=operation_id)
        except Operation.DoesNotExist:
            logger.warning(f"Operation with ID {operation_id} not found")
            return False

        # Get the bot token and group chat ID
        bot_token, group_chat_id, bot = get_embarques_lletra_group_info()

        if not bot_token or not group_chat_id or not bot:
            logger.warning("Telegram notification settings not configured")
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

            logger.info(f"Linked message {message_id} to operation {operation.id}")

        return True
    except Exception as e:
        logger.exception(f"Error sending operation missing items: {str(e)}")
        return False


def notify_operation_approved(operation):
    """
    Send a notification to the Telegram group about an approved operation with assigned folio.

    Args:
        operation (Operation): The Operation instance with assigned folio

    Returns:
        bool: True if notification was sent successfully
    """
    from apps.telegram_bots.models import TelegramBot, TelegramMessage, TelegramChat
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Get the notification bot and group chat ID from settings
        from django.conf import settings

        bot_token = TelegramBot.objects.get(username='prueba_lletra_bot').token

        # Get the "Embarques Lletra" group
        try:
            # Use filter instead of get to handle multiple groups
            groups = TelegramGroup.objects.filter(name='Embarques Lletra')
            if groups.exists():
                group_chat_id = groups.first().telegram_id
                if groups.count() > 1:
                    logger.info(
                        f"Note: Found {groups.count()} groups with name 'Embarques Lletra'. Using the first one.")
            else:
                raise TelegramGroup.DoesNotExist
        except TelegramGroup.DoesNotExist:
            logger.warning("Telegram group 'Embarques Lletra' not found")
            return False

        if not bot_token or not group_chat_id:
            logger.warning("Telegram notification settings not configured")
            return False

        # Get or create the bot
        bot, created = TelegramBot.objects.get_or_create(
            token=bot_token,
            defaults={'name': 'Operations Notification Bot'}
        )

        # Format the message
        message_text = format_operation_approved_notification(operation)

        # Send the message
        response = send_telegram_message(bot, group_chat_id, message_text)

        # If the message was sent successfully, link it to the operation
        if response and 'result' in response and 'message_id' in response['result']:
            message_id = response['result']['message_id']

            # Get the chat
            chat = TelegramChat.objects.get(telegram_id=group_chat_id)

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

            logger.info(f"Linked message {message_id} to operation {operation.id}")

        return True
    except Exception as e:
        logger.exception(f"Error sending Telegram notification: {str(e)}")
        return False
