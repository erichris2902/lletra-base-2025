import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from google_auth_oauthlib.flow import Flow

from .services import (
    get_oauth2_flow, save_credentials, get_drive_service,
    create_folder, check_folder_exists, upload_file, upload_file_content,
    check_file_exists
)
from .models import GoogleDriveCredential, GoogleDriveFolder, GoogleDriveFile



@login_required
def start_oauth(request):
    """
    Start the OAuth2 authorization flow using client secrets file.
    """
    user = request.user
    if not user.is_authenticated:
        return redirect('login')

    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=
        [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/calendar'
        ],
        redirect_uri='http://localhost:8000/google-drive/callback/'
    )

    authorization_url, state = flow.authorization_url(prompt='consent', access_type='offline')
    request.session['google_auth_state'] = state
    return redirect(authorization_url)


@login_required
def oauth2_callback(request):
    """
    Handle the OAuth2 callback from Google.
    """
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    user = request.user
    if not user.is_authenticated:
        return redirect('login')

    # Get the state from the session
    state = request.session.get('google_auth_state')

    # Check if state is valid
    if not state or request.GET.get('state') != state:
        return HttpResponseBadRequest('Invalid state parameter')

    # Create the flow instance
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=
        [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/calendar'
        ],
        redirect_uri='http://localhost:8000/google-drive/callback/'
    )

    # Exchange the authorization code for credentials
    flow.fetch_token(
        authorization_response=request.build_absolute_uri(),
    )

    # Get the credentials
    credentials = flow.credentials

    # Save the credentials
    save_credentials(request.user, credentials)

    # Render the callback template
    return render(request, 'google_drive/oauth2_callback.html')


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    """
    Dashboard view for Google Drive integration.
    """

    def get(self, request):
        # Check if user has credentials
        try:
            credential = GoogleDriveCredential.objects.get(user=request.user)
            has_credentials = True
        except GoogleDriveCredential.DoesNotExist:
            has_credentials = False

        # Get folders and files if user has credentials
        folders = []
        files = []

        if has_credentials:
            # Get root folders (no parent)
            folders = GoogleDriveFolder.objects.filter(
                user=request.user,
                parent_folder=None
            )

            # Get root files (no folder)
            files = GoogleDriveFile.objects.filter(
                user=request.user,
                folder=None
            )

        context = {
            'has_credentials': has_credentials,
            'folders': folders,
            'files': files
        }

        return render(request, 'google_drive/dashboard.html', context)


@method_decorator(login_required, name='dispatch')
class FolderView(View):
    """
    View for displaying folder contents.
    """

    def get(self, request, folder_id):
        try:
            # Get the folder
            folder = GoogleDriveFolder.objects.get(
                user=request.user,
                id=folder_id
            )

            # Get subfolders
            subfolders = GoogleDriveFolder.objects.filter(
                user=request.user,
                parent_folder=folder
            )

            # Get files in folder
            files = GoogleDriveFile.objects.filter(
                user=request.user,
                folder=folder
            )

            context = {
                'folder': folder,
                'subfolders': subfolders,
                'files': files
            }

            return render(request, 'google_drive/folder.html', context)

        except GoogleDriveFolder.DoesNotExist:
            return HttpResponseNotFound('Folder not found')


@login_required
@require_POST
def create_folder_view(request):
    """
    API endpoint for creating a folder.
    """
    folder_name = request.POST.get('name')
    parent_folder_id = request.POST.get('parent_folder_id')

    if not folder_name:
        return JsonResponse({'error': 'Folder name is required'}, status=400)

    # Convert parent_folder_id to Drive ID if it's a UUID
    parent_drive_id = None
    if parent_folder_id:
        try:
            parent_folder = GoogleDriveFolder.objects.get(
                user=request.user,
                id=parent_folder_id
            )
            parent_drive_id = parent_folder.drive_id
        except GoogleDriveFolder.DoesNotExist:
            return JsonResponse({'error': 'Parent folder not found'}, status=404)

    # Create the folder
    folder = create_folder(request.user, folder_name, parent_drive_id)

    if folder:
        return JsonResponse({
            'id': str(folder.id),
            'name': folder.name,
            'drive_id': folder.drive_id,
            'created_at': folder.created_at.isoformat()
        })
    else:
        return JsonResponse({'error': 'Failed to create folder'}, status=500)


