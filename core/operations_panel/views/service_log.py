from __future__ import annotations

import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.utils.timezone import make_aware
from django.views import View
from django.views.generic import TemplateView

from core.system.views import AdminView
from core.operations_panel.models import Operation
from core.operations_panel.models.service_log import ServiceLog
from core.operations_panel.service_logs.service import (
    open_or_create_log_by_folio,
    add_event_and_activity,
    serialize_log,
    ServiceLogEventType,
)


@method_decorator(login_required, name='dispatch')
class ServiceLogSearchView(AdminView, TemplateView):
    template_name = 'operations_panel/service_logs/search.html'
    section = 'Bitácora de Horas de Servicio'
    category = 'Operaciones'

    def get(self, request, *args, **kwargs):
        context = {
            'title': 'Bitácora de Horas de Servicio',
        }
        context = self.context_data_nav(context, request.user)
        return render(request, self.template_name, context)


@login_required
def open_service_log(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('Método no permitido')

    folio = (request.POST.get('folio') or '').strip()
    try:
        log = open_or_create_log_by_folio(folio)
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=400)
        # Render with message on the same page
        context = {'title': 'Bitácora de Horas de Servicio', 'error': str(e)}
        from core.system.views import AdminView as _A
        context = _A().context_data_nav(context, request.user)
        return render(request, 'operations_panel/service_logs/search.html', context, status=400)

    return redirect('operations_panel:service_log_detail', log_id=log.id)


@method_decorator(login_required, name='dispatch')
class ServiceLogDetailView(AdminView, TemplateView):
    template_name = 'operations_panel/service_logs/detail.html'

    def get(self, request, log_id, *args, **kwargs):
        log = get_object_or_404(ServiceLog.objects.select_related(
            'operation', 'operation__driver', 'operation__vehicle', 'operation__route',
            'operation__route__initial_location', 'operation__route__destination_location'
        ), id=log_id)

        context = {
            'title': f'Bitácora {log.operation.folio or "(sin folio)"}',
            'log': log,
        }
        context = self.context_data_nav(context, request.user)
        return render(request, self.template_name, context)


@login_required
def service_log_data(request, log_id):
    log = get_object_or_404(ServiceLog, id=log_id)
    data = serialize_log(log)
    return JsonResponse(data, safe=False)


@login_required
def create_event(request, log_id):
    if request.method != 'POST':
        return HttpResponseBadRequest('Método no permitido')

    log = get_object_or_404(ServiceLog, id=log_id)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}') if request.body else request.POST
    except Exception:
        payload = request.POST

    event_type = payload.get('event_type')
    started_at = payload.get('started_at')
    ended_at = payload.get('ended_at')
    notes = payload.get('notes') or ''

    if not event_type or not started_at:
        return JsonResponse({'error': 'event_type y started_at son requeridos'}, status=400)

    # Parse datetimes (expecting ISO 8601)
    sdt = parse_datetime(started_at)
    edt = parse_datetime(ended_at) if ended_at else None
    if sdt is None:
        return JsonResponse({'error': 'Formato de fecha/hora inválido (started_at)'}, status=400)

    if sdt.tzinfo is None:
        sdt = make_aware(sdt)
    if edt and edt.tzinfo is None:
        edt = make_aware(edt)

    try:
        event, activity = add_event_and_activity(
            service_log=log,
            event_type=event_type,
            started_at=sdt,
            ended_at=edt,
            notes=notes,
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Return current snapshot
    data = serialize_log(log)
    return JsonResponse(data, safe=False)
