import json
import uuid

from django.db import models
from django.db.models import Sum
from django.utils.timezone import localtime
from packaging.utils import _

from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.choices import MEXICAN_STATES_KEY, ShipmentType


class ShipmentFacturapiInvoice(FacturapiInvoice):
    """
    Información adicional de Carta Porte para facturas de FacturAPI.
    Se usa herencia multi-tabla (OneToOne con FacturapiInvoice).
    """
    operation = models.ForeignKey("Operation", on_delete=models.PROTECT, null=True, blank=True)

    total_distance_km = models.PositiveIntegerField(
        _("Distancia total a recorrer (km)"), default=0
    )
    departure_at = models.DateTimeField(
        _("Fecha y hora de salida")
    )
    scheduled_arrival_at = models.DateTimeField(
        _("Fecha y hora programada de llegada")
    )

    sender_name = models.CharField(
        _("Nombre del remitente"), max_length=100
    )
    sender_rfc = models.CharField(
        _("RFC del remitente"), max_length=13
    )

    sct_permit_number = models.CharField(
        _("Número de permiso SCT"), max_length=100
    )
    insurer_name = models.CharField(
        _("Nombre de la aseguradora"), max_length=100
    )
    insurance_policy_number = models.CharField(
        _("Número de póliza de seguro"), max_length=100
    )
    sct_permit_type = models.CharField(  # "PermSCT"
        _("Tipo de permiso SCT"), max_length=100
    )

    ccp_id = models.CharField(
        _("ID de Carta Porte (ccp_id)"), max_length=100, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if self.ccp_id == None:
            self.ccp_id = str(uuid.uuid4())
            self.ccp_id = "CCC" + self.ccp_id[3:].upper()
        super().save(*args, **kwargs)

    def bill(self):
        if self.type == 'I':
            self.bill_type_i_shipment()
        elif self.type == 'T':
            raise Exception("TODO Invoice T cartaporte")
        else:
            raise Exception("Las cartaportes solo pueden timbrarse como Ingreso o Translado")

    class Meta:
        verbose_name = _("Cartaporte")
        verbose_name_plural = _("Cartaportes")

    def bill_type_i_shipment(self):
        from apps.facturapi.services import _set_facturapi_invoice_base_data, _set_facturapi_invoice_cfdi_relation, \
            _set_facturapi_invoice_item, _send_invoice_to_facturapi
        data = _set_facturapi_invoice_base_data(self)
        data["payment_form"] = self.payment_method
        data["payment_method"] = self.payment_form
        data["use"] = self.use
        print(1)
        data = _set_facturapi_invoice_cfdi_relation(self, data)
        data["items"] = []
        print(2)
        for invoice_item in self.items.all():
            item = _set_facturapi_invoice_item(invoice_item)
            data["items"].append(item)
        print(3)
        data["pdf_custom_section"] = self.pdf_custom_section

        # Armado de cartaporte
        print(4)
        data = self.cartaporte_data(data)
        print(data)
        raise Exception("Llego")

        _send_invoice_to_facturapi(shipment_invoice, data)

    def cartaporte_data(self, data):
        data["namespaces"] = []
        namespace = {}
        namespace["prefix"] = "cartaporte31"
        namespace["uri"] = "http://www.sat.gob.mx/CartaPorte31"
        namespace["schema_location"] = "http://www.sat.gob.mx/CartaPorte31 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd"
        data["namespaces"].append(namespace)
        data["complements"] = []

        cartaporte = {}
        cartaporte["type"] = "custom"

        cartaporte[
            "data"] = "<cartaporte31:CartaPorte Version=\"3.1\" TranspInternac=\"No\" TotalDistRec=\"{total_distance_km}\" IdCCP=\"{ccp_id}\">".format(
            total_distance_km=str(self.total_distance_km),
            ccp_id="CCC" + self.ccp_id if self.ccp_id else ""
        )
        cartaporte["data"] += "<cartaporte31:Ubicaciones>"
        cartaporte["data"] += "<cartaporte31:Ubicacion TipoUbicacion=\"Origen\" RFCRemitenteDestinatario=\"{sender_rfc}\" FechaHoraSalidaLlegada=\"{departure_at}\">".format(
            sender_rfc=self.operation.origin.rfc,
            departure_at=localtime(self.departure_at).strftime("%Y-%m-%dT%H:%M:%S")
        )
        cartaporte["data"] += "<cartaporte31:Domicilio Calle=\"{street}\" CodigoPostal=\"{zip_code}\" Estado=\"{state}\" NumeroExterior=\"{exterior_number}\" Pais=\"{country}\"/>".format(
            street=self.operation.origin.address.street,
            zip_code=self.operation.origin.address.zip_code,
            state=self.operation.origin.address.state,
            exterior_number=self.operation.origin.address.exterior_number,
            country="MEX"
        )
        cartaporte["data"] += "</cartaporte31:Ubicacion>"
        for delivery in self.operation.deliveries.all():
            cartaporte["data"] += "<cartaporte31:Ubicacion TipoUbicacion=\"Destino\" RFCRemitenteDestinatario=\"{delivery_rfc}\" DistanciaRecorrida=\"{total_distance_km}\" FechaHoraSalidaLlegada=\"{departure_at}\">".format(
                delivery_rfc=delivery.rfc,
                total_distance_km=str(0),
                departure_at=localtime(self.departure_at).strftime("%Y-%m-%dT%H:%M:%S")
            )
            cartaporte["data"] += "<cartaporte31:Domicilio Calle=\"{street}\" CodigoPostal=\"{zip_code}\" Estado=\"{state}\" NumeroExterior=\"{exterior_number}\" Pais=\"{country}\"/>".format(
                street=delivery.address.street,
                zip_code=delivery.address.zip_code,
                state=MEXICAN_STATES_KEY[delivery.address.state],
                exterior_number=delivery.address.exterior_number,
                country="MEX"
            )
            cartaporte["data"] += "</cartaporte31:Ubicacion>"
        cartaporte["data"] += "<cartaporte31:Ubicacion TipoUbicacion=\"Destino\" RFCRemitenteDestinatario=\"{destination_rfc}\" FechaHoraSalidaLlegada=\"{scheduled_arrival_at}\" DistanciaRecorrida=\"{total_distance_km}\">".format(
            destination_rfc=self.operation.destination.rfc,
            scheduled_arrival_at=localtime(self.scheduled_arrival_at).strftime("%Y-%m-%dT%H:%M:%S"),
            total_distance_km=str(self.total_distance_km)
        )
        cartaporte["data"] += "<cartaporte31:Domicilio Calle=\"{street}\" CodigoPostal=\"{zip_code}\"  Estado=\"{state}\" NumeroExterior=\"{exterior_number}\" Pais=\"{country}\"/>".format(
            street=self.operation.destination.address.street,
            zip_code=self.operation.destination.address.zip_code,
            state=self.operation.destination.address.state,
            exterior_number=self.operation.destination.address.exterior_number,
            country="MEX"
        )
        cartaporte["data"] += "</cartaporte31:Ubicacion></cartaporte31:Ubicaciones>"

        cartaporte["data"] += "<cartaporte31:Mercancias PesoBrutoTotal=\"{products_weight}\" UnidadPeso=\"{weight_key}\" NumTotalMercancias=\"{products_amount}\" >".format(
            products_amount=len(self.operation.transported_products.all()),
            products_weight=self.operation.transported_products.aggregate(total=Sum('weight'))['total'],
            weight_key="KGM"
        )
        for product in self.operation.transported_products.all():
            with open('static/json/material_peligroso.json') as file:
                _data = json.load(file)
            if product.transported_product_key in _data:
                product.is_danger = True
            else:
                product.is_danger = False
            product.save()
            if product.is_danger:
                cartaporte["data"] += "<cartaporte31:Mercancia BienesTransp=\"{transported_product_key}\" Cantidad=\"{amount}\" ClaveUnidad=\"{unit_key}\" Descripcion=\"{description}\" PesoEnKg=\"{weight}\" MaterialPeligroso=\"No\" />".format(
                    transported_product_key=product.transported_product_key,
                    amount=product.amount,
                    unit_key=product.unit_key,
                    description=product.description,
                    weight=product.weight,
                )
            else:
                cartaporte["data"] += "<cartaporte31:Mercancia BienesTransp=\"{transported_product_key}\" Cantidad=\"{amount}\" ClaveUnidad=\"{unit_key}\" Descripcion=\"{description}\" PesoEnKg=\"{weight}\" />".format(
                    transported_product_key=product.transported_product_key,
                    amount=product.amount,
                    unit_key=product.unit_key,
                    description=product.description,
                    weight=product.weight,
                )

        cartaporte["data"] += "<cartaporte31:Autotransporte NumPermisoSCT=\"{sct_permit_number}\"  PermSCT=\"{sct_permit_type}\">".format(
            sct_permit_number=self.sct_permit_number,
            sct_permit_type=self.sct_permit_type
        )
        cartaporte["data"] += "<cartaporte31:IdentificacionVehicular AnioModeloVM=\"{year}\" ConfigVehicular=\"{vehicular_config}\" PlacaVM=\"{plate}\" PesoBrutoVehicular=\"500\"/>".format(
            year=self.operation.vehicle.year,
            vehicular_config=self.operation.vehicle.vehicle_config,
            plate=self.operation.vehicle.license_plate
        )
        cartaporte["data"] += "<cartaporte31:Seguros AseguraRespCivil=\"{insurance_company}\" PolizaRespCivil=\"{insurance_company}\"/>".format(
            insurance_company=self.operation.vehicle.insurance_company,
            insurance_code=self.operation.vehicle.insurance_code
        )
        if self.operation.vehicle_box:
            cartaporte["data"] += "<cartaporte31:Remolques>"
            cartaporte["data"] += "<cartaporte31:Remolque SubTipoRem=\"{vehicular_config}\" Placa=\"{plate}\"></cartaporte31:Remolque>".format(
                vehicular_config=self.operation.vehicle_box.vehicle_config,
                plate=self.operation.vehicle_box.license_plate
            )
            cartaporte["data"] += "</cartaporte31:Remolques>"

        cartaporte["data"] += "</cartaporte31:Autotransporte>"
        cartaporte["data"] += "</cartaporte31:Mercancias>"
        cartaporte["data"] += "<cartaporte31:FiguraTransporte>"
        cartaporte["data"] += "<cartaporte31:TiposFigura TipoFigura=\"01\" RFCFigura=\"{driver_rfc}\" NumLicencia=\"{driver_licence}\" NombreFigura=\"{driver_name}\">".format(
            driver_rfc = self.operation.driver.rfc,
            driver_licence = self.operation.driver.license_number,
            driver_name = " ".join([self.operation.driver.name, self.operation.driver.last_name]),
        )
        cartaporte["data"] += "</cartaporte31:TiposFigura>"
        cartaporte["data"] += "</cartaporte31:FiguraTransporte>"
        cartaporte["data"] += "</cartaporte31:CartaPorte>"
        data["complements"].append(cartaporte)

        data["pdf_custom_section"] = self.custom_cartaporte_data()

        return data

    def custom_cartaporte_data(self):
        context = {}
        context['Cartaporte'] = {}
        context['Cartaporte']['Origen'] = {}
        context['Cartaporte']['Destino'] = {}
        context['Cartaporte']['idccp'] = "CCC" + self.ccp_id if self.ccp_id else ""
        context['Cartaporte']['TotalDistRec'] = self.operation.route.optimized_distance
        context['Cartaporte']['Origen']['FechaHoraSalida'] = localtime(self.departure_at).strftime("%Y-%m-%dT%H:%M:%S")
        context['Cartaporte']['Origen']['NombreRemitente'] = self.operation.origin.name
        context['Cartaporte']['Origen']['RFCRemitente'] = self.operation.origin.rfc
        context['Cartaporte']['Origen']['Calle'] = self.operation.origin.address.street
        context['Cartaporte']['Origen']['CodigoPostal'] = self.operation.origin.address.zip_code
        context['Cartaporte']['Origen']['Colonia'] = self.operation.origin.address.colony
        context['Cartaporte']['Origen']['Estado'] = self.operation.origin.address.state
        context['Cartaporte']['Origen']['Municipio'] = ""
        context['Cartaporte']['Origen']['Localidad'] = self.operation.origin.address.city
        context['Cartaporte']['Origen']['NumeroExterior'] = self.operation.origin.address.exterior_number
        context['Cartaporte']['Origen']['Pais'] = "MEX"
        context['Cartaporte']['MiddlePoint'] = []
        for delivery in self.operation.deliveries.all():
            point_element = {}
            point_element['NombreRemitente'] = delivery.name
            point_element['RFCDestinatario'] = delivery.rfc
            point_element['Calle'] = delivery.address.street
            point_element['CodigoPostal'] = delivery.address.zip_code
            point_element['Colonia'] = delivery.address.colony
            point_element['Estado'] = delivery.address.state
            point_element['Municipio'] = ""
            point_element['Localidad'] = delivery.address.city
            point_element['NumeroExterior'] = delivery.address.exterior_number
            point_element['Pais'] = "MEX"
            context['Cartaporte']['MiddlePoint'].append(point_element)
        context['Cartaporte']['Destino']['FechaHoraSalida'] = localtime(self.scheduled_arrival_at).strftime("%Y-%m-%dT%H:%M:%S")
        context['Cartaporte']['Destino']['NombreRemitente'] = self.operation.destination.name
        context['Cartaporte']['Destino']['RFCDestinatario'] = self.operation.destination.rfc
        context['Cartaporte']['Destino']['Calle'] = self.operation.destination.address.street
        context['Cartaporte']['Destino']['CodigoPostal'] = self.operation.destination.address.zip_code
        context['Cartaporte']['Destino']['Colonia'] = self.operation.destination.address.colony
        context['Cartaporte']['Destino']['Estado'] = self.operation.destination.address.state
        context['Cartaporte']['Destino']['Municipio'] = ""
        context['Cartaporte']['Destino']['Localidad'] = self.operation.destination.address.city
        context['Cartaporte']['Destino']['NumeroExterior'] = self.operation.destination.address.exterior_number
        context['Cartaporte']['Destino']['Pais'] = "MEX"
        context['Cartaporte']['Products'] = []
        for product in self.operation.transported_products.all():
            product_element = {}
            product_element['Cantidad'] = product.amount
            product_element['ClaveUnidad'] = product.unit_key
            product_element['BienesTransp'] = product.transported_product_key
            product_element['Descripcion'] = product.description
            product_element['Moneda'] = product.currency
            product_element['PesoEnKg'] = product.weight
            context['Cartaporte']['Products'].append(product_element)
        context['Cartaporte']['NumPermisoSCT'] = self.sct_permit_number
        context['Cartaporte']['PermSCT'] = self.sct_permit_type
        context['Cartaporte']['NombreAseg'] = self.insurer_name
        context['Cartaporte']['NumPolizaSeguro'] = self.insurance_policy_number
        context['Cartaporte']['AnioModeloVM'] = self.operation.vehicle.year
        context['Cartaporte']['ConfigVehicular'] = self.operation.vehicle.vehicle_config
        context['Cartaporte']['PlacaVM'] = self.operation.vehicle.license_plate
        context['Cartaporte']['Unidad'] = self.operation.vehicle.econ_number
        if self.operation.vehicle_box != None:
            context['Cartaporte']['Caja'] = self.operation.vehicle_box.econ_number
            context['Cartaporte']['PlacaCaja'] = self.operation.vehicle_box.license_plate
        context['Cartaporte']['NumLicencia'] = self.operation.driver.license_number
        context['Cartaporte']['NombreOperador'] = str(self.operation.driver.name) + " " + str(self.operation.driver.last_name)
        context['Cartaporte']['RFCOperador'] = self.operation.driver.rfc
        context['Cartaporte']['OperadorDirection'] = {}
        context['Cartaporte']['OperadorDirection']['Calle'] = ""  # cartaporte.operation.operator.employee.street_and_number
        context['Cartaporte']['OperadorDirection']['CodigoPostal'] = ""  # cartaporte.operation.operator.employee.cp
        context['Cartaporte']['OperadorDirection']['Colonia'] = ""  # cartaporte.operation.operator.employee.colony
        context['Cartaporte']['OperadorDirection']['Estado'] = ""  # cartaporte.operation.operator.employee.state
        context['Cartaporte']['OperadorDirection']['Localidad'] = ""  # cartaporte.operation.operator.employee.city
        context['Cartaporte']['OperadorDirection']['Municipio'] = ""  # cartaporte.operation.operator.employee.municipy
        context['Cartaporte']['OperadorDirection']['NumeroExterior'] = ""  # "S/N"
        context['Cartaporte']['OperadorDirection']['Pais'] = ""  # "MEX"
        context['Cartaporte']['ControlVehicular'] = self.operation.folio

        if self.operation.shipment_type == ShipmentType.ASTURIANO:
            context['is_asturiano'] = True
            context['asturiano_links'] = []
            for tienda in self.operation.deliveries.all():
                link = {}
                link["name"] = tienda.name
                context['asturiano_links'].append(link)
        if self.operation.shipment_type == ShipmentType.THREE_B:
            context['is_3b'] = True
            context['3b_links'] = []
            for tienda in self.operation.deliveries.all():
                link = {}
                link["name"] = tienda.name
                context['3b_links'].append(link)

        #pdf_custom_section = render_to_string('operations_panel/cartaporte/cartaporte.html', context=context)
        return context