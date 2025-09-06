from datetime import datetime

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.facturapi.choices import TaxRegime, PAYMENT_METHOD_CHOICES, TaxType, TaxFactorType, CFDI_TYPES, CFDI_USE, \
    CFDIRelationType, PAYMENT_FORMS
from core.system.models import BaseModel


class FacturapiInvoice(BaseModel):
    """
    Información de facturas de FacturAPI.
    """
    STATUS_CHOICES = (
        ('valid', _('Vigente')),
        ('canceled', _('Cancelado')),
        ('pending', _('Pendiente')),
        ('draft', _('Draft')),
    )
    facturapi_id = models.CharField(
        _('ID de FacturAPI'),
        max_length=255,
        unique=True,
        help_text=_('Identificador de la factura en FacturAPI'),
        null=True,  # Permitimos NULL en BD
        blank=True,  # Permitimos vacío en formularios
    )
    customer = models.ForeignKey(
        "operations_panel.Client",
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name=_('Cliente')
    )
    #customer = models.CharField(_('Tipo de comprobante'), max_length=2, default='I', choices=CFDI_TYPES)  # I, E, T, etc.
    type = models.CharField(_('Tipo de comprobante'), max_length=2, default='I', choices=CFDI_TYPES)  # I, E, T, etc.
    use = models.CharField(_('Uso del CFDI'), max_length=5, choices=CFDI_USE, default="G03", blank=True, null=True)
    payment_form = models.CharField(_('Forma de pago'), max_length=5, choices=PAYMENT_METHOD_CHOICES, default="PPD")
    payment_method = models.CharField(_("Método de pago"), max_length=3, choices=PAYMENT_FORMS, default="99",
                                      blank=True, null=True)
    currency = models.CharField(_('Moneda'), max_length=10, default="MXN")
    pdf_custom_section = models.TextField(_('Sección personalizada del PDF'), blank=True, null=True)

    relation_type = models.CharField(max_length=5, verbose_name='CFDI Relacionados', choices=CFDIRelationType.choices,
                                     blank=True, null=True)
    related_uuids = ArrayField(models.UUIDField(), verbose_name="Folios fiscales (UUID) relacionados", blank=True,
                               null=True)

    idempotency_key = models.CharField(_('idempotency_key'), max_length=36, blank=True, null=True)
    status = models.CharField(_('Estatus'), max_length=10, choices=STATUS_CHOICES, default='valid')
    is_ready_to_stamp = models.BooleanField(_('¿Listo para timbrar?'), default=True)

    uuid = models.CharField(_('UUID del SAT'), max_length=36, blank=True, null=True)
    series = models.CharField(_('Serie'), max_length=50, blank=True, null=True)
    folio_number = models.IntegerField(_('Folio'), blank=True, null=True)
    total = models.DecimalField(_('Total'), default=0, max_digits=12, decimal_places=2)

    stamp_date = models.DateTimeField(_('Fecha de timbrado'), blank=True, null=True)
    sat_cert_number = models.CharField(_('Número de certificado SAT'), max_length=50, blank=True, null=True)
    verification_url = models.URLField(_('URL de verificación del SAT'), blank=True, null=True)
    sat_signature = models.TextField(_('Sello del SAT'), blank=True, null=True)
    signature = models.TextField(_('Sello del emisor'), blank=True, null=True)

    cancellation_status = models.CharField(_('Estatus de cancelación'), max_length=20, blank=True, null=True)

    related_documents = models.JSONField(_('Documentos relacionados'), blank=True, null=True)
    target_invoice_ids = models.JSONField(_('Facturas destino relacionadas'), blank=True, null=True)
    received_payment_ids = models.JSONField(_('Pagos relacionados recibidos'), blank=True, null=True)
    complements = models.JSONField(_('Complementos CFDI'), blank=True, null=True)

    facturapi_response = models.JSONField(
        _('Respuesta completa de FacturAPI'),
        blank=True,
        null=True,
        help_text=_('Respuesta original de FacturAPI al timbrar o consultar')
    )

    is_live = models.BooleanField(default=False, verbose_name=_('¿Entorno Live?'))

    canceled_at = models.DateTimeField(_('Cancelado el'), blank=True, null=True)

    def __str__(self):
        return f"Invoice {self.series}-{self.folio_number} for {self.customer.business_name}"

    class Meta:
        verbose_name = _("FacturAPI Invoice")
        verbose_name_plural = _("FacturAPI Invoices")
        ordering = ["-created_at"]

    def bill(self):
        if self.type == 'I':
            from apps.facturapi.services import bill_type_i
            bill_type_i(self)
        elif self.type == 'T':
            raise Exception("TODO Invoice T")
        elif self.type == 'E':
            from apps.facturapi.services import bill_type_e
            bill_type_e(self)
        elif self.type == 'P':
            from apps.facturapi.services import bill_type_p
            bill_type_p(self)
        else:
            raise Exception("Error con el tipo de factura seleccionado")

    def cancel(self, motivo, sustitucion=None):
        from apps.facturapi.services import cancel_invoice
        cancel_invoice(self, motivo, sustitucion)


