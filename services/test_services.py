"""
Unit tests for SmartLife Bot services
Tests all service layer functionality with mocked dependencies
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.analytics_service import AnalyticsService
from services.ai_suggestion_service import AISuggestionService
from services.brainstorm_service import BrainstormService
from services.note_service import NoteService


class TestAnalyticsService(unittest.TestCase):
    """Test analytics calculation and metrics"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.service = AnalyticsService(self.mock_db)

    def test_calculate_completion_rate(self):
        """Test completion rate calculation"""
        # Mock tasks
        tasks = [
            Mock(completed=True),
            Mock(completed=True),
            Mock(completed=False),
            Mock(completed=False),
        ]
        self.mock_db.get_user_tasks.return_value = tasks

        rate = self.service.calculate_completion_rate(12345)
        self.assertEqual(rate, 50.0)

    def test_calculate_completion_rate_no_tasks(self):
        """Test completion rate with no tasks"""
        self.mock_db.get_user_tasks.return_value = []
        rate = self.service.calculate_completion_rate(12345)
        self.assertEqual(rate, 0.0)

    def test_get_category_breakdown(self):
        """Test task category breakdown"""
        tasks = [
            Mock(category='Work', completed=True),
            Mock(category='Work', completed=False),
            Mock(category='Personal', completed=True),
        ]
        self.mock_db.get_user_tasks.return_value = tasks

        breakdown = self.service.get_category_breakdown(12345)
        self.assertEqual(breakdown['Work'], 2)
        self.assertEqual(breakdown['Personal'], 1)

    def test_calculate_streak(self):
        """Test streak calculation"""
        # Mock completed tasks over consecutive days
        today = datetime.now()
        tasks = [
            Mock(completed=True, completed_at=today),
            Mock(completed=True, completed_at=today - timedelta(days=1)),
            Mock(completed=True, completed_at=today - timedelta(days=2)),
        ]
        self.mock_db.get_completed_tasks.return_value = tasks

        streak = self.service.calculate_streak(12345)
        self.assertEqual(streak, 3)


class TestAISuggestionService(unittest.TestCase):
    """Test AI suggestion service"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = AISuggestionService()

    @patch('services.ai_suggestion_service.genai.GenerativeModel')
    def test_suggest_next_task_with_mood(self, mock_genai):
        """Test task suggestion with mood data"""
        # Mock Gemini response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '''```json
        {
            "recommended_task": "Review code",
            "reasoning": "High energy matches focus work",
            "alternative": "Write tests",
            "tips": ["Take breaks", "Stay hydrated"]
        }
        ```'''
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model

        # Test data
        tasks = [
            {'title': 'Review code', 'priority': 'High'},
            {'title': 'Write tests', 'priority': 'Medium'}
        ]
        mood_data = {'mood': 'Happy', 'energy': 8}

        result = self.service.suggest_next_task(tasks, mood_data, 'morning')

        self.assertEqual(result['recommended_task'], 'Review code')
        self.assertIn('reasoning', result)
        self.assertIn('tips', result)

    def test_suggest_next_task_no_tasks(self):
        """Test suggestion with no available tasks"""
        result = self.service.suggest_next_task([], None, 'morning')
        self.assertIsNone(result)

    @patch('services.ai_suggestion_service.genai.GenerativeModel')
    def test_generate_daily_plan(self, mock_genai):
        """Test daily plan generation"""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '''```json
        {
            "schedule": [
                {
                    "time": "9:00 AM - 11:00 AM",
                    "task": "Review code",
                    "reasoning": "Peak focus hours"
                }
            ],
            "summary": "Focus morning, meetings afternoon",
            "tips": ["Take regular breaks"]
        }
        ```'''
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model

        tasks = [{'title': 'Review code', 'priority': 'High'}]
        result = self.service.generate_daily_plan(tasks, None, 8)

        self.assertIn('schedule', result)
        self.assertIn('summary', result)


class TestBrainstormService(unittest.TestCase):
    """Test brainstorm service"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = BrainstormService()

    @patch('services.brainstorm_service.genai.GenerativeModel')
    def test_generate_ideas(self, mock_genai):
        """Test idea generation"""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '''```json
        {
            "ideas": [
                {
                    "title": "Mobile App",
                    "description": "Build productivity app",
                    "difficulty": "medium"
                }
            ]
        }
        ```'''
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model

        result = self.service.generate_ideas("project ideas", [])

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn('title', result[0])

    @patch('services.brainstorm_service.genai.GenerativeModel')
    def test_expand_idea(self, mock_genai):
        """Test idea expansion"""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Detailed explanation of the idea..."
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model

        idea = {"title": "Mobile App", "description": "Build app"}
        result = self.service.expand_idea(idea)

        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


class TestNoteService(unittest.TestCase):
    """Test note service functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.service = NoteService(self.mock_db)

    def test_extract_hashtags(self):
        """Test hashtag extraction from text"""
        text = "This is a #test note with #multiple #hashtags"
        tags = self.service.extract_hashtags(text)

        self.assertEqual(len(tags), 3)
        self.assertIn('test', tags)
        self.assertIn('multiple', tags)
        self.assertIn('hashtags', tags)

    def test_extract_hashtags_no_tags(self):
        """Test text without hashtags"""
        text = "This note has no tags"
        tags = self.service.extract_hashtags(text)
        self.assertEqual(len(tags), 0)

    def test_search_notes_relevance(self):
        """Test note search with relevance scoring"""
        notes = [
            Mock(title='Python Tutorial', content='Learn Python', tags='python,tutorial'),
            Mock(title='JavaScript Guide', content='JS basics', tags='javascript'),
            Mock(title='Python Advanced', content='Advanced Python', tags='python'),
        ]
        self.mock_db.search_notes.return_value = notes

        results = self.service.search_notes(12345, 'Python')

        # Python notes should rank higher
        self.assertTrue(len(results) > 0)
        self.assertIn('Python', results[0].title)


class TestIntegration(unittest.TestCase):
    """Integration tests for combined functionality"""

    @patch('services.ai_suggestion_service.genai.GenerativeModel')
    @patch('database.db_manager.DatabaseManager')
    def test_full_suggestion_flow(self, mock_db, mock_genai):
        """Test complete suggestion workflow"""
        # Mock database
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance

        mock_db_instance.get_pending_tasks.return_value = [
            Mock(title='Task 1', priority='High', category='Work')
        ]
        mock_db_instance.get_mood_logs.return_value = [
            Mock(mood='Happy', energy_level=8)
        ]

        # Mock Gemini
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '{"recommended_task": "Task 1", "reasoning": "Test"}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model

        # Test flow
        service = AISuggestionService()
        tasks = [{'title': 'Task 1', 'priority': 'High'}]
        result = service.suggest_next_task(tasks, {'mood': 'Happy'}, 'morning')

        self.assertIsNotNone(result)


def run_tests():
    """Run all tests and generate report"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyticsService))
    suite.addTests(loader.loadTestsFromTestCase(TestAISuggestionService))
    suite.addTests(loader.loadTestsFromTestCase(TestBrainstormService))
    suite.addTests(loader.loadTestsFromTestCase(TestNoteService))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)