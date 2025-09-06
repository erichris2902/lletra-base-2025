import os
import io
import json
import logging
import hashlib
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from django.conf import settings
from django.utils import timezone

from .models import GoogleDriveCredential, GoogleDriveServiceAccount, GoogleDriveFolder, GoogleDriveFile

logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/calendar']

# Check if service account should be used
USE_SERVICE_ACCOUNT = os.getenv('GOOGLE_DRIVE_USE_SERVICE_ACCOUNT', False)
SERVICE_ACCOUNT_NAME = getattr(settings, 'GOOGLE_DRIVE_SERVICE_ACCOUNT_NAME', 'default-service-account')


def get_oauth2_flow(redirect_uri=None):
    """
    Create and return an OAuth2 flow instance to authorize with Google.

    Args:
        redirect_uri (str, optional): The redirect URI for the OAuth flow.
            If not provided, uses the one from settings.

    Returns:
        Flow: The OAuth2 flow instance.
    """
    if redirect_uri is None:
        redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
            "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }

    return Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )


def get_credentials_from_user(user):
    """
    Get Google Drive credentials for a user.

    Args:
        user: The Django user.

    Returns:
        Credentials: The Google Drive credentials, or None if not found.
    """
    try:
        credential = GoogleDriveCredential.objects.get(user=user)

        # Check if token is expired and needs refresh
        if credential.token_expiry <= timezone.now():
            # Token is expired, needs to be refreshed
            # This would be handled by the Google API client
            pass

        return Credentials(
            token=credential.access_token,
            refresh_token=credential.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_DRIVE_CLIENT_ID,
            client_secret=settings.GOOGLE_DRIVE_CLIENT_SECRET,
            scopes=SCOPES
        )
    except GoogleDriveCredential.DoesNotExist:
        return None


def save_credentials(user, credentials):
    """
    Save Google Drive credentials for a user.

    Args:
        user: The Django user.
        credentials: The Google Drive credentials.

    Returns:
        GoogleDriveCredential: The saved credential object.
    """
    # Calculate token expiry
    expiry = credentials.expiry  # ✅ ya es datetime

    # Update or create credentials
    credential, created = GoogleDriveCredential.objects.update_or_create(
        user=user,
        defaults={
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_expiry': expiry
        }
    )

    return credential


def get_service_account_credentials():
    """
    Get Google Drive credentials from a service account.

    Returns:
        Credentials: The Google Drive service account credentials, or None if not found.
    """
    try:
        # Get the service account from the database
        service_account_obj = GoogleDriveServiceAccount.objects.get(
            name=SERVICE_ACCOUNT_NAME,
            is_active=True
        )

        # Parse the credentials JSON
        credentials_info = json.loads(service_account_obj.credentials_json)

        # Create credentials from the service account info
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )

        return credentials
    except GoogleDriveServiceAccount.DoesNotExist:
        logger.error(f"Service account '{SERVICE_ACCOUNT_NAME}' not found or not active")
        return None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in service account credentials")
        return None
    except Exception as e:
        logger.error(f"Error getting service account credentials: {str(e)}")
        return None


def get_drive_service(user=None):
    """
    Get a Google Drive service instance.

    Args:
        user (optional): The Django user. If not provided and USE_SERVICE_ACCOUNT is True,
                        service account credentials will be used.

    Returns:
        Resource: The Google Drive service instance, or None if credentials not found.
    """
    # Use service account if configured and no user is provided
    if USE_SERVICE_ACCOUNT and user is None:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            return build("drive", "v3", credentials=credentials)
        except Exception as e:
            logger.exception("Failed to get Drive service using service account")
            return None
    return None


