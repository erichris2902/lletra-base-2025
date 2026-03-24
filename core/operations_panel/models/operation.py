import os
import re
import tempfile
from datetime import datetime, time

from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from packaging.utils import _

from apps.facturapi.services import download_invoice_pdf, download_invoice_xml
from apps.google_drive.services import check_folder_exists_with_service_account, create_folder_with_service_account, \
    upload_file_with_service_account
from core.operations_panel.models.client import Client
from core.operations_panel.models.shipment_facturapi_invoice import ShipmentFacturapiInvoice
from core.operations_panel.models.supplier import Supplier
from core.operations_panel.models.driver import Driver
from core.operations_panel.models.vehicle import Vehicle
from django.utils.timezone import now, make_aware
from apps.google_drive.models import GoogleDriveFile, GoogleDriveFolder
from core.operations_panel.choices import UnitType, ShipmentType, OperationStatus
from core.operations_panel.models.route import Route
from core.operations_panel.models.cargo import Cargo
from core.operations_panel.models.transported_product import TransportedProduct
from core.system.models import BaseModel


class Operation(BaseModel):
    folio = models.CharField(_("Folio"), max_length=10, unique=True, null=True, blank=True)
    pre_folio = models.CharField(_("Pre-folio"), max_length=10, null=True, blank=True, db_index=True)

    shipment_invoice = models.ForeignKey("facturapi.FacturapiInvoice", blank=True, null=True,
                                         related_name="shipment_invoice", on_delete=models.PROTECT)
    invoices = models.ManyToManyField("facturapi.FacturapiInvoice", blank=True, related_name="invoices")

    client = models.ForeignKey(
        Client, verbose_name=_("Cliente"),
        on_delete=models.PROTECT, null=True, blank=True
    )
    supplier = models.ForeignKey(
        Supplier, verbose_name=_("Proveedor"),
        on_delete=models.PROTECT, null=True, blank=True
    )
    driver = models.ForeignKey(
        Driver, verbose_name=_("Conductor"),
        on_delete=models.SET_NULL, null=True, blank=True
    )
    vehicle = models.ForeignKey(
        Vehicle, verbose_name=_("Vehículo"),
        on_delete=models.SET_NULL, null=True, blank=True
    )
    vehicle_box = models.ForeignKey(
        Vehicle, verbose_name=_("Caja"), related_name="operation_box",
        on_delete=models.SET_NULL, null=True, blank=True
    )
    vehicle_type = models.CharField(_("Tipo de unidad"), max_length=30, choices=UnitType.choices, null=True, blank=True)

    operation_date = models.DateField(_("Fecha de operación"))
    shipment_type = models.CharField(_("Tipo de embarque"), max_length=20, choices=ShipmentType.choices)
    status = models.CharField(_("Estatus"), max_length=20, choices=OperationStatus.choices,
                              default=OperationStatus.PENDING)

    notes = models.TextField(_("Notas"), blank=True, null=True)

    need_cartaporte = models.BooleanField(_("¿Requiere carta porte?"), default=True)
    is_rent = models.BooleanField(_("¿Es renta?"), default=False)
    is_packing_ready = models.BooleanField(_("¿Esta listo el packing?"), default=False)

    cargo_appointment = models.DateTimeField(_("Cita de carga"), null=True, blank=True)
    download_appointment = models.DateTimeField(_("Cita de descarga"), null=True, blank=True)
    scheduled_departure_time = models.DateTimeField(_("Hora estimada de salida"), null=True, blank=True)

    # Integración con Google Drive
    invoice_file = models.ForeignKey(
        GoogleDriveFile, verbose_name=_("Archivo de factura en Drive"),
        on_delete=models.SET_NULL, null=True, blank=True, related_name="operations_invoice"
    )
    client_folder = models.ForeignKey(
        GoogleDriveFolder, verbose_name=_("Carpeta del cliente en Drive"),
        on_delete=models.SET_NULL, null=True, blank=True, related_name="operations_client"
    )

    raw_payload = models.JSONField(_("Datos sin procesar (payload)"), null=True)

    cargo = models.ForeignKey(
        Cargo, verbose_name=_("Carga asociada"),
        on_delete=models.SET_NULL, null=True, blank=True
    )

    route = models.ForeignKey(
        Route, verbose_name=_("Ruta asociada"),
        on_delete=models.SET_NULL, null=True, blank=True
    )

    total = models.DecimalField(_("Total antes de impuestos"), default=0, max_digits=12, decimal_places=2)
    handling_amount = models.IntegerField(_("Cantidad de maniobras"), default=0, blank=True, null=True)

    transported_products = models.ManyToManyField(
        TransportedProduct, verbose_name=_("Productos transportados"),
        related_name="operations_transported_products", blank=True
    )

    def set_route(self, initial_location, destination_location):
        if not self.route:
            route = Route()
            route.initial_location = initial_location
            route.destination_location = destination_location
        else:
            raise Exception("La operacion ya tiene una ruta asignada.")

    def add_stop(self, location):
        if self.route is None:
            raise Exception("La operacion no tiene una ruta asociada.")
        self.route.route_stops.add(location)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Primero guarda la operación

    def __str__(self):
        return f"Operación {self.folio or self.pre_folio or self.id}"

    def to_folios_view(self, keys=None):
        result = self.to_display_dict(keys)
        result["deliveries"] = ", ".join(str(route) for route in self.route.route_stops.all()) if self.route and self.route.route_stops else "[]"
        result["folio"] = "SIN FOLIO" if not self.folio else self.folio
        return result

    def to_operations_view(self, keys=None):
        result = self.to_display_dict(keys)
        result["is_invoice_ready"] = str(self.shipment_invoice is not None)
        result["is_ready_to_invoice"] = str(self.is_ready_for_invoicing())
        result["is_packing_ready"] = str(self.is_packing_ready)
        result["products_amount"] = str(self.transported_products.count())
        result["distance"] = str(self.route.direct_distance) if self.route else "0"
        result["shipment_type"] = self.shipment_type
        result["origin"] = str(self.route.initial_location.address) if self.route else "SIN ORIGEN"
        result["destination"] = str(self.route.destination_location.address) if self.route else "SIN DESTINO"
        result["deliveries"] = ", ".join(str(route) for route in self.route.route_stops.all()) if self.route and self.route.route_stops else "[]"
        return result

    def to_operations_general_view(self, keys=None):
        result = self.to_display_dict(keys)
        print(self.folio)
        result["invoice_id"] = str(self.shipment_invoice.id) if self.shipment_invoice else None
        result["is_invoice_ready"] = str(self.shipment_invoice is not None)
        result["is_ready_to_invoice"] = str(self.is_ready_for_invoicing())
        result["is_packing_ready"] = str(self.is_packing_ready)
        return result

    def get_operation_missing_items(self):
        missing_items = {}

        # Check for missing basic information
        basic_info = []
        if not self.client:
            basic_info.append("Cliente")
        if not self.operation_date:
            basic_info.append("Fecha de operación")
        if not self.shipment_type:
            basic_info.append("Tipo de embarque")

        if basic_info:
            missing_items["información_básica"] = basic_info

        # Check for missing logistics information
        logistics_info = []
        if not self.supplier:
            logistics_info.append("Proveedor")
        if not self.driver:
            logistics_info.append("Operador")
        if not self.vehicle:
            logistics_info.append("Vehículo")
        if not self.vehicle_type:
            logistics_info.append("Tipo de unidad")

        if logistics_info:
            missing_items["información_logística"] = logistics_info

        # Check for missing appointment information
        appointment_info = []
        if not self.cargo_appointment:
            appointment_info.append("Cita de carga")
        if not self.download_appointment:
            appointment_info.append("Cita de descarga")
        if not self.scheduled_departure_time:
            appointment_info.append("Hora estimada de salida")

        if appointment_info:
            missing_items["citas"] = appointment_info

        # Check for missing document information
        document_info = []
        if self.need_cartaporte and not self.shipment_invoice:
            document_info.append("Carta porte")
        if not self.folio:
            document_info.append("Folio")

        if document_info:
            missing_items["documentos"] = document_info

        return missing_items

    def format_missing_items(self, missing_items):
        if not missing_items:
            return "✅ *La operación está completa.*"

        category_emojis = {
            "información_básica": "📋",
            "información_logística": "🚛",
            "citas": "📅",
            "documentos": "📄"
        }

        message = "⚠️ *Faltantes en la operación:*\n\n"
        for category, items in missing_items.items():
            emoji = category_emojis.get(category, "🔸")
            message += f"{emoji} *{category.replace('_', ' ').capitalize()}*\n"
            for item in items:
                message += f"   └ 🔻 {item}\n"
            message += "\n"

        return message

    def format_operation_missing_items_message(self):
        try:
            missing_items = self.get_operation_missing_items()
            message = self.format_missing_items(missing_items)
            return message
        except:
            pass
        return "Mensaje con los faltantes de la operación."

    def is_ready_for_invoicing(self):
        """
        Verifica si la operación tiene toda la información necesaria para ser facturada.
        """
        required_fields = [
            self.client,
            self.driver,
            self.vehicle,
            self.cargo_appointment,
            self.download_appointment,
            self.scheduled_departure_time,
            self.route,
        ]

        # Verifica que todos los campos requeridos estén presentes (no sean None o False)
        if not all(required_fields):
            return False

        #if not self.need_cartaporte:
        #    return False

        # Verifica que haya al menos un producto transportado asociado
        has_products = self.transported_products.exists()
        if not has_products:
            return False

        return True

    @staticmethod
    def generate_pre_folio():
        current_year = now().year
        prefix = chr(65 + (current_year - 2020))  # 2020 = A, ..., 2025 = F, etc.

        max_folio = (
            Operation.objects
            .filter(folio__startswith=prefix)
            .aggregate(models.Max("folio"))
            .get("folio__max")
        )

        max_prefolio = (
            Operation.objects
            .filter(pre_folio__startswith=prefix)
            .aggregate(models.Max("pre_folio"))
            .get("pre_folio__max")
        )

        def extract_number(value):
            if not value:
                return 0
            match = re.match(r'^[A-Z](\d{4})', value)
            return int(match.group(1)) if match else 0

        folio_number = extract_number(max_folio)
        prefolio_number = extract_number(max_prefolio)

        next_number = max(folio_number, prefolio_number) + 1
        return f"{prefix}{str(next_number).zfill(4)}"

    def approve(self):
        """
        Approve the operation and assign a pre-folio.
        """
        if not self.pre_folio:
            self.pre_folio = self.generate_pre_folio()
            self.status = OperationStatus.APPROVED
            self.save(update_fields=['pre_folio', 'status'])
        return self.pre_folio

    def assign_folio(self):
        if self.pre_folio and not self.folio:
            self.folio = self.pre_folio
            self.save(update_fields=['folio'])

            # Send notification to Telegram group
            try:
                self.notify_operation_approved()
            except Exception as e:
                print(f"Error sending operation approved notification: {str(e)}")

            if self.operation_date and not self.cargo_appointment:
                dt = datetime.combine(self.operation_date, time(8, 0))
                self.cargo_appointment = make_aware(dt)

            if self.operation_date and not self.download_appointment:
                dt = datetime.combine(self.operation_date, time(20, 0))
                self.download_appointment = make_aware(dt)

            if self.operation_date and not self.scheduled_departure_time:
                dt = datetime.combine(self.operation_date, time(8, 0))
                self.scheduled_departure_time = make_aware(dt)

            self.save()

        return self.folio

    def generate_invoice(self, user):

        if not self.client:
            raise ValueError("Cannot generate invoice without a client")

        if not self.folio:
            raise ValueError("Cannot generate invoice without a folio")

        # For now, we'll just update the status
        self.status = OperationStatus.INVOICED
        self.save(update_fields=['status'])

    def upload_invoice_to_drive(self, user=None):
        """
        Descarga la factura (PDF y XML) desde FacturAPI y la sube a Google Drive.
        Estructura:
            Facturacion/
                └── <Cliente>/
                    └── <Año>/
                        └── <Mes YYYY-MM>/
                            └── <Folio>/
                                ├── factura.pdf
                                └── factura.xml
        """
        if not self.shipment_invoice:
            raise ValueError("Cannot upload invoice that hasn't been generated")

        if not self.client:
            raise ValueError("Cannot upload invoice without a client")

        invoice = self.shipment_invoice

        # --- 1️⃣ Definir estructura de carpetas ---
        ROOT_FOLDER_ID = "1YPzEEXIGOj2Rs-lpLrd0Z94llJNoiaRF"
        FACTURACION_NAME = "Facturacion"
        current_year = str(self.cargo_appointment.year)
        current_month = str(self.cargo_appointment.month).zfill(2)
        client_name = self.client.name.replace("/", "-")
        folio_folder_name = self.folio or str(invoice.folio_number or "SIN-FOLIO")

        # --- 2️⃣ Obtener o crear jerarquía de carpetas ---
        facturacion_id = check_folder_exists_with_service_account(FACTURACION_NAME, ROOT_FOLDER_ID)
        if not facturacion_id:
            facturacion_id = create_folder_with_service_account(FACTURACION_NAME, ROOT_FOLDER_ID)

        client_folder_id = check_folder_exists_with_service_account(client_name, facturacion_id)
        if not client_folder_id:
            client_folder_id = create_folder_with_service_account(client_name, facturacion_id)

        # Guardar cliente folder en BD si no existe
        if not self.client_folder_id:
            client_folder, _ = GoogleDriveFolder.objects.get_or_create(
                user=user,
                drive_id=client_folder_id,
                defaults={"name": client_name},
            )
            self.client_folder = client_folder
            self.save(update_fields=["client_folder"])

        year_folder_id = check_folder_exists_with_service_account(current_year, client_folder_id)
        if not year_folder_id:
            year_folder_id = create_folder_with_service_account(current_year, client_folder_id)

        month_folder_id = check_folder_exists_with_service_account(current_month, year_folder_id)
        if not month_folder_id:
            month_folder_id = create_folder_with_service_account(current_month, year_folder_id)

        folio_folder_id = check_folder_exists_with_service_account(folio_folder_name, month_folder_id)
        if not folio_folder_id:
            folio_folder_id = create_folder_with_service_account(folio_folder_name, month_folder_id)

        # --- 3️⃣ Descargar archivos desde FacturAPI ---
        facturapi_id = invoice.facturapi_id
        if not facturapi_id:
            raise ValueError("Invoice has no FacturAPI ID")

        pdf_result = download_invoice_pdf(facturapi_id)
        xml_result = download_invoice_xml(facturapi_id)

        # FacturAPI devuelve (bytes, filename)
        pdf_content, pdf_filename = pdf_result if isinstance(pdf_result, tuple) else (pdf_result, str(self.folio + ".pdf"))
        xml_content, xml_filename = xml_result if isinstance(xml_result, tuple) else (xml_result, str(self.folio + ".xml"))

        # Validación
        if not isinstance(pdf_content, (bytes, bytearray)):
            raise TypeError(f"Expected PDF content as bytes, got {type(pdf_content)}")
        if not isinstance(xml_content, (bytes, bytearray)):
            raise TypeError(f"Expected XML content as bytes, got {type(xml_content)}")

        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as pdf_temp:
            pdf_temp.write(pdf_content)
            pdf_path = pdf_temp.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as xml_temp:
            xml_temp.write(xml_content)
            xml_path = xml_temp.name

        # Subir a Drive
        upload_file_with_service_account(pdf_path, folio_folder_id, overwrite=True, file_name=self.folio + ".pdf")
        upload_file_with_service_account(xml_path, folio_folder_id, overwrite=True, file_name=self.folio + ".xml")

        # --- 7️⃣ Limpieza de temporales ---
        os.remove(pdf_path)
        os.remove(xml_path)

        print(f"✅ Factura {invoice.series}-{invoice.folio_number} subida correctamente a Drive")
        return self.invoice_file

    def notify_operation_created(self):
        from apps.telegram_bots.models import TelegramBot, TelegramMessage, TelegramChat,TelegramGroup

        try:
            # Get the notification bot and group chat ID from settings
            from django.conf import settings

            bot_token = TelegramBot.objects.get(username='prueba_lletra_bot').token
            group_chat_id = TelegramGroup.objects.get(name='Folios Lletra').telegram_id

            # Get or create the bot
            bot, created = TelegramBot.objects.get_or_create(
                token=bot_token,
                defaults={'name': 'Operations Notification Bot'}
            )

            # Format the message
            message_text = self.format_operation_notification()

            # Send the message
            from apps.telegram_bots.services.services import send_telegram_message
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
                        'operation': self
                    }
                )

                # If the message already existed but wasn't linked to the operation, link it
                if not created and not telegram_message.operation:
                    telegram_message.operation = self
                    telegram_message.save()
            return True
        except Exception as e:
            print(e)
            return False

    def format_operation_notification(self):
        # Get the deliveries as a comma-separated list
        deliveries = ", ".join([d.name for d in self.route.route_stops.all()])

        # Format the message
        message = (
            f"🚚 Nueva operación registrada:\n"
            f"Cliente: {self.client.name if self.client else 'N/A'}\n"
            f"Origen: {self.route.initial_location}\n"
            f"Destino: {self.route.destination_location}\n"
            f"Unidad: {self.get_vehicle_type_display() if self.vehicle_type else 'N/A'}\n"
            f"Proveedor: {self.supplier.business_name if self.supplier else 'N/A'}\n"
            f"Operador: {self.driver.name + ' ' + self.driver.last_name if self.driver else 'N/A'}\n"
            f"Fecha: {self.operation_date.strftime('%Y-%m-%d')}\n"
        )

        if deliveries:
            message += f"Repartos: {deliveries}\n"

        message += f"Folio: {self.pre_folio or 'Pendiente'}"

        return message

    def format_operation_approved_notification(self):
        deliveries = ", ".join([d.name for d in self.route.route_stops.all()])

        # Format the message
        message = (
            f"✅ Operación aprobada con folio asignado:\n"
            f"Folio: {self.folio}\n"
            f"Cliente: {self.client.name if self.client else 'N/A'}\n"
            f"Origen: {self.route.initial_location}\n"
            f"Destino: {self.route.destination_location}\n"
            f"Unidad: {self.get_vehicle_type_display() if self.vehicle_type else 'N/A'}\n"
            f"Proveedor: {self.supplier.business_name if self.supplier else 'N/A'}\n"
            f"Operador: {self.driver.name + ' ' + self.driver.last_name if self.driver else 'N/A'}\n"
            f"Fecha: {self.operation_date.strftime('%Y-%m-%d')}\n"
        )

        if deliveries:
            message += f"Repartos: {deliveries}\n"

        return message

    def notify_operation_approved(self):
        from apps.telegram_bots.models import TelegramBot, TelegramMessage, TelegramChat

        try:
            # Get the notification bot and group chat ID from settings
            from apps.telegram_bots.models import TelegramGroup

            bot_token = TelegramBot.objects.get(username='prueba_lletra_bot').token

            # Get the "Embarques Lletra" group
            try:
                # Use filter instead of get to handle multiple groups
                groups = TelegramGroup.objects.filter(name='Embarques Lletra')
                if groups.exists():
                    group_chat_id = groups.first().telegram_id
                else:
                    raise TelegramGroup.DoesNotExist
            except TelegramGroup.DoesNotExist:
                return False

            if not bot_token or not group_chat_id:
                return False

            # Get or create the bot
            bot, created = TelegramBot.objects.get_or_create(
                token=bot_token,
                defaults={'name': 'Operations Notification Bot'}
            )

            # Format the message
            message_text = self.format_operation_approved_notification()

            # Send the message
            from apps.telegram_bots.services.services import send_telegram_message
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
                        'operation': self
                    }
                )

                # If the message already existed but wasn't linked to the operation, link it
                if not created and not telegram_message.operation:
                    telegram_message.operation = self
                    telegram_message.save()


            return True
        except Exception as e:
            print(e)
            return False

    def build_cartaporte_context(self):
        """
        Construye el contexto para renderizar el template de carta porte.
        Aquí puedes ir refinando nombres/campos según tus modelos actuales.
        """
        factura = ShipmentFacturapiInvoice.objects.get(id=self.shipment_invoice.id)

        route = self.route
        origin = route.initial_location if route else None
        destination = route.destination_location if route else None
        middle_points = route.route_stops.all() if route and route.route_stops.exists() else []

        transported_products = self.transported_products.all()

        context = {
            "operation": self,
            "Factura": factura,
            "Cartaporte": {
                "folio": self.folio or self.pre_folio or "",
                "TotalDistRec": getattr(route, "direct_distance", 0) if route else 0,
                "idccp": factura.ccp_id or "",
                "PermSCT": getattr(self.vehicle, "perm_sct", "") if self.vehicle else "",
                "NumPermisoSCT": getattr(self.vehicle, "sct_permit", "") if self.vehicle else "",
                "NombreAseg": getattr(self.vehicle, "insurance_company", "") if self.vehicle else "",
                "NumPolizaSeguro": getattr(self.vehicle, "insurance_code", "") if self.vehicle else "",
                "Unidad": getattr(self.vehicle, "econ_number", "") if self.vehicle else "",
                "PlacaVM": getattr(self.vehicle, "license_plate", "") if self.vehicle else "",
                "AnioModeloVM": getattr(self.vehicle, "year", "") if self.vehicle else "",
                "Caja": getattr(self.vehicle_box, "model", "") if self.vehicle_box else "",
                "PlacaCaja": getattr(self.vehicle_box, "license_plate", "") if self.vehicle_box else "",
                "NombreOperador": (
                    f"{self.driver.name} {self.driver.last_name}".strip()
                    if self.driver else ""
                ),
                "RFCOperador": getattr(self.driver, "rfc", "") if self.driver else "",
                "NumLicencia": getattr(self.driver, "license_number", "") if self.driver else "",
                "Client": {
                    "business_name": getattr(self.client, "business_name", "") if self.client else "",
                    "rfc": getattr(self.client, "rfc", "") if self.client else "",
                    "cp": (
                        getattr(getattr(self.client, "address", None), "zip_code", "")
                        if self.client else ""
                    ),
                    "use": getattr(self.client, "cfdi_use", "") if self.client else "",
                },
                "Origen": self.serialize_location(origin, is_origin=True),
                "Destino": self.serialize_location(destination, is_origin=False),
                "MiddlePoint": [self.serialize_location(point, is_middle=True) for point in middle_points],
                "Products": [self.serialize_product(product) for product in transported_products],
                "OperadorDirection": self.serialize_driver_address(),
            },
            "is_asturiano": False,
            "asturiano_links": [],
            "is_3b": False,
            "3b_links": [],
        }

        return context

    def serialize_location(self, location, is_origin=False, is_middle=False, is_destination=False):
        """
        Serializa una ubicación/ruta al formato que espera tu template viejo.
        Ajusta nombres de campos según el modelo real de Location/RouteStop.
        """
        if not location:
            return {
                "NombreRemitente": "",
                "RFCRemitente": "",
                "RFCDestinatario": "",
                "FechaHoraSalida": "",
                "Calle": "",
                "NumeroExterior": "",
                "Colonia": "",
                "Localidad": "",
                "Municipio": "",
                "Estado": "",
                "CodigoPostal": "",
                "Pais": "MEX",
                "Products": [],
            }

        address = getattr(location, "address", None)

        data = {
            "NombreRemitente": getattr(location, "name", ""),
            "RFCRemitente": getattr(location, "rfc", ""),
            "RFCDestinatario": getattr(location, "rfc", ""),
            "FechaHoraSalida": self.cargo_appointment if is_origin else self.download_appointment,
            "Calle": getattr(address, "street", "") if address else "",
            "NumeroExterior": getattr(address, "exterior_number", "") if address else "",
            "Colonia": getattr(address, "colony", "") if address else "",
            "Localidad": getattr(address, "city", "") if address else "",
            "Municipio": getattr(address, "city", "") if address else "",
            "Estado": getattr(address, "state", "") if address else "",
            "CodigoPostal": getattr(address, "zip_code", "") if address else "",
            "Pais": "MEX",
            "Products": [],
        }

        if is_middle:
            data["Products"] = [
                self.serialize_product(p)
                for p in self.transported_products.all()
                if getattr(p, "destination_id", None) == getattr(location, "id", None)
            ]

        return data

    def serialize_product(self, product):
        """
        Serializa un producto transportado al formato esperado por el template viejo.
        Ajusta nombres según tu modelo real.
        """
        return {
            "Cantidad": getattr(product, "amount", ""),
            "ClaveUnidad": getattr(product, "unit_key", ""),
            "BienesTransp": getattr(product, "transported_product_key", ""),
            "Descripcion": getattr(product, "description", ""),
            "PesoEnKg": getattr(product, "weight", ""),
            "Destino": getattr(getattr(product, "destination", None), "name", ""),
        }

    def serialize_driver_address(self):
        """
        Serializa la dirección del operador.
        Ajusta según tu modelo Driver.
        """
        if not self.driver:
            return {
                "Calle": "",
                "NumeroExterior": "",
                "Colonia": "",
                "Localidad": "",
                "Municipio": "",
                "Estado": "",
                "CodigoPostal": "",
                "Pais": "MEX",
            }

        address = getattr(self.driver, "address", None)

        return {
            "Calle": getattr(address, "street", "") if address else "",
            "NumeroExterior": getattr(address, "exterior_number", "") if address else "",
            "Colonia": getattr(address, "colony", "") if address else "",
            "Localidad": getattr(address, "city", "") if address else "",
            "Municipio": getattr(address, "city", "") if address else "",
            "Estado": getattr(address, "state", "") if address else "",
            "CodigoPostal": getattr(address, "zip_code", "") if address else "",
            "Pais": "MEX",
        }

    def render_cartaporte_html(self, template_name="operations_panel/cartaporte/cartaporte_only.html"):
        context = self.build_cartaporte_context()
        return render_to_string(template_name, context)

    class Meta:
        verbose_name = "Operación"
        verbose_name_plural = "Operaciones"
        ordering = ['-operation_date', '-created_at']
