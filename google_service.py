import os.path
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import SCOPES

def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def get_events_for_date(target_date):
    service = get_calendar_service()
    
    # Tashkent vaqti bilan kunning boshi va oxiri
    # Z (UTC) o'rniga aniq vaqt oralig'ini belgilaymiz
    time_min = f"{target_date}T00:00:00+05:00"
    time_max = f"{target_date}T23:59:59+05:00"
    
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    return events_result.get('items', [])

def add_event(summary, date_str, time_str, description=""):
    service = get_calendar_service()
    
    # 1. Sanani tekshirish
    if not date_str or date_str == "null":
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Baza ko'rinishidagi event
    event = {
        'summary': summary,
        'description': description if description else "", # Tavsif bo'lsa qo'shadi
    }

    # 2. VAQTNI TEKSHIRISH (Siz aytgan kunlik missiya mantiqi)
    if time_str and time_str != "null" and time_str != "NEED_CLARIFICATION":
        # Vaqt bor bo'lsa - Aniq soatli vazifa
        start_time = f"{date_str}T{time_str}:00"
        start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        end_dt = start_dt + timedelta(hours=1)
        
        event['start'] = {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Tashkent'}
        event['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Tashkent'}
    else:
        # Vaqt yo'q bo'lsa - KUNLIK MISSIYA (All day event)
        event['start'] = {'date': date_str}
        event['end'] = {'date': date_str}

    return service.events().insert(calendarId='primary', body=event).execute()    

def delete_event(event_id):
    service = get_calendar_service()
    service.events().delete(calendarId='primary', eventId=event_id).execute()

def get_upcoming_events():
    service = get_calendar_service()
    # UTC vaqtida keyingi 10 daqiqa uchun qidirish
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(minutes=10)).isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    return events_result.get('items', [])