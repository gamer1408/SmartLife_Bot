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
1. If text is an idea, return "type": "idea".
2. If text is an action, return "type": "task".
3. **PRETTIFY IDEAS**: 
   - Use bold headers (e.g., 💡 **IDEA NAME**).
   - Use bullet points for details.
   - Separate links or references clearly.
   - Do NOT shorten the content, just make it look like a professional report.
4. Return ONLY a JSON object.

JSON Format:
{{
    "type": "idea" or "task",
    "content": "Professional Markdown formatted text",
    "description": "Extra links or metadata",
    "date": "{today}",
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