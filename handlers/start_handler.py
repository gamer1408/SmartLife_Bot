"""
SmartLife Bot - Start and Help Handlers
Handles /start and /help commands
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database.db_manager import db
from utils.keyboards import get_main_menu_keyboard, get_premium_menu_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - welcome new users"""
    user = update.effective_user

    # Create or get user from database
    db_user = db.get_or_create_user(
        user_id=user.id,
        telegram_username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    # Choose keyboard based on premium status
    keyboard = get_premium_menu_keyboard() if db_user.premium else get_main_menu_keyboard()

    welcome_message = f"""
👋 Welcome to **SmartLife Bot**, {user.first_name}!

I'm your AI-powered productivity assistant. I can help you:

📝 **Manage Tasks** - Add, organize, and complete your to-dos
💡 **Capture Ideas** - Save notes and voice messages instantly
📅 **Sync Calendar** - Connect with Google Calendar
📊 **Track Progress** - View your productivity analytics
🎯 **Stay Focused** - Get smart reminders

{"⭐ **Premium Features**:" if db_user.premium else ""}
{"😊 Mood & Energy Tracking" if db_user.premium else ""}
{"🧠 AI Brainstorm Assistant" if db_user.premium else ""}
{"🎤 Full Voice Control" if db_user.premium else ""}

Type /help to see all available commands!

Let's boost your productivity! 🚀
"""

    await update.message.reply_text(
        welcome_message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - show available commands"""
    user = update.effective_user
    db_user = db.get_user(user.id)

    is_premium = db_user.premium if db_user else False

    help_text = """
📚 **Available Commands**

**📝 Task Management:**
/addtask - Add a new task
/tasks - View all your tasks
/complete [id] - Mark task as completed
/delete [id] - Delete a task

**💡 Notes & Ideas:**
/note - Add a quick note
/notes - View all your notes
/search [keyword] - Search in notes

**📅 Calendar:**
/calendar - Connect Google Calendar
/sync - Sync tasks with calendar

**📊 Analytics:**
/stats - View your productivity statistics
/analytics - See detailed analytics

**⚙️ Settings:**
/settings - Configure bot settings
/timezone - Set your timezone
"""

    if is_premium:
        help_text += """
**⭐ Premium Features:**
/mood - Log your current mood & energy
/suggest - Get AI task suggestions
/brainstorm - Start idea generation session
/voice - Enable voice command mode
"""
    else:
        help_text += """
**⭐ Want More?**
/premium - Upgrade to Premium for advanced features!
"""

    help_text += """
**ℹ️ Tips:**
• Send voice messages to capture ideas quickly
• Use buttons in the main menu for quick access
• Tasks support natural language deadlines

Need help? Type your question anytime! 💬
"""

    await update.message.reply_text(help_text, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user = update.effective_user

    # Get stats from database
    stats = db.get_user_stats(user.id)

    stats_message = f"""
📊 **Your Productivity Stats**

📝 **Tasks:**
• Total: {stats['total_tasks']}
• Completed: {stats['completed_tasks']}
• Completion Rate: {stats['completion_rate']:.1f}%

💡 **Notes:**
• Total Notes: {stats['total_notes']}

🎯 Keep up the great work! 💪
"""

    await update.message.reply_text(stats_message, parse_mode='Markdown')


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium features and pricing"""
    user = update.effective_user
    db_user = db.get_user(user.id)

    if db_user and db_user.premium:
        message = """
⭐ **You're already a Premium member!**

Enjoy unlimited access to:
✅ Mood & Energy Tracking
✅ AI Task Suggestions
✅ Brainstorm Assistant
✅ Full Voice Control
✅ Advanced Analytics
✅ Smart Reminders
✅ Priority Support

Thank you for your support! 🙏
"""
    else:
        message = """
⭐ **Upgrade to SmartLife Premium**

**Premium Features:**
😊 **Mood & Energy Tracker** - AI suggests tasks based on your state
🧠 **Brainstorm Assistant** - Generate creative ideas with AI
🎤 **Voice Commands** - Control everything by voice
📈 **Advanced Analytics** - Deep insights into productivity
⚡ **Smart Reminders** - Adaptive notifications
♾️ **Unlimited Storage** - No limits on tasks/notes

**Pricing:**
💰 $4.99/month or $49.99/year (Save 17%!)

**Coming Soon:**
Payment integration will be available in the next update.

For now, contact @your_username for early access! 🚀
"""

    await update.message.reply_text(message, parse_mode='Markdown')


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show and configure settings"""
    user = update.effective_user
    db_user = db.get_user(user.id)

    if not db_user:
        await update.message.reply_text("❌ User not found. Please use /start first.")
        return

    settings_message = f"""
⚙️ **Your Settings**

**Account:**
• User ID: {db_user.user_id}
• Username: @{db_user.telegram_username or 'Not set'}
• Premium: {'✅ Active' if db_user.premium else '❌ Free'}

**Preferences:**
• Timezone: {db_user.timezone}
• Language: {db_user.language_code}

**Commands to change settings:**
/timezone [timezone] - e.g., /timezone America/New_York
/language [code] - e.g., /language en

Type /help for more information.
"""

    await update.message.reply_text(settings_message, parse_mode='Markdown')


# Register handlers
def register_start_handlers(application):
    """Register all start-related handlers"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("settings", settings_command))


class StartHandler:
    pass