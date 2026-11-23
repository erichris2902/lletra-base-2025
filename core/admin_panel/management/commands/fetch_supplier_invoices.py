import os
import re
import imaplib
import email
from email.header import decode_header, make_header
from io import BytesIO
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Tuple, List, Dict

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.core.files.base import ContentFile
from django.core.mail import get_connection, EmailMessage
from django.utils import timezone
import ssl
try:
    import certifi
    _CERTIFI_CA = certifi.where()
except Exception:
    certifi = None
    _CERTIFI_CA = None

from core.admin_panel.models.purchase_order import PurchaseOrder, PurchaseOrderOperation
from core.operation_control.models import OperationMasterControl
from core.operations_panel.models import Operation

# Detecta folios tipo GXXXX en cualquier parte del asunto/cuerpo, sin requerir el texto "Orden de compra"
FOLIO_REGEX = re.compile(r"\bG\d{4,}\b", re.IGNORECASE)


def _decode_mime_words(s: str) -> str:
    try:
        return str(make_header(decode_header(s or "")))
    except Exception:
        return s or ""


def _extract_folio_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    m = FOLIO_REGEX.search(text)
    if m:
        # Con el nuevo patrón, devolvemos el match completo (ej. G4012)
        return m.group(0).upper()
    return None


def _imap_connect():
    host = os.environ.get("EMAIL_IMAP_HOST", os.environ.get("IMAP_HOST", "imap.gmail.com"))
    port = int(os.environ.get("EMAIL_IMAP_PORT", os.environ.get("IMAP_PORT", "993")))
    use_ssl = os.environ.get("EMAIL_IMAP_SSL", os.environ.get("IMAP_SSL", "true")).lower() in ("1", "true", "yes")

    user = os.environ.get("EMAIL_IMAP_USER") or getattr(settings, "EMAIL_HOST_USER", None)
    password = os.environ.get("EMAIL_IMAP_PASSWORD") or getattr(settings, "EMAIL_HOST_PASSWORD", None)

    if not user or not password:
        raise CommandError("No email IMAP credentials found. Set EMAIL_IMAP_USER/EMAIL_IMAP_PASSWORD or EMAIL_HOST_USER/EMAIL_HOST_PASSWORD.")

    if use_ssl:
        M = imaplib.IMAP4_SSL(host, port)
    else:
        M = imaplib.IMAP4(host, port)
    M.login(user, password)
    return M


def _iter_attachments(msg: email.message.Message) -> List[Tuple[str, bytes]]:
    files: List[Tuple[str, bytes]] = []
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get('Content-Disposition') is None and not part.get_filename():
            # Inline or body part without filename
            continue
        filename = part.get_filename()
        if filename:
            filename = _decode_mime_words(filename)
        payload = part.get_payload(decode=True)
        if filename and payload:
            files.append((filename, payload))
    return files


def _choose_pdf_for_xml(attachments: Dict[str, bytes]) -> Optional[Tuple[str, str]]:
    # attachments: mapping of lower-filename -> original filename
    xml_names = [n for n in attachments.keys() if n.lower().endswith('.xml')]
    pdf_names = [n for n in attachments.keys() if n.lower().endswith('.pdf')]
    if not xml_names or not pdf_names:
        return None
    # Try to match by basename (without extension)
    for xml_name in xml_names:
        base = os.path.splitext(os.path.basename(xml_name))[0]
        candidates = [p for p in pdf_names if os.path.splitext(os.path.basename(p))[0].lower() == base.lower()]
        if candidates:
            return (xml_name, candidates[0])
    # Fallback: if only one xml and one pdf, return them
    if len(xml_names) == 1 and len(pdf_names) == 1:
        return (xml_names[0], pdf_names[0])
    return None


