"""
Premium Features Handler
Manages premium features including AI suggestions and brainstorming
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, \
    ConversationHandler
from services.ai_suggestion_service import AISuggestionService
from services.brainstorm_service import BrainstormService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Conversation states
BRAINSTORM_TOPIC, IDEA_SELECTION, IDEA_ACTION = range(3)


class PremiumHandler:
    """Handler for premium features"""

    def __init__(self, db_manager):
        """
        Initialize premium handler

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.ai_suggestion = AISuggestionService()
        self.brainstorm = BrainstormService()

    async def suggest_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get AI suggestion for next best task

        Usage: /suggest
        """
        user_id = update.effective_user.id

        # Check premium
        user = self.db.get_user(user_id)
        if not user or not user.premium_status:
            await update.message.reply_text(
                "🤖 *AI Task Suggestions* is a Premium feature!\n\n"
                "Get personalized task recommendations based on:\n"
                "• Your current mood and energy\n"
                "• Time of day\n"
                "• Task priorities and deadlines\n"
                "• Your productivity patterns\n\n"
                "Use /premium to upgrade!",
                parse_mode='Markdown'
            )
            return

        await update.message.reply_text("🤖 Analyzing your tasks and schedule...")

        # Get pending tasks
        tasks = self.db.get_user_tasks(user_id, status='pending')

        if not tasks:
            await update.message.reply_text(
                "🎉 *No pending tasks!*\n\n"
                "You're all caught up! Time to relax or plan ahead.\n"
                "Use /addtask to add new tasks.",
                parse_mode='Markdown'
            )
            return

        # Get recent mood log
        mood_logs = self.db.get_mood_logs(user_id, days=1)
        mood = None
        energy = None

        if mood_logs:
            latest_mood = mood_logs[0]
            mood = latest_mood.mood
            energy = latest_mood.energy_level

        # Format tasks for AI
        task_dicts = [
            {
                'id': t.id,
                'title': t.title,
                'priority': t.priority,
                'category': t.category,
                'deadline': t.deadline,
                'created_at': t.created_at
            }
            for t in tasks
        ]

        # Get AI suggestion
        suggestion = self.ai_suggestion.suggest_next_task(
            tasks=task_dicts,
            mood=mood,
            energy_level=energy,
            current_time=datetime.now()
        )

        if not suggestion or not suggestion.get('suggested_task'):
            await update.message.reply_text(
                "❌ Unable to generate suggestion. Please try again.",
                parse_mode='Markdown'
            )
            return

        # Format response
        task = suggestion['suggested_task']
        message = "🤖 *AI Task Recommendation*\n\n"

        if mood and energy:
            mood_emoji = self._get_mood_emoji(mood)
            message += f"{mood_emoji} Based on your mood ({mood}) and energy ({energy}/10):\n\n"

        message += f"📋 *Suggested Task:*\n"
        message += f"   #{task['id']} {task['title']}\n"
        message += f"   🎯 Priority: {task['priority'].title()}\n"
        message += f"   📁 Category: {task['category'].title()}\n"

        if task.get('deadline'):
            message += f"   ⏰ Deadline: {task['deadline'].strftime('%b %d, %I:%M %p')}\n"

        message += f"\n💡 *Why this task?*\n{suggestion['reasoning']}\n"

        if suggestion.get('estimated_duration'):
            message += f"\n⏱️ *Estimated Time:* {suggestion['estimated_duration']}\n"

        if suggestion.get('productivity_tip'):
            message += f"\n✨ *Pro Tip:* {suggestion['productivity_tip']}\n"

        if suggestion.get('alternative_task'):
            alt = suggestion['alternative_task']
            message += f"\n🔄 *Alternative:* #{alt['id']} {alt['title']}"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def daily_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Generate AI daily plan

        Usage: /dailyplan [hours]
        """
        user_id = update.effective_user.id

        # Check premium
        user = self.db.get_user(user_id)
        if not user or not user.premium_status:
            await update.message.reply_text(
                "🔒 AI Daily Planning is a Premium feature. Use /premium to upgrade!",
                parse_mode='Markdown'
            )
            return

        # Get available hours
        hours = 8
        if context.args:
            try:
                hours = int(context.args[0])
                hours = min(hours, 16)  # Max 16 hours
            except ValueError:
                pass

        await update.message.reply_text(f"📅 Creating your optimized plan for {hours} hours...")

        # Get tasks
        tasks = self.db.get_user_tasks(user_id, status='pending')

        if not tasks:
            await update.message.reply_text(
                "🎉 No tasks to schedule! You're all caught up.",
                parse_mode='Markdown'
            )
            return

        # Get mood
        mood_logs = self.db.get_mood_logs(user_id, days=1)
        mood = energy = None
        if mood_logs:
            mood = mood_logs[0].mood
            energy = mood_logs[0].energy_level

        # Format tasks
        task_dicts = [
            {
                'title': t.title,
                'priority': t.priority,
                'category': t.category,
                'deadline': t.deadline
            }
            for t in tasks
        ]

        # Generate plan
        plan = self.ai_suggestion.generate_daily_plan(
            tasks=task_dicts,
            available_hours=hours,
            mood=mood,
            energy_level=energy
        )

        if plan:
            message = f"📅 *Your Optimized Daily Plan ({hours} hours)*\n\n{plan}"
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Unable to generate plan. Please try again.",
                parse_mode='Markdown'
            )

    async def brainstorm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Start brainstorming session

        Usage: /brainstorm
        """
        user_id = update.effective_user.id

        # Check premium
        user = self.db.get_user(user_id)
        if not user or not user.premium_status:
            await update.message.reply_text(
                "🧠 *Brainstorm Assistant* is a Premium feature!\n\n"
                "Get AI-powered idea generation:\n"
                "• Generate creative ideas on any topic\n"
                "• Expand and refine ideas\n"
                "• Create action plans\n"
                "• Connect ideas from your notes\n\n"
                "Use /premium to upgrade!",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "🧠 *Brainstorm Assistant*\n\n"
            "What topic would you like to brainstorm about?\n\n"
            "Examples:\n"
            "• Product features for my app\n"
            "• Ways to improve productivity\n"
            "• Content ideas for my blog\n"
            "• Weekend project ideas\n\n"
            "Or /cancel to exit.",
            parse_mode='Markdown'
        )

        return BRAINSTORM_TOPIC

    async def topic_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle brainstorm topic"""
        user_id = update.effective_user.id
        topic = update.message.text

        context.user_data['brainstorm_topic'] = topic

        await update.message.reply_text(f"🤖 Generating ideas for: *{topic}*...", parse_mode='Markdown')

        # Get related notes for context
        notes = self.db.search_notes(user_id, topic.split()[0])  # Search first word
        related_notes = [note.content[:200] for note in notes[:5]]

        # Generate ideas
        result = self.brainstorm.generate_ideas(
            topic=topic,
            related_notes=related_notes if related_notes else None,
            count=5
        )

        if not result or not result.get('ideas'):
            await update.message.reply_text(
                "❌ Unable to generate ideas. Please try a different topic.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Store ideas
        context.user_data['brainstorm_ideas'] = result['ideas']

        # Format ideas
        message = f"💡 *Ideas for: {topic}*\n\n"

        for i, idea in enumerate(result['ideas'], 1):
            message += f"{i}. *{idea['title']}*\n"
            message += f"   {idea['description']}\n"
            message += f"   ⏱️ {idea.get('estimated_time', 'N/A')} | "
            message += f"🎯 {idea.get('difficulty', 'medium').title()}\n\n"

        message += "\nReply with a number (1-5) to:\n"
        message += "• Expand the idea\n"
        message += "• Get action steps\n"
        message += "• Save as note/task\n\n"
        message += "Or /done to finish brainstorming."

        await update.message.reply_text(message, parse_mode='Markdown')

        return IDEA_SELECTION

    async def idea_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle idea selection"""
        try:
            selection = int(update.message.text)
            if not 1 <= selection <= 5:
                raise ValueError()
        except ValueError:
            await update.message.reply_text(
                "Please send a number between 1 and 5, or /done to finish.",
                parse_mode='Markdown'
            )
            return IDEA_SELECTION

        ideas = context.user_data.get('brainstorm_ideas', [])
        if not ideas:
            await update.message.reply_text("Session expired. Use /brainstorm to start again.")
            return ConversationHandler.END

        selected_idea = ideas[selection - 1]
        context.user_data['selected_idea'] = selected_idea

        # Show action options
        keyboard = [
            [
                InlineKeyboardButton("📝 Expand Idea", callback_data='expand_idea'),
                InlineKeyboardButton("🎯 Action Plan", callback_data='action_plan')
            ],
            [
                InlineKeyboardButton("💾 Save as Note", callback_data='save_note'),
                InlineKeyboardButton("✅ Save as Task", callback_data='save_task')
            ],
            [
                InlineKeyboardButton("🔙 Back to Ideas", callback_data='back_ideas')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = f"✨ *Selected Idea:*\n\n"
        message += f"*{selected_idea['title']}*\n\n"
        message += f"{selected_idea['description']}\n\n"
        message += "What would you like to do?"

        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

        return IDEA_ACTION

    async def idea_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle idea action buttons"""
        query = update.callback_query
        await query.answer()

        action = query.data
        selected_idea = context.user_data.get('selected_idea')

        if not selected_idea:
            await query.edit_message_text("Session expired. Use /brainstorm to start again.")
            return ConversationHandler.END

        if action == 'back_ideas':
            # Show ideas again
            topic = context.user_data.get('brainstorm_topic', 'your topic')
            ideas = context.user_data.get('brainstorm_ideas', [])

            message = f"💡 *Ideas for: {topic}*\n\n"
            for i, idea in enumerate(ideas, 1):
                message += f"{i}. *{idea['title']}*\n"
                message += f"   {idea['description']}\n\n"

            message += "Reply with a number (1-5) or /done to finish."

            await query.edit_message_text(message, parse_mode='Markdown')
            return IDEA_SELECTION

        elif action == 'expand_idea':
            await query.edit_message_text("🔄 Expanding idea with more details...")

            expanded = self.brainstorm.expand_idea(
                idea=selected_idea['title'],
                context=selected_idea['description']
            )

            if expanded:
                message = f"📖 *Expanded Idea*\n\n{expanded}"
                await query.message.reply_text(message, parse_mode='Markdown')
            else:
                await query.message.reply_text("❌ Unable to expand. Please try again.")

            return IDEA_ACTION

        elif action == 'action_plan':
            await query.edit_message_text("📋 Creating action plan...")

            plan = self.brainstorm.generate_action_plan(selected_idea['title'])

            if plan:
                message = f"🎯 *Action Plan: {selected_idea['title']}*\n\n"
                message += f"**Goal:** {plan['goal']}\n\n"
                message += f"**Timeline:** {plan['total_timeline']}\n\n"
                message += f"**Next Step:** {plan['next_immediate_action']}\n\n"
                message += "**Milestones:**\n"

                for i, milestone in enumerate(plan['milestones'], 1):
                    message += f"\n{i}. *{milestone['title']}* ({milestone['estimated_duration']})\n"
                    for action in milestone['actions'][:3]:
                        message += f"   • {action}\n"

                await query.message.reply_text(message, parse_mode='Markdown')
            else:
                await query.message.reply_text("❌ Unable to create plan.")

            return IDEA_ACTION

        elif action == 'save_note':
            user_id = update.effective_user.id
            note_content = f"{selected_idea['title']}\n\n{selected_idea['description']}"

            success = self.db.create_note(
                user_id=user_id,
                content=note_content,
                category='ideas'
            )

            if success:
                await query.edit_message_text(
                    f"✅ Saved as note!\n\nUse /notes to view all your notes.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Unable to save note.")

            return ConversationHandler.END

        elif action == 'save_task':
            user_id = update.effective_user.id

            success = self.db.create_task(
                user_id=user_id,
                title=selected_idea['title'],
                description=selected_idea['description'],
                category='personal',
                priority='medium'
            )

            if success:
                await query.edit_message_text(
                    f"✅ Saved as task!\n\nUse /tasks to view all your tasks.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Unable to save task.")

            return ConversationHandler.END

    async def done_brainstorming(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Finish brainstorming session"""
        topic = context.user_data.get('brainstorm_topic', 'your topic')

        await update.message.reply_text(
            f"✅ *Brainstorming session complete!*\n\n"
            f"Topic: {topic}\n\n"
            f"💡 Ideas are temporary - save the ones you like as notes or tasks!\n\n"
            f"Use /brainstorm anytime for more ideas.",
            parse_mode='Markdown'
        )

        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel operation"""
        await update.message.reply_text("❌ Operation cancelled.")
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

    def get_brainstorm_handler(self):
        """Get conversation handler for brainstorming"""
        return ConversationHandler(
            entry_points=[CommandHandler('brainstorm', self.brainstorm)],
            states={
                BRAINSTORM_TOPIC: [
                    CommandHandler('cancel', self.cancel),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.topic_received)
                ],
                IDEA_SELECTION: [
                    CommandHandler('done', self.done_brainstorming),
                    CommandHandler('cancel', self.cancel),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.idea_selected)
                ],
                IDEA_ACTION: [
                    CallbackQueryHandler(self.idea_action),
                    CommandHandler('done', self.done_brainstorming),
                    CommandHandler('cancel', self.cancel)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            allow_reentry=True
        )