from django.db.models.aggregates import Sum

from django.utils import timezone
from datetime import timedelta

from core.sales_panel.forms import LeadCategoryForm, LeadIndustryForm, LeadForm, QuotationForm, LeadExpenseForm
from core.sales_panel.models.commercial import LeadState, Lead, LeadExpense, LeadCategory, LeadIndustry, Quotation
from core.system.views import AdminTemplateView, AdminListView


class DashboardSaleView(AdminTemplateView):
    template_name = 'sale/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Time periods
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_end = month_start - timedelta(days=1)

        # 1. Prospected clients (weekly)
        weekly_prospects = Lead.objects.filter(
            created_date__date__range=[week_start, week_end],
            state=LeadState.PROSPECT,
        ).filter(user=self.request.user.user).count()

        # 2. Conversion rate (weekly)
        weekly_leads = Lead.objects.filter(
            created_date__date__range=[week_start, week_end]
        ).filter(user=self.request.user.user).count()

        weekly_closed = Lead.objects.filter(
            closed_date__date__range=[week_start, week_end],
            state=LeadState.CLOSED
        ).filter(user=self.request.user.user).count()

        weekly_conversion_rate = 0
        if weekly_leads > 0:
            weekly_conversion_rate = (weekly_closed / weekly_leads) * 100

        # 3. Average closing time (monthly)
        monthly_closed_leads = Lead.objects.filter(
            closed_date__date__gte=month_start,
            state=LeadState.CLOSED
        ).filter(user=self.request.user.user)

        avg_closing_time = 0
        if monthly_closed_leads.exists():
            closing_times = []
            for lead in monthly_closed_leads:
                closing_time = (lead.closed_date - lead.created_date).days
                closing_times.append(closing_time)
            avg_closing_time = sum(closing_times) / len(closing_times)

        monthly_expenses = LeadExpense.objects.filter(
            expense_date__date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        new_clients_count = Lead.objects.filter(
            created_date__date__gte=month_start,
            state=LeadState.CLOSED
        ).values('client').distinct().count()

        customer_acquisition_cost = 0
        if new_clients_count > 0:
            customer_acquisition_cost = monthly_expenses / new_clients_count

        # Lead counts by state
        prospect_count = Lead.objects.filter(state=LeadState.PROSPECT).filter(user=self.request.user.user).count()
        contacting_count = Lead.objects.filter(state=LeadState.CONTACTING).filter(user=self.request.user.user).count()
        quoting_count = Lead.objects.filter(state=LeadState.QUOTING).filter(user=self.request.user.user).count()
        closed_count = Lead.objects.filter(state=LeadState.CLOSED).filter(user=self.request.user.user).count()

        # Add KPIs to context
        context.update({
            'weekly_prospects': weekly_prospects,
            'weekly_conversion_rate': round(weekly_conversion_rate, 2),
            'avg_closing_time': round(avg_closing_time, 2),
            # 'avg_sale_amount': round(avg_sale_amount, 2),
            # 'frequent_clients_percentage': round(frequent_clients_percentage, 2),
            'customer_acquisition_cost': round(customer_acquisition_cost, 2),
            'prospect_count': prospect_count,
            'contacting_count': contacting_count,
            'quoting_count': quoting_count,
            'closed_count': closed_count,
            'form_type': 'horizontal',
            'calendar_url': self.request.user.calendar_url
        })
        print(context)

        return context


class AgendaView(AdminTemplateView):
    template_name = 'sale/agenda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Time periods
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_end = month_start - timedelta(days=1)

        # 1. Prospected clients (weekly)
        weekly_prospects = Lead.objects.filter(
            created_date__date__range=[week_start, week_end],
            state=LeadState.PROSPECT,
        ).filter(user=self.request.user.user).count()

        # 2. Conversion rate (weekly)
        weekly_leads = Lead.objects.filter(
            created_date__date__range=[week_start, week_end]
        ).filter(user=self.request.user.user).count()

        weekly_closed = Lead.objects.filter(
            closed_date__date__range=[week_start, week_end],
            state=LeadState.CLOSED
        ).filter(user=self.request.user.user).count()

        weekly_conversion_rate = 0
        if weekly_leads > 0:
            weekly_conversion_rate = (weekly_closed / weekly_leads) * 100

        # 3. Average closing time (monthly)
        monthly_closed_leads = Lead.objects.filter(
            closed_date__date__gte=month_start,
            state=LeadState.CLOSED
        ).filter(user=self.request.user.user)

        avg_closing_time = 0
        if monthly_closed_leads.exists():
            closing_times = []
            for lead in monthly_closed_leads:
                closing_time = (lead.closed_date - lead.created_date).days
                closing_times.append(closing_time)
            avg_closing_time = sum(closing_times) / len(closing_times)

        monthly_expenses = LeadExpense.objects.filter(
            expense_date__date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        new_clients_count = Lead.objects.filter(
            created_date__date__gte=month_start,
            state=LeadState.CLOSED
        ).values('client').distinct().count()

        customer_acquisition_cost = 0
        if new_clients_count > 0:
            customer_acquisition_cost = monthly_expenses / new_clients_count

        # Lead counts by state
        prospect_count = Lead.objects.filter(state=LeadState.PROSPECT).filter(user=self.request.user.user).count()
        contacting_count = Lead.objects.filter(state=LeadState.CONTACTING).filter(user=self.request.user.user).count()
        quoting_count = Lead.objects.filter(state=LeadState.QUOTING).filter(user=self.request.user.user).count()
        closed_count = Lead.objects.filter(state=LeadState.CLOSED).filter(user=self.request.user.user).count()

        # Add KPIs to context
        context.update({
            'weekly_prospects': weekly_prospects,
            'weekly_conversion_rate': round(weekly_conversion_rate, 2),
            'avg_closing_time': round(avg_closing_time, 2),
            # 'avg_sale_amount': round(avg_sale_amount, 2),
            # 'frequent_clients_percentage': round(frequent_clients_percentage, 2),
            'customer_acquisition_cost': round(customer_acquisition_cost, 2),
            'prospect_count': prospect_count,
            'contacting_count': contacting_count,
            'quoting_count': quoting_count,
            'closed_count': closed_count,
            'form_type': 'horizontal',
            'calendar_url': self.request.user.calendar_url
        })
        print(context)

        return context

class LeadCategoryListView(AdminListView):
    model = LeadCategory
    form = LeadCategoryForm
    datatable_keys = [
        'category',
    ]
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = [
        'Categoria',
    ]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'CATALOGO DE CATEGORIAS'
    category = 'Ventas'

class LeadIndustryListView(AdminListView):
    model = LeadIndustry
    form = LeadIndustryForm
    datatable_keys = [
        'industry',
    ]
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = [
        'Industria',
    ]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'CATALOGO DE INDUSTRIAS'
    category = 'Ventas'
    catalogs = [
    ]

class LeadListView(AdminListView):
    model = Lead
    form = LeadForm
    datatable_keys = [
        'business_name',
        'state',
        'industry',
        'geographic_zone',
        'requirements',
        'date_updated',
    ]
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = [
        'EMPRESA',
        'ESTADO',
        'INDUSTRIA',
        'ZONA GEOGRAFICA',
        'REQUERIMIENTOS',
        'ULTIMA INTERACCION',
    ]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'CLIENTES PROSPECTADOS'
    category = 'Ventas'
    catalogs = [
    ]

    def search_data(self, request=None):
        data = []
        for element in self.model.objects.exclude(is_deleted=True).filter(user=self.request.user.user).all():
            data.append(element.toJSON())
        return data

class LeadSaleView(AdminTemplateView):
    template_name = 'sale/leads.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        categories = []
        for category in LeadCategory.objects.filter(is_deleted=False).all():
            _category = {}
            _category['category'] = category
            leads= []
            for lead in Lead.objects.filter(category=category).filter(user=self.request.user.user).filter(is_deleted=False):
                leads.append(lead)
            _category['leads'] = leads
            categories.append(_category)
        context['categories'] = categories

        return context

class QuoteListView(AdminListView):
    model = Quotation
    form = QuotationForm
    datatable_keys = [
        'client',
        'origin',
        'destiny',
        'tipo_carga',
        'unit',
        'peso',
        'cost',
        'status_de_cotizacion',
    ]
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = [
        'Cliente',
        'Origen',
        'Destino',
        'Tipo de carga',
        'Unidad',
        'Peso',
        'Cotizacion',
        'Status de cotizacion',
    ]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'CATALOGO DE INDUSTRIAS'
    category = 'Ventas'
    catalogs = [
    ]

class ExpenseListView(AdminListView):
    model = LeadExpense
    form = LeadExpenseForm
    datatable_keys = [
        'lead',
        'description',
        'amount',
        'expense_date',
        'expense_type',
    ]
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = [
        'Prospecto',
        'Descripcion',
        'Cantidad',
        'Fecha',
        'Tipo',
    ]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'CATALOGO DE INDUSTRIAS'
    category = 'Ventas'
    catalogs = [
    ]