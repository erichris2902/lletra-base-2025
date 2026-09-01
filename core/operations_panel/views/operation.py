import csv
import io
import json
from collections import defaultdict

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from core.operations_panel.choices import AsturianoPacking
from core.operations_panel.forms.address import AddressForm
from core.operations_panel.forms.cargo import AssignCargoToOperationForm
from core.operations_panel.forms.delivery_location import DeliveryLocationForm
from core.operations_panel.forms.distribution_packing import DistributionPackingForm, DistributionPacking2Form
from core.operations_panel.forms.operation import OperationForm, OperationFolioWebsiteForm, OperationApprovalForm, \
    OperationFolioForm, OperationShipmentForm, OperationRouteForm
from core.operations_panel.forms.route import RouteShipmentForm, RouteForm
from core.operations_panel.forms.transported_product import TransportedProductsFormByCSV, \
    OperationTransportedProductForm, TransportedProductForm
from core.operations_panel.models import Cargo, DeliveryLocation
from core.operations_panel.models.address import Address
from core.operations_panel.models.distribution_packing import DistributionPacking
from core.operations_panel.models.operation import Operation
from core.operations_panel.models.route import Route
from core.operations_panel.models.transported_product import TransportedProduct, OperationTransportedProduct
from core.system.views import AdminListView
from django.http import HttpResponse, Http404


