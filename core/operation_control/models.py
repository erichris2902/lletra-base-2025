from decimal import Decimal

from django.conf import settings
from django.db import models

from core.system.models import BaseModel


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

        return self.get_operation_sale_amount()

    @property
    def cost_amount(self):
        if self.cost_amount_override is not None:
            return self.cost_amount_override

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
        Ajustaremos este método cuando revisemos los campos reales
        de tu modelo Operation.
        """
        possible_fields = [
            "price",
            "total",
            "sale_amount",
            "customer_price",
            "amount",
        ]

        for field_name in possible_fields:
            value = getattr(self.operation, field_name, None)

            if value is not None:
                return value

        return Decimal("0.00")

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
