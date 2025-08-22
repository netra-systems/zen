"""
Tests for Corpus Audit Service

Comprehensive tests for audit logging, search, filtering, and reporting functionality.
Follows 450-line limit and async patterns.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions_base import NetraException
from app.core.exceptions_database import DatabaseError
from app.db.models_postgres import CorpusAuditLog
from app.schemas.registry import (
    CorpusAuditAction,
    CorpusAuditMetadata,
    CorpusAuditRecord,
    CorpusAuditSearchFilter,
    CorpusAuditStatus,
)

# Add project root to path
from app.services.audit.corpus_audit import (
    # Add project root to path
    CorpusAuditLogger,
    create_audit_logger,
)
from app.services.audit.repository import CorpusAuditRepository
from app.services.audit.utils import AuditTimer


class TestCorpusAuditRepository:
    """Test corpus audit repository functionality."""

    @pytest.fixture
    def repository(self):
        return CorpusAuditRepository()

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_audit_log(self):
        return CorpusAuditLog(
            id="test-id",
            timestamp=datetime.now(UTC),
            user_id="user-123",
            action="create",
            status="success",
            resource_type="corpus",
            corpus_id="corpus-456"
        )

    async def test_find_by_user_success(self, repository, mock_db, sample_audit_log):
        """Test finding audit records by user ID."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_audit_log]
        mock_db.execute.return_value = mock_result
        
        records = await repository.find_by_user(mock_db, "user-123")
        
        assert len(records) == 1
        assert records[0].user_id == "user-123"

    async def test_find_by_user_database_error(self, repository, mock_db):
        """Test database error handling in find_by_user."""
        mock_db.execute.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseError):
            await repository.find_by_user(mock_db, "user-123")

    async def test_search_records_with_filters(self, repository, mock_db, sample_audit_log):
        """Test searching records with comprehensive filters."""
        filters = CorpusAuditSearchFilter(
            user_id="user-123",
            action=CorpusAuditAction.CREATE,
            status=CorpusAuditStatus.SUCCESS,
            limit=50
        )
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_audit_log]
        mock_db.execute.return_value = mock_result
        
        records = await repository.search_records(mock_db, filters)
        
        assert len(records) == 1
        assert records[0].action == "create"

    async def test_count_records_success(self, repository, mock_db):
        """Test counting audit records with filters."""
        filters = CorpusAuditSearchFilter(user_id="user-123")
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result
        
        count = await repository.count_records(mock_db, filters)
        
        assert count == 42

    async def test_get_summary_stats_success(self, repository, mock_db):
        """Test getting summary statistics."""
        mock_results = [("create", "success", 10), ("update", "failure", 2)]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_results
        mock_db.execute.return_value = mock_result
        
        stats = await repository.get_summary_stats(mock_db, CorpusAuditSearchFilter())
        
        assert stats["create_success"] == 10
        assert stats["update_failure"] == 2


class TestCorpusAuditLogger:
    """Test corpus audit logger functionality."""

    @pytest.fixture
    def mock_repository(self):
        return AsyncMock(spec=CorpusAuditRepository)

    @pytest.fixture
    def audit_logger(self, mock_repository):
        return CorpusAuditLogger(mock_repository)

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_metadata(self):
        return CorpusAuditMetadata(
            user_agent="test-agent",
            ip_address="192.168.1.1",
            request_id="req-123",
            configuration={"setting": "value"}
        )

    async def test_log_operation_success(self, audit_logger, mock_repository, mock_db, sample_metadata):
        """Test successful operation logging."""
        mock_audit_log = CorpusAuditLog(
            id="audit-123",
            timestamp=datetime.now(UTC),
            action="create",
            resource_type="corpus",
            status="success"
        )
        mock_repository.create.return_value = mock_audit_log
        
        result = await audit_logger.log_operation(
            mock_db,
            CorpusAuditAction.CREATE,
            "corpus",
            user_id="user-123",
            metadata=sample_metadata
        )
        
        assert isinstance(result, CorpusAuditRecord)
        assert result.action == CorpusAuditAction.CREATE
        mock_repository.create.assert_called_once()

    async def test_log_operation_with_duration(self, audit_logger, mock_repository, mock_db):
        """Test logging operation with timing data."""
        mock_audit_log = CorpusAuditLog(
            id="audit-123",
            timestamp=datetime.now(UTC),
            action="search",
            resource_type="document",
            status="success",
            operation_duration_ms=150.5
        )
        mock_repository.create.return_value = mock_audit_log
        
        result = await audit_logger.log_operation(
            mock_db,
            CorpusAuditAction.SEARCH,
            "document",
            operation_duration_ms=150.5
        )
        
        assert result.operation_duration_ms == 150.5

    async def test_log_operation_failure(self, audit_logger, mock_repository, mock_db):
        """Test handling of logging failures."""
        mock_repository.create.side_effect = Exception("Database error")
        
        with pytest.raises(NetraException):
            await audit_logger.log_operation(
                mock_db,
                CorpusAuditAction.CREATE,
                "corpus"
            )

    async def test_search_audit_logs_success(self, audit_logger, mock_repository, mock_db):
        """Test searching audit logs with report generation."""
        filters = CorpusAuditSearchFilter(limit=10)
        mock_records = [CorpusAuditLog(
            id="1", 
            timestamp=datetime.now(UTC),
            action="create", 
            resource_type="corpus", 
            status="success"
        )]
        
        mock_repository.search_records.return_value = mock_records
        mock_repository.count_records.return_value = 1
        mock_repository.get_summary_stats.return_value = {"create_success": 1}
        
        report = await audit_logger.search_audit_logs(mock_db, filters)
        
        assert report.total_records == 1
        assert len(report.records) == 1
        assert "create_success" in report.summary

    async def test_search_audit_logs_failure(self, audit_logger, mock_repository, mock_db):
        """Test search failure handling."""
        filters = CorpusAuditSearchFilter()
        mock_repository.search_records.side_effect = Exception("Search failed")
        
        with pytest.raises(NetraException):
            await audit_logger.search_audit_logs(mock_db, filters)


