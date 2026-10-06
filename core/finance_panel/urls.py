from django.urls import path

from core.finance_panel import views

app_name = 'finance_panel'

urlpatterns = [
    # External finance CRUD
    path('externals/', views.ExternalFinanceEntryListView.as_view(), name='external_finance_list'),
    path('externals/new/', views.ExternalFinanceEntryCreateView.as_view(), name='external_finance_create'),
    path('externals/<int:pk>/edit/', views.ExternalFinanceEntryUpdateView.as_view(), name='external_finance_edit'),
    path('externals/<int:pk>/delete/', views.ExternalFinanceEntryDeleteView.as_view(), name='external_finance_delete'),
    path('externals/api/create-category/', views.create_category_api, name='external_finance_create_category'),

    # Finance Control Master edit (mirror of system master-edit finance)
    path('cm/', views.finance_cm, name='cm_finance'),
]