def create_folder(user, folder_name, parent_folder_id=None):
    """
    Create a folder in Google Drive.

    Args:
        user: The Django user.
        folder_name (str): The name of the folder to create.
        parent_folder_id (str, optional): The ID of the parent folder.
            If not provided, the folder will be created in the root of the drive.

    Returns:
        GoogleDriveFolder: The created folder object, or None if creation failed.
    """
    service = get_drive_service(user)
    if not service:
        logger.error(f"Failed to get Drive service for user {user.username}")
        return None

    # Check if folder already exists
    existing_folder = check_folder_exists(user, folder_name, parent_folder_id)
    if existing_folder:
        logger.info(f"Folder '{folder_name}' already exists with ID {existing_folder.drive_id}")
        return existing_folder

    # Prepare folder metadata
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }

    # Add parent folder if specified
    if parent_folder_id:
        folder_metadata['parents'] = [parent_folder_id]

    try:
        # Create the folder
        folder = service.files().create(
            body=folder_metadata,
            fields='id,name,mimeType',
            supportsAllDrives=True
        ).execute()

        # Get parent folder object if it exists in our database
        parent_folder = None
        if parent_folder_id:
            try:
                parent_folder = GoogleDriveFolder.objects.get(
                    user=user,
                    drive_id=parent_folder_id
                )
            except GoogleDriveFolder.DoesNotExist:
                pass

        # Save folder to database
        db_folder = GoogleDriveFolder.objects.create(
            user=user,
            name=folder_name,
            drive_id=folder['id'],
            parent_folder=parent_folder
        )

        logger.info(f"Created folder '{folder_name}' with ID {folder['id']}")
        return db_folder

    except Exception as e:
        logger.error(f"Error creating folder '{folder_name}': {str(e)}")
        return None


def check_folder_exists(user, folder_name, parent_folder_id=None):
    """
    Check if a folder exists in Google Drive.

    Args:
        user: The Django user.
        folder_name (str): The name of the folder to check.
        parent_folder_id (str, optional): The ID of the parent folder.

    Returns:
        GoogleDriveFolder: The folder object if it exists, or None if not found.
    """
    service = get_drive_service(user)
    if not service:
        logger.error(f"Failed to get Drive service for user {user.username}")
        return None

    # Build query
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"

    try:
        # Search for the folder
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True
        ).execute()

        items = results.get('files', [])
        if items:
            # Folder exists in Google Drive, check if it's in our database
            try:
                return GoogleDriveFolder.objects.get(
                    user=user,
                    drive_id=items[0]['id']
                )
            except GoogleDriveFolder.DoesNotExist:
                # Folder exists in Drive but not in our database, create it
                parent_folder = None
                if parent_folder_id:
                    try:
                        parent_folder = GoogleDriveFolder.objects.get(
                            user=user,
                            drive_id=parent_folder_id
                        )
                    except GoogleDriveFolder.DoesNotExist:
                        pass

                return GoogleDriveFolder.objects.create(
                    user=user,
                    name=folder_name,
                    drive_id=items[0]['id'],
                    parent_folder=parent_folder
                )

        return None

    except Exception as e:
        logger.error(f"Error checking if folder '{folder_name}' exists: {str(e)}")
        return None


