import urllib
from datetime import datetime, time, timedelta
from io import BytesIO

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.timezone import now, make_aware
from packaging.utils import _

from apps.telegram_bots.models import TelegramUser
from core.operations_panel.models import Supplier, Client
from core.operations_panel.services import draw_route_on_map, build_address_string
from core.system.functions import paragraph_replace_text
from core.system.models import BaseModel, SystemUser
from apps.google_drive.models import GoogleDriveFile, GoogleDriveFolder
from ikigai2025.settings import GOOGLE_MAPS_API_KEY
from docx import Document
from geopy.distance import geodesic, distance

class LeadState(models.TextChoices):
    PROSPECT = 'PROSPECT', 'Prospect'
    CONTACTING = 'CONTACTING', 'Contacting'
    INTERESTED = 'INTERESTED', 'Interested'
    QUOTING = 'QUOTING', 'Quoting'
    CLOSED = 'CLOSED', 'Closed'
    INACTIVE = 'INACTIVE', 'Inactive'
    NOT_VIABLE = 'NOT_VIABLE', 'Not Viable'


class PriorityFlag(models.TextChoices):
    HIGH = 'HIGH', 'High'
    MEDIUM = 'MEDIUM', 'Medium'
    LOW = 'LOW', 'Low'

class StatusDeCotizacion(models.TextChoices):
    NONE = 'NONE', _('NONE')
    EN_ESPERA = 'EN_ESPERA', _('EN_ESPERA')
    EMITIDA = 'EMITIDA', _('EMITIDA')
    ACEPTADA = 'ACEPTADA', _('ACEPTADA')
    CANCELADA = 'CANCELADA', _('CANCELADA')

class QuoteImportance(models.TextChoices):
    NONE = 'NONE', _('NONE')
    LOW = 'LOW', _('BAJA')
    MED = 'MED', _('MEDIA')
    HIGH = 'HIGH', _('ALTA')

class Event(models.Model):
    """Evento programado en el calendario"""
    user = models.ForeignKey(TelegramUser, verbose_name="Usuario", on_delete=models.CASCADE, related_name="events")
    title = models.CharField("Título", max_length=255)
    description = models.TextField("Descripción", blank=True, null=True)
    start_datetime = models.DateTimeField("Inicio")
    end_datetime = models.DateTimeField("Fin", blank=True, null=True)
    location = models.CharField("Ubicación", max_length=255, blank=True, null=True)
    is_private = models.BooleanField("¿Privado?", default=False)
    created_at = models.DateTimeField("Fecha de creación", auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.start_datetime}"


