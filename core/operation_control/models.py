from decimal import Decimal

from django.conf import settings
from django.db import models

from core.system.models import BaseModel
from core.admin_panel.models.purchase_order import PurchaseOrderOperation, PurchaseOrderAccessory


class OperationMasterControl(BaseModel):
    operation = models.OneToOneField(
        "operations_panel.Operation",
        on_delete=models.PROTECT,
        related_name="master_control",
        verbose_name="Operación",
    )

    # =========================================================
    # CONTROL DOCUMENTAL DEL CLIENTE
    # =========================================================

    missing_approval = models.BooleanField(
        verbose_name="Falta de Vo.Bo.",
        default=False,
    )

    counter_receipt = models.CharField(
        verbose_name="Codigo de plantilla",
        max_length=150,
        blank=True,
        default="",
    )

    counter_receipt_date = models.DateField(
        verbose_name="Fecha de contrarrecibo",
        null=True,
        blank=True,
    )

    customer_invoice_code = models.CharField(
        verbose_name="Código de factura",
        max_length=500,
        blank=True,
        default="",
        help_text="Permite registrar uno o varios códigos de factura.",
    )

    customer_invoice_date = models.DateField(
        verbose_name="Fecha de factura del cliente",
        null=True,
        blank=True,
    )

    expected_collection_date = models.DateField(
        verbose_name="Fecha programada de cobro",
        null=True,
        blank=True,
    )

    # =========================================================
    # CONTROL DEL PROVEEDOR
    # =========================================================

    supplier_invoice_date = models.DateField(
        verbose_name="Fecha de factura del proveedor",
        null=True,
        blank=True,
    )

    supplier_invoice_number = models.CharField(
        verbose_name="Número de factura del proveedor",
        max_length=250,
        blank=True,
        default="",
    )

    scheduled_supplier_payment_date = models.DateField(
        verbose_name="Fecha programada de pago",
        null=True,
        blank=True,
    )

    purchase_order = models.CharField(
        verbose_name="Orden de compra",
        max_length=250,
        blank=True,
        default="",
    )

    # =========================================================
    # IMPORTES MANUALES
    # =========================================================

    sale_amount_override = models.DecimalField(
        verbose_name="Precio manual",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Si está vacío, se utilizará el precio de la operación.",
    )

    cost_amount_override = models.DecimalField(
        verbose_name="Costo manual",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Si está vacío, se utilizará el costo de la operación.",
    )

    # =========================================================
    # FACTORAJE
    # =========================================================

    has_factoring = models.BooleanField(
        verbose_name="Tiene factoraje",
        default=False,
    )

    factoring_amount = models.DecimalField(
        verbose_name="Monto de factoraje",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    factoring_percentage = models.DecimalField(
        verbose_name="Porcentaje de factoraje",
        max_digits=7,
        decimal_places=4,
        default=Decimal("0.0000"),
    )

    # =========================================================
    # CONTROL GENERAL
    # =========================================================

    # Reportes reales (captura manual para seguimiento de flujo)
    collected_amount_reported = models.DecimalField(
        verbose_name="Ingreso real reportado",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monto efectivamente cobrado al cliente (captura manual).",
    )

    supplier_paid_amount_reported = models.DecimalField(
        verbose_name="Egreso real reportado",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monto efectivamente pagado al proveedor (captura manual).",
    )

    notes = models.TextField(
        verbose_name="Observaciones",
        blank=True,
        default="",
    )

    is_reviewed = models.BooleanField(
        verbose_name="Revisado",
        default=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="operation_master_controls_created",
        verbose_name="Creado por",
        null=True,
        blank=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="operation_master_controls_updated",
        verbose_name="Actualizado por",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        verbose_name="Fecha de creación",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        verbose_name="Última actualización",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Control maestro de operación"
        verbose_name_plural = "Controles maestros de operaciones"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["missing_approval"]),
            models.Index(fields=["expected_collection_date"]),
            models.Index(fields=["scheduled_supplier_payment_date"]),
            models.Index(fields=["has_factoring"]),
            models.Index(fields=["is_reviewed"]),
        ]

    def __str__(self):
        return f"Control maestro #{self.pk} - {self.operation}"

    @property
    def sale_amount(self):
        if self.sale_amount_override is not None:
            return self.sale_amount_override

        # Importante: Las Órdenes de Compra corresponden a egresos (costos),
        # por lo que NUNCA deben afectar el ingreso/venta.
        # El ingreso proviene de la operación (precio al cliente).
        return self.get_operation_sale_amount()

    @property
    def cost_amount(self):
        if self.cost_amount_override is not None:
            return self.cost_amount_override

        # Si la operación está ligada a una Orden de Compra (OC),
        # el costo debe provenir del total individual de la operación dentro de la OC
        # (incluye accesorios ligados y el IVA proporcional según la OC).
        po_total = self.get_purchase_order_operation_total()
        if po_total is not None:
            return po_total

        return self.get_operation_cost_amount()

    @property
    def factoring_cost(self):
        if not self.has_factoring:
            return Decimal("0.00")

        if self.factoring_amount:
            return self.factoring_amount

        if self.factoring_percentage and self.sale_amount:
            return (
                self.sale_amount
                * self.factoring_percentage
                / Decimal("100")
            )

        return Decimal("0.00")

    @property
    def profit(self):
        return self.sale_amount - self.cost_amount - self.factoring_cost

    @property
    def profit_percentage(self):
        if not self.sale_amount:
            return Decimal("0.00")

        return (
            self.profit
            * Decimal("100")
            / self.sale_amount
        )

    def get_operation_sale_amount(self):
        """
        Calcula el PRECIO (ingreso) CON impuestos.
        Regla de negocio solicitada:
        - Si hay factura(s) del cliente ligadas a la operación y vigentes (status == 'valid'),
          usar la suma de sus totales (campo `total` de FacturapiInvoice), que ya incluyen impuestos.
        - Si no hay facturas, estimar el total con impuestos a partir del total antes de impuestos
          de la operación (`Operation.total`) aplicando una tasa IVA por defecto.
            - Tasa preferida: si existe una Orden de Compra ligada, reutilizar su tasa efectiva
              (tax_amount/subtotal) como aproximación; de lo contrario, usar 16% por defecto.
        """
        op = getattr(self, "operation", None)
        if not op:
            return Decimal("0.00")

        # 1) Intentar usar facturas del cliente (bruto con impuestos)
        try:
            total_invoices = Decimal("0.00")
            used_any = False
            # Factura principal de embarque
            inv = getattr(op, "shipment_invoice", None)
            if inv is not None:
                status = getattr(inv, "status", None)
                if status == "valid":
                    total_invoices += getattr(inv, "total", Decimal("0.00")) or Decimal("0.00")
                    used_any = True
            # Otras facturas activas
            inv_qs = getattr(op, "invoices", None)
            if inv_qs is not None:
                shipment_id = getattr(inv, "id", None) if inv is not None else None
                for extra in inv_qs.all():
                    if getattr(extra, "status", None) != "valid":
                        continue
                    if shipment_id is not None and (getattr(extra, "id", None) == shipment_id):
                        continue
                    total_invoices += getattr(extra, "total", Decimal("0.00")) or Decimal("0.00")
                    used_any = True
            if used_any:
                return total_invoices
        except Exception:
            # Si algo falla leyendo facturas, hacemos fallback a estimación por tasa
            pass

        # 2) Estimar precio bruto a partir del total neto de la operación
        base_net = getattr(op, "total", None)
        if base_net is None:
            base_net = Decimal("0.00")

        # Tasa preferente desde la OC si existe
        tax_rate = None
        try:
            from core.admin_panel.models.purchase_order import PurchaseOrderOperation as _POO
            link = _POO.objects.select_related('purchase_order').filter(operation=op).first()
            if link and link.purchase_order:
                po = link.purchase_order
                subtotal_po = getattr(po, "subtotal", None) or Decimal("0.00")
                tax_po = getattr(po, "tax_amount", None) or Decimal("0.00")
                if subtotal_po and subtotal_po != Decimal("0.00"):
                    tax_rate = tax_po / subtotal_po
        except Exception:
            tax_rate = None

        if tax_rate is None:
            # Default IVA 16% para cliente
            tax_rate = Decimal("0.16")

        return base_net + (base_net * tax_rate)

    def get_operation_cost_amount(self):
        """
        Ajustaremos este método cuando revisemos los campos reales
        de costo de tu modelo Operation.
        """
        possible_fields = [
            "cost",
            "total_cost",
            "supplier_cost",
        ]

        for field_name in possible_fields:
            value = getattr(self.operation, field_name, None)

            if value is not None:
                return value

        return Decimal("0.00")

    def get_purchase_order_operation_total(self):
        """
        Si la operación está ligada a una Orden de Compra (OC), devuelve el TOTAL correspondiente
        SOLO a esta operación dentro de esa OC, incluyendo accesorios ligados a esta operación
        y el IVA proporcional según la OC. Si no hay OC, devuelve None.
        """
        op = getattr(self, "operation", None)
        if not op:
            return None

        link = PurchaseOrderOperation.objects.select_related('purchase_order').filter(operation=op).first()
        if not link or not link.purchase_order:
            return None

        po = link.purchase_order
        # Determinar tasa de impuesto usada por la OC: tax_amount / subtotal, fallback 12%
        try:
            subtotal_po = po.subtotal or Decimal("0.00")
            tax_po = po.tax_amount or Decimal("0.00")
        except Exception:
            subtotal_po = Decimal("0.00")
            tax_po = Decimal("0.00")

        if subtotal_po and subtotal_po != Decimal("0.00"):
            tax_rate = (tax_po / subtotal_po)
        else:
            tax_rate = Decimal("0.12")

        # Base de la operación dentro de la OC (PurchaseOrder.get_total usa operation.total)
        base = getattr(op, "total", None)
        if base is None:
            base = Decimal("0.00")

        # Accesorios de la OC ligados a ESTA operación
        accessories_qs = PurchaseOrderAccessory.objects.filter(purchase_order=po, operation=op).values_list("subtotal", flat=True)
        accessories_total = sum((a or Decimal("0.00") for a in accessories_qs), Decimal("0.00"))

        subtotal_op = base + accessories_total
        total_op = subtotal_op + (subtotal_op * tax_rate)
        return total_op

class OperationControlChangeLog(models.Model):
    control = models.ForeignKey(
        OperationMasterControl,
        on_delete=models.CASCADE,
        related_name="change_logs",
        verbose_name="Control maestro",
    )

    field_name = models.CharField(max_length=100)
    previous_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Modificado por",
        null=True,
        blank=True,
    )

    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cambio en control maestro"
        verbose_name_plural = "Cambios en control maestro"
        ordering = ["-changed_at", "-id"]
