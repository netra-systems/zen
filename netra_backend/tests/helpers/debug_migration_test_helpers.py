"""
Test helpers for debug and migration utilities testing.
Provides setup, assertion, and fixture functions for debug and migration utility tests.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List

class DebugTestHelpers:
    """Helper functions for debug utility testing."""
    
    @staticmethod
    async def create_slow_function() -> Callable:
        """Create slow function for profiling."""
        async def slow_function():
            await asyncio.sleep(0.1)
            return "result"
        return slow_function
    
    @staticmethod
    def create_memory_intensive_function() -> Callable:
        """Create memory intensive function."""
        def memory_intensive():
            data = [i for i in range(1000000)]
            return len(data)
        return memory_intensive

class MigrationTestHelpers:
    """Helper functions for migration utility testing."""
    
    @staticmethod
    def create_old_schema() -> Dict[str, Any]:
        """Create old schema for testing."""
        return {
            "version": 1,
            "fields": ["id", "name", "email"]
        }
    
    @staticmethod
    def create_new_schema() -> Dict[str, Any]:
        """Create new schema for testing."""
        return {
            "version": 2,
            "fields": ["id", "name", "email", "phone"]
        }
    
    @staticmethod
    def create_test_data() -> List[Dict[str, Any]]:
        """Create test data for migration."""
        return [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "Jane", "email": "jane@example.com"}
        ]
    
    @staticmethod
    def create_transformation_data() -> List[Dict[str, Any]]:
        """Create data for transformation testing."""
        return [
            {"first_name": "John", "last_name": "Doe", "birth_year": 1990},
            {"first_name": "Jane", "last_name": "Smith", "birth_year": 1985}
        ]