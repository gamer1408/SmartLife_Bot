"""
Gemini AI Service
Handles AI-powered features like time suggestions and task analysis
"""

import google.generativeai as genai
import os
from datetime import datetime
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    """Google Gemini AI integration service"""

    def __init__(self):
        """Initialize Gemini service"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def suggest_optimal_time(
            self,
            task_title: str,
            task_priority: str,
            task_deadline: datetime,
            task_category: str,
            free_slots: List[Dict],
            duration_hours: int = 1
    ) -> Optional[Dict]:
        """
        Use AI to suggest the best time slot for a task

        Args:
            task_title: Task description
            task_priority: Priority level (low/medium/high/urgent)
            task_deadline: Task deadline
            task_category: Task category
            free_slots: Available time slots
            duration_hours: Estimated task duration

        Returns:
            Dictionary with suggested time and reasoning, or None if error
        """
        try:
            # Format free slots for prompt
            slots_text = "\n".join([
                f"- {slot['start'].strftime('%A, %B %d at %I:%M %p')} to {slot['end'].strftime('%I:%M %p')}"
                for slot in free_slots[:5]  # Limit to 5 slots
            ])

            prompt = f"""
You are a productivity assistant helping schedule tasks optimally.

Task Details:
- Title: {task_title}
- Category: {task_category}
- Priority: {task_priority}
- Deadline: {task_deadline.strftime('%A, %B %d at %I:%M %p')}
- Estimated Duration: {duration_hours} hour(s)

Available Time Slots:
{slots_text}

Current Date: {datetime.now().strftime('%A, %B %d, %Y')}

Based on these factors, suggest the BEST time slot from the available options. Consider:
1. Task priority and urgency
2. Time until deadline
3. Optimal productivity times (morning for focus work, afternoon for meetings)
4. Category-appropriate timing (e.g., study in morning, personal tasks in evening)
5. Buffer time before deadline

Respond in JSON format:
{{
    "suggested_slot_index": 0,
    "reasoning": "Brief explanation (2-3 sentences)",
    "alternative_index": 1,
    "productivity_tip": "One actionable tip for completing this task"
}}

Use index 0 for the first slot in the list, 1 for second, etc.
"""

            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Remove markdown code blocks if present
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            # Parse JSON response
            result = json.loads(result_text)

            # Add the actual time slot data
            suggested_idx = result.get('suggested_slot_index', 0)
            alternative_idx = result.get('alternative_index', 1)

            if suggested_idx < len(free_slots):
                result['suggested_slot'] = free_slots[suggested_idx]

            if alternative_idx < len(free_slots):
                result['alternative_slot'] = free_slots[alternative_idx]

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Gemini JSON response: {e}")
            logger.error(f"Raw response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error getting time suggestion from Gemini: {e}")
            return None

    def analyze_task_complexity(self, task_title: str, task_category: str) -> Optional[Dict]:
        """
        Analyze task and estimate complexity/duration

        Args:
            task_title: Task description
            task_category: Task category

        Returns:
            Dictionary with complexity analysis
        """
        try:
            prompt = f"""
Analyze this task and provide estimates:

Task: {task_title}
Category: {task_category}

Provide:
1. Estimated duration (in hours, be realistic)
2. Complexity level (simple/moderate/complex)
3. Subtasks that could help break it down (2-4 items)
4. Focus level required (low/medium/high)

Respond in JSON format:
{{
    "duration_hours": 2,
    "complexity": "moderate",
    "subtasks": ["Step 1", "Step 2", "Step 3"],
    "focus_level": "high",
    "tips": "One tip for completing this efficiently"
}}
"""

            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Remove markdown code blocks if present
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            result = json.loads(result_text)
            return result

        except Exception as e:
            logger.error(f"Error analyzing task complexity: {e}")
            return None

    def generate_daily_plan(self, tasks: List[Dict], free_slots: List[Dict]) -> Optional[str]:
        """
        Generate an optimized daily plan from tasks

        Args:
            tasks: List of task dictionaries
            free_slots: Available time slots

        Returns:
            Formatted daily plan text or None if error
        """
        try:
            # Format tasks
            tasks_text = "\n".join([
                f"- {task['title']} (Priority: {task['priority']}, Category: {task['category']})"
                for task in tasks[:10]  # Limit to 10 tasks
            ])

            # Format slots
            slots_text = "\n".join([
                f"- {slot['start'].strftime('%I:%M %p')} - {slot['end'].strftime('%I:%M %p')}"
                for slot in free_slots[:8]  # Limit to 8 slots
            ])

            prompt = f"""
You are a productivity coach. Create an optimized daily schedule.

Tasks to schedule:
{tasks_text}

Available time slots:
{slots_text}

Create a realistic daily plan that:
1. Prioritizes urgent and high-priority tasks
2. Groups similar tasks together
3. Schedules focus work in morning slots
4. Allows buffer time between tasks
5. Considers energy levels throughout the day

Format as a clear, actionable schedule with time blocks and tasks.
Keep it concise and motivating.
"""

            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error generating daily plan: {e}")
            return None

    def get_productivity_insight(self, completed_tasks: int, pending_tasks: int, categories: Dict[str, int]) -> \
    Optional[str]:
        """
        Generate productivity insights based on user stats

        Args:
            completed_tasks: Number of completed tasks
            pending_tasks: Number of pending tasks
            categories: Dictionary of task counts by category

        Returns:
            Insight text or None if error
        """
        try:
            categories_text = ", ".join([f"{k}: {v}" for k, v in categories.items()])

            prompt = f"""
Provide a brief productivity insight (2-3 sentences) based on these stats:

- Completed tasks: {completed_tasks}
- Pending tasks: {pending_tasks}
- Task distribution: {categories_text}

Give one actionable tip for improvement. Be encouraging and specific.
"""

            response = self.model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error getting productivity insight: {e}")
            return None