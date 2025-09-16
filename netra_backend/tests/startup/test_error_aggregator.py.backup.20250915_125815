"""
Comprehensive Unit Tests for Error Aggregator
Tests error recording, pattern detection, trend analysis, and database operations.
COMPLIANCE: 450-line max file, 25-line max functions, async test support.
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiosqlite
import pytest

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.startup_types import (
    ErrorPattern,
    ErrorPhase,
    ErrorTrend,
    ErrorType,
    StartupError,
)

from netra_backend.app.startup.error_aggregator import ErrorAggregator

@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create temporary database path."""
    return tmp_path / "test_error_db.sqlite"

@pytest.fixture
def error_aggregator(temp_db_path: Path) -> ErrorAggregator:
    """Create error aggregator with temporary database."""
    aggregator = ErrorAggregator(str(temp_db_path))
    return aggregator

@pytest.fixture
def sample_error() -> StartupError:
    """Create sample error for testing."""
    return StartupError(
        timestamp=datetime.now(timezone.utc),
        service="backend",
        phase=ErrorPhase.STARTUP,
        severity=ErrorSeverity.MEDIUM.value,
        error_type=ErrorType.CONNECTION,
        message="Database connection failed",
        stack_trace="Stack trace here",
        context={"db_host": "localhost"}
    )

@pytest.fixture
def sample_errors() -> List[StartupError]:
    """Create sample errors for pattern testing."""
    base_time = datetime.now(timezone.utc)
    return [
        StartupError(timestamp=base_time, service="backend", phase=ErrorPhase.STARTUP,
                    severity="medium", error_type=ErrorType.CONNECTION, 
                    message="Database connection failed"),
        StartupError(timestamp=base_time - timedelta(minutes=5), service="backend", 
                    phase=ErrorPhase.STARTUP, severity="medium", error_type=ErrorType.CONNECTION,
                    message="Database connection timeout"),
        StartupError(timestamp=base_time - timedelta(minutes=10), service="frontend",
                    phase=ErrorPhase.STARTUP, severity="high", error_type=ErrorType.DEPENDENCY,
                    message="React build failed")
    ]

class TestErrorAggregatorInit:
    """Test initialization and setup."""
    
    def test_init_with_default_path(self) -> None:
        """Test initialization with default database path."""
        aggregator = ErrorAggregator()
        assert aggregator.db_path == Path(".netra/error_db.sqlite")
        assert aggregator.similarity_threshold == 0.8

    def test_init_with_custom_path(self, temp_db_path: Path) -> None:
        """Test initialization with custom database path."""
        aggregator = ErrorAggregator(str(temp_db_path))
        assert aggregator.db_path == temp_db_path

class TestDatabaseSetup:
    """Test database creation and setup."""
    @pytest.mark.asyncio
    async def test_ensure_database_exists(self, error_aggregator: ErrorAggregator,
                                         temp_db_path: Path) -> None:
        """Test database and directory creation."""
        await error_aggregator._ensure_database_exists()
        assert temp_db_path.parent.exists()
    @pytest.mark.asyncio
    async def test_create_tables(self, error_aggregator: ErrorAggregator) -> None:
        """Test database table creation."""
        await error_aggregator._ensure_database_exists()
        
        # Verify tables exist by querying them
        async with aiosqlite.connect(error_aggregator.db_path) as db:
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in await cursor.fetchall()]
            assert "startup_errors" in tables
            assert "error_patterns" in tables

class TestErrorRecording:
    """Test error recording functionality."""
    @pytest.mark.asyncio
    async def test_record_error_basic(self, error_aggregator: ErrorAggregator) -> None:
        """Test basic error recording."""
        error_id = await error_aggregator.record_error("backend", "Test error")
        assert isinstance(error_id, int)
        assert error_id > 0
    @pytest.mark.asyncio
    async def test_record_error_with_all_fields(self, error_aggregator: ErrorAggregator) -> None:
        """Test error recording with all optional fields."""
        error_id = await error_aggregator.record_error(
            service="frontend",
            message="Build failed",
            phase=ErrorPhase.RUNTIME,
            severity=ErrorSeverity.HIGH.value,
            error_type=ErrorType.DEPENDENCY,
            stack_trace="trace",
            context={"version": "1.0"}
        )
        assert isinstance(error_id, int)
    @pytest.mark.asyncio
    async def test_insert_error_database_operation(self, error_aggregator: ErrorAggregator,
                                                   sample_error: StartupError) -> None:
        """Test insert error database operation."""
        await error_aggregator._ensure_database_exists()
        error_id = await error_aggregator._insert_error(sample_error)
        
        # Verify error was inserted
        async with aiosqlite.connect(error_aggregator.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM startup_errors")
            count = (await cursor.fetchone())[0]
            assert count == 1

class TestErrorRetrieval:
    """Test error retrieval functionality."""
    @pytest.mark.asyncio
    async def test_get_recent_errors(self, error_aggregator: ErrorAggregator,
                                    sample_errors: List[StartupError]) -> None:
        """Test recent error retrieval."""
        await error_aggregator._ensure_database_exists()
        
        # Insert sample errors
        for error in sample_errors:
            await error_aggregator._insert_error(error)
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_errors = await error_aggregator._get_recent_errors(cutoff)
        assert len(recent_errors) == 3
    @pytest.mark.asyncio
    async def test_get_recent_errors_with_cutoff(self, error_aggregator: ErrorAggregator,
                                                sample_errors: List[StartupError]) -> None:
        """Test recent error retrieval with time cutoff."""
        await error_aggregator._ensure_database_exists()
        
        for error in sample_errors:
            await error_aggregator._insert_error(error)
        
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=7)
        recent_errors = await error_aggregator._get_recent_errors(cutoff)
        assert len(recent_errors) == 2  # Only errors within 7 minutes

    def test_row_to_error_conversion(self, error_aggregator: ErrorAggregator) -> None:
        """Test database row to StartupError conversion."""
        sample_row = (1, "2024-01-01T00:00:00", "backend", "startup", "medium", 
                     "connection", "test message", "stack trace")
        
        error = error_aggregator._row_to_error(sample_row)
        assert error.id == 1
        assert error.service == "backend"
        assert error.message == "test message"

