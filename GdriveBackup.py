import os
import zipfile



import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


folder_ids = ['1-x0XXXXXXXXXXXXX,1-x1XXXXXXXXXX']  # list of folder IDs to backup
backup_folder_id = '2KSQDOXXXXXXXXXXXX'  # ID of the backup folder


SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

creds = None
if os.path.exists('my_secret_token.json'):
    creds = Credentials.from_authorized_user_file('my_secret_token.json', SCOPES)
# If there are invalid credentials, connect the user / refresh the token
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'code_secret_client.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # cache the credential into the token file for the next connection
    with open('my_secret_token.json', 'w') as token:
        token.write(creds.to_json())

# create drive service
service = build('drive', 'v3', credentials=creds)

# iterate over all the folders
for folder_id in folder_ids:
  try:
    # get folder name
    folder = service.files().get(fileId=folder_id, fields='name').execute()
    folder_name = folder['name']

    # create a zip file
    zip_file_name = folder_name + '.zip'
    zip_file_path = os.path.join('/tmp', zip_file_name)
    with zipfile.ZipFile(zip_file_path, 'w') as zip_file:
      # get all files
      query = "mimeType='application/vnd.google-apps.folder' and trashed = false and parents in '" + folder_id + "'"
      results = service.files().list(q=query, fields="nextPageToken, files(id, name, mimeType)").execute()
      items = results.get("files", [])

      # add each file to the zip
      for item in items:
        file_id = item['id']
        file = service.files().get(fileId=file_id).execute()
        file_name = item['name']

        # download the file
        if file['mimeType'] != 'application/vnd.google-apps.folder':  # skip folders
          request = service.files().get_media(fileId=file_id)
          file_content = request.execute()
          zip_file.writestr(file_name, file_content)

    # create a folder in the backup folder with the same name as original
    mimetype = 'application/vnd.google-apps.folder'
    folder_metadata = {'name': folder_name, 'mimeType': mimetype, 'parents': [backup_folder_id]}
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    backup_folder_id = folder['id']

    # put the zip file to the backup
    file_metadata = {'name': zip_file_name, 'parents': [backup_folder_id]}
    media = MediaFileUpload(zip_file_path, mimetype='application/zip')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

  except HttpError as error:
    print(f'An error occurred: {error}')
