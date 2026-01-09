"""
Brainstorm Assistant Service
AI-powered idea generation and organization
"""

import google.generativeai as genai
import os
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class BrainstormService:
    """AI brainstorm assistant"""

    def __init__(self):
        """Initialize brainstorm service"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generate_ideas(
            self,
            topic: str,
            related_notes: Optional[List[str]] = None,
            count: int = 5
    ) -> Optional[Dict]:
        """
        Generate creative ideas for a topic

        Args:
            topic: The topic to brainstorm about
            related_notes: User's related notes for context
            count: Number of ideas to generate

        Returns:
            Dictionary with ideas and metadata
        """
        try:
            notes_context = ""
            if related_notes:
                notes_context = "\n\nUser's Related Notes:\n" + "\n".join([
                    f"- {note[:100]}..." for note in related_notes[:5]
                ])

            prompt = f"""
Generate {count} creative and actionable ideas for this topic:

Topic: {topic}
{notes_context}

Requirements:
1. Each idea should be unique and specific
2. Ideas should be actionable and practical
3. Consider different angles and approaches
4. If user has related notes, build upon or connect to those concepts
5. Be creative but realistic

Respond in JSON format:
{{
    "ideas": [
        {{
            "title": "Brief catchy title (5-8 words)",
            "description": "Detailed description (2-3 sentences)",
            "action_steps": ["Step 1", "Step 2", "Step 3"],
            "difficulty": "easy|medium|hard",
            "estimated_time": "X hours/days"
        }}
    ]
}}
"""

            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Clean response
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            result = json.loads(result_text)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing brainstorm response: {e}")
            logger.error(f"Raw response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error generating ideas: {e}")
            return None

    def expand_idea(self, idea: str, context: Optional[str] = None) -> Optional[str]:
        """
        Expand a single idea with more details

        Args:
            idea: The idea to expand
            context: Additional context

        Returns:
            Expanded idea text
        """
        try:
            context_text = f"\n\nContext: {context}" if context else ""

            prompt = f"""
Expand this idea with comprehensive details:

Idea: {idea}
{context_text}

Provide:
1. Detailed explanation (2-3 paragraphs)
2. Potential challenges and solutions
3. Step-by-step implementation guide
4. Resources or tools needed
5. Success metrics

Make it practical and actionable. Use clear formatting with sections.
"""

            response = self.model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error expanding idea: {e}")
            return None

    def organize_ideas(self, ideas: List[str]) -> Optional[Dict]:
        """
        Organize and categorize a list of ideas

        Args:
            ideas: List of idea strings

        Returns:
            Organized ideas by category
        """
        try:
            ideas_text = "\n".join([f"- {idea}" for idea in ideas[:20]])

            prompt = f"""
Organize these ideas into logical categories:

Ideas:
{ideas_text}

Group ideas by:
- Theme or topic
- Priority (High/Medium/Low)
- Difficulty (Easy/Medium/Hard)
- Time required (Quick wins vs Long-term)

Respond in JSON format:
{{
    "categories": {{
        "Quick Wins": ["idea1", "idea2"],
        "Long-term Projects": ["idea3"],
        "High Priority": ["idea4", "idea5"]
    }},
    "recommendations": "Brief text on which category to focus on first and why"
}}
"""

            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            result = json.loads(result_text)
            return result

        except Exception as e:
            logger.error(f"Error organizing ideas: {e}")
            return None

    def connect_ideas(self, idea1: str, idea2: str) -> Optional[str]:
        """
        Find connections between two ideas

        Args:
            idea1: First idea
            idea2: Second idea

        Returns:
            Analysis of connections
        """
        try:
            prompt = f"""
Analyze these two ideas and find creative connections:

Idea 1: {idea1}

Idea 2: {idea2}

Provide:
1. How these ideas complement each other
2. Potential synergies when combined
3. A new hybrid concept that merges both ideas
4. Implementation strategy for the combined approach

Be creative and practical. Keep it concise (3-4 paragraphs).
"""

            response = self.model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error connecting ideas: {e}")
            return None

    def prioritize_ideas(
            self,
            ideas: List[str],
            goals: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Prioritize ideas based on impact and feasibility

        Args:
            ideas: List of ideas
            goals: User's goals (optional)

        Returns:
            Prioritized list with scores
        """
        try:
            ideas_text = "\n".join([f"{i + 1}. {idea}" for i, idea in enumerate(ideas[:10])])
            goals_text = f"\n\nUser's Goals: {goals}" if goals else ""

            prompt = f"""
Prioritize these ideas based on:
1. Impact potential (1-10)
2. Feasibility (1-10)
3. Time to value (Quick/Medium/Long)
4. Resource requirements (Low/Medium/High)

Ideas:
{ideas_text}
{goals_text}

Respond in JSON format:
{{
    "prioritized_ideas": [
        {{
            "idea": "idea text",
            "rank": 1,
            "impact_score": 8,
            "feasibility_score": 7,
            "overall_score": 7.5,
            "reasoning": "Why this ranks here (1-2 sentences)"
        }}
    ]
}}

Sort by overall_score descending.
"""

            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            result = json.loads(result_text)
            return result.get('prioritized_ideas', [])

        except Exception as e:
            logger.error(f"Error prioritizing ideas: {e}")
            return None

    def generate_action_plan(self, idea: str) -> Optional[Dict]:
        """
        Generate a detailed action plan for an idea

        Args:
            idea: The idea to create a plan for

        Returns:
            Structured action plan
        """
        try:
            prompt = f"""
Create a detailed action plan for this idea:

Idea: {idea}

Provide a structured plan with:
1. Goal statement (1 sentence)
2. Key milestones (3-5 milestones)
3. Specific action steps for each milestone
4. Timeline estimate
5. Success criteria

Respond in JSON format:
{{
    "goal": "Clear goal statement",
    "milestones": [
        {{
            "title": "Milestone name",
            "actions": ["Action 1", "Action 2", "Action 3"],
            "estimated_duration": "X days/weeks",
            "success_metric": "How to measure success"
        }}
    ],
    "total_timeline": "Overall time estimate",
    "next_immediate_action": "The very first thing to do"
}}
"""

            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            result = json.loads(result_text)
            return result

        except Exception as e:
            logger.error(f"Error generating action plan: {e}")
            return None