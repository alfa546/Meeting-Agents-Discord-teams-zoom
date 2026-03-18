import os
import re
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def extract_meeting_links(text):
    links = {}
    meet = re.findall(r'https://meet\.google\.com/[a-z0-9\-]+', text)
    if meet:
        links['google_meet'] = meet[0]
    zoom = re.findall(r'https://zoom\.us/j/[0-9]+', text)
    if zoom:
        links['zoom'] = zoom[0]
    teams = re.findall(
        r'https://teams\.microsoft\.com/l/meetup-join/[^\s"<]+', text)
    if teams:
        links['teams'] = teams[0]
    return links


def get_meeting_emails(max_results=10):
    service = get_gmail_service()
    query = "subject:(meeting OR invite OR join) newer_than:1d"
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()
    messages = results.get('messages', [])
    meeting_emails = []
    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()
        headers = msg_data['payload']['headers']
        subject = next(
            (h['value'] for h in headers if h['name'] == 'Subject'),
            'No Subject'
        )
        sender = next(
            (h['value'] for h in headers if h['name'] == 'From'),
            'Unknown'
        )
        body = ""
        payload = msg_data['payload']
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(
                        part['body']['data']
                    ).decode('utf-8')
                    break
        links = extract_meeting_links(subject + " " + body)
        if links:
            meeting_emails.append({
                'subject': subject,
                'from': sender,
                'links': links
            })
    return meeting_emails
