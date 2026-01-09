"""
SmartLife Bot - Main Entry Point
UPDATED VERSION - With Task Management (Phase 2)
"""

import logging
import os
from turtledemo.forest import start

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import Config
from database import db_manager
from handlers.task_handler import TaskHandler, get_task_conversation_handler
from utils.keyboards import get_main_menu_keyboard
from services.voice_service import VoiceService
from config import Config
from database.db_manager import DatabaseManager
from handlers.start_handler import StartHandler
from handlers.calendar_handler import CalendarHandler
from handlers.notes_handler import NotesHandler
from handlers.analytics_handler import AnalyticsHandler
from handlers.mood_handler import MoodHandler
from handlers.premium_handler import PremiumHandler

load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if os.getenv('DEBUG') != 'True' else logging.DEBUG
)
logger = logging.getLogger(__name__)
voice_service = VoiceService()
notes_handler = NotesHandler(db_manager, voice_service)


class SmartLifeBot:
    def __init__(self):
        """Initialize bot with configuration and database"""
        print("\n" + "="*50)
        print("🤖 SmartLife Bot - Starting...")
        print("="*50)

        # Load configuration
        self.config = Config()
        self.config.print_config()

        # Initialize database
        print("\n📦 Initializing database...")
        self.db_manager = DatabaseManager(self.config.DATABASE_PATH)
        print("✅ Database initialized successfully!")

        # Initialize handlers
        self.start_handler = StartHandler(self.db_manager)
        self.task_handler, self.task_conv_handler = get_task_conversation_handler(self.db_manager)

        # Create application
        self.application = Application.builder().token(self.config.TELEGRAM_TOKEN).build()

        # Register all handlers
        self._register_handlers()

        print("\n✅ SmartLife Bot is ready!")
        print("="*50)

    def _register_handlers(self):
        """Register all command and message handlers"""

        # === BASIC COMMANDS ===
        self.application.add_handler(CommandHandler("start", self.start_handler.start_command))
        self.application.add_handler(CommandHandler("help", self.start_handler.help_command))
        self.application.add_handler(CommandHandler("stats", self.start_handler.stats_command))
        self.application.add_handler(CommandHandler("settings", self.start_handler.settings_command))
        self.application.add_handler(CommandHandler("premium", self.start_handler.premium_command))

        # === TASK MANAGEMENT (Phase 2) ===
        # Add Task - Conversation Handler
        self.application.add_handler(self.task_conv_handler)

        # View Tasks
        self.application.add_handler(CommandHandler("tasks", self.task_handler.view_tasks))

        # Complete Task
        self.application.add_handler(CommandHandler("complete", self.task_handler.complete_task))

        # Delete Task
        self.application.add_handler(CommandHandler("delete", self.task_handler.delete_task))

        # Task Filter Callbacks
        self.application.add_handler(
            CallbackQueryHandler(self.task_handler.view_tasks, pattern='^filter_')
        )

        # Task Delete Confirmation
        self.application.add_handler(
            CallbackQueryHandler(self.task_handler.confirm_delete_task, pattern='^confirm_delete_|^cancel_delete')
        )

        # === MENU BUTTON HANDLERS ===
        self.application.add_handler(MessageHandler(
            filters.Regex('^📝 Add Task$'),
            self.task_handler.add_task_start
        ))

        self.application.add_handler(MessageHandler(
            filters.Regex('^✅ View Tasks$'),
            self.task_handler.view_tasks
        ))

        self.application.add_handler(MessageHandler(
            filters.Regex('^📊 Analytics$'),
            self._analytics_placeholder
        ))

        self.application.add_handler(MessageHandler(
            filters.Regex('^📅 Calendar$'),
            self._calendar_placeholder
        ))

        self.application.add_handler(MessageHandler(
            filters.Regex('^💡 Notes$'),
            self._notes_placeholder
        ))

        self.application.add_handler(MessageHandler(
            filters.Regex('^⚙️ Settings$'),
            self.start_handler.settings_command
        ))

        self.application.add_handler(MessageHandler(
            filters.Regex('^⭐ Premium Features$'),
            self.start_handler.premium_command
        ))

        # === CALLBACK HANDLERS ===
        # Action callbacks
        self.application.add_handler(
            CallbackQueryHandler(self.task_handler.add_task_start, pattern='^action_addtask$')
        )

        # Back to menu
        self.application.add_handler(
            CallbackQueryHandler(self._back_to_menu, pattern='^back_to_menu$')
        )

        logger.info("✅ All handlers registered successfully!")

    async def _analytics_placeholder(self, update, context):
        """Placeholder for analytics feature (Phase 5)"""
        await update.message.reply_text(
            "📊 *Analytics Feature*\n\n"
            "🚧 Coming in Phase 5!\n\n"
            "This feature will show:\n"
            "• Daily completion rate\n"
            "• Category distribution\n"
            "• Productivity streaks\n"
            "• Peak hours analysis\n\n"
            "Stay tuned! 🚀",
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )

    async def _calendar_placeholder(self, update, context):
        """Placeholder for calendar feature (Phase 3)"""
        await update.message.reply_text(
            "📅 *Calendar Integration*\n\n"
            "🚧 Coming in Phase 3!\n\n"
            "This feature will allow:\n"
            "• Google Calendar sync\n"
            "• Auto-schedule tasks\n"
            "• Calendar notifications\n"
            "• AI time slot suggestions\n\n"
            "Stay tuned! 🚀",
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )

    async def _notes_placeholder(self, update, context):
        """Placeholder for notes feature (Phase 4)"""
        await update.message.reply_text(
            "💡 *Notes & Ideas*\n\n"
            "🚧 Coming in Phase 4!\n\n"
            "This feature will include:\n"
            "• Quick note creation\n"
            "• Voice-to-text notes\n"
            "• Smart categorization\n"
            "• Idea tagging system\n\n"
            "Stay tuned! 🚀",
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )

    async def _back_to_menu(self, update, context):
        """Return to main menu"""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "🏠 *Main Menu*\n\n"
            "Select an option from the menu below:",
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )

    def run(self):
        """Start the bot"""
        print("\n🚀 Starting bot polling...")
        print("📱 Open Telegram and send /start to your bot\n")
        print("Press Ctrl+C to stop the bot\n")

        # Start polling
        self.application.run_polling(allowed_updates=['message', 'callback_query'])