def _parse_cfdi_fields(xml_bytes: bytes) -> Tuple[Optional[Decimal], Optional[str], Optional[str]]:
    """Return (total, metodo_pago, receptor_rfc) from CFDI XML supporting v3.3/v4.0."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None, None, None

    def local(tag: str) -> str:
        return tag.split('}', 1)[-1] if '}' in tag else tag

    total = None
    metodo = None
    receptor_rfc = None

    # Attributes may be on root 'Comprobante'
    if local(root.tag).lower() == 'comprobante':
        # Total attribute
        for key in ('Total', 'total'):
            if key in root.attrib:
                try:
                    total = Decimal(root.attrib[key])
                except (InvalidOperation, KeyError):
                    pass
        # MetodoPago
        for key in ('MetodoPago', 'metodoPago', 'MetodoDePago', 'metodoDePago'):
            if key in root.attrib:
                metodo = root.attrib[key].upper()
                break
        # Receptor child
        for child in root.iter():
            if local(child.tag).lower() == 'receptor':
                for key in ('Rfc', 'RFC', 'rfc'):
                    if key in child.attrib:
                        receptor_rfc = child.attrib[key].upper()
                        break
                break

    # If not found, try to search generically
    if receptor_rfc is None:
        for el in root.iter():
            if local(el.tag).lower() == 'receptor':
                for key in ('Rfc', 'RFC', 'rfc'):
                    if key in el.attrib:
                        receptor_rfc = el.attrib[key].upper()
                        break

    return total, metodo, receptor_rfc


def _match_purchase_order_by_external_folio(external_folio: str) -> Optional[PurchaseOrder]:
    """
    Map an external PO code like 'G4012' to a PurchaseOrder by:
    - Finding OperationMasterControl where `purchase_order` contains the code
    - Taking related Operation(s) and resolving the PurchaseOrder via PurchaseOrderOperation
    """
    if not external_folio:
        return None

    omcs = Operation.objects.filter(folio=external_folio)
    if not omcs.exists():
        return None
    operations = [omc.id for omc in omcs]
    po_op = (
        PurchaseOrderOperation.objects
        .select_related('purchase_order')
        .filter(operation_id__in=operations)
        .first()
    )
    return po_op.purchase_order if po_op else None


class Command(BaseCommand):
    help = (
        "Lee el buzón IMAP configurado, busca correos con 'ORDEN DE COMPRA G####', "
        "descarga los adjuntos, identifica el XML y el PDF correctos (coinciden por nombre), "
        "valida CFDI (Total, MetodoPago=PPD, RFC receptor=STL191211KM2) y guarda en la orden de compra.\n\n"
        "Variables de entorno: EMAIL_IMAP_HOST, EMAIL_IMAP_PORT, EMAIL_IMAP_SSL, "
        "EMAIL_IMAP_USER, EMAIL_IMAP_PASSWORD. Si no se proveen usuario/contraseña, usa EMAIL_HOST_USER/EMAIL_HOST_PASSWORD.\n\n"
        "Uso: python manage.py fetch_supplier_invoices [--mailbox INBOX] [--since-days 15] [--limit 50] [--dry-run] [--verbose]"
    )

    def add_arguments(self, parser):
        parser.add_argument('--mailbox', default=os.environ.get('EMAIL_IMAP_MAILBOX', 'INBOX'))
        parser.add_argument('--since-days', type=int, default=int(os.environ.get('EMAIL_IMAP_SINCE_DAYS', '30')))
        parser.add_argument('--limit', type=int, default=int(os.environ.get('EMAIL_IMAP_LIMIT', '100')))
        parser.add_argument('--dry-run', action='store_true', default=False)
        parser.add_argument('--verbose', action='store_true', default=False)
        parser.add_argument('--force', action='store_true', default=False, help='Sobrescribe archivos existentes en la orden de compra')
        parser.add_argument('--email-log-to', default=os.environ.get('EMAIL_LOG_TO', 'erichris2902@gmail.com'), help='Correo al que se enviará el log al finalizar')
        parser.add_argument('--email-on', choices=['always', 'saved'], default=os.environ.get('EMAIL_LOG_ON', 'always'), help="Cuándo enviar el log: 'always' o solo si hubo guardados ('saved')")

    def handle(self, *args, **options):
        mailbox = options['mailbox']
        limit = options['limit']
        dry_run = options['dry_run']
        verbose = options['verbose']
        force = options['force']
        email_to = options.get('email-log-to') or os.environ.get('EMAIL_LOG_TO') or 'erichris2902@gmail.com'
        email_on = (options.get('email-on') or os.environ.get('EMAIL_LOG_ON') or 'always').lower()

        # Captura de log: inyectamos un wrapper sobre self.stdout.write para acumular líneas
        log_lines: List[str] = []
        orig_write = self.stdout.write

        def write_and_log(message: str):
            try:
                text = str(message)
            except Exception:
                text = message
            log_lines.append(text)
            return orig_write(message)

        # Monkey-patch del writer durante la ejecución
        self.stdout.write = write_and_log

        M = _imap_connect()
        try:
            typ, _ = M.select(mailbox)
            if typ != 'OK':
                raise CommandError(f"No se pudo abrir el buzón {mailbox}")

            # Get latest messages; IMAP SEARCH ALL then slice tail
            typ, data = M.search(None, 'ALL')
            if typ != 'OK':
                raise CommandError('Fallo al buscar mensajes en IMAP')

            ids = data[0].split()
            ids = ids[-limit:] if limit and len(ids) > limit else ids
            processed = 0
            saved = 0

            for num in reversed(ids):  # newest first
                typ, msg_data = M.fetch(num, '(RFC822 FLAGS)')
                if typ != 'OK' or not msg_data or not msg_data[0]:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])

                subject = _decode_mime_words(msg.get('Subject', ''))
                mbox_from = _decode_mime_words(msg.get('From', ''))
                if verbose:
                    self.stdout.write(f"Revisando: {subject} / From: {mbox_from}")

                folio = _extract_folio_from_text(subject)
                if not folio:
                    # Try first text/plain part
                    body_text = None
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            try:
                                body_text = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                            except Exception:
                                body_text = None
                            break
                    folio = _extract_folio_from_text(body_text or '')

                if not folio:
                    if verbose:
                        self.stdout.write("- Sin folio de orden de compra, se omite.")
                    continue

                order = _match_purchase_order_by_external_folio(folio)
                if not order:
                    self.stdout.write(f"Folio '{folio}' no coincide con ninguna Orden de Compra (via OperationMasterControl.purchase_order). Se omite.")
                    continue

                # Collect attachments
                atts = _iter_attachments(msg)
                if not atts:
                    if verbose:
                        self.stdout.write("- Sin adjuntos, se omite.")
                    continue
                # Build dict by lowercase filename for matching
                att_map: Dict[str, Tuple[str, bytes]] = {}
                for name, content in atts:
                    att_map[name.lower()] = (name, content)

                choice = _choose_pdf_for_xml({k: v[1] for k, v in att_map.items()})
                if not choice:
                    self.stdout.write("- No se pudo identificar pareja XML/PDF (los nombres deben coincidir). Se omite.")
                    continue

                xml_lname, pdf_lname = choice
                xml_name, xml_bytes = att_map[xml_lname][0], att_map[xml_lname][1]
                pdf_name, pdf_bytes = att_map[pdf_lname][0], att_map[pdf_lname][1]

                # Validate XML
                total, metodo, rfc = _parse_cfdi_fields(xml_bytes)
                if total is None or metodo is None or rfc is None:
                    self.stdout.write("- XML no válido o faltan campos (Total/MetodoPago/RFC Receptor). Se omite.")
                    continue

                # Compare totals (round to 2)
                try:
                    order_total = (order.total or Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    xml_total = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                except Exception:
                    self.stdout.write("- Error al convertir el total a Decimal. Se omite.")
                    continue

                if xml_total != order_total:
                    self.stdout.write(f"- Total XML {xml_total} != Total OC {order_total}. No se guardan archivos.")
                    continue
                if metodo.upper() != 'PPD':
                    self.stdout.write(f"- MetodoPago XML es '{metodo}', se requiere 'PPD'. No se guardan archivos.")
                    continue
                if rfc.upper() != 'STL191211KM2':
                    self.stdout.write(f"- RFC Receptor XML es '{rfc}', se requiere 'STL191211KM2'. No se guardan archivos.")
                    continue

                if not force and (order.supplier_invoice_pdf or order.supplier_invoice_xml):
                    self.stdout.write(f"- La OC {order.folio} ya tiene archivos de factura del proveedor. Use --force para sobrescribir.")
                    continue

                safe_base = re.sub(r'[^A-Za-z0-9_.-]+', '_', os.path.splitext(os.path.basename(xml_name))[0])
                xml_store_name = f"{order.folio}__{safe_base}.xml"
                pdf_store_name = f"{order.folio}__{safe_base}.pdf"

                if dry_run:
                    self.stdout.write(f"DRY-RUN: Guardaría {pdf_store_name} y {xml_store_name} en OC {order.folio}")
                else:
                    with transaction.atomic():
                        order.supplier_invoice_xml.save(xml_store_name, ContentFile(xml_bytes), save=False)
                        order.supplier_invoice_pdf.save(pdf_store_name, ContentFile(pdf_bytes), save=False)
                        order.save(update_fields=['supplier_invoice_xml', 'supplier_invoice_pdf'])
                    self.stdout.write(f"Guardado en OC {order.folio}: {pdf_store_name}, {xml_store_name}")
                    saved += 1

                processed += 1

            self.stdout.write(self.style.SUCCESS(f"Procesados: {processed}, Guardados: {saved}"))
        finally:
            try:
                M.close()
            except Exception:
                pass
            try:
                M.logout()
            except Exception:
                pass

            # Restaurar writer original antes de enviar correo
            try:
                self.stdout.write = orig_write
            except Exception:
                pass

            # Enviar log por correo según configuración
            try:
                should_send = (email_on == 'always') or (email_on == 'saved' and saved > 0)
            except Exception:
                should_send = True

            if email_to and should_send:
                try:
                    ts = timezone.now().strftime('%Y-%m-%d %H:%M')
                    subject = f"[fetch_supplier_invoices] {ts} Procesados: {processed}, Guardados: {saved}"
                    header = [
                        f"Mailbox: {mailbox}",
                        f"Limit: {limit}",
                        f"Dry-run: {dry_run}",
                        f"Force: {force}",
                        f"Email-on: {email_on}",
                    ]
                    body = (
                        "Resumen:\n" + "\n".join(header) +
                        "\n\nLog completo:\n" + "\n".join(log_lines)
                    )
                    from_addr = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', '')
                    # Use a certifi-backed SSL context to avoid CERTIFICATE_VERIFY_FAILED on some Windows setups
                    if _CERTIFI_CA:
                        ctx = ssl.create_default_context(cafile=_CERTIFI_CA)
                    else:
                        ctx = ssl.create_default_context()
                    with get_connection(fail_silently=False, ssl_context=ctx) as connection:
                        email_message = EmailMessage(subject, body, from_addr, [email_to], connection=connection)
                        email_message.send()
                except Exception as e:
                    # Si falla el envío, lo reportamos en consola sin interrumpir
                    try:
                        orig_write(f"No se pudo enviar el log por email a {email_to}: {e}")
                    except Exception:
                        pass
