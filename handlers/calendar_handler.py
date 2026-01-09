"""
Calendar Handler
Handles all calendar-related commands and operations
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
from services.calendar_service import CalendarService
from services.gemini_service import GeminiService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_OAUTH_CODE = 1


class CalendarHandler:
    """Handler for calendar integration commands"""

    def __init__(self, db_manager):
        """
        Initialize calendar handler

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.calendar_service = CalendarService(db_manager)
        self.gemini_service = GeminiService()

    async def connect_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Start Google Calendar OAuth flow

        Usage: /connect_calendar
        """
        user_id = update.effective_user.id

        # Check if already connected
        if self.calendar_service.is_connected(user_id):
            await update.message.reply_text(
                "✅ Your Google Calendar is already connected!\n\n"
                "Use /disconnect_calendar to disconnect and reconnect.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Generate OAuth URL
        auth_url = self.calendar_service.get_auth_url(user_id)

        if not auth_url:
            await update.message.reply_text(
                "❌ Error: Could not generate authorization URL.\n\n"
                "Please make sure credentials.json file is present.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Send instructions
        message = (
            "🔗 *Connect Google Calendar*\n\n"
            "To connect your calendar:\n\n"
            "1️⃣ Click the link below\n"
            "2️⃣ Sign in to your Google account\n"
            "3️⃣ Grant calendar access\n"
            "4️⃣ Copy the authorization code\n"
            "5️⃣ Send it back to me\n\n"
            f"[Click here to authorize]({auth_url})\n\n"
            "Or use /cancel to abort."
        )

        await update.message.reply_text(message, parse_mode='Markdown')
        return AWAITING_OAUTH_CODE

    async def receive_oauth_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Receive and process OAuth authorization code
        """
        user_id = update.effective_user.id
        code = update.message.text.strip()

        await update.message.reply_text("🔄 Connecting to your calendar...")

        # Exchange code for tokens
        success = self.calendar_service.exchange_code_for_tokens(code, user_id)

        if success:
            await update.message.reply_text(
                "✅ *Calendar Connected Successfully!*\n\n"
                "Your tasks can now be synced to Google Calendar.\n\n"
                "Try these commands:\n"
                "• /sync - Sync all tasks to calendar\n"
                "• /schedule <task_id> - Get AI time suggestions\n"
                "• /calendar_view - View upcoming events",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ *Connection Failed*\n\n"
                "The authorization code might be invalid or expired.\n"
                "Please try /connect_calendar again.",
                parse_mode='Markdown'
            )

        return ConversationHandler.END

    async def disconnect_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Disconnect Google Calendar

        Usage: /disconnect_calendar
        """
        user_id = update.effective_user.id

        if not self.calendar_service.is_connected(user_id):
            await update.message.reply_text(
                "ℹ️ Your Google Calendar is not connected.\n\n"
                "Use /connect_calendar to connect it.",
                parse_mode='Markdown'
            )
            return

        # Disconnect
        success = self.calendar_service.disconnect(user_id)

        if success:
            await update.message.reply_text(
                "✅ *Calendar Disconnected*\n\n"
                "Your calendar has been disconnected.\n"
                "Calendar events from tasks will remain in your Google Calendar.\n\n"
                "Use /connect_calendar to reconnect anytime.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Error disconnecting calendar. Please try again.",
                parse_mode='Markdown'
            )

    async def sync_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Sync all pending tasks to calendar

        Usage: /sync
        """
        user_id = update.effective_user.id

        # Check if calendar connected
        if not self.calendar_service.is_connected(user_id):
            await update.message.reply_text(
                "❌ *Calendar Not Connected*\n\n"
                "Please connect your calendar first:\n"
                "/connect_calendar",
                parse_mode='Markdown'
            )
            return

        await update.message.reply_text("🔄 Syncing tasks to calendar...")

        # Get all pending tasks
        tasks = self.db.get_user_tasks(user_id, status='pending')

        if not tasks:
            await update.message.reply_text(
                "ℹ️ No pending tasks to sync.\n\n"
                "Create tasks with /addtask first.",
                parse_mode='Markdown'
            )
            return

        # Sync each task
        synced = 0
        failed = 0

        for task in tasks:
            if not task.calendar_event_id:  # Don't sync if already synced
                event_id = self.calendar_service.sync_task_to_calendar(user_id, task.id)
                if event_id:
                    synced += 1
                else:
                    failed += 1

        # Send result
        message = f"✅ *Sync Complete!*\n\n"
        message += f"✔️ Synced: {synced} tasks\n"
        if failed > 0:
            message += f"❌ Failed: {failed} tasks\n"
        message += f"\nCheck your Google Calendar to see your tasks!"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def schedule_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get AI-powered time suggestions for a task

        Usage: /schedule <task_id>
        """
        user_id = update.effective_user.id

        # Check if calendar connected
        if not self.calendar_service.is_connected(user_id):
            await update.message.reply_text(
                "❌ *Calendar Not Connected*\n\n"
                "Please connect your calendar first:\n"
                "/connect_calendar",
                parse_mode='Markdown'
            )
            return

        # Get task ID from args
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a task ID.\n\n"
                "Usage: /schedule <task_id>\n"
                "Example: /schedule 5",
                parse_mode='Markdown'
            )
            return

        try:
            task_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid task ID. Please use a number.")
            return

        # Get task
        task = self.db.get_task(task_id, user_id)
        if not task:
            await update.message.reply_text(f"❌ Task #{task_id} not found.")
            return

        await update.message.reply_text("🤖 Analyzing your schedule...")

        # Find free slots
        free_slots = self.calendar_service.find_free_slots(user_id, duration_hours=1, days_ahead=7)

        if not free_slots:
            await update.message.reply_text(
                "😅 Looks like your calendar is packed!\n\n"
                "No free slots found in the next 7 days.\n"
                "Consider rescheduling some events or extending the search period.",
                parse_mode='Markdown'
            )
            return

        # Get AI suggestion
        suggestion = self.gemini_service.suggest_optimal_time(
            task_title=task.title,
            task_priority=task.priority,
            task_deadline=task.deadline,
            task_category=task.category,
            free_slots=free_slots,
            duration_hours=1
        )

        if not suggestion:
            await update.message.reply_text("❌ Error getting AI suggestion. Please try again.")
            return

        # Format response
        suggested_slot = suggestion.get('suggested_slot')
        alternative_slot = suggestion.get('alternative_slot')

        message = f"🤖 *AI Schedule Suggestion*\n\n"
        message += f"📋 Task: {task.title}\n"
        message += f"🎯 Priority: {task.priority.title()}\n\n"

        if suggested_slot:
            message += f"⭐ *Recommended Time:*\n"
            message += f"   {suggested_slot['start'].strftime('%A, %B %d')}\n"
            message += f"   {suggested_slot['start'].strftime('%I:%M %p')} - {suggested_slot['end'].strftime('%I:%M %p')}\n\n"

        message += f"💡 *Why this time?*\n"
        message += f"   {suggestion.get('reasoning', 'Optimal time based on your schedule')}\n\n"

        if alternative_slot:
            message += f"🔄 *Alternative:*\n"
            message += f"   {alternative_slot['start'].strftime('%A, %B %d at %I:%M %p')}\n\n"

        if suggestion.get('productivity_tip'):
            message += f"✨ *Tip:* {suggestion['productivity_tip']}\n\n"

        message += f"Use /sync to add this to your calendar!"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def calendar_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        View upcoming calendar events

        Usage: /calendar_view
        """
        user_id = update.effective_user.id

        # Check if calendar connected
        if not self.calendar_service.is_connected(user_id):
            await update.message.reply_text(
                "❌ *Calendar Not Connected*\n\n"
                "Please connect your calendar first:\n"
                "/connect_calendar",
                parse_mode='Markdown'
            )
            return

        await update.message.reply_text("📅 Loading your calendar...")

        # Get upcoming events
        events = self.calendar_service.get_upcoming_events(user_id, days=7)

        if not events:
            await update.message.reply_text(
                "📅 *Your Calendar*\n\n"
                "No upcoming events in the next 7 days.\n"
                "Looks like you have a clear schedule! 🎉",
                parse_mode='Markdown'
            )
            return

        # Format events
        message = "📅 *Upcoming Events (Next 7 Days)*\n\n"

        current_date = None
        for event in events[:15]:  # Limit to 15 events
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))

            # Add date header if new day
            if current_date != start_dt.date():
                current_date = start_dt.date()
                message += f"\n📆 *{start_dt.strftime('%A, %B %d')}*\n"

            # Add event
            summary = event.get('summary', 'No title')
            time_str = start_dt.strftime('%I:%M %p')
            message += f"   • {time_str} - {summary}\n"

        if len(events) > 15:
            message += f"\n... and {len(events) - 15} more events"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation"""
        await update.message.reply_text(
            "❌ Operation cancelled.\n\n"
            "Use /help to see available commands."
        )
        return ConversationHandler.END

    def get_conversation_handler(self):
        """
        Get conversation handler for calendar OAuth flow

        Returns:
            ConversationHandler for OAuth flow
        """
        return ConversationHandler(
            entry_points=[CommandHandler('connect_calendar', self.connect_calendar)],
            states={
                AWAITING_OAUTH_CODE: [
                    CommandHandler('cancel', self.cancel),
                    # Any text message is treated as OAuth code
                    CommandHandler('start', self.receive_oauth_code),
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            allow_reentry=True
        )