from datetime import datetime
from groq import Groq
import json
import os
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def process_text_with_ai(user_text):
    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
Today is {today}.
If the text is an idea/thought, return "type": "idea". 
DO NOT shorten the idea content, optimize it but keep ALL details.
If it is an action to do, return "type": "task".

Return JSON:
{{
    "type": "idea" or "task",
    "content": "Full detailed content of the idea",
    "description": "Any links or extra info",
    "date": "{today}",
    "time": null,
    "category": "category name"
}}
"""
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", # Juda aqlli va bepul model
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        # Zaxira varianti (Manual)
        return {"type": "idea", "content": user_text, "category": "General", "date": None, "time": None}

def transcribe_voice(file_path):
    # Groq juda tez ovozni matnga o'giradi (Whisper)
    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3",
            response_format="text"
        )
    return transcription