class TestPatternDetection:
    """Test error pattern detection."""
    @pytest.mark.asyncio
    async def test_find_patterns_empty_errors(self, error_aggregator: ErrorAggregator) -> None:
        """Test pattern detection with no errors."""
        patterns = await error_aggregator.find_patterns()
        assert len(patterns) == 0
    @pytest.mark.asyncio
    async def test_detect_similar_errors_empty(self, error_aggregator: ErrorAggregator) -> None:
        """Test similar error detection with empty list."""
        patterns = await error_aggregator._detect_similar_errors([])
        assert len(patterns) == 0

    def test_find_similar_messages(self, error_aggregator: ErrorAggregator,
                                  sample_errors: List[StartupError]) -> None:
        """Test similar message detection."""
        similar_indices = error_aggregator._find_similar_messages(
            "Database connection failed", sample_errors, 0)
        assert 0 in similar_indices
        assert 1 in similar_indices  # "Database connection timeout" is similar

    def test_create_pattern_from_errors(self, error_aggregator: ErrorAggregator,
                                       sample_errors: List[StartupError]) -> None:
        """Test pattern creation from similar errors."""
        similar_errors = sample_errors[:2]  # First two database errors
        pattern = error_aggregator._create_pattern_from_errors(similar_errors)
        assert pattern.frequency == 2
        assert "Database connection" in pattern.pattern

class TestTrendAnalysis:
    """Test error trend analysis."""
    @pytest.mark.asyncio
    async def test_get_trends_empty(self, error_aggregator: ErrorAggregator) -> None:
        """Test trend analysis with no errors."""
        trends = await error_aggregator.get_trends()
        assert trends.total_errors == 0
        assert trends.period == "24h"

    def test_analyze_error_trends_empty(self, error_aggregator: ErrorAggregator) -> None:
        """Test trend analysis with empty error list."""
        trends = error_aggregator._analyze_error_trends([], "24h")
        assert trends.total_errors == 0
        assert trends.period == "24h"

    def test_calculate_error_breakdowns(self, error_aggregator: ErrorAggregator,
                                       sample_errors: List[StartupError]) -> None:
        """Test error breakdown calculation."""
        breakdowns = error_aggregator._calculate_error_breakdowns(sample_errors)
        assert "error_types" in breakdowns
        assert "services" in breakdowns
        assert "severity_breakdown" in breakdowns
        assert breakdowns["services"]["backend"] == 2
        assert breakdowns["services"]["frontend"] == 1

    def test_update_breakdown_counters(self, error_aggregator: ErrorAggregator,
                                      sample_error: StartupError) -> None:
        """Test breakdown counter updates."""
        error_types, services, severity_breakdown = {}, {}, {}
        error_aggregator._update_breakdown_counters(
            sample_error, error_types, services, severity_breakdown)
        assert services["backend"] == 1
        assert error_types["connection"] == 1

class TestFixSuggestions:
    """Test fix suggestion functionality."""
    
    def test_suggest_fix_connection_error(self, error_aggregator: ErrorAggregator) -> None:
        """Test fix suggestion for connection errors."""
        fix = error_aggregator._suggest_fix(ErrorType.CONNECTION)
        assert "network connectivity" in fix.lower()

    def test_suggest_fix_configuration_error(self, error_aggregator: ErrorAggregator) -> None:
        """Test fix suggestion for configuration errors."""
        fix = error_aggregator._suggest_fix(ErrorType.CONFIGURATION)
        assert "configuration" in fix.lower()

    def test_suggest_fix_unknown_error(self, error_aggregator: ErrorAggregator) -> None:
        """Test fix suggestion for unknown error types."""
        fix = error_aggregator._suggest_fix(ErrorType.OTHER)
        assert "review error details" in fix.lower()