def main():
    """Start the bot"""

    # Get bot token
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return

    # Initialize database
    db = DatabaseManager(Config.DATABASE_PATH)

    # Initialize handlers
    start_handler = StartHandler(db)
    task_handler = TaskHandler(db)
    calendar_handler = CalendarHandler(db)
    notes_handler = NotesHandler(db)
    analytics_handler = AnalyticsHandler(db)
    mood_handler = MoodHandler(db)  # NEW Phase 6
    premium_handler = PremiumHandler(db)  # NEW Phase 6

    # Create application
    app = Application.builder().token(token).build()

    # Register basic command handlers
    app.add_handler(CommandHandler("start", start_handler.start))
    app.add_handler(CommandHandler("help", start_handler.help_command))
    app.add_handler(CommandHandler("stats", start_handler.stats))
    app.add_handler(CommandHandler("settings", start_handler.settings))
    app.add_handler(CommandHandler("premium", start_handler.premium))

    # Register task handlers (Phase 2)
    app.add_handler(task_handler.get_conversation_handler())
    app.add_handler(CommandHandler("tasks", task_handler.view_tasks))
    app.add_handler(CommandHandler("complete", task_handler.complete_task))
    app.add_handler(CommandHandler("delete", task_handler.delete_task))

    # Register calendar handlers (Phase 3)
    app.add_handler(calendar_handler.get_conversation_handler())
    app.add_handler(CommandHandler("disconnect_calendar", calendar_handler.disconnect_calendar))
    app.add_handler(CommandHandler("sync", calendar_handler.sync_tasks))
    app.add_handler(CommandHandler("schedule", calendar_handler.schedule_task))
    app.add_handler(CommandHandler("calendar_view", calendar_handler.calendar_view))

    # Register notes handlers (Phase 4)
    app.add_handler(notes_handler.get_note_conversation_handler())
    app.add_handler(CommandHandler("notes", notes_handler.view_notes))
    app.add_handler(CommandHandler("viewnote", notes_handler.view_single_note))
    app.add_handler(CommandHandler("deletenote", notes_handler.delete_note))
    app.add_handler(CommandHandler("searchnotes", notes_handler.search_notes_cmd))
    app.add_handler(CommandHandler("tags", notes_handler.list_tags))
    app.add_handler(CommandHandler("categories", notes_handler.list_categories))
    # Voice message handler
    app.add_handler(MessageHandler(
        filters.VOICE,
        notes_handler.handle_voice_message
    ))

    # Register analytics handlers (Phase 5)
    app.add_handler(CommandHandler("analytics", analytics_handler.analytics_dashboard))
    app.add_handler(CommandHandler("trends", analytics_handler.productivity_trends))
    app.add_handler(CommandHandler("breakdown", analytics_handler.task_breakdown))
    app.add_handler(CommandHandler("time", analytics_handler.time_analysis))
    app.add_handler(CommandHandler("achievements", analytics_handler.view_achievements))
    app.add_handler(CommandHandler("mood_insights", analytics_handler.mood_insights))
    app.add_handler(CommandHandler("report", analytics_handler.generate_report))

    # Register premium handlers (Phase 6) - NEW
    app.add_handler(mood_handler.get_conversation_handler())
    app.add_handler(CommandHandler("mood_history", mood_handler.view_mood_history))
    app.add_handler(CommandHandler("suggest", premium_handler.suggest_task))
    app.add_handler(CommandHandler("dailyplan", premium_handler.daily_plan))
    app.add_handler(premium_handler.get_brainstorm_handler())

    # Register callback query handler for inline keyboards
    app.add_handler(task_handler.get_callback_handler())

    # Register menu button handler
    app.add_handler(MessageHandler(
        filters.Regex('^(📝 Add Task|✅ View Tasks|📅 Calendar|💡 Notes|📊 Analytics|⚙️ Settings|⭐ Premium Features)$'),
        start_handler.handle_menu_button
    ))

    # Start bot
    logger.info("=" * 60)
    logger.info("SmartLife Bot started successfully!")
    logger.info("Phase 6: Premium Features - ACTIVE")
    logger.info("=" * 60)
    logger.info("Features available:")
    logger.info("  ✅ Task Management (Phase 2)")
    logger.info("  ✅ Calendar Integration (Phase 3)")
    logger.info("  ✅ Notes & Voice (Phase 4)")
    logger.info("  ✅ Analytics Dashboard (Phase 5)")
    logger.info("  ✅ Mood Tracking (Phase 6)")
    logger.info("  ✅ AI Task Suggestions (Phase 6)")
    logger.info("  ✅ Brainstorm Assistant (Phase 6)")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop the bot")
    logger.info("=" * 60)

    app.run_polling(allowed_updates=['message', 'callback_query'])


if __name__ == '__main__':
    main()