# Google Drive App

This Django app provides integration with Google Drive, allowing users to create folders, upload files, and verify the existence of files. It includes features to prevent overwriting existing files.

## Features

- OAuth2 authentication with Google Drive API
- Create folders and subfolders in Google Drive
- Upload files to Google Drive with duplicate checking
- Verify the existence of files in Google Drive
- Track files and folders in the database
- Admin interface for managing credentials, folders, and files
- API endpoints for folder and file operations

## Models

- **GoogleDriveCredential**: Stores OAuth2 credentials for users (access token, refresh token, expiry)
- **GoogleDriveFolder**: Tracks Google Drive folders with support for nested folders
- **GoogleDriveFile**: Tracks Google Drive files with metadata like size, MIME type, and checksums

## Setup

### 1. Install Required Packages

Make sure you have the required packages installed:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 2. Configure Google Drive API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create OAuth2 credentials (Web application type)
5. Add your redirect URI (e.g., http://localhost:8000/google-drive/oauth2callback/)
6. Note your Client ID and Client Secret

### 3. Configure Environment Variables

Add the following to your `.env` file:

```
GOOGLE_DRIVE_CLIENT_ID=your-client-id
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret
GOOGLE_DRIVE_REDIRECT_URI=http://localhost:8000/google-drive/oauth2callback/
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## Usage

### Authentication

To authenticate a user with Google Drive:

1. Redirect the user to the authorization URL:
   ```python
   from django.shortcuts import redirect
   
   def start_auth(request):
       return redirect('google_drive:auth')
   ```

2. The user will be redirected to Google's consent screen
3. After granting permission, the user will be redirected back to your app
4. The app will store the credentials in the database

### Creating Folders

```python
from apps.google_drive.services import create_folder

# Create a folder in the root of the drive
folder = create_folder(user, "My Folder")

# Create a subfolder
subfolder = create_folder(user, "My Subfolder", folder.drive_id)
```

### Uploading Files

```python
from apps.google_drive.services import upload_file

# Upload a file to the root of the drive
file = upload_file(user, "/path/to/file.txt")

# Upload a file to a folder
file = upload_file(user, "/path/to/file.txt", folder.drive_id)

# Upload a file and overwrite if it exists
file = upload_file(user, "/path/to/file.txt", folder.drive_id, overwrite=True)
```

### Checking if Files Exist

```python
from apps.google_drive.services import check_file_exists

# Check if a file exists in the root of the drive
file = check_file_exists(user, "file.txt")

# Check if a file exists in a folder
file = check_file_exists(user, "file.txt", folder.drive_id)

# Check if a file with a specific MD5 checksum exists
file = check_file_exists(user, "file.txt", folder.drive_id, md5_checksum)
```

## API Endpoints

The app provides the following API endpoints:

- **Authentication**
  - `/google-drive/auth/`: Start the OAuth2 authorization flow
  - `/google-drive/oauth2callback/`: Handle the OAuth2 callback from Google

- **Dashboard and Folder Views**
  - `/google-drive/dashboard/`: View the root folders and files
  - `/google-drive/folder/<folder_id>/`: View the contents of a folder

- **API Endpoints**
  - `/google-drive/api/folders/create/`: Create a folder
  - `/google-drive/api/files/upload/`: Upload a file
  - `/google-drive/api/files/exists/`: Check if a file exists
  - `/google-drive/api/files/list/`: List files in a folder
  - `/google-drive/api/folders/list/`: List subfolders in a folder

## Admin Interface

The app provides an admin interface for managing:

- OAuth2 credentials
- Folders
- Files

Access the admin interface at `/admin/google_drive/`.

## Error Handling

The app includes comprehensive error handling for:

- Authentication failures
- File upload errors
- Folder creation errors
- Permission issues

All errors are logged using Django's logging system.

## Security

- All views are protected with `@login_required` decorator
- API endpoints validate user permissions
- OAuth2 state parameter is validated to prevent CSRF attacks
- Credentials are stored securely in the database