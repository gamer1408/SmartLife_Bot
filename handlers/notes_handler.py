"""
Notes Handler - Telegram bot handlers for note commands and voice messages
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    filters, ConversationHandler, CallbackQueryHandler
)
from services.note_service import NoteService
from services.voice_service import VoiceService
from database.db_manager import DatabaseManager
import traceback

# Conversation states
AWAITING_NOTE_TITLE, AWAITING_NOTE_CONTENT, AWAITING_NOTE_CATEGORY = range(3)


class NotesHandler:
    """Handler for all note-related commands and voice messages"""

    def __init__(self, db_manager: DatabaseManager, voice_service: VoiceService):
        self.db = db_manager
        self.note_service = NoteService(db_manager)
        self.voice_service = voice_service

    def get_handlers(self):
        """Get all note-related handlers"""
        return [
            # Note creation conversation
            ConversationHandler(
                entry_points=[CommandHandler('newnote', self.start_note_creation)],
                states={
                    AWAITING_NOTE_TITLE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_note_title)
                    ],
                    AWAITING_NOTE_CONTENT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_note_content)
                    ],
                    AWAITING_NOTE_CATEGORY: [
                        CallbackQueryHandler(self.receive_note_category)
                    ]
                },
                fallbacks=[CommandHandler('cancel', self.cancel_note_creation)]
            ),

            # Quick note (single message)
            CommandHandler('quicknote', self.quick_note),

            # Note management
            CommandHandler('notes', self.list_notes),
            CommandHandler('viewnote', self.view_note),
            CommandHandler('editnote', self.edit_note),
            CommandHandler('deletenote', self.delete_note),

            # Search and organization
            CommandHandler('searchnotes', self.search_notes),
            CommandHandler('tags', self.list_tags),
            CommandHandler('categories', self.list_categories),

            # Voice message handler
            MessageHandler(filters.VOICE, self.handle_voice_message)
        ]

    # === Note Creation ===

    async def start_note_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start interactive note creation"""
        user_id = update.effective_user.id

        # Check user exists
        user = self.db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Use /start first.")
            return ConversationHandler.END

        await update.message.reply_text(
            "📝 **Create New Note**\n\n"
            "Let's create a note together!\n\n"
            "**Step 1:** What's the title of your note?\n\n"
            "_Type /cancel to stop_",
            parse_mode='Markdown'
        )

        return AWAITING_NOTE_TITLE

    async def receive_note_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive note title"""
        title = update.message.text.strip()

        if len(title) > 200:
            await update.message.reply_text(
                "❌ Title too long! Maximum 200 characters.\n"
                "Please send a shorter title:"
            )
            return AWAITING_NOTE_TITLE

        # Store title in context
        context.user_data['note_title'] = title

        await update.message.reply_text(
            f"✅ Title: **{title}**\n\n"
            "**Step 2:** Now write your note content.\n\n"
            "✨ _You can use formatting:_\n"
            "• **Bold text** with `**text**`\n"
            "• _Italic text_ with `*text*`\n"
            "• `Code` with `` `code` ``\n"
            "• Add #hashtags for tagging\n\n"
            "_Type /cancel to stop_",
            parse_mode='Markdown'
        )

        return AWAITING_NOTE_CONTENT

    async def receive_note_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive note content"""
        content = update.message.text.strip()

        if len(content) > 10000:
            await update.message.reply_text(
                "❌ Content too long! Maximum 10,000 characters.\n"
                "Please send shorter content:"
            )
            return AWAITING_NOTE_CONTENT

        # Store content
        context.user_data['note_content'] = content

        # Get user's categories
        user_id = update.effective_user.id
        categories = self.note_service.get_categories(user_id)

        # Create category selection keyboard
        keyboard = []
        for cat in categories[:10]:  # Show up to 10 recent
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])

        keyboard.append([InlineKeyboardButton("➕ New Category", callback_data="cat_new")])
        keyboard.append([InlineKeyboardButton("⏭️ Skip Category", callback_data="cat_skip")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "✅ Content saved!\n\n"
            "**Step 3:** Choose a category (optional):",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return AWAITING_NOTE_CATEGORY

    async def receive_note_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive category selection"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        category = None

        if query.data == "cat_new":
            await query.edit_message_text(
                "📁 Please type the new category name:"
            )
            # Would need another state for custom category
            # For simplicity, we'll skip
            category = "General"
        elif query.data == "cat_skip":
            category = None
        else:
            category = query.data.replace("cat_", "")

        # Create the note
        try:
            title = context.user_data['note_title']
            content = context.user_data['note_content']

            note = self.note_service.create_note(
                user_id=user_id,
                title=title,
                content=content,
                category=category
            )

            tags_text = ""
            if note['tags']:
                tags_text = f"\n🏷️ Tags: {', '.join(f'#{tag}' for tag in note['tags'])}"

            await query.edit_message_text(
                f"✅ **Note Created!**\n\n"
                f"📝 **{note['title']}**\n"
                f"📁 Category: {note['category'] or 'None'}"
                f"{tags_text}\n"
                f"🆔 Note ID: `{note['id']}`\n\n"
                f"_Use `/viewnote {note['id']}` to view it_",
                parse_mode='Markdown'
            )

            # Clear context
            context.user_data.clear()

        except Exception as e:
            await query.edit_message_text(
                f"❌ Error creating note: {str(e)}\n"
                "Please try again with /newnote"
            )

        return ConversationHandler.END

    async def cancel_note_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel note creation"""
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Note creation cancelled.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    async def quick_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create a quick note in one command"""
        user_id = update.effective_user.id

        # Check user
        user = self.db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Use /start first.")
            return

        # Parse command
        if not context.args:
            await update.message.reply_text(
                "📝 **Quick Note**\n\n"
                "Usage: `/quicknote Your note content here`\n\n"
                "First sentence becomes title, rest is content.\n"
                "Add #hashtags for tagging!",
                parse_mode='Markdown'
            )
            return

        # Get full text
        full_text = ' '.join(context.args)

        # Split into title and content (first sentence as title)
        parts = full_text.split('.', 1)
        title = parts[0].strip()[:200]  # Max 200 chars
        content = parts[1].strip() if len(parts) > 1 else full_text

        try:
            note = self.note_service.create_note(
                user_id=user_id,
                title=title,
                content=content
            )

            tags_text = ""
            if note['tags']:
                tags_text = f"\n🏷️ Tags: {', '.join(f'#{tag}' for tag in note['tags'])}"

            await update.message.reply_text(
                f"✅ **Quick Note Saved!**\n\n"
                f"📝 **{note['title']}**\n"
                f"🆔 ID: `{note['id']}`"
                f"{tags_text}",
                parse_mode='Markdown'
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    # === Note Management ===

    async def list_notes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List user's notes"""
        user_id = update.effective_user.id

        # Get category filter if provided
        category = context.args[0] if context.args else None

        notes = self.note_service.list_notes(user_id, category=category, limit=20)

        if not notes:
            msg = "📝 No notes found."
            if category:
                msg += f" in category '{category}'"
            await update.message.reply_text(msg)
            return

        # Format notes list
        msg = f"📝 **Your Notes**"
        if category:
            msg += f" (Category: {category})"
        msg += f"\n\n_Showing {len(notes)} notes_\n\n"

        for note in notes:
            tags = f" {', '.join(f'#{t}' for t in note['tags'])}" if note['tags'] else ""

            msg += (
                f"🆔 `{note['id']}` • **{note['title']}**\n"
                f"📁 {note['category'] or 'Uncategorized'}{tags}\n"
                f"_{note['content']}_\n\n"
            )

        msg += "_Use `/viewnote <id>` to view full note_"

        await update.message.reply_text(msg, parse_mode='Markdown')

    async def view_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View a specific note"""
        user_id = update.effective_user.id

        if not context.args:
            await update.message.reply_text(
                "Usage: `/viewnote <note_id>`\n\n"
                "Use /notes to see your note IDs",
                parse_mode='Markdown'
            )
            return

        try:
            note_id = int(context.args[0])
            note = self.note_service.get_note(note_id, user_id)

            if not note:
                await update.message.reply_text("❌ Note not found.")
                return

            # Format note
            tags_text = ""
            if note['tags']:
                tags_text = f"\n🏷️ Tags: {', '.join(f'#{tag}' for tag in note['tags'])}"

            msg = (
                f"📝 **{note['title']}**\n"
                f"🆔 ID: `{note['id']}`\n"
                f"📁 Category: {note['category'] or 'None'}"
                f"{tags_text}\n"
                f"📅 Created: {note['created_at']}\n\n"
                f"---\n\n"
                f"{note['content']}"
            )

            await update.message.reply_text(msg, parse_mode='Markdown')

        except ValueError:
            await update.message.reply_text("❌ Invalid note ID. Must be a number.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def edit_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Edit a note (simplified version)"""
        await update.message.reply_text(
            "📝 **Edit Note**\n\n"
            "To edit a note:\n"
            "1. Use `/viewnote <id>` to see current content\n"
            "2. Use `/deletenote <id>` to remove it\n"
            "3. Create a new note with updated content\n\n"
            "_Full editing coming in Phase 6!_",
            parse_mode='Markdown'
        )

    async def delete_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a note"""
        user_id = update.effective_user.id

        if not context.args:
            await update.message.reply_text(
                "Usage: `/deletenote <note_id>`",
                parse_mode='Markdown'
            )
            return

        try:
            note_id = int(context.args[0])

            if self.note_service.delete_note(note_id, user_id):
                await update.message.reply_text("✅ Note deleted successfully!")
            else:
                await update.message.reply_text("❌ Note not found or already deleted.")

        except ValueError:
            await update.message.reply_text("❌ Invalid note ID.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    # === Search ===

    async def search_notes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search notes by text or tags"""
        user_id = update.effective_user.id

        if not context.args:
            await update.message.reply_text(
                "🔍 **Search Notes**\n\n"
                "Usage: `/searchnotes <query>`\n\n"
                "Examples:\n"
                "• `/searchnotes meeting` - Find notes about meetings\n"
                "• `/searchnotes #work` - Find notes with #work tag\n"
                "• `/searchnotes project ideas` - Search for text",
                parse_mode='Markdown'
            )
            return

        query = ' '.join(context.args)

        # Extract tags from query
        tags = [word[1:] for word in context.args if word.startswith('#')]
        search_text = ' '.join(word for word in context.args if not word.startswith('#'))

        results = self.note_service.search_notes(
            user_id=user_id,
            query=search_text,
            tags=tags if tags else None,
            limit=20
        )

        if not results:
            await update.message.reply_text(f"🔍 No notes found for: _{query}_", parse_mode='Markdown')
            return

        msg = f"🔍 **Search Results**: _{query}_\n\n_Found {len(results)} notes_\n\n"

        for result in results[:10]:  # Show top 10
            tags_text = f" {', '.join(f'#{t}' for t in result['tags'])}" if result['tags'] else ""

            msg += (
                f"🆔 `{result['id']}` • **{result['title']}**\n"
                f"📁 {result['category']}{tags_text}\n"
                f"_{result['content']}_\n\n"
            )

        msg += "_Use `/viewnote <id>` to read full note_"

        await update.message.reply_text(msg, parse_mode='Markdown')

    async def list_tags(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all tags used by user"""
        user_id = update.effective_user.id

        tags = self.note_service.get_all_tags(user_id)

        if not tags:
            await update.message.reply_text("🏷️ You haven't used any tags yet!")
            return

        msg = f"🏷️ **Your Tags** ({len(tags)} total)\n\n"
        msg += ', '.join(f'#{tag}' for tag in sorted(tags))
        msg += "\n\n_Use `/searchnotes #tagname` to find notes_"

        await update.message.reply_text(msg, parse_mode='Markdown')

    async def list_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all note categories"""
        user_id = update.effective_user.id

        categories = self.note_service.get_categories(user_id)

        if not categories:
            await update.message.reply_text("📁 No categories yet!")
            return

        msg = f"📁 **Your Categories** ({len(categories)} total)\n\n"

        for cat in categories:
            msg += f"• {cat}\n"

        msg += "\n_Use `/notes <category>` to filter_"

        await update.message.reply_text(msg, parse_mode='Markdown')

    # === Voice Messages ===

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice message and convert to note"""
        user_id = update.effective_user.id

        # Check user
        user = self.db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ Use /start first.")
            return

        # Notify processing
        status_msg = await update.message.reply_text(
            "🎤 Transcribing voice message...",
            parse_mode='Markdown'
        )

        try:
            # Get voice file
            voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)

            # Download audio
            audio_data = await file.download_as_bytearray()

            # Transcribe
            transcription = await self.voice_service.transcribe_voice_message(
                audio_data=bytes(audio_data),
                file_format='ogg'
            )

            # Create note from transcription
            text = transcription['text']

            # First 50 chars as title
            title = text[:50] + ("..." if len(text) > 50 else "")

            # Format content with metadata
            content = self.voice_service.format_transcription_for_note(
                transcription,
                include_metadata=True
            )

            # Save note
            note = self.note_service.create_note(
                user_id=user_id,
                title=f"🎤 {title}",
                content=content,
                category="Voice Notes"
            )

            await status_msg.edit_text(
                f"✅ **Voice Note Saved!**\n\n"
                f"📝 **{note['title']}**\n"
                f"🆔 ID: `{note['id']}`\n\n"
                f"_Transcription:_\n{text}",
                parse_mode='Markdown'
            )

        except Exception as e:
            print(f"Voice transcription error: {traceback.format_exc()}")
            await status_msg.edit_text(
                f"❌ Error transcribing voice message: {str(e)}\n\n"
                "_Make sure OpenAI API key is configured_"
            )