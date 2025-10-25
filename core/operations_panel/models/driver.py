from datetime import datetime

from django.db import models

from core.system.functions import extract_best_coincidence_from_field_in_model
from core.system.models import BaseModel

class Driver(BaseModel):
    name = models.CharField(max_length=100, verbose_name="Nombre")
    last_name = models.CharField(max_length=100, verbose_name="Apellido paterno")
    mother_last_name = models.CharField(max_length=100, verbose_name="Apellido materno")
    rfc = models.CharField(max_length=13, verbose_name="RFC")
    license_number = models.CharField(max_length=20, verbose_name="Número de licencia")
    license_type = models.CharField(max_length=20, verbose_name="Tipo de licencia")
    license_expiration = models.DateField(verbose_name="Vencimiento de licencia")
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")

    @staticmethod
    def get_or_create_by_str(name: str = None):
        if not name:
            return None

        name_parts = name.split()
        if len(name_parts) >= 3:
            first_name = name_parts[0]
            last_name = name_parts[1]
            mother_last_name = ' '.join(name_parts[2:])
        elif len(name_parts) == 2:
            first_name = name_parts[0]
            last_name = name_parts[1]
            mother_last_name = ""
        else:
            first_name = name
            last_name = ""
            mother_last_name = ""

        # Try exact match first
        try:
            return Driver.objects.get(
                name__iexact=first_name,
                last_name__iexact=last_name
            )
        except Driver.DoesNotExist:
            pass

        # Try fuzzy matching
        best_coincidence = extract_best_coincidence_from_field_in_model(Driver, 'name', name, 80)
        if best_coincidence:
            return best_coincidence

        best_coincidence = extract_best_coincidence_from_field_in_model(Driver, 'last_name', name, 80)
        if best_coincidence:
            return best_coincidence

        best_coincidence = extract_best_coincidence_from_field_in_model(Driver, 'mother_last_name', name, 80)
        if best_coincidence:
            return best_coincidence

        # Create new driver if no match found
        return Driver.objects.create(
            name=first_name,
            last_name=last_name,
            mother_last_name=mother_last_name,
            rfc="XAXX010101000",  # Default RFC for Mexico
            license_number="DEFAULT",
            license_type="DEFAULT",
            license_expiration=datetime.now().date().replace(year=datetime.now().year + 5)  # 5 years from now
        )

    def __str__(self):
        return f"{self.name} {self.last_name} {self.mother_last_name}"

    class Meta:
        verbose_name = "Conductor"
        verbose_name_plural = "Conductores"