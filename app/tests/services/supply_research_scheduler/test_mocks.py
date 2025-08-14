"""
Mock classes for supply research scheduler tests
"""

from unittest.mock import AsyncMock, MagicMock


class MockDatabase:
    """Mock database context manager"""
    def __init__(self, db_session):
        self.db_session = db_session
    
    def get_db(self):
        return MockDBContext(self.db_session)


class MockDBContext:
    """Mock database context"""
    def __init__(self, db_session):
        self.db_session = db_session
    
    def __enter__(self):
        return self.db_session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockSupplyResearchService:
    """Mock supply research service"""
    def __init__(self):
        self.calculate_price_changes = MagicMock()
        self.calculate_price_changes.return_value = {
            "all_changes": [
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "field": "pricing_input",
                    "percent_change": 15.5
                }
            ]
        }


class MockAgent:
    """Mock supply researcher agent"""
    def __init__(self):
        self.process_scheduled_research = AsyncMock()
        self.process_scheduled_research.return_value = {
            "results": [
                {
                    "provider": "openai",
                    "result": {
                        "updates_made": {
                            "updates_count": 2,
                            "updates": [
                                {"action": "created", "model": "new-model-1"},
                                {"action": "updated", "model": "existing-model"}
                            ]
                        }
                    }
                }
            ]
        }