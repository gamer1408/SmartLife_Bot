"""
SmartLife Bot - Chart Generation Service
Creates visual charts for productivity analytics using Matplotlib
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List
import io
import os


class ChartService:
    """Service for generating analytics charts"""

    def __init__(self):
        # Set matplotlib style
        plt.style.use('seaborn-v0_8-darkgrid')

        # Create charts directory if it doesn't exist
        self.charts_dir = 'charts'
        if not os.path.exists(self.charts_dir):
            os.makedirs(self.charts_dir)

    def generate_completion_trend_chart(
            self,
            daily_data: Dict[str, int],
            user_id: int
    ) -> str:
        """Generate line chart showing task completion trend"""

        # Sort dates
        dates = sorted(daily_data.keys())
        counts = [daily_data[date] for date in dates]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))

        # Convert string dates to datetime
        date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

        # Plot line
        ax.plot(date_objects, counts, marker='o', linewidth=2,
                markersize=6, color='#2E86AB', label='Tasks Completed')

        # Fill area under line
        ax.fill_between(date_objects, counts, alpha=0.3, color='#2E86AB')

        # Formatting
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tasks Completed', fontsize=12, fontweight='bold')
        ax.set_title('Task Completion Trend', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.xticks(rotation=45, ha='right')

        # Add average line
        if counts:
            avg = sum(counts) / len(counts)
            ax.axhline(y=avg, color='#A23B72', linestyle='--',
                       label=f'Average: {avg:.1f}', linewidth=2)

        ax.legend(loc='upper left', fontsize=10)

        # Tight layout
        plt.tight_layout()

        # Save
        filename = f'{self.charts_dir}/completion_trend_{user_id}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        return filename

    def generate_category_pie_chart(
            self,
            category_data: Dict[str, int],
            user_id: int
    ) -> str:
        """Generate pie chart showing task distribution by category"""

        if not category_data:
            return None

        # Prepare data
        categories = list(category_data.keys())
        counts = list(category_data.values())

        # Colors
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))

        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            counts,
            labels=categories,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(categories)],
            textprops={'fontsize': 11, 'weight': 'bold'}
        )

        # Make percentage text white
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(12)

        ax.set_title('Task Distribution by Category',
                     fontsize=14, fontweight='bold', pad=20)

        # Equal aspect ratio
        ax.axis('equal')

        # Save
        filename = f'{self.charts_dir}/category_pie_{user_id}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        return filename

    def generate_weekday_bar_chart(
            self,
            weekday_data: Dict[str, int],
            user_id: int
    ) -> str:
        """Generate bar chart showing productivity by day of week"""

        # Order days correctly
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                     'Friday', 'Saturday', 'Sunday']

        days = []
        counts = []
        for day in day_order:
            if day in weekday_data:
                days.append(day[:3])  # Abbreviate
                counts.append(weekday_data[day])
            else:
                days.append(day[:3])
                counts.append(0)

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))

        # Create bars with gradient colors
        colors = ['#2E86AB' if c == max(counts) else '#6B9AC4' for c in counts]
        bars = ax.bar(days, counts, color=colors, edgecolor='black', linewidth=1.5)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold', fontsize=11)

        # Formatting
        ax.set_xlabel('Day of Week', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tasks Completed', fontsize=12, fontweight='bold')
        ax.set_title('Productivity by Day of Week',
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='y', alpha=0.3)

        # Tight layout
        plt.tight_layout()

        # Save
        filename = f'{self.charts_dir}/weekday_bar_{user_id}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        return filename

    def generate_hourly_heatmap(
            self,
            hourly_data: Dict[int, int],
            user_id: int
    ) -> str:
        """Generate heatmap showing productivity by hour of day"""

        # Prepare data for 24 hours
        hours = list(range(24))
        counts = [hourly_data.get(h, 0) for h in hours]

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 4))

        # Create color map
        colors = plt.cm.YlOrRd([(c / max(counts) if max(counts) > 0 else 0) for c in counts])

        # Create bars
        bars = ax.bar(hours, counts, color=colors, edgecolor='black', linewidth=1)

        # Add value labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', fontweight='bold', fontsize=9)

        # Formatting
        ax.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tasks Completed', fontsize=12, fontweight='bold')
        ax.set_title('Productivity Heatmap by Hour',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(hours)
        ax.set_xticklabels([f'{h:02d}:00' for h in hours], rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)

        # Tight layout
        plt.tight_layout()

        # Save
        filename = f'{self.charts_dir}/hourly_heatmap_{user_id}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        return filename

    def generate_mood_energy_chart(
            self,
            mood_distribution: Dict[str, int],
            avg_energy: float,
            user_id: int
    ) -> str:
        """Generate mood distribution and energy level chart (Premium)"""

        if not mood_distribution:
            return None

        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Mood distribution (left)
        moods = list(mood_distribution.keys())
        counts = list(mood_distribution.values())
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']

        ax1.bar(moods, counts, color=colors[:len(moods)],
                edgecolor='black', linewidth=1.5)
        ax1.set_title('Mood Distribution', fontsize=13, fontweight='bold')
        ax1.set_xlabel('Mood', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Count', fontsize=11, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)

        # Add value labels
        for i, count in enumerate(counts):
            ax1.text(i, count, str(count), ha='center',
                     va='bottom', fontweight='bold', fontsize=10)

        # Energy gauge (right)
        # Create a gauge-style visualization
        ax2.barh(['Energy Level'], [avg_energy], height=0.5,
                 color='#2E86AB', edgecolor='black', linewidth=2)
        ax2.set_xlim(0, 10)
        ax2.set_title('Average Energy Level', fontsize=13, fontweight='bold')
        ax2.set_xlabel('Energy (1-10)', fontsize=11, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)

        # Add energy value text
        ax2.text(avg_energy + 0.3, 0, f'{avg_energy:.1f}',
                 va='center', fontweight='bold', fontsize=14)

        # Tight layout
        plt.tight_layout()

        # Save
        filename = f'{self.charts_dir}/mood_energy_{user_id}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        return filename

    def generate_achievements_progress(
            self,
            achievements: List[Dict],
            user_id: int
    ) -> str:
        """Generate progress chart for achievements"""

        # Filter to show only next 5 locked achievements
        locked = [a for a in achievements if not a['unlocked']][:5]

        if not locked:
            return None

        # Prepare data
        titles = [a['title'] for a in locked]
        progress = [a['progress'] for a in locked]
        targets = [a['target'] for a in locked]
        percentages = [(p / t * 100) if t > 0 else 0 for p, t in zip(progress, targets)]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))

        # Create horizontal bars
        y_pos = range(len(titles))

        # Background bars (total)
        ax.barh(y_pos, targets, color='#E0E0E0', edgecolor='black', linewidth=1)

        # Progress bars
        colors = ['#2E86AB' if p >= 50 else '#6B9AC4' for p in percentages]
        ax.barh(y_pos, progress, color=colors, edgecolor='black', linewidth=1.5)

        # Add labels
        for i, (prog, targ, pct) in enumerate(zip(progress, targets, percentages)):
            ax.text(targ + (max(targets) * 0.02), i,
                    f'{prog}/{targ} ({pct:.0f}%)',
                    va='center', fontweight='bold', fontsize=10)

        # Formatting
        ax.set_yticks(y_pos)
        ax.set_yticklabels(titles, fontsize=10, fontweight='bold')
        ax.invert_yaxis()
        ax.set_xlabel('Progress', fontsize=12, fontweight='bold')
        ax.set_title('Next Achievements to Unlock',
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3)

        # Tight layout
        plt.tight_layout()

        # Save
        filename = f'{self.charts_dir}/achievements_{user_id}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        return filename

    def cleanup_user_charts(self, user_id: int):
        """Delete all charts for a user"""
        import glob

        pattern = f'{self.charts_dir}/*_{user_id}.png'
        for file in glob.glob(pattern):
            try:
                os.remove(file)
            except Exception as e:
                print(f"Error deleting {file}: {e}")


# Global instance
chart_service = ChartService()