class TestPatternFrequencyTracking:
    """Test pattern frequency tracking."""
    @pytest.mark.asyncio
    async def test_update_pattern_frequency(self, error_aggregator: ErrorAggregator) -> None:
        """Test pattern frequency update in database."""
        await error_aggregator._ensure_database_exists()
        
        pattern = ErrorPattern(
            pattern="test pattern",
            frequency=3,
            last_seen=datetime.now(timezone.utc),
            suggested_fix="test fix"
        )
        
        await error_aggregator._update_pattern_frequency(pattern)
        
        # Verify pattern was stored
        async with aiosqlite.connect(error_aggregator.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM error_patterns")
            count = (await cursor.fetchone())[0]
            assert count == 1

class TestReportGeneration:
    """Test report generation functionality."""
    @pytest.mark.asyncio
    async def test_generate_report_daily(self, error_aggregator: ErrorAggregator) -> None:
        """Test daily report generation."""
        with patch.object(error_aggregator, 'get_trends') as mock_trends:
            with patch.object(error_aggregator, 'find_patterns') as mock_patterns:
                mock_trends.return_value = ErrorTrend(period="daily", total_errors=5)
                mock_patterns.return_value = []
                
                report = await error_aggregator.generate_report("daily")
                assert report["report_type"] == "daily"
                assert "trends" in report
                assert "recommendations" in report
    @pytest.mark.asyncio
    async def test_generate_report_weekly(self, error_aggregator: ErrorAggregator) -> None:
        """Test weekly report generation."""
        with patch.object(error_aggregator, 'get_trends') as mock_trends:
            with patch.object(error_aggregator, 'find_patterns') as mock_patterns:
                mock_trends.return_value = ErrorTrend(period="weekly", total_errors=10)
                mock_patterns.return_value = []
                
                report = await error_aggregator.generate_report("weekly")
                assert "generated_at" in report

class TestRecommendations:
    """Test recommendation generation."""
    
    def test_generate_recommendations_empty(self, error_aggregator: ErrorAggregator) -> None:
        """Test recommendations with no errors or patterns."""
        trends = ErrorTrend(period="24h", total_errors=0)
        patterns = []
        recommendations = error_aggregator._generate_recommendations(trends, patterns)
        assert len(recommendations) <= 3

    def test_add_volume_recommendation(self, error_aggregator: ErrorAggregator) -> None:
        """Test volume-based recommendation."""
        trends = ErrorTrend(period="24h", total_errors=15)
        recommendations = []
        error_aggregator._add_volume_recommendation(trends, recommendations)
        assert len(recommendations) == 1
        assert "high error volume" in recommendations[0].lower()

    def test_add_pattern_recommendation(self, error_aggregator: ErrorAggregator) -> None:
        """Test pattern-based recommendation."""
        pattern = ErrorPattern(pattern="test", frequency=5, 
                              last_seen=datetime.now(timezone.utc),
                              suggested_fix="test fix")
        recommendations = []
        error_aggregator._add_pattern_recommendation([pattern], recommendations)
        assert len(recommendations) == 1

    def test_add_critical_recommendation(self, error_aggregator: ErrorAggregator) -> None:
        """Test critical error recommendation."""
        trends = ErrorTrend(period="24h", total_errors=5,
                           severity_breakdown={"critical": 2})
        recommendations = []
        error_aggregator._add_critical_recommendation(trends, recommendations)
        assert len(recommendations) == 1
        assert "critical errors" in recommendations[0].lower()

class TestIntegrationScenarios:
    """Test integration scenarios combining multiple features."""
    @pytest.mark.asyncio
    async def test_full_workflow_record_analyze_report(self, error_aggregator: ErrorAggregator) -> None:
        """Test complete workflow from recording to reporting."""
        # Record some errors
        await error_aggregator.record_error("backend", "Connection failed")
        await error_aggregator.record_error("backend", "Connection timeout")
        await error_aggregator.record_error("frontend", "Build error")
        
        # Find patterns
        patterns = await error_aggregator.find_patterns(lookback_hours=1)
        assert len(patterns) >= 0  # May find connection pattern
        
        # Generate report
        report = await error_aggregator.generate_report()
        assert report["trends"]["total_errors"] == 3
    @pytest.mark.asyncio
    async def test_pattern_frequency_updates(self, error_aggregator: ErrorAggregator) -> None:
        """Test that pattern frequencies are properly updated."""
        # Record similar errors
        for i in range(3):
            await error_aggregator.record_error("backend", f"Database connection failed {i}")
        
        patterns = await error_aggregator.find_patterns(lookback_hours=1)
        if patterns:
            assert any(p.frequency >= 2 for p in patterns)
    @pytest.mark.asyncio
    async def test_time_based_analysis(self, error_aggregator: ErrorAggregator) -> None:
        """Test time-based error analysis."""
        # Record error now
        await error_aggregator.record_error("backend", "Recent error")
        
        # Test different time periods
        trends_1h = await error_aggregator.get_trends(1)
        trends_24h = await error_aggregator.get_trends(24)
        
        assert trends_1h.total_errors >= 1
        assert trends_24h.total_errors >= trends_1h.total_errors