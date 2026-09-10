from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date
from django.db.models import Q
import csv
from datetime import date

from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.models.operation import Operation


class Command(BaseCommand):
    help = (
        "Lista facturas FacturAPI de tipo I (ingreso) que no están enlazadas a ninguna "
        "operación vía Operation.shipment_invoice. Permite filtrar por fecha de timbrado "
        "(stamp_date) y exportar a CSV."
    )

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="date_from", help="Fecha desde (YYYY-MM-DD) por stamp_date")
        parser.add_argument("--to", dest="date_to", help="Fecha hasta (YYYY-MM-DD) por stamp_date")
        parser.add_argument("--status", choices=["valid", "canceled", "pending", "draft", "all"], default="all",
                            help="Estatus de la factura a considerar (default: all)")
        parser.add_argument("--format", choices=["console", "csv"], default="console",
                            help="Formato de salida (default: console)")
        parser.add_argument("--output", dest="output", help="Ruta del archivo CSV cuando --format=csv")
        parser.add_argument("--limit", dest="limit", type=int, default=0,
                            help="Límite máximo de filas a mostrar/exportar (0 = sin límite)")

    def handle(self, *args, **options):
        date_from_s = options.get("date_from")
        date_to_s = options.get("date_to")
        status = options.get("status")
        out_format = options.get("format")
        out_path = options.get("output")
        limit = int(options.get("limit") or 0)

        # Validar fechas
        d_from = parse_date(date_from_s) if date_from_s else None
        d_to = parse_date(date_to_s) if date_to_s else None
        if date_from_s and not d_from:
            raise CommandError("--from debe tener formato YYYY-MM-DD")
        if date_to_s and not d_to:
            raise CommandError("--to debe tener formato YYYY-MM-DD")

        # IDs de facturas ya usadas en alguna Operation
        used_invoice_ids = Operation.objects.filter(
            shipment_invoice__isnull=False
        ).values_list("shipment_invoice_id", flat=True)

        qs = FacturapiInvoice.objects.filter(type="I").exclude(id__in=used_invoice_ids)

        if status and status != "all":
            qs = qs.filter(status=status)

        if d_from:
            qs = qs.filter(stamp_date__date__gte=d_from)
        if d_to:
            qs = qs.filter(stamp_date__date__lte=d_to)

        qs = qs.order_by("-stamp_date", "-created_at", "-id")

        # Preparar iteración con límite opcional
        rows_iter = qs.iterator(chunk_size=1000)

        headers = [
            "id", "uuid", "series", "folio_number", "customer", "total", "status", "stamp_date"
        ]

        if out_format == "csv":
            if not out_path:
                raise CommandError("Debe indicar --output para --format=csv")
            count = 0
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for inv in rows_iter:
                    writer.writerow(self._row(inv))
                    count += 1
                    if limit and count >= limit:
                        break
            self.stdout.write(self.style.SUCCESS(f"Exportado {count} registros a {out_path}"))
            return

        # Formato consola: imprimir en columnas simples separadas por tabulador
        # Encabezados
        self.stdout.write("\t".join(headers))
        count = 0
        for inv in rows_iter:
            self.stdout.write("\t".join([str(col) if col is not None else "" for col in self._row(inv)]))
            count += 1
            if limit and count >= limit:
                break
        self.stdout.write(self.style.SUCCESS(f"Total mostrado: {count}"))

    def _row(self, inv: FacturapiInvoice):
        customer_name = getattr(getattr(inv, "customer", None), "business_name", None) or \
                        getattr(getattr(inv, "customer", None), "name", None)
        return [
            inv.id,
            inv.uuid or "",
            inv.series or "",
            inv.folio_number if inv.folio_number is not None else "",
            customer_name or "",
            str(inv.total) if getattr(inv, "total", None) is not None else "",
            inv.status or "",
            inv.stamp_date.isoformat(sep=" ") if getattr(inv, "stamp_date", None) else "",
        ]
