"""
Note Service - Handles note creation, search, and management
"""
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from database.db_manager import DatabaseManager


class NoteService:
    """Service for managing notes with search, tags, and formatting"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_note(
            self,
            user_id: int,
            title: str,
            content: str,
            category: Optional[str] = None,
            tags: Optional[List[str]] = None,
            linked_task_id: Optional[int] = None
    ) -> Dict:
        """
        Create a new note

        Args:
            user_id: User ID
            title: Note title
            content: Note content (supports markdown)
            category: Optional category (e.g., "Personal", "Work")
            tags: Optional list of tags
            linked_task_id: Optional task ID to link to

        Returns:
            dict: Created note data
        """
        try:
            # Extract tags from content if not provided
            if tags is None:
                tags = self._extract_tags(content)

            # Clean and format content
            formatted_content = self._format_content(content)

            # Create note in database
            note = self.db.create_note(
                user_id=user_id,
                title=title,
                content=formatted_content,
                category=category,
                tags=tags,
                linked_task_id=linked_task_id
            )

            return {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'category': note.category,
                'tags': note.tags.split(',') if note.tags else [],
                'linked_task_id': note.linked_task_id,
                'created_at': note.created_at
            }
        except Exception as e:
            print(f"Error creating note: {e}")
            raise

    def search_notes(
            self,
            user_id: int,
            query: str,
            category: Optional[str] = None,
            tags: Optional[List[str]] = None,
            limit: int = 20
    ) -> List[Dict]:
        """
        Search notes by text, category, or tags

        Args:
            user_id: User ID
            query: Search query (searches title and content)
            category: Filter by category
            tags: Filter by tags
            limit: Maximum results to return

        Returns:
            list: Matching notes with relevance scoring
        """
        try:
            notes = self.db.search_notes(
                user_id=user_id,
                query=query,
                category=category,
                tags=tags,
                limit=limit
            )

            # Score and sort results
            scored_notes = []
            for note in notes:
                score = self._calculate_relevance(note, query, tags)
                scored_notes.append({
                    'note': note,
                    'score': score
                })

            # Sort by relevance
            scored_notes.sort(key=lambda x: x['score'], reverse=True)

            return [
                {
                    'id': item['note'].id,
                    'title': item['note'].title,
                    'content': item['note'].content[:200],  # Preview
                    'category': item['note'].category,
                    'tags': item['note'].tags.split(',') if item['note'].tags else [],
                    'created_at': item['note'].created_at,
                    'relevance': item['score']
                }
                for item in scored_notes
            ]
        except Exception as e:
            print(f"Error searching notes: {e}")
            return []

    def get_note(self, note_id: int, user_id: int) -> Optional[Dict]:
        """Get a specific note by ID"""
        try:
            note = self.db.get_note(note_id, user_id)
            if not note:
                return None

            return {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'category': note.category,
                'tags': note.tags.split(',') if note.tags else [],
                'linked_task_id': note.linked_task_id,
                'created_at': note.created_at,
                'updated_at': note.updated_at
            }
        except Exception as e:
            print(f"Error getting note: {e}")
            return None

    def update_note(
            self,
            note_id: int,
            user_id: int,
            title: Optional[str] = None,
            content: Optional[str] = None,
            category: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> bool:
        """Update an existing note"""
        try:
            updates = {}

            if title is not None:
                updates['title'] = title

            if content is not None:
                updates['content'] = self._format_content(content)
                # Extract tags from new content
                if tags is None:
                    tags = self._extract_tags(content)

            if category is not None:
                updates['category'] = category

            if tags is not None:
                updates['tags'] = ','.join(tags)

            return self.db.update_note(note_id, user_id, **updates)
        except Exception as e:
            print(f"Error updating note: {e}")
            return False

    def delete_note(self, note_id: int, user_id: int) -> bool:
        """Delete a note"""
        try:
            return self.db.delete_note(note_id, user_id)
        except Exception as e:
            print(f"Error deleting note: {e}")
            return False

    def list_notes(
            self,
            user_id: int,
            category: Optional[str] = None,
            limit: int = 50
    ) -> List[Dict]:
        """List user's notes"""
        try:
            notes = self.db.list_notes(user_id, category, limit)

            return [
                {
                    'id': note.id,
                    'title': note.title,
                    'content': note.content[:100],  # Preview
                    'category': note.category,
                    'tags': note.tags.split(',') if note.tags else [],
                    'created_at': note.created_at
                }
                for note in notes
            ]
        except Exception as e:
            print(f"Error listing notes: {e}")
            return []

    def get_categories(self, user_id: int) -> List[str]:
        """Get all note categories for user"""
        try:
            return self.db.get_note_categories(user_id)
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []

    def get_all_tags(self, user_id: int) -> List[str]:
        """Get all tags used by user"""
        try:
            return self.db.get_all_note_tags(user_id)
        except Exception as e:
            print(f"Error getting tags: {e}")
            return []

    def _extract_tags(self, content: str) -> List[str]:
        """Extract hashtags from content"""
        # Find all #hashtags
        tags = re.findall(r'#(\w+)', content)
        # Remove duplicates and return
        return list(set(tags))

    def _format_content(self, content: str) -> str:
        """
        Format note content
        Preserves markdown-style formatting
        """
        # Preserve line breaks
        content = content.strip()

        # Preserve markdown formatting (don't convert, just validate)
        # Telegram supports: bold (**text**), italic (*text*), code (`text`)

        return content

    def _calculate_relevance(
            self,
            note,
            query: str,
            tags: Optional[List[str]] = None
    ) -> float:
        """
        Calculate relevance score for search result

        Scoring:
        - Title exact match: +10
        - Title contains: +5
        - Content contains: +1 per occurrence
        - Tag match: +3 per tag
        """
        score = 0.0
        query_lower = query.lower()

        # Title scoring
        title_lower = note.title.lower()
        if query_lower == title_lower:
            score += 10
        elif query_lower in title_lower:
            score += 5

        # Content scoring
        content_lower = note.content.lower()
        score += content_lower.count(query_lower)

        # Tag scoring
        if tags and note.tags:
            note_tags = note.tags.split(',')
            for tag in tags:
                if tag in note_tags:
                    score += 3

        return score