class Task(models.Model):
    """Tareas pendientes o por hacer"""
    user = models.ForeignKey(TelegramUser, verbose_name="Usuario", on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField("Título", max_length=255)
    description = models.TextField("Descripción", blank=True, null=True)
    is_completed = models.BooleanField("¿Completada?", default=False)
    due_date = models.DateTimeField("Fecha límite", blank=True, null=True)
    is_recurring = models.BooleanField("¿Recurrente?", default=False)
    recurrence_interval = models.DurationField("Intervalo de recurrencia", blank=True, null=True)
    created_at = models.DateTimeField("Fecha de creación", auto_now_add=True)

    def __str__(self):
        return self.title

class Quotation(BaseModel):
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE, null=True, blank=True, related_name='user_quotes')

    client = models.CharField(max_length=150, verbose_name='Cliente', blank=True, null=True)

    origin = models.CharField(max_length=150, verbose_name='Origen', blank=True, null=True)
    destiny = models.CharField(max_length=150, verbose_name='Destino', blank=True, null=True)
    tipo_carga = models.CharField(max_length=150, verbose_name='Tipo de carga', blank=True, null=True)
    unit = models.CharField(max_length=150, verbose_name='Unidad', blank=True, null=True)
    requerimientos = models.CharField(max_length=150, verbose_name='Requerimientos', blank=True, null=True)
    peso = models.CharField(max_length=150, verbose_name='Peso (Kgs)', blank=True, null=True)

    cost = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Costo', blank=True, null=True)
    date = models.DateField(default=datetime.now(), verbose_name='Fecha de operacion', blank=True, null=True)

    supplier1 = models.ForeignKey(Supplier, related_name="supplier1", verbose_name='Proveedor #1',
                                  on_delete=models.SET_NULL, null=True, blank=True)
    supplier2 = models.ForeignKey(Supplier, related_name="supplier2", verbose_name='Proveedor #2',
                                  on_delete=models.SET_NULL, null=True, blank=True)
    supplier3 = models.ForeignKey(Supplier, related_name="supplier3", verbose_name='Proveedor #3',
                                  on_delete=models.SET_NULL, null=True, blank=True)
    supplier4 = models.ForeignKey(Supplier, related_name="supplier4", verbose_name='Proveedor #4',
                                  on_delete=models.SET_NULL, null=True, blank=True)
    supplier5 = models.ForeignKey(Supplier, related_name="supplier5", verbose_name='Proveedor #5',
                                  on_delete=models.SET_NULL, null=True, blank=True)

    cost1 = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Costo', blank=True, null=True)
    cost2 = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Costo', blank=True, null=True)
    cost3 = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Costo', blank=True, null=True)
    cost4 = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Costo', blank=True, null=True)
    cost5 = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Costo', blank=True, null=True)

    comment1 = models.CharField(max_length=150, verbose_name='Comentarios', blank=True, null=True)
    comment2 = models.CharField(max_length=150, verbose_name='Comentarios', blank=True, null=True)
    comment3 = models.CharField(max_length=150, verbose_name='Comentarios', blank=True, null=True)
    comment4 = models.CharField(max_length=150, verbose_name='Comentarios', blank=True, null=True)
    comment5 = models.CharField(max_length=150, verbose_name='Comentarios', blank=True, null=True)

    final_supplier = models.ForeignKey(Supplier, related_name="final_supplier", verbose_name='Proveedor seleccionado',
                                       on_delete=models.SET_NULL, null=True, blank=True)

    status_de_cotizacion = models.CharField(max_length=30, verbose_name='Status de cotizacion', blank=True, null=True,
                                            choices=StatusDeCotizacion.choices, default=StatusDeCotizacion.EN_ESPERA)

    importancia_de_cotizacion = models.CharField(max_length=30, verbose_name='Importancia', blank=True, null=True,
                                            choices=QuoteImportance.choices, default=QuoteImportance.HIGH)

    client_email = models.CharField(max_length=150, verbose_name='Email del cliente', blank=True, null=True)
    email_sended = models.BooleanField(default=False, verbose_name='¿Se envio el correo?', blank=True, null=True)
    docx = models.FileField(upload_to='quotes/', null=True, blank=True)

    image = models.ImageField(upload_to="telegram_images/", null=True, blank=True)

    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    date_created = models.DateTimeField(auto_now=True, verbose_name='Fecha de creacion')
    date_updated = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de modificacion')

    def __str__(self):
        status = dict(self._meta.get_field("status_de_cotizacion").choices).get(self.status_de_cotizacion, "Sin estado")
        return f"📝 Cotización #{self.id} - {self.client or 'Cliente sin nombre'} - {status} - {self.date:%d/%m/%Y}"

    def toJSON(self):
        data = {
            "id": self.id,
            "client": self.client,
            "origin": self.origin,
            "destiny": self.destiny,
            "status": self.status_de_cotizacion,
            "unidad": self.unit,
            "costo": "$" + '{:,}'.format(self.cost),
        }
        return data

    def generateDocx(self):
        args = {}
        args['context'] = {
            "Cliente": {
                "Nombre": self.client,
                "Direccion": "Sin direccion",
                "Ciudad": "Sin ciudad",
            },
            "Detalle": {
                "Origen": self.origin,
                "Destino": self.destiny,
                "Unidad": self.unit,
                "Costo": "$" + str(self.cost),
            },
            "Fechas": {
                "Expedicion": self.date_joined,
                "Expiracion": self.date_joined,
            },
            "Folio": {
                "Numero": str(self.id),
            },
        }

        document = Document('static/PlantillaCotizacion.docx')

        import re
        folio = re.compile("<FOLIO>")
        cliente = re.compile("<NOMBRE_CLIENTE>")
        direccion = re.compile("<DIRECCION_CLIENTE>")
        ciudad = re.compile("<CIUDAD_CLIENTE>")
        exped = re.compile("<FECHA_EXPE>")
        expir = re.compile("<FECHA_EXPI>")
        origen = re.compile("<ORIGEN>")
        destino = re.compile("<DESTINO>")
        unidad = re.compile("<UNIDAD>")
        subtotal = re.compile("<SUBTOTAL>")
        iva = re.compile("<IVA>")
        total = re.compile("<TOTAL>")
        usuario = re.compile("<USUARIO_LLETRA>")
        cargo = re.compile("<CARGO>")
        firma = re.compile("<FIRMA>")

        # import io
        # imgLinkData= io.BytesIO(requests.get(args['context']["Trabajador"]['Instructor'].firma.url).content)

        three_months_later = args['context']['Fechas']['Expedicion'] + timedelta(days=3 * 30)

        for paragraph in document.paragraphs:
            paragraph_replace_text(paragraph, folio, args['context']["Folio"]['Numero'])

            paragraph_replace_text(paragraph, cliente, args['context']["Cliente"]['Nombre'])
            paragraph_replace_text(paragraph, direccion, args['context']["Cliente"]['Direccion'])
            paragraph_replace_text(paragraph, ciudad, args['context']["Cliente"]['Ciudad'])

            paragraph_replace_text(paragraph, exped,
                                   f"{args['context']['Fechas']['Expedicion']:%d}" + "/" + f"{args['context']['Fechas']['Expedicion']:%m}" + "/" + f"{args['context']['Fechas']['Expedicion']:%y}")
            paragraph_replace_text(paragraph, expir,
                                   f"{three_months_later:%d}" + "/" + f"{three_months_later:%m}" + "/" + f"{three_months_later:%y}")

            paragraph_replace_text(paragraph, origen, args['context']["Detalle"]['Origen'])
            paragraph_replace_text(paragraph, destino, args['context']["Detalle"]['Destino'])
            paragraph_replace_text(paragraph, unidad, args['context']["Detalle"]['Unidad'])
            paragraph_replace_text(paragraph, subtotal, args['context']["Detalle"]['Costo'])

            paragraph_replace_text(paragraph, total, args['context']["Detalle"]['Costo'])
            paragraph_replace_text(paragraph, iva, "")

            paragraph_replace_text(paragraph, usuario, "")
            paragraph_replace_text(paragraph, cargo, "")
            paragraph_replace_text(paragraph, firma, "")

        # INSERTAR AQUI LA LOGICA PARA GUARDARLO EN self.docx
        # Guardar en memoria y asignar a FileField
        buffer = BytesIO()
        document.save(buffer)
        buffer.seek(0)
        filename = f"cotizacion-{str(self.id)}.docx"
        self.docx.save(filename, ContentFile(buffer.read()), save=False)
        buffer.close()
        self.save()
        return self.docx.url

    class Meta:
        verbose_name = 'Cotizacion de viaje'
        verbose_name_plural = 'Cotizaciones de viajes'
        db_table = 'travel_quote'
        ordering = ['-id']

