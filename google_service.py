import os
import json
import os.path
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import SCOPES

def get_calendar_service():
    creds = None
    # 1. Avval tokenni Environment Variable'dan tekshirish
    google_token = os.getenv('GOOGLE_TOKEN_JSON')
    if google_token:
        creds = Credentials.from_authorized_user_info(json.loads(google_token), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # 2. credentials.json matnini o'zgaruvchidan olish
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if not creds_json:
                raise FileNotFoundError("GOOGLE_CREDENTIALS_JSON topilmadi!")
            
            flow = InstalledAppFlow.from_client_config(json.loads(creds_json), SCOPES)
            # Renderda brauzer ochib bo'lmaydi, shuning uchun bu qism xato beradi
            # Siz lokalda olingan token.json ni GOOGLE_TOKEN_JSON ga qo'yishingiz shart
            raise PermissionError("Lokal token.json matnini GOOGLE_TOKEN_JSON o'zgaruvchisiga qo'ying!")
            
    return build('calendar', 'v3', credentials=creds)


def get_events_for_date(target_date):
    service = get_calendar_service()
    
    # O'zbekiston vaqti (+05:00) bo'yicha kunning boshi va oxiri
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
    
    if not date_str or date_str == "null":
        date_str = datetime.now().strftime("%Y-%m-%d")

    event = {
        'summary': summary,
        'description': description if description else "",
    }

    # VAQTNI TEKSHIRISH
    if time_str and time_str != "null" and time_str != "NEED_CLARIFICATION":
        start_time = f"{date_str}T{time_str}:00"
        start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        end_dt = start_dt + timedelta(hours=1)
        
        event['start'] = {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Tashkent'}
        event['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Tashkent'}
        
        # BILDIRISHNOMALAR (1h, 5h, 12h oldin)
        event['reminders'] = {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 60},    # 1 soat oldin
                {'method': 'popup', 'minutes': 300},   # 5 soat oldin
                {'method': 'popup', 'minutes': 720},   # 12 soat oldin
            ],
        }
    else:
        # Kunlik missiya (Muddat/Deadline uchun ham shu ishlaydi)
        event['start'] = {'date': date_str}
        event['end'] = {'date': date_str}
        
        # Kunlik missiyalar uchun bildirishnomalar odatda ishlamaydi, 
        # lekin Google Calendar orqali standart 9:00 dagi eslatmani yoqish mumkin
        event['reminders'] = {'useDefault': True}

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