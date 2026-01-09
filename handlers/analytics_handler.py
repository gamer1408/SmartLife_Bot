"""
SmartLife Bot - Analytics Handler
Handles analytics and insights commands
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from services.analytics_service import analytics_service
from services.chart_service import chart_service
from database.db_manager import db


async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive analytics dashboard"""
    user_id = update.effective_user.id

    await update.message.reply_text("📊 Generating your analytics dashboard...")

    # Get overview
    overview = analytics_service.get_user_overview(user_id)

    if not overview:
        await update.message.reply_text(
            "❌ Unable to fetch analytics. Try /start first."
        )
        return

    # Format message
    msg = f"""
📊 **Your Productivity Dashboard**

**Overview:**
✅ Completed Tasks: {overview['completed_tasks']}
⏳ Pending Tasks: {overview['pending_tasks']}
📈 Completion Rate: {overview['completion_rate']}%
📝 Total Notes: {overview['total_notes']}
🔥 Current Streak: {overview['current_streak']} days
👤 Member Since: {overview['member_since']}

Use these commands for detailed insights:
/trends - View productivity trends
/breakdown - See task breakdown
/time - Analyze best working hours
/achievements - View your achievements
{"⭐ /mood_insights - Mood & energy analysis" if overview['is_premium'] else ""}

Generating visual charts...
"""

    await update.message.reply_text(msg, parse_mode='Markdown')

    # Generate and send charts
    try:
        # Get data for charts
        trends = analytics_service.get_productivity_trends(user_id, days=30)
        breakdown = analytics_service.get_task_breakdown(user_id)
        time_analysis = analytics_service.get_time_analysis(user_id)

        # Generate trend chart
        if trends['daily_breakdown']:
            trend_chart = chart_service.generate_completion_trend_chart(
                trends['daily_breakdown'],
                user_id
            )
            if trend_chart:
                with open(trend_chart, 'rb') as photo:
                    await update.message.reply_photo(
                        photo,
                        caption="📈 Your 30-day completion trend"
                    )

        # Generate category pie chart
        if breakdown['by_category']:
            pie_chart = chart_service.generate_category_pie_chart(
                breakdown['by_category'],
                user_id
            )
            if pie_chart:
                with open(pie_chart, 'rb') as photo:
                    await update.message.reply_photo(
                        photo,
                        caption="🎯 Task distribution by category"
                    )

        # Generate weekday chart
        if time_analysis['weekday_distribution']:
            weekday_chart = chart_service.generate_weekday_bar_chart(
                time_analysis['weekday_distribution'],
                user_id
            )
            if weekday_chart:
                with open(weekday_chart, 'rb') as photo:
                    await update.message.reply_photo(
                        photo,
                        caption="📅 Productivity by day of week"
                    )

    except Exception as e:
        print(f"Error generating charts: {e}")
        await update.message.reply_text(
            "⚠️ Some charts couldn't be generated. Try again later."
        )


async def trends_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show productivity trends"""
    user_id = update.effective_user.id

    # Parse days argument
    days = 30
    if context.args and context.args[0].isdigit():
        days = int(context.args[0])
        days = min(days, 365)  # Max 1 year

    trends = analytics_service.get_productivity_trends(user_id, days)

    msg = f"""
📈 **Productivity Trends ({days} days)**

**Summary:**
✅ Tasks Completed: {trends['total_completed']}
📊 Average per Day: {trends['average_per_day']}

**Most Productive Day:**
📅 {trends['most_productive_day']['date'] or 'N/A'}
🎯 {trends['most_productive_day']['count']} tasks completed

