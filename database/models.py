"""
SmartLife Bot - Database Models
SQLAlchemy ORM models for all database tables
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User table - stores Telegram user information"""
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)  # Telegram user ID
    telegram_username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    premium = Column(Boolean, default=False)
    timezone = Column(String(50), default='UTC')
    language_code = Column(String(10), default='en')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    calendar_tokens = Column(Text, nullable=True)  # JSON string of OAuth tokens
    calendar_connected = Column(Boolean, default=False)  # Calendar connection status
    oauth_state = Column(String(500), nullable=True)  # Temporary OAuth state for verification
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")

    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    mood_logs = relationship("MoodLog", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.telegram_username})>"


class Task(Base):
    """Task table - stores user tasks and to-dos"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # Work, Study, Personal, Urgent
    priority = Column(Integer, default=0)  # 0=low, 1=medium, 2=high
    deadline = Column(DateTime)
    status = Column(String(20), default='pending')  # pending, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    google_calendar_event_id = Column(String(200))
    calendar_event_id = Column(String(500), nullable=True) # For calendar sync

    # Relationships
    user = relationship("User", back_populates="tasks")
    reminders = relationship("Reminder", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"


class Note(Base):
    """Note model for storing user notes"""
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    tags = Column(String(500), nullable=True)  # Comma-separated
    linked_task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notes")
    linked_task = relationship("Task", backref="linked_notes")

class MoodLog(Base):
    """MoodLog table - tracks user mood and energy levels (Premium feature)"""
    __tablename__ = 'mood_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    mood = Column(String(50))  # sleepy, tired, hungry, stressed, energetic
    energy_level = Column(Integer)  # 1-10 scale
    context = Column(Text)  # What the user was doing
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="mood_logs")

    def __repr__(self):
        return f"<MoodLog(id={self.id}, mood={self.mood}, energy={self.energy_level})>"


class Reminder(Base):
    """Reminder table - stores scheduled reminders for tasks"""
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'))  # Optional, can be general reminder
    reminder_time = Column(DateTime, nullable=False)
    message = Column(Text)
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="reminders")
    task = relationship("Task", back_populates="reminders")

    def __repr__(self):
        return f"<Reminder(id={self.id}, time={self.reminder_time}, sent={self.sent})>"


class ProductivityStat(Base):
    """ProductivityStat table - stores aggregated productivity statistics"""
    __tablename__ = 'productivity_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    date = Column(DateTime, nullable=False)  # Date of the stats
    tasks_completed = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    notes_created = Column(Integer, default=0)
    voice_messages = Column(Integer, default=0)
    active_hours = Column(Float, default=0.0)  # Hours active that day
    streak_days = Column(Integer, default=0)  # Current streak

    def __repr__(self):
        return f"<ProductivityStat(user_id={self.user_id}, date={self.date})>"