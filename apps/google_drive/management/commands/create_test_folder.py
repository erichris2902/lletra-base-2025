import logging
import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.google_drive.services import (
    create_folder, check_folder_exists,
    create_folder_with_service_account, check_folder_exists_with_service_account, get_drive_service
)

logger = logging.getLogger(__name__)
User = get_user_model()

# Check if service account should be used
USE_SERVICE_ACCOUNT = os.getenv('GOOGLE_DRIVE_USE_SERVICE_ACCOUNT', False)

class Command(BaseCommand):
    help = 'Create a test folder named "prueba" in Google Drive to verify the implementation'

    def add_arguments(self, parser):
        if not USE_SERVICE_ACCOUNT:
            parser.add_argument('username', type=str, help='Username of the user to create the folder for')
        parser.add_argument('--parent', type=str, help='Parent folder ID (optional)', default=None)

    def handle(self, *args, **options):
        parent_folder_id = options.get('parent')
        self.check_access_to_folder(parent_folder_id)
        if USE_SERVICE_ACCOUNT:
            self.handle_service_account(parent_folder_id)
        else:
            username = options.get('username')
            if not username:
                raise CommandError('Username is required when not using service account')
            self.handle_user_account(username, parent_folder_id)

    def check_access_to_folder(self, folder_id):
        service = get_drive_service()
        try:
            metadata = service.files().get(fileId=folder_id, supportsAllDrives=True).execute()

            print(f"✅ Acceso correcto a la carpeta: {metadata['name']} ({metadata['id']})")
            return True
        except Exception as e:
            print(f"❌ La cuenta de servicio no tiene acceso a la carpeta {folder_id}: {e}")
            return False

    def handle_service_account(self, parent_folder_id=None):
        """
        Handle folder creation using service account.
        """
        # Check if folder already exists
        print(1)
        existing_folder_id = check_folder_exists_with_service_account("prueba", parent_folder_id)
        if existing_folder_id:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Folder "prueba" already exists with ID {existing_folder_id}'
                )
            )
            return
        # Create the folder
        folder_id = create_folder_with_service_account("prueba", parent_folder_id)
        if folder_id:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created folder "prueba" with ID {folder_id}'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Failed to create folder "prueba". Check if the service account has valid Google Drive credentials.'
                )
            )
            # Provide more detailed error information
            self.stdout.write(
                self.style.WARNING(
                    'Make sure the service account is properly configured and has access to Google Drive.'
                )
            )

    def handle_user_account(self, username, parent_folder_id=None):
        """
        Handle folder creation using user account.
        """
        try:
            # Get the user
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User with username {username} not found')

        # Check if folder already exists
        existing_folder = check_folder_exists(user, "prueba", parent_folder_id)
        if existing_folder:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Folder "prueba" already exists with ID {existing_folder.drive_id}'
                )
            )
            return

        # Create the folder
        folder = create_folder(user, "prueba", parent_folder_id)

        if folder:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created folder "prueba" with ID {folder.drive_id}'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Failed to create folder "prueba". Check if the user has valid Google Drive credentials.'
                )
            )
            # Provide more detailed error information
            self.stdout.write(
                self.style.WARNING(
                    'Make sure the user has authenticated with Google Drive and has valid credentials.'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    'You can authenticate by visiting /google-drive/auth/ while logged in as this user.'
                )
            )