Use /analytics to see visual charts!
"""

    await update.message.reply_text(msg, parse_mode='Markdown')

    # Generate chart
    if trends['daily_breakdown']:
        chart_file = chart_service.generate_completion_trend_chart(
            trends['daily_breakdown'],
            user_id
        )
        if chart_file:
            with open(chart_file, 'rb') as photo:
                await update.message.reply_photo(photo)


async def breakdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show task breakdown by category and status"""
    user_id = update.effective_user.id

    breakdown = analytics_service.get_task_breakdown(user_id)
    category_perf = analytics_service.get_category_performance(user_id)

    # Format categories
    cat_text = ""
    for cat, stats in category_perf.items():
        cat_text += f"\n**{cat}:**\n"
        cat_text += f"  Total: {stats['total']} | "
        cat_text += f"Completed: {stats['completed']} | "
        cat_text += f"Rate: {stats['completion_rate']}%"

    # Format priorities
    priorities = breakdown['by_priority']

    msg = f"""
🎯 **Task Breakdown**

**By Status:**
⏳ Pending: {breakdown['by_status'].get('pending', 0)}
✅ Completed: {breakdown['by_status'].get('completed', 0)}
❌ Cancelled: {breakdown['by_status'].get('cancelled', 0)}

**By Priority:**
🔴 High: {priorities['high']}
🟡 Medium: {priorities['medium']}
🟢 Low: {priorities['low']}

**By Category:**{cat_text or "\nNo categories yet."}

Tip: Use /analytics to see visual charts!
"""

    await update.message.reply_text(msg, parse_mode='Markdown')

    # Generate pie chart
    if breakdown['by_category']:
        pie_chart = chart_service.generate_category_pie_chart(
            breakdown['by_category'],
            user_id
        )
        if pie_chart:
            with open(pie_chart, 'rb') as photo:
                await update.message.reply_photo(photo)


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze productivity by time of day"""
    user_id = update.effective_user.id

    time_analysis = analytics_service.get_time_analysis(user_id)
    speed = analytics_service.get_completion_speed(user_id)

    peak_hour = time_analysis['peak_hour']
    peak_hour_str = f"{peak_hour}:00" if peak_hour is not None else "N/A"

    msg = f"""
⏰ **Time Analysis**

**Peak Performance:**
🌟 Best Hour: {peak_hour_str}
📅 Best Day: {time_analysis['most_productive_weekday'] or 'N/A'}

**Completion Speed:**
⚡ Average: {speed['average_hours']:.1f} hours
🚀 Fastest: {speed['fastest_hours']:.1f} hours
🐌 Slowest: {speed['slowest_hours']:.1f} hours
📊 Sample Size: {speed['sample_size']} tasks

💡 **Insight:** Your most productive time is around {peak_hour_str}. 
Schedule important tasks during this window!

Use /analytics to see hourly heatmap!
"""

    await update.message.reply_text(msg, parse_mode='Markdown')

    # Generate hourly heatmap
    if time_analysis['hourly_distribution']:
        heatmap = chart_service.generate_hourly_heatmap(
            time_analysis['hourly_distribution'],
            user_id
        )
        if heatmap:
            with open(heatmap, 'rb') as photo:
                await update.message.reply_photo(photo)

    # Generate weekday chart
    if time_analysis['weekday_distribution']:
        weekday_chart = chart_service.generate_weekday_bar_chart(
            time_analysis['weekday_distribution'],
            user_id
        )
        if weekday_chart:
            with open(weekday_chart, 'rb') as photo:
                await update.message.reply_photo(photo)


async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user achievements and progress"""
    user_id = update.effective_user.id

    achievements = analytics_service.get_achievements(user_id)

    # Separate unlocked and locked
    unlocked = [a for a in achievements if a['unlocked']]
    locked = [a for a in achievements if not a['unlocked']]

    # Format message
    msg = "🏆 **Your Achievements**\n\n"

    if unlocked:
        msg += "**Unlocked:**\n"
        for ach in unlocked:
            msg += f"✅ {ach['title']}\n   _{ach['description']}_\n"
    else:
        msg += "**Unlocked:** None yet - keep going!\n"

    msg += "\n**In Progress:**\n"
    for ach in locked[:5]:  # Show next 5
        progress_bar = "█" * int(ach['progress'] / ach['target'] * 10)
        progress_bar += "░" * (10 - len(progress_bar))
        msg += f"🔒 {ach['title']}\n"
        msg += f"   {progress_bar} {ach['progress']}/{ach['target']}\n"
        msg += f"   _{ach['description']}_\n"

    msg += f"\n🎯 Total Unlocked: {len(unlocked)}/{len(achievements)}"

    await update.message.reply_text(msg, parse_mode='Markdown')

    # Generate progress chart
    if locked:
        chart_file = chart_service.generate_achievements_progress(
            achievements,
            user_id
        )
        if chart_file:
            with open(chart_file, 'rb') as photo:
                await update.message.reply_photo(
                    photo,
                    caption="🎯 Your achievement progress"
                )


