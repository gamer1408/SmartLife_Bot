from datetime import datetime
from groq import Groq
import json
import os
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def process_text_with_ai(user_text):
    today = datetime.now().strftime("%Y-%m-%d")

    # Matnni aniq chegaralash va JSON formatini qat'iylashtirish
    prompt = f"""
Today is {today}.
Rules:
1. If the text contains keywords like "deadline", "muddat", "sana", or "date", ALWAYS set "type": "task".
2. If it is a general thought or information without a timeline, set "type": "idea".
3. **DO NOT SHORTEN IDEAS**: Keep full details for ideas, but format them nicely.
4. For tasks: Extract the deadline date into "date". If no specific time is mentioned, set "time": null.

Return ONLY JSON:
{{
    "type": "task" or "idea",
    "content": "Professional Title",
    "description": "Full details and links",
    "date": "YYYY-MM-DD",
    "time": "HH:MM" or null,
    "category": "category"
}}
"""

    try:
        # AIga foydalanuvchi matnini aniq ko'rsatamiz
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt + f"\n\nUser's Original Text: {user_text}"}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        # Xatolik yuz bersa, matnni asl holicha qaytaramiz
        return {"type": "idea", "content": user_text, "category": "General", "date": today, "time": None}

def transcribe_voice(file_path):
    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3",
            response_format="text"
        )
    return transcription