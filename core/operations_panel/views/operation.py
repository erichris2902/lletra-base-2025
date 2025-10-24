import csv
import io
import json
from collections import defaultdict

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from core.operations_panel.choices import AsturianoPacking
from core.operations_panel.forms.cargo import AssignCargoToOperationForm
from core.operations_panel.forms.distribution_packing import DistributionPackingForm
from core.operations_panel.forms.operation import OperationForm, OperationFolioWebsiteForm, OperationApprovalForm, \
    OperationFolioForm, OperationShipmentForm
from core.operations_panel.forms.route import RouteShipmentForm
from core.operations_panel.forms.transported_product import TransportedProductsFormByCSV, \
    OperationTransportedProductForm
from core.operations_panel.models import Cargo
from core.operations_panel.models.distribution_packing import DistributionPacking
from core.operations_panel.models.operation import Operation
from core.operations_panel.models.route import Route
from core.operations_panel.models.transported_product import TransportedProduct, OperationTransportedProduct
from core.system.views import AdminListView


class OperationListView(AdminListView):
    model = Operation
    form = OperationForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Control vehicular", "Cliente", "Packing", "Lista para fac", "Facturado"]
    datatable_keys = ["folio", "client", "is_packing_ready", "is_ready_to_invoice", "is_invoice_ready"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Operaciones'
    category = 'Operaciones'
    dropdown_action_path = 'operations_panel/operation/table/actions.js'
    static_path = 'operations_panel/operation/table/base.html'

    def handle_searchdata(self, request, data):
        """
        Retorna todos los registros como lista de dicts.
        """
        # Obtén los objetos de la tabla (o filtra según tus necesidades)
        queryset = self.get_queryset()
        datatable_keys = self.datatable_keys
        data = [obj.to_operations_view(keys=datatable_keys) for obj in self.get_queryset()]
        return data

    def handle_release(self, request, data):
        pass

    def get_queryset(self):
        # Puedes adaptar esto si usas SoftDeleteModel
        return self.model.objects.exclude(Q(folio__isnull=True) | Q(folio="")).all()


class FolioOperationListView(AdminListView):
    model = Operation
    form = OperationFolioWebsiteForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Control vehicular", "Fecha", "Requiere Porte", "Cliente", "Ruta", "Repartos",
                         "Unidad", "Operador", "Status"]
    datatable_keys = ["folio", "operation_date", "need_cartaporte", "client", "route", "deliveries",
                      "vehicle", "driver", "status"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Folios'
    category = 'Operaciones'

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
        """
        Retorna todos los registros como lista de dicts.
        """
        # Obtén los objetos de la tabla (o filtra según tus necesidades)
        queryset = self.get_queryset()
        datatable_keys = self.datatable_keys
        data = [obj.to_operations_view(keys=datatable_keys) for obj in self.get_queryset()]
        return data


class ShipmentOperationListView(AdminListView):
    model = Operation
    form = OperationShipmentForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = [
        "Control vehicular",
        "Origen",
        "Repartos",
        "Destino",
        "Productos",
        "Kms",
        "Lista para Facturacion?",
        "Packing",
    ]
    datatable_keys = [
        "folio",
        "origin",
        "deliveries",
        "destination",
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
            'id': 'id_products',
            'service': 'TransportedProducts',
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
        print(1)
        """
        Retorna todos los registros como lista de dicts.
        """
        # Obtén los objetos de la tabla (o filtra según tus necesidades)
        datatable_keys = self.datatable_keys
        data = [obj.to_operations_view(keys=datatable_keys) for obj in self.get_queryset()]
        return data

    def handle_get_route(self, request, data):
        operation = self.model.objects.get(pk=request.POST.get('id'))
        self.model = Route
        self.form = RouteShipmentForm
        self.form_action = "update_route"

        data['id'] = str(operation.route.id)
        data['form'] = self.render_form(request, operation.route)

    def handle_update_route(self, request, data):
        route = Route.objects.get(pk=request.POST.get('id'))
        form = RouteShipmentForm(request.POST, instance=route)
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
        print(operation)
        print(operation.transported_products.all())
        products = operation.transported_products.all()
        products_data = {
            'products': [],
        }
        for product in products:
            products_data['products'].append(json.loads(product.to_json()))
        data['form'] = self.render_others_form(request, operation, TransportedProductsFormByCSV, "update_cargo",
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

    def handle_get_packing(self, request, data):
        context = {}
        operation = Operation.objects.get(pk=request.POST.get('id'))
        if not Operation.objects.filter(folio=operation.folio + "B").exists():
            for delivery in operation.deliveries.all():
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

    def handle_generate_invoice(self, request, data):
        try:
            instance = self.model.objects.get(pk=request.POST.get('id'))
            if not instance.folio:
                data['error'] = "No se puede generar factura sin un folio asignado"
                return True

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
        return self.model.objects.exclude(Q(folio__isnull=True) | Q(folio="")).all()

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

    def handle_assignproducts(self, request, data):
        operation_id = request.POST["id"]
        product_ids = request.POST["transported_product"].split(",")
        weight = request.POST["weight"].split(",")
        amount = request.POST["amount"].split(",")

        operation = get_object_or_404(Operation, pk=operation_id)
        products = TransportedProduct.objects.filter(id__in=product_ids)

        for index in range(0, products.count()):
            OperationTransportedProduct.objects.create(
                operation=operation,
                transported_product=products[index],
                weight=products[index].weight,
                amount=products[index].amount
            )

            products[index].id = None
            products[index].weight = weight[index]
            products[index].amount = amount[index]
            products[index].save()
            operation.transported_products.add(products[index])
            operation.save()

        data["success"] = True
        data["message"] = f"{products.count()} productos asignados a {operation.folio}"
        return data

    def handle_get_assign_cargo_form(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        data['id'] = str(operation.id)
        data["form"] = self.render_others_form(request, operation, AssignCargoToOperationForm(), "AssignCargo", data=data)
        return data

    def handle_get_assign_products_form(self, request, data):
        operation = Operation.objects.get(pk=request.POST.get('id'))
        self.form_path = 'operations_panel/shipment/transported_product_form.html'
        data['id'] = str(operation.id)
        data['products'] = []
        for product in operation.transported_products.all():
            data['products'].append(json.loads(product.to_json()))
        data["form"] = self.render_others_form(request, operation, OperationTransportedProductForm(), "AssignProducts", data=data)
        return data
