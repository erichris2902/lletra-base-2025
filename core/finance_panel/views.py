from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, DeleteView
from django.shortcuts import render

from core.finance_panel.forms import ExternalFinanceEntryForm, ExternalFinanceCategoryForm
from core.finance_panel.models import ExternalFinanceEntry
from core.system.views import AdminListView


@login_required
def finance_cm(request):
    """Render Finance Control Master quick-edit page under /finance/cm/.
    Mirrors the system master-edit finance but focused on reported amounts.
    """
    return render(request, 'finance_panel/cm_finance.html')


@method_decorator(login_required, name="dispatch")
class ExternalFinanceEntryListView(AdminListView):
    model = ExternalFinanceEntry
    form = ExternalFinanceEntryForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = [
        "Fecha de pago", "Tipo", "Concepto", "Categoría", "Operación", "Monto (IVA incl.)",
        "Pagado", "Fecha limite de pago", "Comentarios"
    ]
    datatable_keys = [
        "paid_date", "entry_type", "concept", "category", "operation", "amount",
        "paid", "date", "comments"
    ]
    datatable_actions = True
    title = "Ingresos/Egresos externos"
    form_path = 'base/elements/forms/form.html'
    section = 'Finanzas'
    category = 'Sistema'
    ordering = 'desc'

    search_fields = ['concept', 'category__name', 'operation__folio', 'comments']


    def search_data(self, request=None):
        qs = self.model.objects.select_related('category', 'operation').all()
        # Filtros básicos (GET): date_from, date_to, entry_type, paid, category, operation_folio, concept
        df = request.GET.get("date_from") or ""
        dt = request.GET.get("date_to") or ""
        et = request.GET.get("entry_type") or ""
        paid = request.GET.get("paid") or ""
        cat = request.GET.get("category") or ""
        folio = (request.GET.get("operation_folio") or "").strip()
        concept = (request.GET.get("concept") or "").strip()

        if df:
            qs = qs.filter(date__gte=df)
        if dt:
            qs = qs.filter(date__lte=dt)
        if et in ("INCOME", "EXPENSE"):
            qs = qs.filter(entry_type=et)
        if paid in ("y", "n"):
            qs = qs.filter(paid=(paid == "y"))
        if cat:
            qs = qs.filter(category_id=cat)
        if folio:
            qs = qs.filter(operation__folio__icontains=folio)
        if concept:
            qs = qs.filter(concept__icontains=concept)
        return qs.order_by("-date", "-id")


@method_decorator(login_required, name="dispatch")
class ExternalFinanceEntryCreateView(CreateView):
    model = ExternalFinanceEntry
    form_class = ExternalFinanceEntryForm
    template_name = 'base/elements/forms/form.html'

    def form_valid(self, form):
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            try:
                form.instance.created_by = user
            except Exception:
                pass
        return super().form_valid(form)

    def get_success_url(self):
        from django.urls import reverse
        return reverse('finance_panel:external_finance_list')


@method_decorator(login_required, name="dispatch")
class ExternalFinanceEntryUpdateView(UpdateView):
    model = ExternalFinanceEntry
    form_class = ExternalFinanceEntryForm
    template_name = 'base/elements/forms/form.html'

    def get_success_url(self):
        from django.urls import reverse
        return reverse('finance_panel:external_finance_list')


@method_decorator(login_required, name="dispatch")
class ExternalFinanceEntryDeleteView(DeleteView):
    model = ExternalFinanceEntry
    template_name = 'base/elements/forms/confirm_delete.html'

    def get_success_url(self):
        from django.urls import reverse
        return reverse('finance_panel:external_finance_list')


@login_required
@require_POST
def create_category_api(request):
    form = ExternalFinanceCategoryForm(request.POST)
    if form.is_valid():
        obj = form.save()
        return JsonResponse({"ok": True, "id": obj.id, "name": obj.name})
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)
