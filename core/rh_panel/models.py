from django.db import models
from django.utils import timezone

from core.system.models import BaseModel


class Employee(BaseModel):
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.name


class Embedding(BaseModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='embeddings')
    vector = models.JSONField()  # [0.123, ...]


class Attendance(BaseModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance')
    confidence = models.FloatField(default=0)
    snapshot = models.ImageField(upload_to='snapshots/', null=True, blank=True)
    emotion_check_in = models.CharField(max_length=20, null=True, blank=True)  # 😀 feliz, 😐 neutral, etc.
    emotion_check_out = models.CharField(max_length=20, null=True, blank=True)  # 😀 feliz, 😐 neutral, etc.

    # 🕒 Nuevos campos
    date = models.DateField(default=timezone.now)  # Fecha del registro
    check_in = models.TimeField(null=True, blank=True)  # Hora de entrada
    check_out = models.TimeField(null=True, blank=True)  # Hora de salida