class LeadContact(BaseModel):
    """Contacto del cliente potencial"""
    name = models.CharField("Nombre", max_length=100)
    position = models.CharField("Puesto", max_length=100)
    email = models.EmailField("Correo electrónico")
    phone = models.CharField("Teléfono", max_length=20)

    def __str__(self):
        return self.name + " - " + self.position + " - " + self.phone + " - " + self.email

class LeadIndustry(BaseModel):
    """Industria del cliente potencial"""
    industry = models.CharField("Industria", max_length=200)

    def __str__(self):
        return self.industry

    def toJSON(self):
        data = {
            'id': self.id,
            'industry': self.industry,
        }
        for key in data.keys():
            if data[key] == "None":
                data[key] = ""
        return data

class LeadCategory(BaseModel):
    """Categoría del cliente potencial"""
    category = models.CharField("Categoría", max_length=200)

    def __str__(self):
        return self.category

    def toJSON(self):
        data = {
            'id': self.id,
            'category': self.category,
        }
        for key in data.keys():
            if data[key] == "None":
                data[key] = ""
        return data

class Lead(BaseModel):
    user = models.ForeignKey(TelegramUser, verbose_name="Usuario", on_delete=models.CASCADE, null=True, blank=True, related_name='leads')
    business_name = models.CharField("Nombre comercial", max_length=200)
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.SET_NULL, related_name='leads', null=True, blank=True)
    category = models.ForeignKey(LeadCategory, verbose_name="Categoría", on_delete=models.SET_NULL, related_name='category_lead', null=True, blank=True)
    industry = models.ForeignKey(LeadIndustry, verbose_name="Industria", on_delete=models.SET_NULL, related_name='industry_type_lead', null=True, blank=True)
    contacts = models.ManyToManyField(LeadContact, verbose_name="Contactos", blank=True, related_name='lead_contacts')
    state = models.CharField("Estado del lead", max_length=20, choices=LeadState.choices, default=LeadState.PROSPECT)
    geographic_zone = models.CharField("Zona geográfica", max_length=200, null=True, blank=True)
    requirements = models.TextField("Requerimientos", blank=True, null=True)
    created_date = models.DateTimeField("Fecha de creación", default=timezone.now)
    modified_date = models.DateTimeField("Fecha de modificación", auto_now=True)
    closed_date = models.DateTimeField("Fecha de cierre", null=True, blank=True)

    def __str__(self):
        return f"{self.business_name} - {self.get_state_display()} - {self.geographic_zone or 'Zona desconocida'}"

    def get_contact(self):
        if self.contacts.all().count() > 0:
            return self.contacts.all()[0]
        return "Sin contacto"

    def toJSON(self):
        _name = ""
        _position = ""
        _email = ""
        _phone = ""
        if self.contacts.all().count() > 0:
            _name = self.contacts.all().first().name
            _position = self.contacts.all().first().position
            _email = self.contacts.all().first().email
            _phone = self.contacts.all().first().phone

        data = {
            'id': self.id,
            'business_name': self.business_name,
            'category': str(self.category),
            'industry': str(self.industry),
            'name': _name,
            'position': _position,
            'email': _email,
            'phone': _phone,
            'state': self.state,
            'geographic_zone': self.geographic_zone,
            'requirements': self.requirements,
            'date_updated': self.date_updated,
        }
        print(data)
        for key in data.keys():
            if data[key] == "None":
                data[key] = ""
        return data

