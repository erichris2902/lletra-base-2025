from django.urls import path
from . import views

app_name = 'rh_panel'

urlpatterns = [
    # Dashboard URL for RH users
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]