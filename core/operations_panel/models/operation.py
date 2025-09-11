import re
from datetime import datetime, time
from django.db import models
from packaging.utils import _
from core.operations_panel.models.client import Client
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
    """
    Modelo para operaciones.
    """
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

    def to_operations_view(self, keys=None):
        result = self.to_display_dict(keys)
        result["is_invoice_ready"] = str(self.shipment_invoice is not None)
        result["is_ready_to_invoice"] = str(self.is_ready_for_invoicing())
        result["is_packing_ready"] = str(self.is_packing_ready)
        result["products_amount"] = str(self.transported_products.count())
        result["distance"] = str(self.route.direct_distance) if self.route else "0"
        result["shipment_type"] = self.shipment_type
        result["origin"] = str(self.route.initial_location)
        result["destination"] = str(self.route.destination_location)
        result["deliveries"] = ", ".join(str(route) for route in self.route.route_stops.all()) if self.route.route_stops else "[]"
        return result

    def get_operation_missing_items(self):
        """
        Identify missing items for an operation.

        Args:
            operation (Operation): The Operation instance to check

        Returns:
            dict: Dictionary with missing items categorized
        """
        missing_items = {}

        # Check for missing basic information
        basic_info = []
        if not self.client:
            basic_info.append("Cliente")
        if not self.origin:
            basic_info.append("Origen")
        if not self.destination:
            basic_info.append("Destino")
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
        if self.need_cartaporte and not self.invoice:
            document_info.append("Carta porte")
        if not self.folio:
            document_info.append("Folio")

        if document_info:
            missing_items["documentos"] = document_info

        return missing_items

    def format_missing_items(self, missing_items):
        """
        Formatea los faltantes de una operación como un mensaje para Telegram.

        Args:
            missing_items (dict): Diccionario con los campos faltantes categorizados.

        Returns:
            str: Mensaje listo para enviar por Telegram.
        """
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
        """
        Format a message with missing items for an operation.
        This is an empty function that will be filled with the actual message content later.

        Args:
            operation (Operation): The Operation instance to check

        Returns:
            str: Formatted message with missing items
        """
        # This function will be filled with the actual message content later
        # For now, it returns a placeholder message
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

        if not self.need_cartaporte:
            return False

        # Verifica que haya al menos un producto transportado asociado
        has_products = self.transported_products.exists()
        if not has_products:
            return False

        return True

    @staticmethod
    def generate_pre_folio():
        """
        Generate a pre-folio for a new operation.
        Format: [Letter][Number] where letter is based on the current year (2020=A, 2021=B, etc.)
        and number is sequential.
        """
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
            """
                Extrae la parte numérica del folio, ignorando la letra inicial y cualquier letra al final.
                Ej: 'F0003B' -> 3, 'F0123' -> 123
                """
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
        """
        Assign the pre-folio to the folio field.
        """
        if self.pre_folio and not self.folio:
            self.folio = self.pre_folio
            self.save(update_fields=['folio'])

            # Send notification to Telegram group
            try:
                from apps.telegram_bots.operations import notify_operation_approved
                notify_operation_approved(self)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception(f"Error sending operation approved notification: {str(e)}")

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
        """
        Generate an invoice for the operation using FacturAPI.
        This is a placeholder method that should be implemented with actual FacturAPI integration.
        """

        if not self.client:
            raise ValueError("Cannot generate invoice without a client")

        if not self.folio:
            raise ValueError("Cannot generate invoice without a folio")

        # This is a simplified example. In a real implementation, you would:
        # 1. Get or create a FacturapiCustomer for the client
        # 2. Create line items based on the operation details
        # 3. Generate the invoice with cartaporte complement
        # 4. Save the invoice reference to this operation

        # For now, we'll just update the status
        self.status = OperationStatus.INVOICED
        self.save(update_fields=['status'])

        return self.invoice

    def upload_invoice_to_drive(self, user):
        """
        Upload the invoice to Google Drive.
        This is a placeholder method that should be implemented with actual Google Drive integration.
        """
        import datetime

        if not self.invoice:
            raise ValueError("Cannot upload invoice that hasn't been generated")

        if not self.client:
            raise ValueError("Cannot upload invoice without a client")

        # This is a simplified example. In a real implementation, you would:
        # 1. Get or create a folder for the client
        # 2. Get or create a subfolder for the current month/year
        # 3. Upload the invoice PDF to that folder
        # 4. Save the file reference to this operation

        # For demonstration purposes, we'll just set up the folder structure
        current_month = datetime.datetime.now().strftime('%Y-%m')

        # In a real implementation, you would use the GoogleDriveService to:
        # 1. Find or create the client folder
        # 2. Find or create the month folder
        # 3. Upload the invoice file

        return self.invoice_file

    class Meta:
        verbose_name = "Operación"
        verbose_name_plural = "Operaciones"
        ordering = ['-operation_date', '-created_at']