class FacturapiTax(BaseModel):
    """
    Información de impuestos de FacturAPI.
    """
    name = models.CharField(_('Identificador'), max_length=40)  # IDENTIFICADOR
    type = models.CharField(_('Impuesto'), max_length=10, choices=TaxType.choices,
                            default=TaxType.IVA)  # IVA, ISR, IEPS
    rate = models.DecimalField(_('Tasa'), max_digits=6, decimal_places=4)
    factor = models.CharField(_('Factor'), max_length=10, choices=TaxFactorType.choices,
                              default=TaxFactorType.TASA)  # Tasa, Cuota, Exento
    withholding = models.BooleanField(_('Marcado = Retencion, Desmarcado = Translado'), default=False)
    is_retained = models.BooleanField(_('¿Es retenido?'), default=False)
    is_quota = models.BooleanField(_('¿Es cuota?'), default=False)

    def __str__(self):
        retained = "retenido" if self.withholding else ""
        return f"{self.type} {self.rate}% {retained}"

    class Meta:
        verbose_name = _("FacturAPI Tax")
        verbose_name_plural = _("FacturAPI Taxes")
        ordering = ["type", "rate"]


class FacturapiProduct(BaseModel):
    """
    Información de productos/servicios de FacturAPI.
    """
    name = models.CharField(_('Nombre del producto'), max_length=255)
    sku = models.CharField(_('Clave SKU'), max_length=255, unique=True)
    description = models.TextField(_('Descripción'))
    product_key = models.CharField(_('Clave de producto SAT'), max_length=20)
    unit_key = models.CharField(_('Clave de unidad SAT'), max_length=5)
    price = models.DecimalField(_('Precio sin IVA'), max_digits=10, decimal_places=2)
    taxes = models.ManyToManyField(
        FacturapiTax,
        related_name="products",
        blank=True,
        verbose_name=_('Impuestos')
    )

    def __str__(self):
        return f"{self.description} (${self.price})"

    class Meta:
        verbose_name = _("FacturAPI Product")
        verbose_name_plural = _("FacturAPI Products")
        ordering = ["description"]


class FacturapiInvoiceItem(BaseModel):
    """
    Conceptos/partidas de una factura de FacturAPI.
    """
    invoice = models.ForeignKey(
        FacturapiInvoice,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_('Factura')
    )
    product = models.ForeignKey(
        FacturapiProduct,
        on_delete=models.PROTECT,
        related_name="invoice_items",
        verbose_name=_('Producto/Servicio')
    )
    quantity = models.DecimalField(_('Cantidad'), max_digits=10, decimal_places=2)
    discount = models.DecimalField(_('Descuento'), max_digits=10, decimal_places=2, default=0)
    description = models.CharField(_('Descripción'), max_length=255)
    product_key = models.CharField(_('Clave de producto SAT'), max_length=20)
    unit_key = models.CharField(_('Clave de unidad SAT'), max_length=5)
    unit_price = models.DecimalField(_('Precio unitario'), max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(_('Subtotal'), max_digits=12, decimal_places=2)
    total = models.DecimalField(_('Total'), max_digits=12, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} x {self.description}"

    class Meta:
        verbose_name = _("FacturAPI Invoice Item")
        verbose_name_plural = _("FacturAPI Invoice Items")
        ordering = ["invoice", "id"]


class FacturapiInvoicePayment(BaseModel):
    """
    Conceptos/partidas de una factura de FacturAPI.
    """
    invoice = models.ForeignKey(
        FacturapiInvoice,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_('Factura')
    )
    uuid = models.CharField(max_length=100, verbose_name='UUID relacionado al pago')
    amount = models.DecimalField(decimal_places=2, max_digits=9, default=0, verbose_name='Pago actual del comprobante')
    installment = models.DecimalField(decimal_places=2, max_digits=9, default=0, verbose_name='Número de parcialidad del pago')
    last_balance = models.DecimalField(decimal_places=2, default=0, max_digits=9, verbose_name='Pendiente por pagar anteriormente')
    payment_day = models.DateField(default=datetime.now, verbose_name='Fecha de pago (dd/mm/yyyy)')
    taxes = models.ManyToManyField(FacturapiTax, verbose_name='Impuestos')
