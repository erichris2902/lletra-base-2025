from django.urls import path
from . import views

app_name = 'sales_panel'

urlpatterns = [
    # Dashboard URL for COMERCIAL users
    path('', views.DashboardSaleView.as_view(), name='DashboardSaleView'),
    path('lead/category', views.LeadCategoryListView.as_view(), name="LeadCategoryListView"),
    path('lead/industry', views.LeadIndustryListView.as_view(), name="LeadIndustryListView"),
    path('leads', views.LeadListView.as_view(), name="LeadListView"),
    path('leads/user', views.LeadSaleView.as_view(), name="LeadSaleView"),
    path('agenda', views.AgendaView.as_view(), name="AgendaView"),
    path('quote', views.QuoteListView.as_view(), name="QuoteListView"),
    path('expenses', views.ExpenseListView.as_view(), name="ExpenseListView"),
]