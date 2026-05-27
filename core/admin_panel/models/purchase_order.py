from django.db import models, IntegrityError
from django.utils import timezone
from decimal import Decimal

from core.system.models import BaseModel
from core.operations_panel.models import Client, Operation, Driver, Supplier
from apps.telegram_bots.models import TelegramUser


class PurchaseOrderStatus(models.TextChoices):
    BORRADOR = 'BORRADOR', 'Borrador'
    PUBLICADA = 'PUBLICADA', 'Publicada'
    ENVIADA = 'ENVIADA', 'Enviada'
    EN_ESPERA = 'EN_ESPERA', 'En Espera'
    APROBADA = 'APROBADA', 'Aprobada'
    PAGADA = 'PAGADA', 'Pagada'


class AccessoryType(models.TextChoices):
    CASETAS = 'CASETAS', 'Casetas'
    GASOLINA = 'GASOLINA', 'Gasolina'
    MANIOBRAS = 'MANIOBRAS', 'Maniobras'
    OTROS = 'OTROS', 'Otros'


class PurchaseOrder(BaseModel):
    """Orden de compra generada a partir de operaciones seleccionadas"""

    # Información básica
    folio = models.CharField(max_length=50, unique=True, verbose_name="Folio")
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        verbose_name="Cliente",
        related_name="purchase_orders",
        null=True,
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Driver",
        related_name="purchase_orders"
    )

    # Estado y fechas
    status = models.CharField(
        max_length=20,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.BORRADOR,
        verbose_name="Estado"
    )

    # Totales
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Subtotal"
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="IVA"
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total"
    )

    # Archivos
    pdf_file = models.FileField(
        upload_to='purchase_orders/pdf/',
        null=True,
        blank=True,
        verbose_name="PDF"
    )
    invoice_file = models.FileField(
        upload_to='purchase_orders/invoices/',
        null=True,
        blank=True,
        verbose_name="Factura del cliente"
    )
    # Archivos de factura cargados por el proveedor (portal)
    supplier_invoice_pdf = models.FileField(
        upload_to='purchase_orders/supplier_invoices/pdf/',
        null=True,
        blank=True,
        verbose_name="Factura del proveedor (PDF)"
    )
    supplier_invoice_xml = models.FileField(
        upload_to='purchase_orders/supplier_invoices/xml/',
        null=True,
        blank=True,
        verbose_name="Factura del proveedor (XML)"
    )

    # Observaciones
    notes = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    # Control de fechas
    sent_date = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de envío")
    waiting_date = models.DateTimeField(null=True, blank=True, verbose_name="Fecha en espera")
    approved_date = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de aprobación")
    paid_date = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de pago")

    def save(self, *args, **kwargs):
        if self.folio:
            return super().save(*args, **kwargs)

        year = timezone.now().year
        prefix = f"OC-{year}-"

        for _ in range(10):
            last_order = PurchaseOrder.objects.filter(
                folio__startswith=prefix
            ).order_by('-folio').first()

            last_number = 0
            if last_order and last_order.folio:
                try:
                    last_number = int(last_order.folio.split('-')[-1])
                except (ValueError, IndexError):
                    last_number = 0

            self.folio = f"{prefix}{last_number + 1:04d}"

            try:
                return super().save(*args, **kwargs)
            except IntegrityError:
                self.folio = None

        raise IntegrityError("No se pudo generar un folio único para la orden de compra.")

    def calculate_totals(self):
        """Calcula los totales basado en operaciones y accesorios"""
        operations_total = sum(
            item.operation.total or Decimal('0.00')
            for item in self.operations.all()
        )
        accessories_total = sum(
            acc.subtotal for acc in self.accessories.all()
        )

        self.subtotal = operations_total + accessories_total
        self.tax_amount = self.subtotal * Decimal('0.16')  # 16% IVA
        self.total = self.subtotal + self.tax_amount
        self.save()

    def __str__(self):
        return f"{self.folio} - {self.client.business_name} - {self.get_status_display()}"

    class Meta:
        verbose_name = "Orden de Compra"
        verbose_name_plural = "Órdenes de Compra"
        ordering = ['-created_at']


class PurchaseOrderOperation(BaseModel):
    """Relación entre orden de compra y operaciones"""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="operations",
        verbose_name="Orden de Compra"
    )
    operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        verbose_name="Operación"
    )

    class Meta:
        verbose_name = "Operación en Orden"
        verbose_name_plural = "Operaciones en Orden"
        unique_together = ['purchase_order', 'operation']


class PurchaseOrderAccessory(BaseModel):
    """Accesorios adicionales de la orden de compra ligados a una operación específica"""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="accessories",
        verbose_name="Orden de Compra"
    )
    operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        verbose_name="Operación relacionada",
        help_text="Operación a la cual está ligado este accesorio"
    )
    type = models.CharField(
        max_length=20,
        choices=AccessoryType.choices,
        verbose_name="Tipo"
    )
    description = models.CharField(max_length=255, verbose_name="Descripción")
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name="Cantidad"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio Unitario"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Subtotal"
    )

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Recalcular totales de la orden
        self.purchase_order.calculate_totals()

    def __str__(self):
        return f"{self.get_type_display()} - {self.description} - ${self.subtotal} (Op: {self.operation.folio if hasattr(self.operation, 'folio') else self.operation.id})"

    class Meta:
        verbose_name = "Accesorio"
        verbose_name_plural = "Accesorios"