def upload_file(user, file_path, folder_id=None, overwrite=False):
    """
    Upload a file to Google Drive.

    Args:
        user: The Django user.
        file_path (str): The path to the file to upload.
        folder_id (str, optional): The ID of the folder to upload to.
            If not provided, the file will be uploaded to the root of the drive.
        overwrite (bool, optional): Whether to overwrite the file if it already exists.
            Default is False.

    Returns:
        GoogleDriveFile: The uploaded file object, or None if upload failed.
    """
    service = get_drive_service(user)
    if not service:
        logger.error(f"Failed to get Drive service for user {user.username}")
        return None

    # Get file name and calculate MD5 checksum
    file_name = os.path.basename(file_path)
    md5_checksum = calculate_md5(file_path)

    # Check if file already exists
    existing_file = check_file_exists(user, file_name, folder_id, md5_checksum)
    if existing_file and not overwrite:
        logger.info(f"File '{file_name}' already exists with ID {existing_file.drive_id} and will not be overwritten")
        return existing_file

    # Prepare file metadata
    file_metadata = {
        'name': file_name
    }

    # Add parent folder if specified
    if folder_id:
        file_metadata['parents'] = [folder_id]

    # Get MIME type
    mime_type = get_mime_type(file_path)

    try:
        # Create media
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        # Upload the file
        if existing_file and overwrite:
            # Update existing file
            file = service.files().update(
                fileId=existing_file.drive_id,
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size,md5Checksum',
                supportsAllDrives=True
            ).execute()

            # Update file in database
            existing_file.name = file['name']
            existing_file.mime_type = file['mimeType']
            existing_file.size = int(file.get('size', 0))
            existing_file.md5_checksum = file.get('md5Checksum', '')
            existing_file.save()

            logger.info(f"Updated file '{file_name}' with ID {file['id']}")
            return existing_file
        else:
            # Create new file
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size,md5Checksum',
                supportsAllDrives=True
            ).execute()

            # Get folder object if it exists in our database
            folder = None
            if folder_id:
                try:
                    folder = GoogleDriveFolder.objects.get(
                        user=user,
                        drive_id=folder_id
                    )
                except GoogleDriveFolder.DoesNotExist:
                    pass

            # Save file to database
            db_file = GoogleDriveFile.objects.create(
                user=user,
                name=file['name'],
                drive_id=file['id'],
                mime_type=file['mimeType'],
                size=int(file.get('size', 0)),
                md5_checksum=file.get('md5Checksum', ''),
                folder=folder
            )

            logger.info(f"Uploaded file '{file_name}' with ID {file['id']}")
            return db_file

    except Exception as e:
        logger.error(f"Error uploading file '{file_name}': {str(e)}")
        return None


def upload_file_content(user, file_name, content, mime_type, folder_id=None, overwrite=False):
    """
    Upload file content to Google Drive.

    Args:
        user: The Django user.
        file_name (str): The name of the file to upload.
        content (bytes or str): The content of the file.
        mime_type (str): The MIME type of the file.
        folder_id (str, optional): The ID of the folder to upload to.
        overwrite (bool, optional): Whether to overwrite the file if it already exists.

    Returns:
        GoogleDriveFile: The uploaded file object, or None if upload failed.
    """
    service = get_drive_service(user)
    if not service:
        logger.error(f"Failed to get Drive service for user {user.username}")
        return None

    # Convert content to bytes if it's a string
    if isinstance(content, str):
        content = content.encode('utf-8')

    # Calculate MD5 checksum
    md5_checksum = hashlib.md5(content).hexdigest()

    # Check if file already exists
    existing_file = check_file_exists(user, file_name, folder_id, md5_checksum)
    if existing_file and not overwrite:
        logger.info(f"File '{file_name}' already exists with ID {existing_file.drive_id} and will not be overwritten")
        return existing_file

    # Prepare file metadata
    file_metadata = {
        'name': file_name
    }

    # Add parent folder if specified
    if folder_id:
        file_metadata['parents'] = [folder_id]

    try:
        # Create media
        media = MediaIoBaseUpload(
            io.BytesIO(content),
            mimetype=mime_type,
            resumable=True
        )

        # Upload the file
        if existing_file and overwrite:
            # Update existing file
            file = service.files().update(
                fileId=existing_file.drive_id,
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size,md5Checksum',
                supportsAllDrives=True
            ).execute()

            # Update file in database
            existing_file.name = file['name']
            existing_file.mime_type = file['mimeType']
            existing_file.size = int(file.get('size', 0))
            existing_file.md5_checksum = file.get('md5Checksum', '')
            existing_file.save()

            logger.info(f"Updated file '{file_name}' with ID {file['id']}")
            return existing_file
        else:
            # Create new file
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size,md5Checksum',
                supportsAllDrives=True
            ).execute()

            # Get folder object if it exists in our database
            folder = None
            if folder_id:
                try:
                    folder = GoogleDriveFolder.objects.get(
                        user=user,
                        drive_id=folder_id
                    )
                except GoogleDriveFolder.DoesNotExist:
                    pass

            # Save file to database
            db_file = GoogleDriveFile.objects.create(
                user=user,
                name=file['name'],
                drive_id=file['id'],
                mime_type=file['mimeType'],
                size=int(file.get('size', 0)),
                md5_checksum=file.get('md5Checksum', ''),
                folder=folder
            )

            logger.info(f"Uploaded file '{file_name}' with ID {file['id']}")
            return db_file

    except Exception as e:
        logger.error(f"Error uploading file '{file_name}': {str(e)}")
        return None


