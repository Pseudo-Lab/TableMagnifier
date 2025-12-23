import pandas as pd
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import io
import json
from pymongo.mongo_client import MongoClient
from tqdm import tqdm


def get_drive_service():
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly'] # Google Drive API 스코프 설정
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "/Users/seyeon/Desktop/데이터구축/TableMagnifier/info/client.json",
                SCOPES
            )
            creds = flow.run_local_server(
                host="localhost",
                port=8080,
                open_browser=True
                )

        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)


def find_root_folder(service):
    root_folders = service.files().list(
        q="'root' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name)"
    ).execute().get("files", [])
    
    return root_folders


def child_folders(service, folder_id, page_size=200):
    q = f"'{folder_id}' in parents and trashed = false"
    res = service.files().list(
        q=q,
        pageSize=page_size,
        fields="files(id,name,mimeType)"
    ).execute()
    return res.get("files", [])


def download_file_bytes(service, file_id):
    # fileID에 해당하는 이미지를 byte 형태로 read
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()


def list_all_files_in_folder(service, folder_id):
    files = []
    page_token = None
    while True:
        res = service.files().list(
            q=(
                f"'{folder_id}' in parents and "
                "mimeType != 'application/vnd.google-apps.folder' and "
                "trashed = false"
            ),
            fields="nextPageToken, files(id,name,mimeType)",
            pageToken=page_token,
            pageSize=1000
        ).execute()

        files.extend(res.get("files", []))
        page_token = res.get("nextPageToken")

        if not page_token:
            break

    return files


def save_image_to_local(file_bytes, file_path):
    """바이트 데이터를 이미지 파일로 저장"""
    with open(file_path, 'wb') as f:
        f.write(file_bytes)
    print(f"이미지 저장: {file_path}")


def mongo_client(PASSWORD, collection_name):
    URI = f"mongodb+srv://TableMagnifier:{PASSWORD}@tablemagnifier.gf5mkkc.mongodb.net/?appName=TableMagnifier"
    mongo_client = MongoClient(
        URI,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    
    # Database 선택
    db = mongo_client['TableInformation']
    # Collection 선택 : Academic, Business, Finance, Insurance, Medical, Public
    collection = db[f'{collection_name}']
    return collection

def get_file_information(file_id):
    file_info = service.files().get(
        fileId=file_id,
        fields="id,name,mimeType"
    ).execute()
    return file_info

def table_json_format():
    db_json = {
        "Domain":"",
        "ImageFileName":"",
        "ImageFileID":"",
        "HTMLText":"",
        "QAPair":{},
        "Evaluation_Result":{}}
    return db_json


def database_data_insert(PASSWORD):
    service = get_drive_service()
    START_FOLDER_ID = ""
    folders = child_folders(service, START_FOLDER_ID)

    domains = {}
    for folder in folders:
        domains[f'{folder["name"]}'] = folder["id"]


    for domain in domains.keys():
        collection = mongo_client(PASSWORD, domain)
        domain_folder = child_folders(service, domains[f"{domain}"])
        
        sub_folders = {}
        for folder in domain_folder:
            sub_folders[f"{folder["name"]}"] = folder['id']

        table_folders = child_folders(service, sub_folders["Table"])
            
        for folder in table_folders:
            folder_name = folder["name"]
            folder_id = folder["id"]
            # print(f"\n폴더 '{folder_name}' (ID: {folder_id}")
            
            files = list_all_files_in_folder(service, folder_id)
            # print(f"  - 파일 개수: {len(files)}")

            # 각 파일 읽기 및 Database 적재
            for file in files:
                file_name = file["name"]
                file_id = file["id"]
                file_mime = file.get("mimeType", "unknown")
                
                file_json = table_json_format()
                file_json['Domain'] = domain
                file_json['ImageFileName'] = file_name
                file_json["ImageFileID"] = file_id
                print(file_json)
                collection.insert_one(file_json)


if __name__ == '__main__':
    # create_csv()
    PASSWORD = ""
    database_data_insert(PASSWORD)
    