class OperationListView(AdminListView):
    model = Operation
    form = OperationForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Fecha", "Control vehicular",  "Cliente", "Packing", "Lista para fac", "Facturado"]
    datatable_keys = ["operation_date", "folio", "client", "is_packing_ready", "is_ready_to_invoice", "is_invoice_ready"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Operaciones'
    category = 'Operaciones'
    dropdown_action_path = 'operations_panel/operation/table/actions.js'
    static_path = 'operations_panel/operation/table/base.html'
    search_fields = ['folio', 'client', 'operation_date']


    def handle_searchdata(self, request, data):
        # DataTables manda esto
        draw = int(request.POST.get("draw", 1))
        start = int(request.POST.get("start", 0))
        length = int(request.POST.get("length", 50))
        search = (request.POST.get("search", "") or "").strip()

        # 1) queryset base
        qs = self.get_queryset()
        records_total = qs.count()

        # 2) filtro por búsqueda
        if search:
            search_fields = getattr(self, "search_fields", self.search_fields)
            search_fields = self._safe_search_fields(search_fields)

            q_obj = Q()
            for field in search_fields:
                q_obj |= Q(**{f"{field}__icontains": search})
            qs = qs.filter(q_obj)

        records_filtered = qs.count()

        # 3) orden (opcional, pero recomendado)
        order_col = request.POST.get("order_col")
        order_dir = request.POST.get("order_dir", "asc")
        if order_col is not None and order_col != "":
            try:
                col_idx = int(order_col)
                col_key = self.datatable_keys[col_idx]  # ej: "name"

                # si es columna virtual, se anota
                if col_key in self.virtual_search:
                    qs = qs.annotate(**{col_key: self.virtual_search[col_key]})
                    order_field = col_key
                else:
                    order_field = self.datatable_keys[col_idx]

                if order_dir == "desc":
                    order_field = f"-{order_field}"

                qs = qs.order_by(order_field)
            except (ValueError, IndexError):
                pass

        # 4) paginación
        qs_page = qs[start:start + length]

        # 5) data
        data = [obj.to_operations_general_view(keys=self.datatable_keys) for obj in qs_page]

        return {
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": data
        }

    def handle_release(self, request, data):
        pass

    def get_queryset(self):
        return self.model.objects.exclude(Q(folio__isnull=True) | Q(folio="")).prefetch_related("client", "driver",
                                                                                                "vehicle", "route",
                                                                                                "shipment_invoice",
                                                                                                "transported_products").all()


class FolioOperationListView(AdminListView):
    model = Operation
    form = OperationFolioWebsiteForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Control vehicular", "Fecha", "Cliente", "Ruta", "Repartos",
                         "Unidad", "Proveedor", "Status"]
    datatable_keys = ["folio", "operation_date", "client", "route", "deliveries",
                      "vehicle", "supplier", "status"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Folios'
    category = 'Operaciones'
    ordering = 'desc'
    static_path = 'operations_panel/folio/table/base.html'

    search_fields = ['folio', 'client', 'route', 'operation_date', 'vehicle', 'driver', 'status', 'raw_payload']

    def handle_approve(self):
        data = {}
        instance = self.model.objects.get(pk=self.request.POST.get('id'))
        form = OperationApprovalForm(self.request.POST, instance=instance)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Operación aprobada con pre-folio: {instance.pre_folio}"
        else:
            data['error'] = form.errors
        return data

    def handle_assign_folio(self):
        data = {}
        instance = self.model.objects.get(pk=self.request.POST.get('id'))
        form = OperationFolioForm(self.request.POST, instance=instance)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Folio asignado: {instance.folio}"
        else:
            data['error'] = form.errors
        return data

    def handle_generate_invoice(self):
        data = {}
        try:
            instance = self.model.objects.get(pk=self.request.POST.get('id'))
            if not instance.folio:
                data['error'] = "No se puede generar factura sin un folio asignado"
                return True

            invoice = instance.generate_invoice(self.request.user)
            data['success'] = True
            data['message'] = f"Factura generada correctamente"
        except Exception as e:
            print(e)
            data['error'] = str(e)
        return data

    def handle_upload_to_drive(self):
        data = {}
        try:
            instance = self.model.objects.get(pk=self.request.POST.get('id'))
            if not instance.invoice:
                data['error'] = "No se puede subir a Drive sin una factura generada"
                return True

            file = instance.upload_invoice_to_drive(self.request.user)
            data['success'] = True
            data['message'] = f"Factura subida a Google Drive correctamente"
        except Exception as e:
            print(e)
            data['error'] = str(e)
        return data

    def handle_searchdata(self, request, data):
        # DataTables manda esto
        draw = int(request.POST.get("draw", 1))
        start = int(request.POST.get("start", 0))
        length = int(request.POST.get("length", 50))
        search = (request.POST.get("search", "") or "").strip()

        # 1) queryset base
        qs = self.get_queryset()
        records_total = qs.count()

        # 2) filtro por búsqueda
        if search:
            search_fields = getattr(self, "search_fields", self.search_fields)
            search_fields = self._safe_search_fields(search_fields)

            q_obj = Q()
            for field in search_fields:
                q_obj |= Q(**{f"{field}__icontains": search})
            qs = qs.filter(q_obj)

        records_filtered = qs.count()

        # 3) orden (opcional, pero recomendado)
        order_col = request.POST.get("order_col")
        order_dir = request.POST.get("order_dir", "asc")
        if order_col is not None and order_col != "":
            try:
                col_idx = int(order_col)
                col_key = self.datatable_keys[col_idx]  # ej: "name"

                # si es columna virtual, se anota
                if col_key in self.virtual_search:
                    qs = qs.annotate(**{col_key: self.virtual_search[col_key]})
                    order_field = col_key
                else:
                    order_field = self.datatable_keys[col_idx]

                if order_dir == "desc":
                    order_field = f"-{order_field}"

                qs = qs.order_by(order_field)
            except (ValueError, IndexError):
                pass

        # 4) paginación
        qs_page = qs[start:start + length]

        # 5) data
        data = [obj.to_folios_view(keys=self.datatable_keys) for obj in qs_page]

        return {
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": data
        }

    def handle_get_shipment(self, request, data):
        obj_id = request.POST.get('id')
        if obj_id == '-1':
            instance = self.model()
            self.form_action = "Add"
        else:
            instance = get_object_or_404(self.model, pk=obj_id)
            self.form_action = "update_shipment"
        data['id'] = str(instance.id)
        data['form'] = self.render_form(request, instance, form=OperationShipmentForm)
        return data

    def handle_update_shipment(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        form = OperationShipmentForm(request.POST, instance=operation)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Operacion actualizada exitosamente"

    def get_queryset(self):
        return self.model.objects.prefetch_related("client", "driver",
                                                   "vehicle", "route",
                                                   "route__route_stops",
                                                   "route__initial_location",
                                                   "route__destination_location").all()


class ShipmentOperationListView(AdminListView):
    search_fields = ['folio', 'client', 'route', 'operation_date', 'vehicle', 'driver', 'status', 'raw_payload']
    model = Operation
    form = OperationShipmentForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = [
        "Control vehicular",
        "Cliente",
        "Unidad",
        "Origen",
        "Repartos",
        "Destino",
        "Ruta asignada",
        "Productos",
        "Kms",
        "Lista para Facturacion?",
        "Packing",
    ]
    datatable_keys = [
        "folio",
        "client",
        "vehicle",
        "origin",
        "deliveries",
        "destination",
        "assigned_route",
        "products_amount",
        "distance",
        "is_ready_to_invoice",
        "is_packing_ready",
    ]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Operaciones'
    category = 'Embarques'
    dropdown_action_path = 'operations_panel/shipment/table/actions.js'
    static_path = 'operations_panel/shipment/table/base.html'
    catalogs = [
        {
            'id': 'id_transported_product_key',
            'service': 'ProductAndServiceCatalog',
            'placeholder': '',
        },
        {
            'id': 'id_unit_key',
            'service': 'UnitSat',
            'placeholder': '',
        },
    ]

    def parse_packing_data(self, querydict):
        data = defaultdict(dict)

        for key, value in querydict.items():
            if '-' in key:
                # Separa el campo como la última parte después del último guion
                parts = key.rsplit('-', 1)
                if len(parts) != 2:
                    continue
                uid, field = parts
                data[uid][field] = value

        return data

    def handle_searchdata(self, request, data):
        # DataTables manda esto
        draw = int(request.POST.get("draw", 1))
        start = int(request.POST.get("start", 0))
        length = int(request.POST.get("length", 50))
        search = (request.POST.get("search", "") or "").strip()

        # 1) queryset base
        qs = self.get_queryset()
        records_total = qs.count()

        # 2) filtro por búsqueda
        if search:
            search_fields = getattr(self, "search_fields", self.search_fields)
            search_fields = self._safe_search_fields(search_fields)

            q_obj = Q()
            for field in search_fields:
                q_obj |= Q(**{f"{field}__icontains": search})
            qs = qs.filter(q_obj)

        records_filtered = qs.count()

        # 3) orden (opcional, pero recomendado)
        order_col = request.POST.get("order_col")
        order_dir = request.POST.get("order_dir", "asc")
        if order_col is not None and order_col != "":
            try:
                col_idx = int(order_col)
                col_key = self.datatable_keys[col_idx]  # ej: "name"

                # si es columna virtual, se anota
                if col_key in self.virtual_search:
                    qs = qs.annotate(**{col_key: self.virtual_search[col_key]})
                    order_field = col_key
                else:
                    order_field = self.datatable_keys[col_idx]

                if order_dir == "desc":
                    order_field = f"-{order_field}"

                qs = qs.order_by(order_field)
            except (ValueError, IndexError):
                pass

        # 4) paginación
        qs_page = qs[start:start + length]
        print(qs_page)
        for obj in qs_page:
            print(obj)
            if obj.notes == '' or obj.notes is None:
                if obj.raw_payload:
                    print(obj.raw_payload)
                    obj.notes = ''
                    obj.notes += 'FECHA: ' + obj.raw_payload.get('fecha', '') + '\n'
                    obj.notes += 'CLIENTE: ' + obj.raw_payload.get('cliente', '') + '\n'
                    obj.notes += 'ORIGEN: ' + obj.raw_payload.get('origen', '') + '\n'
                    obj.notes += 'DESTINO: ' + obj.raw_payload.get('destino', '') + '\n'
                    obj.notes += 'REPARTOS: ' + str(obj.raw_payload.get('repartos', '')) + '\n'
                    obj.notes += 'PLACAS: ' + obj.raw_payload.get('placas', '') + '\n'
                    obj.notes += 'UNIDAD: ' + obj.raw_payload.get('unidad', '') + '\n'
                    obj.notes += 'OPERADOR: ' + obj.raw_payload.get('operador', '') + '\n'
                    obj.notes += 'PROVEEDOR: ' + obj.raw_payload.get('proveedor', '') + '\n'
                    print("save")
                    obj.save()
        # for obj in qs_page:
        #     print(obj)
        #     if obj.notes == '' or obj.notes is None:
        #         obj.notes = ''
        #         if obj.raw_payload:
        # 5) data
        data = [obj.to_operations_view(keys=self.datatable_keys) for obj in qs_page]

        return {
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": data
        }

    def handle_get_route(self, request, data):
        operation = self.model.objects.get(pk=request.POST.get('id'))
        self.model = Route
        self.form = RouteShipmentForm
        self.form_action = "update_route"

        data['id'] = str(operation.route.id)
        data['form'] = self.render_form(request, operation.route)

    def handle_get_origin(self, request, data):
        operation = self.model.objects.get(pk=request.POST.get('id'))
        origin = operation.route.initial_location.address
        self.model = Address
        self.form = AddressForm
        self.form_action = "update_origin"

        data['id'] = str(origin.id)
        data['form'] = self.render_form(request, origin)

    def handle_get_destiny(self, request, data):
        operation = self.model.objects.get(pk=request.POST.get('id'))
        destiny = operation.route.destination_location.address
        self.model = Address
        self.form = AddressForm
        self.form_action = "update_destiny"

        data['id'] = str(destiny.id)
        data['form'] = self.render_form(request, destiny)

    def handle_get_stops(self, request, data):
        operation = self.model.objects.get(pk=request.POST.get('id'))
        route = operation.route
        self.model = Route
        self.form = RouteForm
        self.form_action = "update_stops"

        data['id'] = str(route.id)
        data['form'] = self.render_form(request, route)

    def handle_get_sacos_cajas(self, request, data):
        context = {}
        operation = Operation.objects.get(pk=request.POST.get('id'))
        if operation.folio.endswith("B"):
            raise Exception("No se puede distribuir el packing de un viaje derivado, solo el viaje original.")
        if not Operation.objects.filter(folio=operation.folio + "B").exists() or operation.folio.endswith("B"):
            distribution_packings = DistributionPacking.objects.filter(operation=operation)
            for distribution_packing in distribution_packings:
                distribution_packing.delete()
            for delivery in operation.route.route_stops.all():
                packing, _ = DistributionPacking.objects.get_or_create(
                    operation=operation,
                    delivery_shop=delivery,
                    defaults={
                        "distribution": AsturianoPacking.CVZ_AB,
                        "weight": 300,
                        "amount": 1,
                    }
                )
        distribution_packings = DistributionPacking.objects.filter(operation=operation)
        self.form = DistributionPacking2Form
        self.form_action = "update_packing2"
        data['id'] = str(operation.id)
        data['form'] = self.render_formset(request, distribution_packings, DistributionPacking2Form)

    def handle_get_route_select(self, request, data):
        operation = self.model.objects.get(pk=request.POST.get('id'))
        self.model = Operation
        self.form = OperationRouteForm
        self.form_action = "update_route_select"

        data['id'] = str(operation.id)
        data['form'] = self.render_form(request, operation)

    def handle_update_route(self, request, data):
        route = Route.objects.get(pk=request.POST.get('id'))
        form = RouteShipmentForm(request.POST, instance=route)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Ruta actualizada exitosamente"

    def handle_update_stops(self, request, data):
        route = Route.objects.get(pk=request.POST.get('id'))
        form = RouteForm(request.POST, instance=route)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Ruta actualizada exitosamente"

    def handle_update_origin(self, request, data):
        route = Address.objects.get(pk=request.POST.get('id'))
        form = AddressForm(request.POST, instance=route)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Direccion de origen actualizada exitosamente"

    def handle_update_destiny(self, request, data):
        route = Address.objects.get(pk=request.POST.get('id'))
        form = AddressForm(request.POST, instance=route)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Direccion de destino actualizada exitosamente"

    def handle_update_route_select(self, request, data):
        operation = self.model.objects.get(pk=request.POST.get('id'))
        form = OperationRouteForm(request.POST, instance=operation)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Ruta actualizada exitosamente"

    def handle_get_cargo(self, request, data):
        context = {}
        operation = self.model.objects.get(pk=request.POST.get('id'))
        self.form = TransportedProductsFormByCSV
        self.form_action = "update_cargo"
        data['id'] = str(operation.id)
        self.form_path = 'operations_panel/shipment/cargo_form.html'
        products = operation.transported_products.all()
        products_data = {
            'products': [],
        }
        for product in products:
            products_data['products'].append(json.loads(product.to_json()))
        data['form'] = self.render_others_form(request, operation, TransportedProductsFormByCSV(), "update_cargo",
                                               products_data)

    def handle_update_packing(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        querydict = request.POST  # o el QueryDict que compartiste
        parsed = self.parse_packing_data(querydict)
        for key, value in parsed.items():
            dp = DistributionPacking.objects.get(operation=operation, pk=key)
            dp.weight = value['weight']
            dp.amount = value['amount']
            dp.distribution = value['distribution']
            dp.save()
        all_packings = DistributionPacking.objects.filter(operation=operation)
        has_cvz_ab = all_packings.filter(distribution=AsturianoPacking.CVZ_AB).exists()
        if not has_cvz_ab:
            raise Exception("No se puede distribuir el packing si solo se entrega un tipo de producto")
        # 2.1 Crear una copia de la operación
        if Operation.objects.filter(folio=operation.folio + "B").exists():
            pass
        else:
            operation.pk = None  # Esto duplica la instancia
            operation.folio = operation.folio + "B"  # Debes implementar esta función
            operation.save()
        cvz_operation = operation
        ab_operation = Operation.objects.get(pk=request.POST.get('id'))
        # 3. Reasignar DistributionPacking y TransportedProduct
        for dp in all_packings:
            if dp.distribution == AsturianoPacking.CVZ:
                dp.operation = operation  # Se pasa a la nueva operación
                dp.save()
            elif dp.distribution == AsturianoPacking.AB:
                # Se queda en la original
                continue
            elif dp.distribution == AsturianoPacking.CVZ_AB:
                dp.operation = ab_operation
                dp.distribution = AsturianoPacking.AB
                dp.save()
                dp.pk = None
                dp.operation = cvz_operation
                dp.distribution = AsturianoPacking.CVZ
                dp.save()
                continue
        ab_operation = Operation.objects.get(pk=request.POST.get('id'))
        cvz_operation = Operation.objects.get(folio=ab_operation.folio + "B")
        ab_packings = DistributionPacking.objects.filter(operation=ab_operation)
        ab_operation.transported_products.clear()
        for packing in ab_packings:
            abarrote_product = TransportedProduct.objects.filter(description="ABARROTES_BASE").first()
            abarrote_product.pk = None
            abarrote_product.weight = packing.weight
            abarrote_product.amount = packing.amount
            abarrote_product.save()
            ab_operation.transported_products.add(abarrote_product)
            ab_operation.save()
        cvz_packings = DistributionPacking.objects.filter(operation=cvz_operation)
        cvz_operation.transported_products.clear()
        for packing in cvz_packings:
            cerveza_product = TransportedProduct.objects.filter(description="CERVEZA_BASE").first()
            cerveza_product.pk = None
            cerveza_product.description = "CERVEZA"
            cerveza_product.weight = packing.weight
            cerveza_product.amount = packing.amount
            cerveza_product.save()
            cvz_operation.transported_products.add(cerveza_product)
            cvz_operation.save()


    def handle_update_packing2(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        querydict = request.POST  # o el QueryDict que compartiste
        parsed = self.parse_packing_data(querydict)
        for key, value in parsed.items():
            dp = DistributionPacking.objects.get(operation=operation, pk=key)
            dp.cajas_ab = value['cajas_ab']
            dp.bolsas_ab = value['bolsas_ab']
            dp.weight_ab = value['weight_ab']
            dp.cajas_cvz = value['cajas_cvz']
            dp.bolsas_cvz = value['bolsas_cvz']
            dp.weight_cvz = value['weight_cvz']
            dp.save()
        all_packings = DistributionPacking.objects.filter(operation=operation)
        #Veruificar que ambos tengan peso

        create_b = False
        for dp in all_packings:
            # if dp.distribution == AsturianoPacking.CVZ:
            if dp.weight_ab > 0 and dp.weight_cvz > 0:
                create_b = True

        # 2.1 Crear una copia de la operación
        if Operation.objects.filter(folio=operation.folio + "B").exists():
            pass
        else:
            if create_b:
                operation.pk = None  # Esto duplica la instancia
                operation.folio = operation.folio + "B"  # Debes implementar esta función
                operation.save()

        cvz_operation = operation
        ab_operation = Operation.objects.get(pk=request.POST.get('id'))

        # 3. Reasignar DistributionPacking y TransportedProduct
        for dp in all_packings:
            #if dp.distribution == AsturianoPacking.CVZ:
            if dp.weight_ab == 0  and dp.weight_cvz > 0:
                dp.distribution = AsturianoPacking.CVZ
                dp.operation = operation  # Se pasa a la nueva operación
                dp.save()
            #elif dp.distribution == AsturianoPacking.AB:
            elif dp.weight_ab > 0 and dp.weight_cvz == 0:
                # Se queda en la original
                dp.distribution = AsturianoPacking.AB
                dp.save()
                continue
            elif dp.weight_ab > 0 and dp.weight_cvz > 0:
                dp.operation = ab_operation
                dp.distribution = AsturianoPacking.AB
                dp.save()
                dp.pk = None
                dp.operation = cvz_operation
                dp.distribution = AsturianoPacking.CVZ
                dp.save()
                continue
        ab_operation = Operation.objects.get(pk=request.POST.get('id'))
        cvz_operation = Operation.objects.get(folio=ab_operation.folio + "B")
        ab_packings = DistributionPacking.objects.filter(operation=ab_operation)
        ab_operation.transported_products.clear()
        for packing in ab_packings:
            if packing.cajas_ab > 0:
                abarrote_product_caja = TransportedProduct.objects.filter(description="ABARROTE (CAJA)").first()
                abarrote_product_caja.pk = None
                abarrote_product_caja.weight = packing.weight_ab
                abarrote_product_caja.amount = packing.cajas_ab
                abarrote_product_caja.save()
                ab_operation.transported_products.add(abarrote_product_caja)
                ab_operation.save()
            if packing.bolsas_ab > 0:
                abarrote_product_bolsa = TransportedProduct.objects.filter(description="ABARROTE (BULTO)").first()
                abarrote_product_bolsa.pk = None
                abarrote_product_bolsa.weight = packing.weight_ab
                abarrote_product_bolsa.amount = packing.bolsas_ab
                abarrote_product_bolsa.save()
                ab_operation.transported_products.add(abarrote_product_bolsa)
                ab_operation.save()
        cvz_packings = DistributionPacking.objects.filter(operation=cvz_operation)
        cvz_operation.transported_products.clear()
        for packing in cvz_packings:
            if packing.cajas_cvz > 0:
                abarrote_product_caja = TransportedProduct.objects.filter(description="CERVEZA (CAJA)").first()
                abarrote_product_caja.pk = None
                abarrote_product_caja.weight = packing.weight_ab
                abarrote_product_caja.amount = packing.cajas_ab
                abarrote_product_caja.save()
                cvz_operation.transported_products.add(abarrote_product_caja)
                cvz_operation.save()
            if packing.bolsas_cvz > 0:
                abarrote_product_bolsa = TransportedProduct.objects.filter(description="CERVEZA (BULTO)").first()
                abarrote_product_bolsa.pk = None
                abarrote_product_bolsa.weight = packing.weight_ab
                abarrote_product_bolsa.amount = packing.bolsas_ab
                abarrote_product_bolsa.save()
                cvz_operation.transported_products.add(abarrote_product_bolsa)
                cvz_operation.save()

    def handle_get_packing(self, request, data):
        context = {}
        operation = Operation.objects.get(pk=request.POST.get('id'))
        if operation.folio.endswith("B"):
            raise Exception("No se puede distribuir el packing de un viaje derivado, solo el viaje original.")
        if not Operation.objects.filter(folio=operation.folio + "B").exists() or operation.folio.endswith("B"):
            distribution_packings = DistributionPacking.objects.filter(operation=operation)
            for distribution_packing in distribution_packings:
                distribution_packing.delete()
            for delivery in operation.route.route_stops.all():
                packing, _ = DistributionPacking.objects.get_or_create(
                    operation=operation,
                    delivery_shop=delivery,
                    defaults={
                        "distribution": AsturianoPacking.CVZ_AB,
                        "weight": 300,
                        "amount": 1,
                    }
                )
        distribution_packings = DistributionPacking.objects.filter(operation=operation)
        self.form = DistributionPackingForm
        self.form_action = "update_packing"
        data['id'] = str(operation.id)
        data['form'] = self.render_formset(request, distribution_packings, DistributionPackingForm)

    def handle_update_cargo(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        uploaded_file = request.FILES.get("csv_products")
        # Decodifica el archivo como texto
        file_data = uploaded_file.read().decode('utf-8')
        csv_file = io.StringIO(file_data)

        # Lee el contenido CSV
        reader = csv.DictReader(csv_file)
        created = 0
        with transaction.atomic():
            operation.transported_products.clear()
            for row in reader:
                product = TransportedProduct.objects.create(
                    transported_product_key=row['BIENES TRANSPORTADOS'].strip(),
                    description=row['DESCRIPCION DEL BIEN'].strip(),
                    amount=int(row['CANTIDAD'].strip()),
                    unit_key=row['CLAVE SAT'].strip(),
                    currency=row.get('MONEDA', 'MXN').strip(),
                    weight=float(row['PESO EN KG'].strip()),
                )
                with open('static/json/material_peligroso.json') as file:
                    data = json.load(file)
                if product.transported_product_key in data:
                    product.is_danger = True
                else:
                    product.is_danger = False
                product.save()
                # Enlaza a la operación (asumiendo que recibiste `operation_id` o similar)
                operation.transported_products.add(product)
                created += 1

    def handle_confirm(self, request, data):
        instance = self.model.objects.get(pk=request.POST.get('id'))
        instance.is_packing_ready = True
        instance.save()

    def handle_approve(self, request, data):
        instance = self.model.objects.get(pk=request.POST.get('id'))
        form = OperationApprovalForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Operación aprobada con pre-folio: {instance.pre_folio}"
        else:
            data['error'] = form.errors

    def handle_assign_folio(self, request, data):
        instance = self.model.objects.get(pk=request.POST.get('id'))
        form = OperationFolioForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save()
            data['success'] = True
            data['message'] = f"Folio asignado: {instance.folio}"
        else:
            data['error'] = form.errors

    def handle_auto_invoice(self, request, data):
        try:


            instance = self.model.objects.get(pk=request.POST.get('id'))

            if instance.shipment_invoice:
                raise Exception("Ya existe una factura para esta operacion")

            invoice = instance.generate_invoice(request.user)
            data['success'] = True
            data['message'] = f"Factura generada correctamente"
        except Exception as e:
            print(e)
            data['error'] = str(e)

    def handle_upload_to_drive(self, request, data):
        try:
            instance = self.model.objects.get(pk=request.POST.get('id'))
            if not instance.invoice:
                data['error'] = "No se puede subir a Drive sin una factura generada"
                return True

            file = instance.upload_invoice_to_drive(request.user)
            data['success'] = True
            data['message'] = f"Factura subida a Google Drive correctamente"
        except Exception as e:
            print(e)
            data['error'] = str(e)

    def get_queryset(self):
        # Puedes adaptar esto si usas SoftDeleteModel
        return self.model.objects.exclude(Q(folio__isnull=True) | Q(folio="")).all().prefetch_related(
            "route__initial_location__address",
            "route__destination_location__address",
            "route__destination_location",
            "route__initial_location",
            "route__route_stops",
            "route",
            "transported_products",
            "shipment_invoice",
            "client",
            "driver",
            "vehicle",
            )

    def handle_assign_cargo(self, request, data):
        operation_id = request.POST.get("operation_id")
        cargo_id = request.POST.get("cargo_id")

        operation = get_object_or_404(Operation, pk=operation_id)
        cargo = get_object_or_404(Cargo, pk=cargo_id)

        for product in cargo.products.all():
            OperationTransportedProduct.objects.create(
                operation=operation,
                transported_product=product,
                weight=product.weight,
                amount=product.amount
            )

        data["success"] = True
        data["message"] = f"Productos de la carga '{cargo.identifier}' asignados a {operation.identifier}"
        return data

    def handle_duplicate(self, request, data):
        operation_a = Operation.objects.get(pk=request.POST.get('id'))
        if Operation.objects.filter(folio=operation_a.folio + "B").exists():
            pass
        else:
            operation_a.pk = None  # Esto duplica la instancia
            operation_a.folio = operation_a.folio + "B"  # Debes implementar esta función
            operation_a.save()
        operation_b = Operation.objects.get(pk=request.POST.get('id'))

        for transported_product in operation_b.transported_products.all():
            transported_product.pk = None  # Esto duplica la instancia
            transported_product.save()
            operation_a.transported_products.add(transported_product)

        return
        operation_id = request.POST.get("operation_id")
        cargo_id = request.POST.get("cargo_id")

        operation = get_object_or_404(Operation, pk=operation_id)
        cargo = get_object_or_404(Cargo, pk=cargo_id)

        for product in cargo.products.all():
            OperationTransportedProduct.objects.create(
                operation=operation,
                transported_product=product,
                weight=product.weight,
                amount=product.amount
            )

        data["success"] = True
        data["message"] = f"Productos de la carga '{cargo.identifier}' asignados a {operation.identifier}"
        return data

    def handle_assignproducts(self, request, data):
        operation_id = request.POST["id"]
        product_id = request.POST["transported_product"]
        weight = request.POST["weight"]
        amount = request.POST["amount"]
        operation = get_object_or_404(Operation, pk=operation_id)
        product = TransportedProduct.objects.get(id=product_id)

        product.id = None
        product.weight = weight
        product.amount = amount
        product.save()
        operation.transported_products.add(product)
        operation.save()

        data["success"] = True
        data["message"] = f"Un productos asignados a {operation.folio}, "
        return data

    def handle_get_assign_cargo_form(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        data['id'] = str(operation.id)
        data["form"] = self.render_others_form(request, operation, AssignCargoToOperationForm(), "AssignCargo",
                                               data=data)
        return data

    def handle_get_assign_products_form(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        self.form_path = 'operations_panel/shipment/transported_product_form.html'
        data['id'] = str(operation.id)
        data['products'] = []
        for product in operation.transported_products.all():
            data['products'].append(json.loads(product.to_json()))
        data["form"] = self.render_others_form(request, operation, OperationTransportedProductForm(), "AssignProducts",
                                               data=data)
        return data

    def handle_get_assign_products_form_old(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        self.form_action = "AssignProductOld"
        data['id'] = str(operation.id)
        self.form = TransportedProductForm
        data["form"] = self.render_old_form(request, operation, TransportedProductForm)
        return data

    def handle_assignproductold(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        print(operation)
        self.form = TransportedProductForm
        instance, errors = self.save_form(request)
        if instance:
            operation.transported_products.add(instance)
            operation.save()
            data['success'] = True
            data['id'] = str(instance.id)
        else:
            data['error'] = str(errors)
        return data

        raise Exception("No se puede asignar productos")
        return data

    def render_old_form(self, request, instance, form=None):
        form_instance = self.form()
        context = {
            'form': form_instance,
            'form_action': self.form_action,
            'form_type': self.form_type,
            'id': instance.id if instance else None,
            'add_form_layout': getattr(form_instance, 'layout', []),
            'add_form_fields': {name: form_instance[name] for name in form_instance.fields},
        }
        html = render(request, self.form_path, context)
        return html.content.decode("utf-8")

    def handle_delete_product(self, request, data):
        transported_product = TransportedProduct.objects.get(pk=request.POST.get('product_id'))
        transported_product.delete()
        return data


