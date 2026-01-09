"""
SmartLife Bot - Telegram Keyboards
Reusable keyboard layouts for bot interactions
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard():
    """Main menu keyboard with primary features"""
    keyboard = [
        ["📝 Add Task", "✅ View Tasks"],
        ["💡 Add Note", "📚 My Notes"],
        ["📅 Calendar", "📊 Analytics"],
        ["⚙️ Settings", "❓ Help"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_premium_menu_keyboard():
    """Extended menu for premium users"""
    keyboard = [
        ["📝 Add Task", "✅ View Tasks"],
        ["💡 Add Note", "📚 My Notes"],
        ["📅 Calendar", "📊 Analytics"],
        ["😊 Log Mood", "🧠 Brainstorm"],
        ["⚙️ Settings", "❓ Help"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_task_category_keyboard():
    """Keyboard for selecting task category"""
    keyboard = [
        ["💼 Work", "📚 Study"],
        ["🏠 Personal", "🔥 Urgent"],
        ["❌ Cancel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_task_actions_keyboard(task_id):
    """Inline keyboard for task actions"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Complete", callback_data=f"complete_{task_id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{task_id}")
        ],
        [
            InlineKeyboardButton("⏰ Set Reminder", callback_data=f"remind_{task_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{task_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_mood_keyboard():
    """Keyboard for mood selection (premium feature)"""
    keyboard = [
        ["😴 Sleepy", "😫 Tired"],
        ["😋 Hungry", "😰 Stressed"],
        ["⚡ Energetic", "😊 Good"],
        ["❌ Cancel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_energy_level_keyboard():
    """Keyboard for energy level selection"""
    keyboard = [
        ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"],
        ["6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"],
        ["❌ Cancel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_idea_priority_keyboard():
    """Keyboard for idea priority tagging"""
    keyboard = [
        ["🔥 Urgent", "⏰ Later"],
        ["📝 Optional", "❌ Cancel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_yes_no_keyboard():
    """Simple Yes/No keyboard"""
    keyboard = [
        ["✅ Yes", "❌ No"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_task_filter_keyboard():
    """Inline keyboard for filtering tasks"""
    keyboard = [
        [
            InlineKeyboardButton("All", callback_data="filter_all"),
            InlineKeyboardButton("Pending", callback_data="filter_pending"),
            InlineKeyboardButton("Completed", callback_data="filter_completed")
        ],
        [
            InlineKeyboardButton("💼 Work", callback_data="filter_work"),
            InlineKeyboardButton("📚 Study", callback_data="filter_study"),
            InlineKeyboardButton("🏠 Personal", callback_data="filter_personal")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calendar_sync_keyboard():
    """Keyboard for calendar sync options"""
    keyboard = [
        [
            InlineKeyboardButton("🔗 Connect Google Calendar", callback_data="connect_calendar")
        ],
        [
            InlineKeyboardButton("🔄 Sync Now", callback_data="sync_calendar"),
            InlineKeyboardButton("⚙️ Settings", callback_data="calendar_settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_premium_upgrade_keyboard():
    """Keyboard for premium upgrade"""
    keyboard = [
        [
            InlineKeyboardButton("⭐ Upgrade to Premium", callback_data="upgrade_premium")
        ],
        [
            InlineKeyboardButton("📋 View Features", callback_data="premium_features"),
            InlineKeyboardButton("💰 Pricing", callback_data="premium_pricing")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard():
    """Simple cancel keyboard"""
    keyboard = [["❌ Cancel"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def remove_keyboard():
    """Remove custom keyboard"""
    from telegram import ReplyKeyboardRemove
    return ReplyKeyboardRemove()


def get_task_list_keyboard():
    return None