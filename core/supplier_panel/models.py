from django.core.validators import RegexValidator
from django.db import models

from core.system.models import BaseModel, SystemUser


class PaymentRequest(BaseModel):
    STATUS_CHOICES = (
        ('revision', 'EN REVISION'),
        ('aprobada', 'APROBADA'),
        ('denegada', 'DENEGADA'),
        ('complemento', 'EN ESPERA DE COMPLEMENTO'),
        ('finalizada', 'FINALIZADA'),
    )

    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, null=True, blank=True, related_name='user_payment_request')

    # Factura de ingreso
    invoice_pdf = models.FileField(
        upload_to='payment_requests/invoice/pdf/',
        verbose_name='Factura de ingreso (PDF)'
    )
    invoice_xml = models.FileField(
        upload_to='payment_requests/invoice/xml/',
        verbose_name='Factura de ingreso (XML)'
    )

    # Control vehicular: 1 letra + 4 números
    vehicle_control = models.CharField(
        max_length=5,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z]{1}[0-9]{4}$',
                message='El control vehicular debe tener 1 letra seguida de 4 números'
            )
        ],
        verbose_name='Control vehicular'
    )

    # Monto antes de impuestos
    amount_before_taxes = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Monto posterior a impuestos'
    )

    # Complemento de pago
    payment_complement_pdf = models.FileField(
        upload_to='payment_requests/complement/pdf/',
        verbose_name='Complemento de pago (PDF)',
        null=True,
        blank=True
    )
    payment_complement_xml = models.FileField(
        upload_to='payment_requests/complement/xml/',
        verbose_name='Complemento de pago (XML)',
        null=True,
        blank=True
    )

    # Estatus
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='revision',
        verbose_name='Estatus'
    )

    # Comentarios
    comments = models.TextField(
        null=True,
        blank=True,
        verbose_name='Comentarios'
    )

    def __str__(self):
        return f'{self.name} - {self.get_status_display()}'