class TestAuditTimer:
    """Test audit timer context manager."""

    def test_timer_measures_duration(self):
        """Test timer correctly measures operation duration."""
        import time
        
        with AuditTimer() as timer:
            time.sleep(0.01)  # 10ms sleep
        
        duration = timer.get_duration()
        assert duration is not None
        assert duration > 5  # Should be at least 5ms

    def test_timer_without_context(self):
        """Test timer when not used as context manager."""
        timer = AuditTimer()
        duration = timer.get_duration()
        assert duration is None


class TestAuditIntegration:
    """Integration tests for audit system."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    async def test_create_audit_logger_factory(self, mock_db):
        """Test audit logger factory function."""
        logger = await create_audit_logger(mock_db)
        
        assert isinstance(logger, CorpusAuditLogger)
        assert isinstance(logger.repository, CorpusAuditRepository)

    async def test_end_to_end_audit_workflow(self, mock_db):
        """Test complete audit workflow from logging to reporting."""
        # Setup
        logger = await create_audit_logger(mock_db)
        logger.repository = AsyncMock(spec=CorpusAuditRepository)
        
        # Mock audit log creation
        mock_audit_log = CorpusAuditLog(
            id="audit-123",
            timestamp=datetime.now(UTC),
            user_id="user-123",
            action="create",
            resource_type="corpus",
            status="success",
            corpus_id="corpus-456"
        )
        logger.repository.create.return_value = mock_audit_log
        
        # Test logging
        result = await logger.log_operation(
            mock_db,
            CorpusAuditAction.CREATE,
            "corpus",
            user_id="user-123",
            corpus_id="corpus-456"
        )
        
        assert result.user_id == "user-123"
        assert result.corpus_id == "corpus-456"
        
        # Test searching
        logger.repository.search_records.return_value = [mock_audit_log]
        logger.repository.count_records.return_value = 1
        logger.repository.get_summary_stats.return_value = {"create_success": 1}
        
        filters = CorpusAuditSearchFilter(user_id="user-123")
        report = await logger.search_audit_logs(mock_db, filters)
        
        assert report.total_records == 1
        assert len(report.records) == 1
        assert report.records[0].user_id == "user-123"


# Performance and edge case tests
class TestAuditPerformance:
    """Test audit system performance and edge cases."""

    @pytest.fixture
    def audit_logger(self):
        repository = AsyncMock(spec=CorpusAuditRepository)
        return CorpusAuditLogger(repository)

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    async def test_large_result_data_handling(self, audit_logger, mock_db):
        """Test handling of large result data objects."""
        large_data = {"results": ["item"] * 1000}  # Large data set
        
        mock_audit_log = CorpusAuditLog(
            id="audit-123",
            timestamp=datetime.now(UTC),
            action="export",
            resource_type="corpus",
            status="success",
            result_data=large_data
        )
        audit_logger.repository.create.return_value = mock_audit_log
        
        result = await audit_logger.log_operation(
            mock_db,
            CorpusAuditAction.EXPORT,
            "corpus",
            result_data=large_data
        )
        
        assert len(result.result_data["results"]) == 1000

    async def test_metadata_edge_cases(self, audit_logger, mock_db):
        """Test metadata handling with edge cases."""
        empty_metadata = CorpusAuditMetadata()
        
        mock_audit_log = CorpusAuditLog(
            id="audit-123",
            timestamp=datetime.now(UTC),
            action="validate",
            resource_type="document",
            status="success"
        )
        audit_logger.repository.create.return_value = mock_audit_log
        
        result = await audit_logger.log_operation(
            mock_db,
            CorpusAuditAction.VALIDATE,
            "document",
            metadata=empty_metadata
        )
        
        assert isinstance(result.metadata, CorpusAuditMetadata)


if __name__ == "__main__":
    pytest.main([__file__])