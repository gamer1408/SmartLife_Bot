"""
SmartLife Bot - Analytics Service
Calculates productivity metrics and generates insights
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import Counter
import pytz

from database.db_manager import db


class AnalyticsService:
    """Service for calculating productivity analytics"""

    def __init__(self):
        self.db = db

    def get_user_overview(self, user_id: int) -> Dict:
        """Get comprehensive user statistics overview"""
        session = self.db.get_session()
        try:
            from database.models import User, Task, Note, MoodLog

            user = session.query(User).filter_by(user_id=user_id).first()
            if not user:
                return {}

            # Task statistics
            total_tasks = session.query(Task).filter_by(user_id=user_id).count()
            completed = session.query(Task).filter_by(
                user_id=user_id, status='completed'
            ).count()
            pending = session.query(Task).filter_by(
                user_id=user_id, status='pending'
            ).count()

            # Note statistics
            total_notes = session.query(Note).filter_by(user_id=user_id).count()

            # Calculate completion rate
            completion_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0

            # Calculate streak
            streak = self._calculate_streak(user_id, session)

            return {
                'total_tasks': total_tasks,
                'completed_tasks': completed,
                'pending_tasks': pending,
                'completion_rate': round(completion_rate, 1),
                'total_notes': total_notes,
                'current_streak': streak,
                'member_since': user.created_at.strftime('%Y-%m-%d'),
                'is_premium': user.premium
            }
        finally:
            session.close()

    def get_task_breakdown(self, user_id: int) -> Dict:
        """Get task breakdown by category and status"""
        session = self.db.get_session()
        try:
            from database.models import Task

            tasks = session.query(Task).filter_by(user_id=user_id).all()

            # Category breakdown
            categories = Counter(t.category for t in tasks if t.category)

            # Status breakdown
            statuses = Counter(t.status for t in tasks)

            # Priority breakdown
            priorities = {
                'high': len([t for t in tasks if t.priority == 2]),
                'medium': len([t for t in tasks if t.priority == 1]),
                'low': len([t for t in tasks if t.priority == 0])
            }

            return {
                'by_category': dict(categories),
                'by_status': dict(statuses),
                'by_priority': priorities
            }
        finally:
            session.close()

    def get_productivity_trends(self, user_id: int, days: int = 30) -> Dict:
        """Get productivity trends over time"""
        session = self.db.get_session()
        try:
            from database.models import Task

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Tasks completed per day
            completed_tasks = session.query(Task).filter(
                Task.user_id == user_id,
                Task.status == 'completed',
                Task.completed_at >= start_date
            ).all()

            # Group by date
            daily_completions = Counter()
            for task in completed_tasks:
                date_key = task.completed_at.strftime('%Y-%m-%d')
                daily_completions[date_key] += 1

            # Calculate average
            total_completed = len(completed_tasks)
            avg_per_day = total_completed / days if days > 0 else 0

            # Find most productive day
            most_productive = None
            if daily_completions:
                most_productive = max(
                    daily_completions.items(),
                    key=lambda x: x[1]
                )

            return {
                'period_days': days,
                'total_completed': total_completed,
                'average_per_day': round(avg_per_day, 2),
                'daily_breakdown': dict(daily_completions),
                'most_productive_day': {
                    'date': most_productive[0] if most_productive else None,
                    'count': most_productive[1] if most_productive else 0
                }
            }
        finally:
            session.close()

    def get_time_analysis(self, user_id: int) -> Dict:
        """Analyze task completion by time of day and day of week"""
        session = self.db.get_session()
        try:
            from database.models import Task, User

            user = session.query(User).filter_by(user_id=user_id).first()
            tz = pytz.timezone(user.timezone if user else 'UTC')

            completed = session.query(Task).filter_by(
                user_id=user_id,
                status='completed'
            ).all()

            # Hour of day analysis
            hours = Counter()
            weekdays = Counter()

            for task in completed:
                if task.completed_at:
                    local_time = task.completed_at.replace(tzinfo=pytz.UTC).astimezone(tz)
                    hours[local_time.hour] += 1
                    weekdays[local_time.strftime('%A')] += 1

            # Find peak hours
            peak_hour = max(hours.items(), key=lambda x: x[1])[0] if hours else None

            return {
                'peak_hour': peak_hour,
                'hourly_distribution': dict(hours),
                'weekday_distribution': dict(weekdays),
                'most_productive_weekday': max(
                    weekdays.items(),
                    key=lambda x: x[1]
                )[0] if weekdays else None
            }
        finally:
            session.close()

    def get_completion_speed(self, user_id: int) -> Dict:
        """Analyze how quickly tasks are completed"""
        session = self.db.get_session()
        try:
            from database.models import Task

            completed = session.query(Task).filter_by(
                user_id=user_id,
                status='completed'
            ).all()

            speeds = []
            for task in completed:
                if task.completed_at and task.created_at:
                    delta = task.completed_at - task.created_at
                    hours = delta.total_seconds() / 3600
                    speeds.append(hours)

            if not speeds:
                return {
                    'average_hours': 0,
                    'fastest_hours': 0,
                    'slowest_hours': 0,
                    'sample_size': 0
                }

            return {
                'average_hours': round(sum(speeds) / len(speeds), 2),
                'fastest_hours': round(min(speeds), 2),
                'slowest_hours': round(max(speeds), 2),
                'sample_size': len(speeds)
            }
        finally:
            session.close()

    def get_mood_insights(self, user_id: int, days: int = 30) -> Dict:
        """Get mood tracking insights (Premium feature)"""
        session = self.db.get_session()
        try:
            from database.models import MoodLog, User

            # Check premium status
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user or not user.premium:
                return {'error': 'Premium feature'}

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            mood_logs = session.query(MoodLog).filter(
                MoodLog.user_id == user_id,
                MoodLog.timestamp >= start_date
            ).all()

            if not mood_logs:
                return {
                    'total_logs': 0,
                    'average_energy': 0,
                    'mood_distribution': {}
                }

            # Calculate statistics
            moods = Counter(log.mood for log in mood_logs)
            energy_levels = [log.energy_level for log in mood_logs if log.energy_level]
            avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else 0

            # Find patterns
            most_common_mood = moods.most_common(1)[0] if moods else (None, 0)

            return {
                'total_logs': len(mood_logs),
                'average_energy': round(avg_energy, 1),
                'mood_distribution': dict(moods),
                'most_common_mood': most_common_mood[0],
                'mood_count': most_common_mood[1],
                'energy_trend': self._calculate_energy_trend(mood_logs)
            }
        finally:
            session.close()

    def get_category_performance(self, user_id: int) -> Dict:
        """Analyze performance by task category"""
        session = self.db.get_session()
        try:
            from database.models import Task

            tasks = session.query(Task).filter_by(user_id=user_id).all()

            category_stats = {}
            for task in tasks:
                cat = task.category or 'Uncategorized'
                if cat not in category_stats:
                    category_stats[cat] = {
                        'total': 0,
                        'completed': 0,
                        'pending': 0,
                        'completion_rate': 0
                    }

                category_stats[cat]['total'] += 1
                if task.status == 'completed':
                    category_stats[cat]['completed'] += 1
                elif task.status == 'pending':
                    category_stats[cat]['pending'] += 1

            # Calculate completion rates
            for cat in category_stats:
                total = category_stats[cat]['total']
                completed = category_stats[cat]['completed']
                category_stats[cat]['completion_rate'] = round(
                    (completed / total * 100) if total > 0 else 0,
                    1
                )

            return category_stats
        finally:
            session.close()

    def get_achievements(self, user_id: int) -> List[Dict]:
        """Get user achievements and milestones"""
        session = self.db.get_session()
        try:
            from database.models import Task, Note, User

            user = session.query(User).filter_by(user_id=user_id).first()
            completed_count = session.query(Task).filter_by(
                user_id=user_id,
                status='completed'
            ).count()
            note_count = session.query(Note).filter_by(user_id=user_id).count()
            streak = self._calculate_streak(user_id, session)

            achievements = []

            # Task achievements
            task_milestones = [
                (1, "🎯 First Task", "Complete your first task"),
                (10, "🌟 Task Warrior", "Complete 10 tasks"),
                (50, "🏆 Productivity Master", "Complete 50 tasks"),
                (100, "💎 Century Club", "Complete 100 tasks"),
                (500, "👑 Legendary", "Complete 500 tasks")
            ]

            for count, title, desc in task_milestones:
                achievements.append({
                    'title': title,
                    'description': desc,
                    'unlocked': completed_count >= count,
                    'progress': min(completed_count, count),
                    'target': count,
                    'type': 'task'
                })

            # Note achievements
            note_milestones = [
                (1, "📝 Note Taker", "Create your first note"),
                (25, "📚 Knowledge Builder", "Create 25 notes"),
                (100, "🧠 Brain Builder", "Create 100 notes")
            ]

            for count, title, desc in note_milestones:
                achievements.append({
                    'title': title,
                    'description': desc,
                    'unlocked': note_count >= count,
                    'progress': min(note_count, count),
                    'target': count,
                    'type': 'note'
                })

            # Streak achievements
            streak_milestones = [
                (3, "🔥 On Fire", "3-day streak"),
                (7, "⚡ Unstoppable", "7-day streak"),
                (30, "💪 Consistency King", "30-day streak")
            ]

            for count, title, desc in streak_milestones:
                achievements.append({
                    'title': title,
                    'description': desc,
                    'unlocked': streak >= count,
                    'progress': min(streak, count),
                    'target': count,
                    'type': 'streak'
                })

            return achievements
        finally:
            session.close()

    def _calculate_streak(self, user_id: int, session) -> int:
        """Calculate current completion streak in days"""
        from database.models import Task

        today = datetime.utcnow().date()
        streak = 0
        current_date = today

        while True:
            completed_today = session.query(Task).filter(
                Task.user_id == user_id,
                Task.status == 'completed',
                Task.completed_at >= datetime.combine(current_date, datetime.min.time()),
                Task.completed_at < datetime.combine(current_date + timedelta(days=1), datetime.min.time())
            ).count()

            if completed_today > 0:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break

            # Prevent infinite loop
            if streak > 365:
                break

        return streak

    def _calculate_energy_trend(self, mood_logs: List) -> str:
        """Calculate if energy is trending up, down, or stable"""
        if len(mood_logs) < 2:
            return "insufficient_data"

        # Sort by timestamp
        sorted_logs = sorted(mood_logs, key=lambda x: x.timestamp)

        # Compare first half vs second half
        mid = len(sorted_logs) // 2
        first_half = [log.energy_level for log in sorted_logs[:mid] if log.energy_level]
        second_half = [log.energy_level for log in sorted_logs[mid:] if log.energy_level]

        if not first_half or not second_half:
            return "insufficient_data"

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        diff = avg_second - avg_first

        if diff > 0.5:
            return "increasing"
        elif diff < -0.5:
            return "decreasing"
        else:
            return "stable"


# Global instance
analytics_service = AnalyticsService()