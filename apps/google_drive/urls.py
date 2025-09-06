from django.urls import path
from . import views

app_name = 'google_drive'

urlpatterns = [
    # Authentication URLs
    path('auth/', views.start_oauth, name='google_drive_auth'),
    path('callback/', views.oauth2_callback, name='oauth2callback'),

    # Dashboard and folder views
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('folder/<uuid:folder_id>/', views.FolderView.as_view(), name='folder'),

    # API endpoints
    path('api/folders/create/', views.create_folder_view, name='create_folder'),
    path('api/files/upload/', views.upload_file_view, name='upload_file'),
    path('api/files/exists/', views.check_file_exists_view, name='check_file_exists'),
    path('api/files/list/', views.list_files_view, name='list_files'),
    path('api/folders/list/', views.list_folders_view, name='list_folders'),
]