class LeadEvent(BaseModel):
    """Evento relacionado al cliente potencial"""
    lead = models.ForeignKey(Lead, verbose_name="Lead", on_delete=models.CASCADE, related_name='events')
    title = models.CharField("Título", max_length=200)
    description = models.TextField("Descripción", blank=True, null=True)
    event_type = models.CharField("Tipo de evento", max_length=20, choices=[
        ('CALL', 'Llamada'),
        ('VISIT', 'Visita'),
        ('EMAIL', 'Correo'),
        ('MEETING', 'Reunión'),
    ])
    start_time = models.DateTimeField("Hora de inicio")
    end_time = models.DateTimeField("Hora de fin")
    location = models.CharField("Ubicación", max_length=200, blank=True, null=True)
    external_calendar_id = models.CharField("ID en calendario externo", max_length=200, blank=True, null=True)


    def __str__(self):
        return f"{self.title} - {self.lead.client}"

class LeadExpense(BaseModel):
    """Gasto relacionado al lead"""
    lead = models.ForeignKey(Lead, verbose_name="Lead", on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField("Título", max_length=200)
    description = models.TextField("Descripción", blank=True, null=True)
    amount = models.DecimalField("Monto", max_digits=10, decimal_places=2)
    expense_date = models.DateTimeField("Fecha del gasto", default=timezone.now)
    expense_type = models.CharField("Tipo de gasto", max_length=50, choices=[
        ('GAS', 'Gasolina'),
        ('TOLLS', 'Casetas'),
        ('OTHER', 'Otros'),
    ])
    receipt = models.FileField("Comprobante", upload_to='expenses/', null=True, blank=True)

    def __str__(self):
        tipo = dict(self._meta.get_field("expense_type").choices).get(self.expense_type, self.expense_type)
        return f"{self.title} - {self.amount:.2f} MXN - {tipo} - {self.expense_date:%d/%m/%Y}"