@login_required
@require_POST
def upload_file_view(request):
    """
    API endpoint for uploading a file.
    """
    folder_id = request.POST.get('folder_id')
    overwrite = request.POST.get('overwrite', 'false').lower() == 'true'

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)

    uploaded_file = request.FILES['file']

    # Convert folder_id to Drive ID if it's a UUID
    folder_drive_id = None
    if folder_id:
        try:
            folder = GoogleDriveFolder.objects.get(
                user=request.user,
                id=folder_id
            )
            folder_drive_id = folder.drive_id
        except GoogleDriveFolder.DoesNotExist:
            return JsonResponse({'error': 'Folder not found'}, status=404)

    # Save the file temporarily
    temp_path = default_storage.save(
        f'temp/{uploaded_file.name}',
        ContentFile(uploaded_file.read())
    )
    temp_full_path = os.path.join(settings.MEDIA_ROOT, temp_path)

    try:
        # Upload the file to Google Drive
        file = upload_file(request.user, temp_full_path, folder_drive_id, overwrite)

        if file:
            return JsonResponse({
                'id': str(file.id),
                'name': file.name,
                'drive_id': file.drive_id,
                'mime_type': file.mime_type,
                'size': file.size,
                'created_at': file.created_at.isoformat()
            })
        else:
            return JsonResponse({'error': 'Failed to upload file'}, status=500)
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_full_path):
            os.remove(temp_full_path)


@login_required
@require_POST
def check_file_exists_view(request):
    """
    API endpoint for checking if a file exists.
    """
    file_name = request.POST.get('name')
    folder_id = request.POST.get('folder_id')

    if not file_name:
        return JsonResponse({'error': 'File name is required'}, status=400)

    # Convert folder_id to Drive ID if it's a UUID
    folder_drive_id = None
    if folder_id:
        try:
            folder = GoogleDriveFolder.objects.get(
                user=request.user,
                id=folder_id
            )
            folder_drive_id = folder.drive_id
        except GoogleDriveFolder.DoesNotExist:
            return JsonResponse({'error': 'Folder not found'}, status=404)

    # Check if file exists
    file = check_file_exists(request.user, file_name, folder_drive_id)

    if file:
        return JsonResponse({
            'exists': True,
            'id': str(file.id),
            'name': file.name,
            'drive_id': file.drive_id,
            'mime_type': file.mime_type,
            'size': file.size,
            'created_at': file.created_at.isoformat()
        })
    else:
        return JsonResponse({'exists': False})


@login_required
@require_GET
def list_files_view(request):
    """
    API endpoint for listing files in a folder.
    """
    folder_id = request.GET.get('folder_id')

    # If folder_id is provided, get files in that folder
    if folder_id:
        try:
            folder = GoogleDriveFolder.objects.get(
                user=request.user,
                id=folder_id
            )
            files = GoogleDriveFile.objects.filter(
                user=request.user,
                folder=folder
            )
        except GoogleDriveFolder.DoesNotExist:
            return JsonResponse({'error': 'Folder not found'}, status=404)
    else:
        # Get root files (no folder)
        files = GoogleDriveFile.objects.filter(
            user=request.user,
            folder=None
        )

    # Convert files to JSON
    files_json = [{
        'id': str(file.id),
        'name': file.name,
        'drive_id': file.drive_id,
        'mime_type': file.mime_type,
        'size': file.size,
        'created_at': file.created_at.isoformat()
    } for file in files]

    return JsonResponse({'files': files_json})


@login_required
@require_GET
def list_folders_view(request):
    """
    API endpoint for listing subfolders in a folder.
    """
    folder_id = request.GET.get('folder_id')

    # If folder_id is provided, get subfolders in that folder
    if folder_id:
        try:
            folder = GoogleDriveFolder.objects.get(
                user=request.user,
                id=folder_id
            )
            folders = GoogleDriveFolder.objects.filter(
                user=request.user,
                parent_folder=folder
            )
        except GoogleDriveFolder.DoesNotExist:
            return JsonResponse({'error': 'Folder not found'}, status=404)
    else:
        # Get root folders (no parent)
        folders = GoogleDriveFolder.objects.filter(
            user=request.user,
            parent_folder=None
        )

    # Convert folders to JSON
    folders_json = [{
        'id': str(folder.id),
        'name': folder.name,
        'drive_id': folder.drive_id,
        'created_at': folder.created_at.isoformat()
    } for folder in folders]

    return JsonResponse({'folders': folders_json})