async def mood_insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mood and energy insights (Premium feature)"""
    user_id = update.effective_user.id

    # Check premium status
    user = db.get_user(user_id)
    if not user or not user.premium:
        await update.message.reply_text(
            "⭐ This is a Premium feature!\n\n"
            "Mood & Energy Tracking includes:\n"
            "• Daily mood logging\n"
            "• Energy level tracking\n"
            "• Trend analysis\n"
            "• AI-powered insights\n\n"
            "Use /premium to learn more!"
        )
        return

    # Parse days argument
    days = 30
    if context.args and context.args[0].isdigit():
        days = int(context.args[0])
        days = min(days, 90)

    mood_data = analytics_service.get_mood_insights(user_id, days)

    if 'error' in mood_data:
        await update.message.reply_text(
            f"❌ {mood_data['error']}"
        )
        return

    if mood_data['total_logs'] == 0:
        await update.message.reply_text(
            "📊 No mood data yet!\n\n"
            "Start tracking with /mood command."
        )
        return

    # Trend emoji
    trend_emoji = {
        'increasing': '📈',
        'decreasing': '📉',
        'stable': '➡️',
        'insufficient_data': '❓'
    }

    msg = f"""
😊 **Mood & Energy Insights ({days} days)**

**Summary:**
📝 Total Logs: {mood_data['total_logs']}
⚡ Average Energy: {mood_data['average_energy']}/10
😊 Most Common: {mood_data['most_common_mood']} ({mood_data['mood_count']} times)

**Energy Trend:** {trend_emoji[mood_data['energy_trend']]} {mood_data['energy_trend'].replace('_', ' ').title()}

**Mood Distribution:**
"""

    for mood, count in mood_data['mood_distribution'].items():
        percentage = (count / mood_data['total_logs'] * 100)
        msg += f"  {mood}: {count} ({percentage:.1f}%)\n"

    msg += "\n💡 Keep logging to see detailed patterns!"

    await update.message.reply_text(msg, parse_mode='Markdown')

    # Generate mood chart
    chart_file = chart_service.generate_mood_energy_chart(
        mood_data['mood_distribution'],
        mood_data['average_energy'],
        user_id
    )
    if chart_file:
        with open(chart_file, 'rb') as photo:
            await update.message.reply_photo(photo)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate comprehensive weekly/monthly report"""
    user_id = update.effective_user.id

    # Default to weekly
    period = 'weekly'
    days = 7

    if context.args and context.args[0].lower() in ['weekly', 'monthly']:
        period = context.args[0].lower()
        days = 7 if period == 'weekly' else 30

    await update.message.reply_text(
        f"📊 Generating your {period} report..."
    )

    # Get all data
    overview = analytics_service.get_user_overview(user_id)
    trends = analytics_service.get_productivity_trends(user_id, days)
    breakdown = analytics_service.get_task_breakdown(user_id)
    time_analysis = analytics_service.get_time_analysis(user_id)

    # Generate report
    msg = f"""
📋 **{period.title()} Productivity Report**

**Period:** Last {days} days

**📊 Performance:**
✅ Tasks Completed: {trends['total_completed']}
📈 Daily Average: {trends['average_per_day']}
🎯 Completion Rate: {overview['completion_rate']}%
🔥 Current Streak: {overview['current_streak']} days

**🎯 Task Status:**
⏳ Pending: {breakdown['by_status'].get('pending', 0)}
✅ Completed: {breakdown['by_status'].get('completed', 0)}

**⏰ Best Time:**
🌟 Peak Hour: {time_analysis['peak_hour'] or 'N/A'}:00
📅 Best Day: {time_analysis['most_productive_weekday'] or 'N/A'}

**🏆 Top Category:**
"""

    # Find top category
    if breakdown['by_category']:
        top_cat = max(breakdown['by_category'].items(), key=lambda x: x[1])
        msg += f"{top_cat[0]}: {top_cat[1]} tasks"
    else:
        msg += "No categories yet"

    msg += f"\n\n💡 Keep up the great work! 🚀"

    await update.message.reply_text(msg, parse_mode='Markdown')


# Register handlers
def register_analytics_handlers(application):
    """Register all analytics handlers"""
    application.add_handler(CommandHandler("analytics", analytics_command))
    application.add_handler(CommandHandler("trends", trends_command))
    application.add_handler(CommandHandler("breakdown", breakdown_command))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("mood_insights", mood_insights_command))
    application.add_handler(CommandHandler("report", report_command))


class AnalyticsHandler:
    pass