def check_file_exists(user, file_name, folder_id=None, md5_checksum=None):
    """
    Check if a file exists in Google Drive.

    Args:
        user: The Django user.
        file_name (str): The name of the file to check.
        folder_id (str, optional): The ID of the folder to check in.
        md5_checksum (str, optional): The MD5 checksum of the file.

    Returns:
        GoogleDriveFile: The file object if it exists, or None if not found.
    """
    service = get_drive_service(user)
    if not service:
        logger.error(f"Failed to get Drive service for user {user.username}")
        return None

    # Build query
    query = f"name='{file_name}' and trashed=false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    try:
        # Search for the file
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, size, md5Checksum)',
            supportsAllDrives=True
        ).execute()

        items = results.get('files', [])
        if items:
            # If MD5 checksum is provided, check if any file matches
            if md5_checksum:
                for item in items:
                    if item.get('md5Checksum') == md5_checksum:
                        # File with same name and checksum exists
                        try:
                            return GoogleDriveFile.objects.get(
                                user=user,
                                drive_id=item['id']
                            )
                        except GoogleDriveFile.DoesNotExist:
                            # File exists in Drive but not in our database, create it
                            folder = None
                            if folder_id:
                                try:
                                    folder = GoogleDriveFolder.objects.get(
                                        user=user,
                                        drive_id=folder_id
                                    )
                                except GoogleDriveFolder.DoesNotExist:
                                    pass

                            return GoogleDriveFile.objects.create(
                                user=user,
                                name=item['name'],
                                drive_id=item['id'],
                                mime_type=item['mimeType'],
                                size=int(item.get('size', 0)),
                                md5_checksum=item.get('md5Checksum', ''),
                                folder=folder
                            )

            # If no MD5 match or MD5 not provided, return the first file
            try:
                return GoogleDriveFile.objects.get(
                    user=user,
                    drive_id=items[0]['id']
                )
            except GoogleDriveFile.DoesNotExist:
                # File exists in Drive but not in our database, create it
                folder = None
                if folder_id:
                    try:
                        folder = GoogleDriveFolder.objects.get(
                            user=user,
                            drive_id=folder_id
                        )
                    except GoogleDriveFolder.DoesNotExist:
                        pass

                return GoogleDriveFile.objects.create(
                    user=user,
                    name=items[0]['name'],
                    drive_id=items[0]['id'],
                    mime_type=items[0]['mimeType'],
                    size=int(items[0].get('size', 0)),
                    md5_checksum=items[0].get('md5Checksum', ''),
                    folder=folder
                )

        return None

    except Exception as e:
        logger.error(f"Error checking if file '{file_name}' exists: {str(e)}")
        return None


def create_folder_with_service_account(folder_name, parent_folder_id=None):
    """
    Create a folder in Google Drive using service account credentials.

    Args:
        folder_name (str): The name of the folder to create.
        parent_folder_id (str, optional): The ID of the parent folder.
            If not provided, the folder will be created in the root of the drive.

    Returns:
        str: The ID of the created folder, or None if creation failed.
    """
    service = get_drive_service()
    if not service:
        logger.error("Failed to get Drive service using service account")
        return None

    # Prepare folder metadata
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }

    # Add parent folder if specified
    if parent_folder_id:
        folder_metadata['parents'] = [parent_folder_id]

    try:
        # Create the folder
        folder = service.files().create(
            body=folder_metadata,
            fields='id,name,mimeType',
            supportsAllDrives=True
        ).execute()

        logger.info(f"Created folder '{folder_name}' with ID {folder['id']} using service account")
        return folder['id']

    except Exception as e:
        logger.error(f"Error creating folder '{folder_name}' with service account: {str(e)}")
        return None


