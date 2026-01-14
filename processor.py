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
1. If the text is an idea, thought, or reflection, return "type": "idea".
2. If the text is an action, task, or command (e.g., "do", "go", "buy", "remind"), return "type": "task".
3. For "idea" types, DO NOT shorten the content. Keep all original details but optimize the grammar.
4. If there is a link, put it in the "description".

Return ONLY a JSON object:
{{
    "type": "idea" or "task",
    "content": "Full detailed content of the message",
    "description": "Any links or extra info",
    "date": "{today}",
    "time": "HH:MM" or null,
    "category": "category name"
}}
""" # Mana bu yerda triple-quote yopilishi shart

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt + f"\n\nUser text: {user_text}"}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        return {"type": "idea", "content": user_text, "category": "General", "date": today, "time": None}

def transcribe_voice(file_path):
    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3",
            response_format="text"
        )
    return transcription