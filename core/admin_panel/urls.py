from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Login URL
    path('', views.AdminLoginView.as_view(), name='login'),

    # Logout URL
    path('logout/', views.AdminLogoutView.as_view(), name='logout'),

    # Dispatch URL - redirects users based on their system type
    path('dispatch/', views.UserDispatchView.as_view(), name='dispatch'),

    # Dashboard URL for SYSTEM users
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]
