"""Explicit private-only OAuth upload; never called during rendering."""
import argparse
import hashlib
import json
import os
from pathlib import Path

SCOPES=['https://www.googleapis.com/auth/youtube.force-ssl']

def upload_body(metadata):
    return {'snippet':{k:metadata[k] for k in ('title','description','tags','defaultLanguage')},'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False}}

def upload(directory,client_secret,token):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    directory=Path(directory); token=Path(token)
    manifest=json.loads((directory/'manifest.json').read_text())
    if not manifest.get('qa_decode_passed'): raise ValueError('Video QA required')
    for name in ('video.mp4','metadata.json','thumbnail.jpg','subtitles.srt'):
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=manifest['files'][name]: raise ValueError('Artifact changed since QA')
    receipt=directory/'upload-receipt.json'
    if receipt.exists(): raise ValueError('Already uploaded; inspect receipt to avoid duplicate upload')
    creds=Credentials.from_authorized_user_file(str(token),SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
    if not creds or not creds.valid:
        creds=InstalledAppFlow.from_client_secrets_file(str(client_secret),SCOPES).run_local_server(port=0)
    token.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(token,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f: f.write(creds.to_json())
    os.chmod(token,0o600)
    api=build('youtube','v3',credentials=creds)
    metadata=json.loads((directory/'metadata.json').read_text())
    body=upload_body(metadata)
    request=api.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(directory/'video.mp4'),mimetype='video/mp4',resumable=True))
    response=None
    while response is None: _,response=request.next_chunk()
    receipt.write_text(json.dumps({'video_id':response['id'],'privacyStatus':response['status']['privacyStatus']},indent=2))
    api.thumbnails().set(videoId=response['id'],media_body=MediaFileUpload(str(directory/'thumbnail.jpg'),mimetype='image/jpeg')).execute()
    api.captions().insert(part='snippet',body={'snippet':{'videoId':response['id'],'language':'en','name':'English','isDraft':False}},media_body=MediaFileUpload(str(directory/'subtitles.srt'),mimetype='application/octet-stream')).execute()
    return response['id']

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--directory',required=True); p.add_argument('--client-secret',required=True); p.add_argument('--token',required=True); a=p.parse_args(); print(upload(a.directory,a.client_secret,a.token))
