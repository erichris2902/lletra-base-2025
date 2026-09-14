import sys
import json
from typing import Optional

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from decimal import Decimal

from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.models import Client
from apps.facturapi.services import FACTURAPI_BASE_URL, get_headers, DEFAULT_TIMEOUT


class Command(BaseCommand):
    help = (
        "Envía un payload JSON directamente a FacturAPI para generar una factura y guarda el resultado en BD.\n\n"
        "Fuentes de datos (usa exactamente UNA):\n"
        "  --file ruta.json    Leer JSON desde archivo\n"
        "  --data '{...}'      Proveer JSON inline\n"
        "  --stdin             Leer JSON desde stdin\n\n"
        "Opciones:\n"
        "  --idempotency KEY   Enviar cabecera Idempotency-Key\n"
        "  --dry-run           Solo validar/mostrar payload; no llama a FacturAPI\n"
        "  --echo              Imprime el payload que se enviaría\n"
    )

    def add_arguments(self, parser):
        parser.add_argument('--file', dest='file', help='Ruta de archivo JSON con el payload')
        parser.add_argument('--data', dest='data', help='JSON literal en la línea de comandos')
        parser.add_argument('--stdin', action='store_true', help='Leer JSON desde stdin')
        parser.add_argument('--idempotency', dest='idempotency', help='Idempotency-Key para la solicitud')
        parser.add_argument('--dry-run', action='store_true', help='Solo valida, no envía a FacturAPI')
        parser.add_argument('--echo', action='store_true', help='Imprime el payload normalizado')

    def handle(self, *args, **options):
        payload = self._read_payload(options)
        self._validate_minimal(payload)

        if options.get('echo') or options.get('dry_run'):
            self.stdout.write(self.style.NOTICE('Payload listo para enviar:'))
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            if options.get('dry_run'):
                self.stdout.write(self.style.SUCCESS('Dry-run OK (no se llamó a FacturAPI).'))
                return

        # Preparar request
        url = FACTURAPI_BASE_URL + '/invoices'
        headers = get_headers()
        idem = options.get('idempotency')
        if idem:
            headers['Idempotency-Key'] = str(idem)

        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            # Intenta mostrar mensaje legible
            msg = self._format_error(resp)
            raise CommandError(msg)

        data = resp.json()
        inv = self._persist_invoice(data, payload)

        # Salida legible
        display = self._summary(inv)
        self.stdout.write(self.style.SUCCESS('Factura creada correctamente en FacturAPI y guardada en BD.'))
        self.stdout.write(display)

    # ---------------------------- helpers ----------------------------
    def _read_payload(self, options) -> dict:
        srcs = [bool(options.get('file')), bool(options.get('data')), bool(options.get('stdin'))]
        if sum(1 for s in srcs if s) != 1:
            raise CommandError('Debes indicar exactamente una fuente de datos: --file, --data o --stdin')

        raw: Optional[str] = None
        if options.get('file'):
            path = options['file']
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw = f.read()
            except FileNotFoundError:
                raise CommandError(f'Archivo no encontrado: {path}')
        elif options.get('data'):
            raw = options['data']
        else:  # stdin
            raw = sys.stdin.read()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise CommandError(f'JSON inválido: {e}')
        if not isinstance(payload, dict):
            raise CommandError('El payload raíz debe ser un objeto JSON (dict)')
        return payload

    def _validate_minimal(self, p: dict):
        # Requisitos mínimos de FacturAPI
        required_root = ['type', 'customer', 'items']
        for k in required_root:
            if k not in p:
                raise CommandError(f'Falta la llave requerida en el payload: {k}')
        if not isinstance(p['customer'], dict):
            raise CommandError('customer debe ser un objeto')
        if not isinstance(p['items'], list) or not p['items']:
            raise CommandError('items debe ser una lista no vacía')

    def _format_error(self, resp: requests.Response) -> str:
        try:
            j = resp.json()
            # FacturAPI suele enviar error como { "message": "...", "code": ... }
            msg = j.get('message') or j
            return f"HTTP {resp.status_code}: {msg}"
        except Exception:
            return f"HTTP {resp.status_code}: {resp.text}"

    def _persist_invoice(self, s: dict, request_payload: dict) -> FacturapiInvoice:
        # Resolver/crear cliente a partir del payload de la solicitud (no de la respuesta)
        cust = request_payload.get('customer') or {}
        tax_id = (cust.get('tax_id') or cust.get('rfc') or '').strip() or None
        legal_name = (cust.get('legal_name') or cust.get('name') or '').strip() or None

        client_obj: Optional[Client] = None
        if tax_id:
            client_obj = Client.objects.filter(rfc=tax_id).first()
        if client_obj is None and legal_name:
            client_obj = Client.objects.filter(business_name=legal_name).first() or \
                         Client.objects.filter(name=legal_name).first()
        if client_obj is None:
            # Crear cliente mínimo si tenemos al menos un dato
            if tax_id or legal_name:
                client_obj = Client.objects.create(
                    rfc=tax_id or None,
                    business_name=legal_name or (tax_id or 'CLIENTE SIN NOMBRE'),
                    name=legal_name or (tax_id or 'CLIENTE SIN NOMBRE'),
                )
            else:
                # Como último recurso, toma cualquier cliente (evitar null FK). Si no hay, abortar con mensaje claro.
                client_obj = Client.objects.first()
                if client_obj is None:
                    raise CommandError('No se pudo resolver/crear un Client para asociar la factura.')

        inv = FacturapiInvoice.objects.create(
            customer=client_obj,
            type=str(request_payload.get('type') or 'I'),
            use=request_payload.get('use') or None,
            payment_form=request_payload.get('payment_method') or None,
            payment_method=request_payload.get('payment_form') or None,
            currency=request_payload.get('currency') or 'MXN',
            pdf_custom_section=request_payload.get('pdf_custom_section') or None,
            facturapi_response=s,
        )

        # Mapear campos principales desde la respuesta (similar a services._send_invoice_to_facturapi)
        stamp = s.get('stamp') or {}
        inv.facturapi_id = s.get('id') or inv.facturapi_id
        inv.status = s.get('status') or inv.status
        inv.cancellation_status = s.get('cancellation_status') or inv.cancellation_status
        inv.verification_url = s.get('verification_url') or inv.verification_url
        inv.uuid = s.get('uuid') or inv.uuid
        inv.series = s.get('series') or inv.series
        inv.folio_number = s.get('folio_number') or inv.folio_number
        if s.get('total') is not None:
            try:
                inv.total = Decimal(str(s['total']))
            except Exception:
                pass
        inv.is_live = s.get('livemode', inv.is_live)
        if stamp.get('date'):
            try:
                inv.stamp_date = parse_datetime(stamp['date'])
            except Exception:
                pass
        inv.sat_cert_number = stamp.get('sat_cert_number') or inv.sat_cert_number
        inv.sat_signature = stamp.get('sat_signature') or inv.sat_signature
        inv.signature = stamp.get('signature') or inv.signature
        inv.save()
        return inv

    def _summary(self, inv: FacturapiInvoice) -> str:
        parts = [
            f"id_bd={inv.id}",
            f"facturapi_id={inv.facturapi_id}",
            f"uuid={inv.uuid}",
            f"serie={inv.series}",
            f"folio={inv.folio_number}",
            f"status={inv.status}",
            f"total={inv.total}",
            f"cliente={getattr(inv.customer, 'business_name', None) or getattr(inv.customer, 'name', None)}",
        ]
        return "\n".join(parts)
