"""
Simple edge case tests for app/startup_checks.py

This module tests basic edge cases and boundary conditions.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupChecker, StartupCheckResult


class TestBasicEdgeCases:
    """Test basic edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_concurrent_check_timing(self):
        """Test that check durations are properly recorded"""
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        self._setup_slow_checks(checker)
        results = await checker.run_all_checks()
        self._verify_timing_results(results)
    
    def _setup_slow_checks(self, checker):
        """Setup slow check methods for timing test"""
        async def slow_check():
            await asyncio.sleep(0.01)  # 10ms delay
            return StartupCheckResult(
                name="slow_check",
                success=True,
                message="Slow check completed"
            )
        
        # Patch all checker methods
        checker.env_checker.check_environment_variables = slow_check
        checker.env_checker.check_configuration = slow_check
        checker.system_checker.check_file_permissions = slow_check
        checker.db_checker.check_database_connection = slow_check
        checker.service_checker.check_redis = slow_check
        checker.service_checker.check_clickhouse = slow_check
        checker.service_checker.check_llm_providers = slow_check
        checker.system_checker.check_memory_and_resources = slow_check
        checker.system_checker.check_network_connectivity = slow_check
        checker.db_checker.check_or_create_assistant = slow_check
    
    def _verify_timing_results(self, results):
        """Verify timing results are properly recorded"""
        # Each check should have some duration
        for result in results['results']:
            assert result.duration_ms >= 0
        
        # Total duration should be reasonable
        assert results['duration_ms'] >= 0


class TestStartupCheckResultEdgeCases:
    """Test StartupCheckResult edge cases"""
    
    def test_result_with_zero_duration(self):
        """Test result with zero duration"""
        result = StartupCheckResult(
            name="zero_duration_check",
            success=True,
            message="Check completed instantly",
            duration_ms=0.0
        )
        
        assert result.duration_ms == 0.0
        assert result.success is True
    
    def test_result_with_very_long_message(self):
        """Test result with very long message"""
        long_message = "A" * 1000  # Very long message
        result = StartupCheckResult(
            name="long_message_check",
            success=False,
            message=long_message,
            critical=True
        )
        
        assert len(result.message) == 1000
        assert result.success is False
        assert result.critical is True
    
    def test_result_with_special_characters(self):
        """Test result with special characters in message"""
        special_message = "Check failed: 特殊字符 русский العربية 🔥💥"
        result = StartupCheckResult(
            name="special_chars_check",
            success=False,
            message=special_message
        )
        
        assert result.message == special_message
        assert result.success is False


class TestCheckerInitialization:
    """Test checker initialization edge cases"""
    
    def test_checker_with_minimal_app(self):
        """Test checker with minimal app configuration"""
        mock_app = MagicMock()
        mock_app.state = MagicMock()
        
        checker = StartupChecker(mock_app)
        
        assert checker.app == mock_app
        assert checker.results == []
        assert hasattr(checker, 'env_checker')
        assert hasattr(checker, 'db_checker')
        assert hasattr(checker, 'service_checker')
        assert hasattr(checker, 'system_checker')
    
    def test_checker_start_time_initialization(self):
        """Test that checker initializes start time"""
        import time
        before_init = time.time()
        
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        after_init = time.time()
        
        assert before_init <= checker.start_time <= after_init
    
    def test_checker_sub_checkers_created(self):
        """Test that all sub-checkers are properly created"""
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        # Verify all sub-checkers exist
        assert checker.env_checker is not None
        assert checker.db_checker is not None
        assert checker.service_checker is not None
        assert checker.system_checker is not None
        
        # Verify they have the right app reference where needed
        assert checker.db_checker.app == mock_app
        assert checker.service_checker.app == mock_app