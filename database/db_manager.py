"""
SmartLife Bot - Database Manager
Handles database connection, initialization, and CRUD operations
"""
from typing import Optional, List, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import os

from database.models import Base, User, Task, Note, MoodLog, Reminder, ProductivityStat
from config import Config
from main import logger


class DatabaseManager:
    """Manages database connection and operations"""

    def __init__(self, db_path=None):
        """Initialize database connection"""
        if db_path is None:
            db_path = Config.DATABASE_PATH

        # Create SQLite database
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=Config.DEBUG)

        # Create session factory
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

        print(f"📦 Database initialized at: {db_path}")

    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(self.engine)
        print("✅ Database tables created successfully!")

    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(self.engine)
        print("⚠️ All tables dropped!")

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    # === USER OPERATIONS ===

    def get_or_create_user(self, user_id, telegram_username=None, first_name=None, last_name=None):
        """Get existing user or create new one"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()

            if not user:
                user = User(
                    user_id=user_id,
                    telegram_username=telegram_username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.commit()
                print(f"✅ New user created: {user_id}")
            else:
                # Update last active time
                user.last_active = datetime.utcnow()
                session.commit()

            return user
        except Exception as e:
            session.rollback()
            print(f"❌ Error in get_or_create_user: {e}")
            return None
        finally:
            session.close()

    def get_user(self, user_id):
        """Get user by ID"""
        session = self.get_session()
        try:
            return session.query(User).filter_by(user_id=user_id).first()
        finally:
            session.close()

    def update_user_premium(self, user_id, premium_status):
        """Update user premium status"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                user.premium = premium_status
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"❌ Error updating premium status: {e}")
            return False
        finally:
            session.close()

    # === TASK OPERATIONS ===

    def add_task(self, user_id, title, description=None, category=None, deadline=None):
        """Add a new task"""
        session = self.get_session()
        try:
            task = Task(
                user_id=user_id,
                title=title,
                description=description,
                category=category,
                deadline=deadline
            )
            session.add(task)
            session.commit()
            task_id = task.id
            return task_id
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding task: {e}")
            return None
        finally:
            session.close()

    def get_user_tasks(self, user_id, status='pending', limit=50):
        """Get user's tasks"""
        session = self.get_session()
        try:
            query = session.query(Task).filter_by(user_id=user_id)

            if status:
                query = query.filter_by(status=status)

            tasks = query.order_by(Task.created_at.desc()).limit(limit).all()
            return tasks
        finally:
            session.close()

    def complete_task(self, task_id, user_id):
        """Mark task as completed"""
        session = self.get_session()
        try:
            task = session.query(Task).filter_by(id=task_id, user_id=user_id).first()
            if task:
                task.status = 'completed'
                task.completed_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"❌ Error completing task: {e}")
            return False
        finally:
            session.close()

    def delete_task(self, task_id, user_id):
        """Delete a task"""
        session = self.get_session()
        try:
            task = session.query(Task).filter_by(id=task_id, user_id=user_id).first()
            if task:
                session.delete(task)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"❌ Error deleting task: {e}")
            return False
        finally:
            session.close()

    # === NOTE OPERATIONS ===

    def add_note(self, user_id, content, tags=None, category=None, is_idea=False):
        """Add a new note or idea"""
        session = self.get_session()
        try:
            note = Note(
                user_id=user_id,
                content=content,
                tags=tags,
                category=category,
                is_idea=is_idea
            )
            session.add(note)
            session.commit()
            return note.id
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding note: {e}")
            return None
        finally:
            session.close()

    def get_user_notes(self, user_id, limit=50):
        """Get user's notes"""
        session = self.get_session()
        try:
            notes = session.query(Note).filter_by(user_id=user_id) \
                .order_by(Note.created_at.desc()).limit(limit).all()
            return notes
        finally:
            session.close()

    def search_notes(self, user_id, keyword):
        """Search notes by keyword"""
        session = self.get_session()
        try:
            notes = session.query(Note).filter(
                Note.user_id == user_id,
                Note.content.contains(keyword)
            ).all()
            return notes
        finally:
            session.close()

    def create_note(
            self,
            user_id: int,
            title: str,
            content: str,
            category: Optional[str] = None,
            tags: Optional[List[str]] = None,
            linked_task_id: Optional[int] = None
    ):
        """Create a new note"""
        from database.models import Note

        session = self.Session()
        try:
            note = Note(
                user_id=user_id,
                title=title,
                content=content,
                category=category,
                tags=','.join(tags) if tags else None,
                linked_task_id=linked_task_id
            )
            session.add(note)
            session.commit()
            session.refresh(note)
            return note
        except Exception as e:
            session.rollback()
            print(f"Error creating note: {e}")
            raise
        finally:
            session.close()

    def get_note(self, note_id: int, user_id: int):
        """Get a specific note by ID"""
        from database.models import Note

        session = self.Session()
        try:
            note = session.query(Note).filter_by(
                id=note_id,
                user_id=user_id
            ).first()
            return note
        finally:
            session.close()

    def list_notes(
            self,
            user_id: int,
            category: Optional[str] = None,
            limit: int = 50
    ):
        """List user's notes"""
        from database.models import Note

        session = self.Session()
        try:
            query = session.query(Note).filter_by(user_id=user_id)

            if category:
                query = query.filter_by(category=category)

            notes = query.order_by(Note.created_at.desc()).limit(limit).all()
            return notes
        finally:
            session.close()

    def search_notes(
            self,
            user_id: int,
            query: str,
            category: Optional[str] = None,
            tags: Optional[List[str]] = None,
            limit: int = 20
    ):
        """Search notes by text, category, or tags"""
        from database.models import Note

        session = self.Session()
        try:
            q = session.query(Note).filter_by(user_id=user_id)

            # Text search
            if query:
                search_filter = f"%{query}%"
                q = q.filter(
                    (Note.title.like(search_filter)) |
                    (Note.content.like(search_filter))
                )

            # Category filter
            if category:
                q = q.filter_by(category=category)

            # Tag filter
            if tags:
                for tag in tags:
                    q = q.filter(Note.tags.like(f"%{tag}%"))

            notes = q.order_by(Note.updated_at.desc()).limit(limit).all()
            return notes
        finally:
            session.close()

    def update_note(
            self,
            note_id: int,
            user_id: int,
            **updates
    ) -> bool:
        """Update a note"""
        from database.models import Note

        session = self.Session()
        try:
            note = session.query(Note).filter_by(
                id=note_id,
                user_id=user_id
            ).first()

            if not note:
                return False

            for key, value in updates.items():
                if hasattr(note, key):
                    setattr(note, key, value)

            note.updated_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error updating note: {e}")
            return False
        finally:
            session.close()

    def delete_note(self, note_id: int, user_id: int) -> bool:
        """Delete a note"""
        from database.models import Note

        session = self.Session()
        try:
            note = session.query(Note).filter_by(
                id=note_id,
                user_id=user_id
            ).first()

            if not note:
                return False

            session.delete(note)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error deleting note: {e}")
            return False
        finally:
            session.close()

    def get_note_categories(self, user_id: int) -> List[str]:
        """Get all note categories for a user"""
        from database.models import Note

        session = self.Session()
        try:
            categories = session.query(Note.category).filter(
                Note.user_id == user_id,
                Note.category.isnot(None)
            ).distinct().all()

            return [cat[0] for cat in categories]
        finally:
            session.close()

    def get_all_note_tags(self, user_id: int) -> List[str]:
        """Get all tags used by a user"""
        from database.models import Note

        session = self.Session()
        try:
            notes = session.query(Note.tags).filter(
                Note.user_id == user_id,
                Note.tags.isnot(None)
            ).all()

            # Collect all tags
            all_tags = set()
            for note in notes:
                if note[0]:
                    tags = note[0].split(',')
                    all_tags.update(tags)

            return sorted(list(all_tags))
        finally:
            session.close()

    # === MOOD LOG OPERATIONS ===

    def add_mood_log(self, user_id, mood, energy_level, context=None):
        """Add a mood log entry (premium feature)"""
        session = self.get_session()
        try:
            mood_log = MoodLog(
                user_id=user_id,
                mood=mood,
                energy_level=energy_level,
                context=context
            )
            session.add(mood_log)
            session.commit()
            return mood_log.id
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding mood log: {e}")
            return None
        finally:
            session.close()

    def get_recent_mood_logs(self, user_id, limit=10):
        """Get user's recent mood logs"""
        session = self.get_session()
        try:
            logs = session.query(MoodLog).filter_by(user_id=user_id) \
                .order_by(MoodLog.timestamp.desc()).limit(limit).all()
            return logs
        finally:
            session.close()

    # === REMINDER OPERATIONS ===

    def add_reminder(self, user_id, reminder_time, message, task_id=None):
        """Add a new reminder"""
        session = self.get_session()
        try:
            reminder = Reminder(
                user_id=user_id,
                task_id=task_id,
                reminder_time=reminder_time,
                message=message
            )
            session.add(reminder)
            session.commit()
            return reminder.id
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding reminder: {e}")
            return None
        finally:
            session.close()

    def get_pending_reminders(self):
        """Get all pending reminders that need to be sent"""
        session = self.get_session()
        try:
            now = datetime.utcnow()
            reminders = session.query(Reminder).filter(
                Reminder.sent == False,
                Reminder.reminder_time <= now
            ).all()
            return reminders
        finally:
            session.close()

    def mark_reminder_sent(self, reminder_id):
        """Mark reminder as sent"""
        session = self.get_session()
        try:
            reminder = session.query(Reminder).filter_by(id=reminder_id).first()
            if reminder:
                reminder.sent = True
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"❌ Error marking reminder as sent: {e}")
            return False
        finally:
            session.close()

    # === STATISTICS ===

    def get_user_stats(self, user_id):
        """Get user statistics"""
        session = self.get_session()
        try:
            total_tasks = session.query(Task).filter_by(user_id=user_id).count()
            completed_tasks = session.query(Task).filter_by(
                user_id=user_id, status='completed'
            ).count()
            total_notes = session.query(Note).filter_by(user_id=user_id).count()

            return {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'total_notes': total_notes,
                'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            }
        finally:
            session.close()


# Create global database instance
db = DatabaseManager()

if __name__ == "__main__":
    # Test database creation
    print("\n🧪 Testing Database Manager...")
    db.create_tables()

    # Test user creation
    user = db.get_or_create_user(
        user_id=123456789,
        telegram_username="test_user",
        first_name="Test"
    )
    print(f"✅ User created/retrieved: {user}")

    # Test task creation
    task_id = db.add_task(
        user_id=123456789,
        title="Test Task",
        category="Work"
    )
    print(f"✅ Task created with ID: {task_id}")

    # Test note creation
    note_id = db.add_note(
        user_id=123456789,
        content="Test note content",
        is_idea=True
    )
    print(f"✅ Note created with ID: {note_id}")

    # Get stats
    stats = db.get_user_stats(123456789)
    print(f"✅ User stats: {stats}")

    print("\n✅ Database Manager tests passed!")


    # Add these methods to your DatabaseManager class in database/db_manager.py

    def log_mood(self, user_id: int, mood: str, energy_level: int, context: str) -> bool:
        """
        Log user's mood and energy level

        Args:
            user_id: Telegram user ID
            mood: Mood state
            energy_level: Energy level (1-10)
            context: What user is doing

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            from database.models import MoodLog

            mood_log = MoodLog(
                user_id=user_id,
                mood=mood,
                energy_level=energy_level,
                context=context,
                timestamp=datetime.utcnow()
            )

            session.add(mood_log)
            session.commit()
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Error logging mood: {e}")
            return False
        finally:
            session.close()


    def get_mood_logs(self, user_id: int, days: int = 7) -> List:
        """
        Get mood logs for user

        Args:
            user_id: Telegram user ID
            days: Number of days to look back

        Returns:
            List of mood log objects
        """
        session = self.Session()
        try:
            from database.models import MoodLog
            from datetime import datetime, timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            logs = session.query(MoodLog).filter(
                MoodLog.user_id == user_id,
                MoodLog.timestamp >= cutoff_date
            ).order_by(MoodLog.timestamp.desc()).all()

            return logs

        except Exception as e:
            logger.error(f"Error getting mood logs: {e}")
            return []
        finally:
            session.close()


    def get_user(self, user_id: int):
        """
        Get user by ID

        Args:
            user_id: Telegram user ID

        Returns:
            User object or None
        """
        session = self.Session()
        try:
            from database.models import User

            user = session.query(User).filter(
                User.telegram_id == user_id
            ).first()

            return user

        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
        finally:
            session.close()


    def set_premium_status(self, user_id: int, status: bool = True) -> bool:
        """
        Set user's premium status

        Args:
            user_id: Telegram user ID
            status: Premium status (True/False)

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            from database.models import User

            user = session.query(User).filter(
                User.telegram_id == user_id
            ).first()

            if user:
                user.premium_status = status
                session.commit()
                return True
            return False

        except Exception as e:
            session.rollback()
            logger.error(f"Error setting premium status: {e}")
            return False
        finally:
            session.close()


    def get_task_stats(self, user_id: int) -> Dict:
        """
        Get task statistics for user

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary with task stats
        """
        session = self.Session()
        try:
            from database.models import Task
            from sqlalchemy import func

            total_tasks = session.query(func.count(Task.id)).filter(
                Task.user_id == user_id
            ).scalar()

            completed_tasks = session.query(func.count(Task.id)).filter(
                Task.user_id == user_id,
                Task.status == 'completed'
            ).scalar()

            pending_tasks = session.query(func.count(Task.id)).filter(
                Task.user_id == user_id,
                Task.status == 'pending'
            ).scalar()

            return {
                'total': total_tasks or 0,
                'completed': completed_tasks or 0,
                'pending': pending_tasks or 0
            }

        except Exception as e:
            logger.error(f"Error getting task stats: {e}")
            return {'total': 0, 'completed': 0, 'pending': 0}
        finally:
            session.close()


    # Add these methods to your DatabaseManager class in database/db_manager.py

    def save_oauth_state(self, user_id: int, state: str) -> bool:
        """
        Save OAuth state for verification

        Args:
            user_id: Telegram user ID
            state: OAuth state string

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            user = session.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.oauth_state = state
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving OAuth state: {e}")
            return False
        finally:
            session.close()


    def save_calendar_tokens(self, user_id: int, tokens: str) -> bool:
        """
        Save Google Calendar OAuth tokens

        Args:
            user_id: Telegram user ID
            tokens: JSON string of tokens

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            user = session.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.calendar_tokens = tokens
                user.calendar_connected = True
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving calendar tokens: {e}")
            return False
        finally:
            session.close()


    def get_calendar_tokens(self, user_id: int) -> Optional[str]:
        """
        Get Google Calendar OAuth tokens

        Args:
            user_id: Telegram user ID

        Returns:
            JSON string of tokens or None
        """
        session = self.Session()
        try:
            user = session.query(User).filter(User.telegram_id == user_id).first()
            if user and user.calendar_connected:
                return user.calendar_tokens
            return None
        except Exception as e:
            logger.error(f"Error getting calendar tokens: {e}")
            return None
        finally:
            session.close()


    def delete_calendar_tokens(self, user_id: int) -> bool:
        """
        Delete calendar tokens (disconnect calendar)

        Args:
            user_id: Telegram user ID

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            user = session.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.calendar_tokens = None
                user.calendar_connected = False
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting calendar tokens: {e}")
            return False
        finally:
            session.close()


    def update_task_calendar_event(self, task_id: int, event_id: Optional[str]) -> bool:
        """
        Update task's calendar event ID

        Args:
            task_id: Task ID
            event_id: Google Calendar event ID or None to clear

        Returns:
            True if successful
        """
        session = self.Session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.calendar_event_id = event_id
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating task calendar event: {e}")
            return False
        finally:
            session.close()


    def get_task(self, task_id: int, user_id: int) -> Optional[Task]:
        """
        Get a single task by ID and user

        Args:
            task_id: Task ID
            user_id: User ID

        Returns:
            Task object or None
        """
        session = self.Session()
        try:
            task = session.query(Task).filter(
                Task.id == task_id,
                Task.user_id == user_id
            ).first()
            return task
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None
        finally:
            session.close()