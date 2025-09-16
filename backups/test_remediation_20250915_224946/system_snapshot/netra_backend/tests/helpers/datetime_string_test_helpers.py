"""
Test helpers for datetime and string utilities testing.
Provides setup, assertion, and fixture functions for datetime and string utility tests.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import patch

class DatetimeTestHelpers:
    """Helper functions for datetime utility testing."""
    
    @staticmethod
    def create_utc_time() -> datetime:
        """Create UTC time for testing."""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def create_dst_spring_time() -> datetime:
        """Create spring DST transition time."""
        return datetime(2025, 3, 9, 1, 30, tzinfo=timezone.utc)
    
    @staticmethod
    def create_dst_fall_time() -> datetime:
        """Create fall DST transition time."""
        return datetime(2025, 11, 2, 1, 30)
    
    @staticmethod
    def assert_timezone_offset_change(before: datetime, after: datetime):
        """Assert timezone offset changed between times."""
        assert before.strftime("%z") != after.strftime("%z")

class StringTestHelpers:
    """Helper functions for string utility testing."""
    
    @staticmethod
    def create_xss_payload() -> str:
        """Create XSS payload for testing."""
        return '<script>alert("XSS")</script>Hello'
    
    @staticmethod
    def create_event_handler_payload() -> str:
        """Create event handler payload."""
        return '<div onclick="alert(1)">Click me</div>'
    
    @staticmethod
    def create_sql_injection_payload() -> str:
        """Create SQL injection payload."""
        return "'; DROP TABLE users; --"
    
    @staticmethod
    def assert_xss_sanitized(original: str, sanitized: str):
        """Assert XSS content was sanitized."""
        assert '<script>' not in sanitized
        assert 'Hello' in sanitized