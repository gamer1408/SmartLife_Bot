"""
Task Management Handler
Handles all task-related commands: add, view, complete, delete, edit
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, \
    filters
from datetime import datetime, timedelta
import logging

from database.db_manager import DatabaseManager
from utils.keyboards import get_task_category_keyboard, get_task_list_keyboard, get_main_menu_keyboard

# Conversation states
WAITING_TASK_TITLE, WAITING_TASK_CATEGORY, WAITING_TASK_DEADLINE, WAITING_TASK_PRIORITY = range(4)

logger = logging.getLogger(__name__)


class TaskHandler:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def add_task_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the add task conversation"""
        user_id = update.effective_user.id

        # Check free tier limits
        user = self.db.get_user(user_id)
        if not user['premium_status']:
            today_tasks = self.db.get_tasks_count_today(user_id)
            if today_tasks >= 20:
                await update.message.reply_text(
                    "⚠️ Free tier limit reached!\n\n"
                    "You've added 20 tasks today. Upgrade to Premium for unlimited tasks!\n\n"
                    "Use /premium to learn more.",
                    reply_markup=get_main_menu_keyboard()
                )
                return ConversationHandler.END

        await update.message.reply_text(
            "📝 *Add New Task*\n\n"
            "What task would you like to add?\n"
            "Type the task title (e.g., 'Finish project report')\n\n"
            "Or send /cancel to cancel.",
            parse_mode='Markdown'
        )
        return WAITING_TASK_TITLE

    async def receive_task_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive task title and ask for category"""
        task_title = update.message.text.strip()

        # Validate title length
        if len(task_title) > 200:
            await update.message.reply_text(
                "❌ Task title is too long! Please keep it under 200 characters.\n"
                "Try again or send /cancel to cancel."
            )
            return WAITING_TASK_TITLE

        if len(task_title) < 3:
            await update.message.reply_text(
                "❌ Task title is too short! Please provide at least 3 characters.\n"
                "Try again or send /cancel to cancel."
            )
            return WAITING_TASK_TITLE

        # Store task title in context
        context.user_data['task_title'] = task_title

        await update.message.reply_text(
            f"✅ Task: *{task_title}*\n\n"
            "📁 Select a category:",
            parse_mode='Markdown',
            reply_markup=get_task_category_keyboard()
        )
        return WAITING_TASK_CATEGORY

    async def receive_task_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive category and ask for deadline"""
        query = update.callback_query
        await query.answer()

        category = query.data.replace('category_', '')
        context.user_data['task_category'] = category

        # Deadline options keyboard
        keyboard = [
            [
                InlineKeyboardButton("📅 Today", callback_data='deadline_today'),
                InlineKeyboardButton("📅 Tomorrow", callback_data='deadline_tomorrow')
            ],
            [
                InlineKeyboardButton("📅 This Week", callback_data='deadline_week'),
                InlineKeyboardButton("📅 Next Week", callback_data='deadline_nextweek')
            ],
            [
                InlineKeyboardButton("📅 Custom Date", callback_data='deadline_custom'),
                InlineKeyboardButton("⏭️ No Deadline", callback_data='deadline_none')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ Category: *{category.title()}*\n\n"
            "⏰ When is the deadline?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return WAITING_TASK_DEADLINE

    async def receive_task_deadline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive deadline and ask for priority"""
        query = update.callback_query
        await query.answer()

        deadline_choice = query.data.replace('deadline_', '')

        # Calculate deadline
        deadline = None
        deadline_text = "No deadline"

        if deadline_choice == 'today':
            deadline = datetime.now() + timedelta(hours=8)
            deadline_text = "Today (8 PM)"
        elif deadline_choice == 'tomorrow':
            deadline = datetime.now() + timedelta(days=1)
            deadline_text = "Tomorrow"
        elif deadline_choice == 'week':
            deadline = datetime.now() + timedelta(days=7)
            deadline_text = "This week"
        elif deadline_choice == 'nextweek':
            deadline = datetime.now() + timedelta(days=14)
            deadline_text = "Next week"
        elif deadline_choice == 'custom':
            await query.edit_message_text(
                "📅 Please enter the deadline date in format:\n"
                "*DD-MM-YYYY* or *DD-MM-YYYY HH:MM*\n\n"
                "Example: 15-01-2026 or 15-01-2026 14:30\n\n"
                "Or send /cancel to cancel.",
                parse_mode='Markdown'
            )
            context.user_data['waiting_custom_deadline'] = True
            return WAITING_TASK_DEADLINE

        context.user_data['task_deadline'] = deadline

        # Priority keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔥 High", callback_data='priority_3'),
                InlineKeyboardButton("⚡ Medium", callback_data='priority_2')
            ],
            [
                InlineKeyboardButton("📌 Low", callback_data='priority_1'),
                InlineKeyboardButton("➡️ Skip", callback_data='priority_0')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ Deadline: *{deadline_text}*\n\n"
            "⭐ What's the priority?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return WAITING_TASK_PRIORITY

    async def receive_custom_deadline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle custom deadline input"""
        if not context.user_data.get('waiting_custom_deadline'):
            return WAITING_TASK_DEADLINE

        date_text = update.message.text.strip()

        try:
            # Try parsing with time
            if ' ' in date_text:
                deadline = datetime.strptime(date_text, '%d-%m-%Y %H:%M')
            else:
                deadline = datetime.strptime(date_text, '%d-%m-%Y')

            # Check if date is in the past
            if deadline < datetime.now():
                await update.message.reply_text(
                    "❌ Deadline cannot be in the past!\n"
                    "Please enter a future date or send /cancel to cancel."
                )
                return WAITING_TASK_DEADLINE

            context.user_data['task_deadline'] = deadline
            context.user_data['waiting_custom_deadline'] = False

            # Priority keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🔥 High", callback_data='priority_3'),
                    InlineKeyboardButton("⚡ Medium", callback_data='priority_2')
                ],
                [
                    InlineKeyboardButton("📌 Low", callback_data='priority_1'),
                    InlineKeyboardButton("➡️ Skip", callback_data='priority_0')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Deadline: *{deadline.strftime('%d %B %Y at %H:%M')}*\n\n"
                "⭐ What's the priority?",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return WAITING_TASK_PRIORITY

        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format!\n\n"
                "Please use: *DD-MM-YYYY* or *DD-MM-YYYY HH:MM*\n"
                "Example: 15-01-2026 or 15-01-2026 14:30\n\n"
                "Or send /cancel to cancel.",
                parse_mode='Markdown'
            )
            return WAITING_TASK_DEADLINE

    async def receive_task_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive priority and save task"""
        query = update.callback_query
        await query.answer()

        priority = int(query.data.replace('priority_', ''))

        # Get all task data
        user_id = update.effective_user.id
        title = context.user_data['task_title']
        category = context.user_data['task_category']
        deadline = context.user_data.get('task_deadline')

        # Save task to database
        task_id = self.db.add_task(
            user_id=user_id,
            title=title,
            category=category,
            deadline=deadline,
            priority=priority
        )

        # Clear context
        context.user_data.clear()

        # Format response
        priority_emoji = {0: "➡️", 1: "📌", 2: "⚡", 3: "🔥"}
        category_emoji = {
            'work': '💼',
            'study': '📚',
            'personal': '🏠',
            'urgent': '🔥'
        }

        deadline_text = "No deadline"
        if deadline:
            deadline_text = deadline.strftime('%d %B %Y')

        await query.edit_message_text(
            "✅ *Task Added Successfully!*\n\n"
            f"📝 *Title:* {title}\n"
            f"{category_emoji.get(category, '📁')} *Category:* {category.title()}\n"
            f"📅 *Deadline:* {deadline_text}\n"
            f"{priority_emoji[priority]} *Priority:* {['Default', 'Low', 'Medium', 'High'][priority]}\n\n"
            f"Task ID: #{task_id}\n\n"
            "Use /tasks to view all your tasks!",
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )

        return ConversationHandler.END

    async def view_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View all tasks with filters"""
        user_id = update.effective_user.id

        # Get filter from callback or default to 'all'
        filter_type = 'all'
        if update.callback_query:
            await update.callback_query.answer()
            filter_type = update.callback_query.data.replace('filter_', '')

        # Get tasks based on filter
        if filter_type == 'all':
            tasks = self.db.get_user_tasks(user_id)
        elif filter_type == 'pending':
            tasks = self.db.get_user_tasks(user_id, status='pending')
        elif filter_type == 'completed':
            tasks = self.db.get_user_tasks(user_id, status='completed')
        elif filter_type == 'today':
            tasks = self.db.get_tasks_due_today(user_id)
        elif filter_type in ['work', 'study', 'personal', 'urgent']:
            tasks = self.db.get_user_tasks(user_id, category=filter_type)
        else:
            tasks = self.db.get_user_tasks(user_id)

        if not tasks:
            message = "📋 *No tasks found!*\n\n"
            if filter_type == 'all':
                message += "You haven't added any tasks yet.\nUse /addtask to create your first task!"
            else:
                message += f"No {filter_type} tasks found.\nTry a different filter!"

            keyboard = [
                [InlineKeyboardButton("➕ Add Task", callback_data='action_addtask')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            return

        # Format tasks
        message = f"📋 *Your Tasks* ({filter_type.title()})\n\n"

        category_emoji = {
            'work': '💼',
            'study': '📚',
            'personal': '🏠',
            'urgent': '🔥'
        }
        priority_emoji = {0: "", 1: "📌", 2: "⚡", 3: "🔥"}

        for i, task in enumerate(tasks[:10], 1):  # Limit to 10 tasks per page
            status = "✅" if task['status'] == 'completed' else "⏳"
            emoji = category_emoji.get(task['category'], '📁')
            priority = priority_emoji.get(task['priority'], '')

            deadline_text = ""
            if task['deadline']:
                deadline = datetime.fromisoformat(task['deadline'])
                days_left = (deadline - datetime.now()).days

                if days_left < 0:
                    deadline_text = f"⚠️ Overdue by {abs(days_left)} days"
                elif days_left == 0:
                    deadline_text = "🔔 Due today"
                elif days_left == 1:
                    deadline_text = "📅 Due tomorrow"
                else:
                    deadline_text = f"📅 {days_left} days left"

            message += (
                f"{status} *#{task['task_id']}* {emoji} {priority}\n"
                f"   {task['title']}\n"
            )
            if deadline_text:
                message += f"   {deadline_text}\n"
            message += "\n"

        # Filter buttons
        keyboard = [
            [
                InlineKeyboardButton("📋 All", callback_data='filter_all'),
                InlineKeyboardButton("⏳ Pending", callback_data='filter_pending'),
                InlineKeyboardButton("✅ Done", callback_data='filter_completed')
            ],
            [
                InlineKeyboardButton("📅 Today", callback_data='filter_today'),
                InlineKeyboardButton("💼 Work", callback_data='filter_work'),
                InlineKeyboardButton("📚 Study", callback_data='filter_study')
            ],
            [
                InlineKeyboardButton("🏠 Personal", callback_data='filter_personal'),
                InlineKeyboardButton("🔥 Urgent", callback_data='filter_urgent')
            ],
            [InlineKeyboardButton("🔄 Refresh", callback_data='filter_' + filter_type)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message += "\n💡 *Quick Actions:*\n"
        message += "• `/complete <task_id>` - Mark as done\n"
        message += "• `/delete <task_id>` - Delete task\n"
        message += "• `/edit <task_id>` - Edit task"

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

    async def complete_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mark task as completed"""
        user_id = update.effective_user.id

        # Get task ID from command
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a task ID!\n\n"
                "Usage: `/complete <task_id>`\n"
                "Example: `/complete 5`",
                parse_mode='Markdown'
            )
            return

        try:
            task_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid task ID! Please provide a number.\n"
                "Example: `/complete 5`",
                parse_mode='Markdown'
            )
            return

        # Get task
        task = self.db.get_task(task_id, user_id)

        if not task:
            await update.message.reply_text(
                f"❌ Task #{task_id} not found!\n\n"
                "Use /tasks to see your task list.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        if task['status'] == 'completed':
            await update.message.reply_text(
                f"ℹ️ Task #{task_id} is already completed!\n\n"
                f"📝 {task['title']}",
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Complete task
        success = self.db.complete_task(task_id, user_id)

        if success:
            await update.message.reply_text(
                f"✅ *Task Completed!*\n\n"
                f"📝 {task['title']}\n\n"
                "Great job! Keep up the productivity! 🎉",
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Failed to complete task. Please try again.",
                reply_markup=get_main_menu_keyboard()
            )

    async def delete_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a task"""
        user_id = update.effective_user.id

        # Get task ID from command
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a task ID!\n\n"
                "Usage: `/delete <task_id>`\n"
                "Example: `/delete 5`",
                parse_mode='Markdown'
            )
            return

        try:
            task_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid task ID! Please provide a number.\n"
                "Example: `/delete 5`",
                parse_mode='Markdown'
            )
            return

        # Get task
        task = self.db.get_task(task_id, user_id)

        if not task:
            await update.message.reply_text(
                f"❌ Task #{task_id} not found!\n\n"
                "Use /tasks to see your task list.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Delete", callback_data=f'confirm_delete_{task_id}'),
                InlineKeyboardButton("❌ Cancel", callback_data='cancel_delete')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"⚠️ *Confirm Deletion*\n\n"
            f"Are you sure you want to delete this task?\n\n"
            f"📝 {task['title']}\n\n"
            "This action cannot be undone!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def confirm_delete_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and delete task"""
        query = update.callback_query
        await query.answer()

        if query.data == 'cancel_delete':
            await query.edit_message_text(
                "❌ Deletion cancelled.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        task_id = int(query.data.replace('confirm_delete_', ''))
        user_id = update.effective_user.id

        # Delete task
        success = self.db.delete_task(task_id, user_id)

        if success:
            await query.edit_message_text(
                f"✅ Task #{task_id} deleted successfully!",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Failed to delete task. Please try again.",
                reply_markup=get_main_menu_keyboard()
            )

    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel any ongoing conversation"""
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Operation cancelled.",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END


def get_task_conversation_handler(db_manager: DatabaseManager):
    """Create and return the task conversation handler"""
    handler = TaskHandler(db_manager)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addtask', handler.add_task_start)],
        states={
            WAITING_TASK_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.receive_task_title)
            ],
            WAITING_TASK_CATEGORY: [
                CallbackQueryHandler(handler.receive_task_category, pattern='^category_')
            ],
            WAITING_TASK_DEADLINE: [
                CallbackQueryHandler(handler.receive_task_deadline, pattern='^deadline_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.receive_custom_deadline)
            ],
            WAITING_TASK_PRIORITY: [
                CallbackQueryHandler(handler.receive_task_priority, pattern='^priority_')
            ],
        },
        fallbacks=[CommandHandler('cancel', handler.cancel_conversation)],
    )

    return handler, conv_handler