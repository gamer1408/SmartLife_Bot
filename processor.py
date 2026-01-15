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
Instruction: Analyze the text and strictly categorize it.
Rules:
1. If the text contains a specific date, time, or mentions a deadline (e.g., "15-yanvar", "Deadline", "Ertaga", "due date"), it MUST be "type": "task".
2. If the text describes an action to be done (e.g., "buy", "go", "call", "send"), it is a "task".
3. If the text is general information, a plan without a specific date, or a thought, it is an "idea".
4. For IDEAS: Do NOT shorten or summarize the content. Optimize it for clarity while keeping ALL original details.

Return ONLY JSON:
{{
    "type": "task" or "idea",
    "content": "Short title for task OR full detailed text for idea",
    "description": "Any additional links or full details for tasks",
    "date": "YYYY-MM-DD",
    "time": "HH:MM" or null,
    "category": "category name"
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