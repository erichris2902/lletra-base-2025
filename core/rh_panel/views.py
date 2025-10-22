import json
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.rh_panel.forms import EmployeeForm
from core.rh_panel.models import Employee, Embedding, Attendance
from core.system.views import AdminTemplateView, AdminListView


class DashboardView(LoginRequiredMixin, AdminTemplateView):
    template_name = 'rh_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard de Recursos Humanos'
        return context

class EmployeeListView(AdminListView):
    model = Employee
    form = EmployeeForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre"]
    datatable_keys = ["name"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Empleados'
    category = 'Recursos Humanos'
    static_path = 'static/employee/base.html'

    def handle_add_attendance(self, request, data):
        try:
            employee = Employee.objects.get(pk=request.POST["employee_id"])
        except Employee.DoesNotExist:
            return {"error": "Empleado no encontrado"}

        now_localtime = timezone.localtime().time()

        # Busca o crea asistencia del día
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=date.today(),
            defaults={
                "check_in": now_localtime,
                "confidence": request.POST.get("confidence", 0),
                "emotion_check_in": request.POST.get("emotion", None),
            }
        )

        # Si ya existía, marca hora de salida
        if not created:
            attendance.check_out = now_localtime
            # Puedes actualizar también la emoción si la detección fue reciente
            attendance.emotion_check_out = request.POST.get("emotion", attendance.emotion_check_out)
            attendance.save(update_fields=["check_out", "emotion_check_out"])

        # Devuelve el estado actual
        return {
            "employee": employee.name,
            "message": employee.name,
            "check_in": attendance.check_in,
            "check_out": attendance.check_out,
            "created": created,
            "timestamp": now_localtime.strftime("%H:%M:%S"),
            "status": "entrada" if created else "salida",
        }

class CaptureView(LoginRequiredMixin, AdminTemplateView):
    template_name = 'rh_panel/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class RegisterFaceView(LoginRequiredMixin, AdminTemplateView):
    template_name = 'rh_panel/enroll.html'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        print(request.POST)
        action = request.POST.get('action')
        if action == 'add':
            employee_id = kwargs.get('employee_id')
            employee = get_object_or_404(Employee, pk=employee_id)
            descriptor = request.POST.get('descriptors')
            print(employee)
            embedding = Embedding.objects.create(
                employee=employee,
                vector=descriptor
            )
        return JsonResponse({}, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

def get_embeddings(request):
    employees_data = []

    # Recorremos cada empleado con embeddings
    for employee in Employee.objects.prefetch_related('embeddings').all():
        embeddings = [e.vector for e in employee.embeddings.all()]
        if embeddings:
            employees_data.append({
                "employee_id": str(employee.id),
                "name": employee.name,
                "descriptors": embeddings,  # lista de listas de floats
            })
    print(employees_data)

    return JsonResponse(employees_data, safe=False)