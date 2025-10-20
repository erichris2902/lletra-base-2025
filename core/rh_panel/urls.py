from django.urls import path
from . import views

app_name = 'rh_panel'

urlpatterns = [
    # Dashboard URL for RH users
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('employee/', views.EmployeeListView.as_view(), name='employee'),
    path('capture/', views.CaptureView.as_view(), name='capture_attendance'),
    path('capture/embeddings', views.get_embeddings, name='embeddings'),
    path('employee/<uuid:employee_id>', views.RegisterFaceView.as_view(), name='register_face'),
]