def check_folder_exists_with_service_account(folder_name, parent_folder_id=None):
    """
    Check if a folder exists in Google Drive using service account credentials.

    Args:
        folder_name (str): The name of the folder to check.
        parent_folder_id (str, optional): The ID of the parent folder.

    Returns:
        str: The ID of the folder if it exists, or None if not found.
    """
    service = get_drive_service()
    if not service:
        logger.error("Failed to get Drive service using service account")
        return None

    # Build query
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"

    try:
        # Search for the folder
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True  # 👈 Esto es lo que te faltaba
        ).execute()

        items = results.get('files', [])
        if items:
            logger.info(f"Found folder '{folder_name}' with ID {items[0]['id']} using service account")
            return items[0]['id']

        return None

    except Exception as e:
        logger.error(f"Error checking if folder '{folder_name}' exists with service account: {str(e)}")
        return None


def upload_file_with_service_account(file_path, folder_id=None, overwrite=True):
    """
    Upload a file to Google Drive using service account credentials.

    Args:
        file_path (str): The path to the file to upload.
        folder_id (str, optional): The ID of the folder to upload to.
            If not provided, the file will be uploaded to the root of the drive.
        overwrite (bool, optional): Whether to overwrite the file if it already exists.
            Default is False.

    Returns:
        str: The ID of the uploaded file, or None if upload failed.
    """
    service = get_drive_service()
    if not service:
        logger.error("Failed to get Drive service using service account")
        return None

    # Get file name and calculate MD5 checksum
    file_name = os.path.basename(file_path)
    md5_checksum = calculate_md5(file_path)

    # Check if file already exists
    existing_file_id = check_file_exists_with_service_account(file_name, folder_id)

    if existing_file_id and not overwrite:
        logger.info(f"File '{file_name}' already exists with ID {existing_file_id} and will not be overwritten")
        return existing_file_id

    # Prepare file metadata
    file_metadata = {
        'name': file_name
    }

    # Add parent folder if specified
    if folder_id:
        file_metadata['parents'] = [folder_id]

    # Get MIME type
    mime_type = get_mime_type(file_path)

    try:
        # Create media
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        # Upload the file
        if existing_file_id and overwrite:
            file_metadata.pop('parents', None)
            # Update existing file
            file = service.files().update(
                fileId=existing_file_id,
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size,md5Checksum',
                supportsAllDrives=True
            ).execute()

            logger.info(f"Updated file '{file_name}' with ID {file['id']} using service account")
            return file['id']
        else:
            # Create new file
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size,md5Checksum',
                supportsAllDrives=True,
            ).execute()

            logger.info(f"Uploaded file '{file_name}' with ID {file['id']} using service account")
            return file['id']

    except Exception as e:
        logger.error(f"Error uploading file '{file_name}' with service account: {str(e)}")
        return None


def check_file_exists_with_service_account(file_name, folder_id=None):
    """
    Check if a file exists in a specific Google Drive folder using service account.

    Returns:
        str: File ID if found, None otherwise.
    """
    service = get_drive_service()
    if not service:
        logger.error("Failed to get Drive service using service account")
        return None

    query = f"name = '{file_name}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, modifiedTime)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True  # 👈 Esto es lo que te faltaba
        ).execute()
        print(results)
        files = results.get('files', [])
        if files:
            file_id = files[0]['id']
            logger.info(f"Found existing file '{file_name}' with ID {file_id}")
            return file_id

        return None

    except Exception as e:
        logger.error(f"Error checking for file '{file_name}': {str(e)}")
        return None


def calculate_md5(file_path):
    """
    Calculate MD5 checksum of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The MD5 checksum of the file.
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_mime_type(file_path):
    """
    Get the MIME type of a file based on its extension.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The MIME type of the file.
    """
    extension = os.path.splitext(file_path)[1].lower()

    # Common MIME types
    mime_types = {
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.mp3': 'audio/mpeg',
        '.mp4': 'video/mp4',
        '.zip': 'application/zip',
        '.csv': 'text/csv'
    }

    return mime_types.get(extension, 'application/octet-stream')
