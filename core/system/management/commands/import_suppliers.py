import csv
from django.core.management.base import BaseCommand
from core.operations_panel.models.operations import Address, Supplier


def parse(value):
    if not value or value.strip().upper() in ["NULL", ""]:
        return None
    return value.strip()


class Command(BaseCommand):
    help = 'Importa proveedores desde CSV sin encabezado'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Ruta al archivo CSV')

    def handle(self, *args, **options):
        file_path = options['file']

        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            count = 0
            for row in reader:
                try:

                    print(row)
                    (
                        supplier_id, code, business_name, tax_regime, rfc,
                        email, phone, clabe, bank, account_number, city, _,
                        _, _, _, address_id, _, _, _,  # fecha creación/actualización, etc.
                    ) = row[:19]  # Asegura que se están leyendo correctamente
                    print(parse(code))
                    # Crear o buscar Address básico con ciudad y estado
                    print(f"Address ID: {address_id}")
                    address, _ = Address.objects.get_or_create(
                        id=int(address_id),
                    )
                    print("------")
                    supplier, created = Supplier.objects.update_or_create(
                        code=parse(code),
                        defaults={
                            "business_name": parse(business_name),
                            "tax_regime": parse(tax_regime),
                            "rfc": parse(rfc),
                            "email": parse(email) or "sin_correo@example.com",
                            "phone": parse(phone) or "",
                            "bank": parse(bank) or "",
                            "clabe": parse(clabe) or "",
                            "address": address,
                        }
                    )
                    print("XXXXXX")
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f"{'🆕 Creado' if created else '🔄 Actualizado'}: {supplier.code}"))

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Error procesando fila: {row[:5]} - {str(e)}"))

            self.stdout.write(self.style.SUCCESS(f"✅ Proveedores importados: {count}"))
