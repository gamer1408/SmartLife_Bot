"""
Mood Tracking Handler
Handles mood and energy logging for premium users
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, \
    filters
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Conversation states
MOOD_SELECT, ENERGY_SELECT, CONTEXT_INPUT = range(3)


class MoodHandler:
    """Handler for mood tracking (Premium feature)"""

    def __init__(self, db_manager):
        """
        Initialize mood handler

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager

    async def log_mood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Start mood logging conversation

        Usage: /mood
        """
        user_id = update.effective_user.id

        # Check premium status
        user = self.db.get_user(user_id)
        if not user or not user.premium_status:
            await update.message.reply_text(
                "😊 *Mood Tracking* is a Premium feature!\n\n"
                "Upgrade to Premium to:\n"
                "• Track your mood and energy levels\n"
                "• Get AI task suggestions based on mood\n"
                "• See mood-productivity correlations\n"
                "• Unlock smart recommendations\n\n"
                "Use /premium to learn more!",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Show mood selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("😊 Happy", callback_data='mood_happy'),
                InlineKeyboardButton("😌 Calm", callback_data='mood_calm')
            ],
            [
                InlineKeyboardButton("😓 Stressed", callback_data='mood_stressed'),
                InlineKeyboardButton("😴 Tired", callback_data='mood_tired')
            ],
            [
                InlineKeyboardButton("😤 Frustrated", callback_data='mood_frustrated'),
                InlineKeyboardButton("🤗 Motivated", callback_data='mood_motivated')
            ],
            [
                InlineKeyboardButton("😐 Neutral", callback_data='mood_neutral'),
                InlineKeyboardButton("❌ Cancel", callback_data='mood_cancel')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "😊 *How are you feeling right now?*\n\n"
            "Select your current mood:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return MOOD_SELECT

    async def mood_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle mood selection"""
        query = update.callback_query
        await query.answer()

        if query.data == 'mood_cancel':
            await query.edit_message_text("❌ Mood logging cancelled.")
            return ConversationHandler.END

        # Store mood in context
        mood = query.data.replace('mood_', '')
        context.user_data['mood'] = mood

        # Show energy level keyboard
        keyboard = [
            [
                InlineKeyboardButton("1️⃣", callback_data='energy_1'),
                InlineKeyboardButton("2️⃣", callback_data='energy_2'),
                InlineKeyboardButton("3️⃣", callback_data='energy_3'),
                InlineKeyboardButton("4️⃣", callback_data='energy_4'),
                InlineKeyboardButton("5️⃣", callback_data='energy_5')
            ],
            [
                InlineKeyboardButton("6️⃣", callback_data='energy_6'),
                InlineKeyboardButton("7️⃣", callback_data='energy_7'),
                InlineKeyboardButton("8️⃣", callback_data='energy_8'),
                InlineKeyboardButton("9️⃣", callback_data='energy_9'),
                InlineKeyboardButton("🔟", callback_data='energy_10')
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data='energy_cancel')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        mood_emoji = self._get_mood_emoji(mood)
        await query.edit_message_text(
            f"{mood_emoji} *Mood: {mood.title()}*\n\n"
            "⚡ *What's your energy level?*\n"
            "1 = Exhausted | 10 = Fully Energized",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return ENERGY_SELECT

    async def energy_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle energy level selection"""
        query = update.callback_query
        await query.answer()

        if query.data == 'energy_cancel':
            await query.edit_message_text("❌ Mood logging cancelled.")
            return ConversationHandler.END

        # Store energy level
        energy = int(query.data.replace('energy_', ''))
        context.user_data['energy'] = energy

        mood = context.user_data['mood']
        mood_emoji = self._get_mood_emoji(mood)

        await query.edit_message_text(
            f"{mood_emoji} *Mood: {mood.title()}*\n"
            f"⚡ *Energy: {energy}/10*\n\n"
            "📝 *What are you working on right now?*\n"
            "(Send a brief description or /skip)",
            parse_mode='Markdown'
        )

        return CONTEXT_INPUT

    async def context_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle context input"""
        user_id = update.effective_user.id
        mood = context.user_data['mood']
        energy = context.user_data['energy']
        context_text = update.message.text

        # Save to database
        success = self.db.log_mood(
            user_id=user_id,
            mood=mood,
            energy_level=energy,
            context=context_text
        )

        if success:
            mood_emoji = self._get_mood_emoji(mood)

            # Get mood insight
            insight = self._get_mood_insight(mood, energy)

            message = (
                f"✅ *Mood Logged Successfully!*\n\n"
                f"{mood_emoji} Mood: {mood.title()}\n"
                f"⚡ Energy: {energy}/10\n"
                f"📝 Context: {context_text}\n\n"
                f"💡 *Insight:*\n{insight}\n\n"
                f"Use /mood_insights to see your mood patterns!"
            )

            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Error logging mood. Please try again.",
                parse_mode='Markdown'
            )

        # Clear user data
        context.user_data.clear()
        return ConversationHandler.END

    async def skip_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Skip context input"""
        user_id = update.effective_user.id
        mood = context.user_data['mood']
        energy = context.user_data['energy']

        # Save without context
        success = self.db.log_mood(
            user_id=user_id,
            mood=mood,
            energy_level=energy,
            context="No context provided"
        )

        if success:
            mood_emoji = self._get_mood_emoji(mood)
            insight = self._get_mood_insight(mood, energy)

            message = (
                f"✅ *Mood Logged!*\n\n"
                f"{mood_emoji} Mood: {mood.title()}\n"
                f"⚡ Energy: {energy}/10\n\n"
                f"💡 *Insight:*\n{insight}\n\n"
                f"Use /mood_insights to see patterns!"
            )

            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Error logging mood.")

        context.user_data.clear()
        return ConversationHandler.END

    async def view_mood_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        View mood history

        Usage: /mood_history [days]
        """
        user_id = update.effective_user.id

        # Check premium
        user = self.db.get_user(user_id)
        if not user or not user.premium_status:
            await update.message.reply_text(
                "🔒 This is a Premium feature. Use /premium to upgrade!",
                parse_mode='Markdown'
            )
            return

        # Get days parameter
        days = 7
        if context.args:
            try:
                days = int(context.args[0])
                days = min(days, 90)  # Max 90 days
            except ValueError:
                pass

        # Get mood logs
        mood_logs = self.db.get_mood_logs(user_id, days)

        if not mood_logs:
            await update.message.reply_text(
                f"📊 No mood logs found in the last {days} days.\n\n"
                f"Start logging your mood with /mood!",
                parse_mode='Markdown'
            )
            return

        # Format history
        message = f"😊 *Mood History (Last {days} Days)*\n\n"

        for log in mood_logs[:15]:  # Show last 15
            mood_emoji = self._get_mood_emoji(log.mood)
            date_str = log.timestamp.strftime('%b %d, %I:%M %p')
            energy_bar = '⚡' * log.energy_level + '○' * (10 - log.energy_level)

            message += f"📅 {date_str}\n"
            message += f"   {mood_emoji} {log.mood.title()} | {energy_bar}\n"
            if log.context and log.context != "No context provided":
                message += f"   📝 {log.context[:50]}...\n"
            message += "\n"

        if len(mood_logs) > 15:
            message += f"\n... and {len(mood_logs) - 15} more entries\n"

        message += f"\nUse /mood_insights for detailed analysis!"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel mood logging"""
        await update.message.reply_text("❌ Mood logging cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

    def _get_mood_emoji(self, mood: str) -> str:
        """Get emoji for mood"""
        emojis = {
            'happy': '😊',
            'calm': '😌',
            'stressed': '😓',
            'tired': '😴',
            'frustrated': '😤',
            'motivated': '🤗',
            'neutral': '😐'
        }
        return emojis.get(mood, '😊')

    def _get_mood_insight(self, mood: str, energy: int) -> str:
        """Get contextual insight based on mood and energy"""
        if energy >= 8:
            if mood in ['happy', 'motivated', 'calm']:
                return "Perfect time for challenging tasks! You're in peak condition. 🚀"
            else:
                return "Good energy despite stress. Take breaks and tackle high-priority items. 💪"
        elif energy >= 5:
            if mood in ['happy', 'calm', 'motivated']:
                return "Solid state for steady work. Focus on medium-priority tasks. 👍"
            elif mood == 'stressed':
                return "Moderate energy but stressed. Try breaking tasks into smaller steps. 🧘"
            else:
                return "Average energy. Consider light tasks or take a short break. ☕"
        else:
            if mood in ['tired', 'stressed', 'frustrated']:
                return "Low energy detected. Rest is productive too. Consider easier tasks or a break. 🛋️"
            else:
                return "Energy is low. Perfect time for planning, organizing, or recharging. 🔋"

    def get_conversation_handler(self):
        """
        Get conversation handler for mood logging

        Returns:
            ConversationHandler for mood flow
        """
        return ConversationHandler(
            entry_points=[CommandHandler('mood', self.log_mood)],
            states={
                MOOD_SELECT: [
                    CallbackQueryHandler(self.mood_selected)
                ],
                ENERGY_SELECT: [
                    CallbackQueryHandler(self.energy_selected)
                ],
                CONTEXT_INPUT: [
                    CommandHandler('skip', self.skip_context),
                    CommandHandler('cancel', self.cancel),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.context_received)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            allow_reentry=True
        )