"""
SmartLife Bot - Configuration Module
Loads environment variables and provides centralized configuration
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration from environment variables"""

    # === TELEGRAM BOT ===
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # === GOOGLE GEMINI API (FREE AI) ===
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    # === GOOGLE SPEECH-TO-TEXT ===
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    # === GOOGLE CALENDAR API ===
    GOOGLE_CALENDAR_CLIENT_ID = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
    GOOGLE_CALENDAR_CLIENT_SECRET = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')

    # === DATABASE ===
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')

    # === APPLICATION SETTINGS ===
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Tashkent')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

    # === FEATURE FLAGS ===
    ENABLE_VOICE = True
    ENABLE_PREMIUM = True
    ENABLE_CALENDAR = True

    # === LIMITS ===
    MAX_VOICE_DURATION = 120  # seconds
    MAX_NOTE_LENGTH = 5000  # characters
    MAX_TASK_TITLE = 200  # characters
    FREE_TASK_LIMIT = 50  # max tasks for free users
    FREE_NOTE_LIMIT = 100  # max notes for free users

    # === PREMIUM SETTINGS ===
    PREMIUM_PRICE_MONTHLY = 4.99
    PREMIUM_PRICE_YEARLY = 49.99

    @classmethod
    def validate(cls):
        """Validate that required environment variables are set"""
        errors = []

        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is not set in .env file")

        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set in .env file")

        if errors:
            print("\n❌ Configuration Errors:")
            for error in errors:
                print(f"  - {error}")
            print("\n💡 Please create a .env file with the required variables")
            return False

        return True

    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("\n" + "=" * 50)
        print("📋 SmartLife Bot Configuration")
        print("=" * 50)
        print(f"Telegram Token: {'✅ Set' if cls.TELEGRAM_BOT_TOKEN else '❌ Missing'}")
        print(f"Gemini API Key: {'✅ Set' if cls.GEMINI_API_KEY else '❌ Missing'}")
        print(f"Database Path: {cls.DATABASE_PATH}")
        print(f"Timezone: {cls.TIMEZONE}")
        print(f"Debug Mode: {cls.DEBUG}")
        print(f"Voice Enabled: {cls.ENABLE_VOICE}")
        print(f"Premium Enabled: {cls.ENABLE_PREMIUM}")
        print("=" * 50 + "\n")


# Validate configuration on import
if __name__ == "__main__":
    Config.print_config()
    if Config.validate():
        print("✅ Configuration is valid!")
    else:
        print("❌ Configuration has errors!")