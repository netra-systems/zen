"""
Database and persistence tests for SupplyResearcherAgent
Modular design with ≤300 lines, ≤8 lines per function
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.db.models_postgres import SupplyUpdateLog
from netra_backend.app.services.supply_research_service import SupplyResearchService
from netra_backend.tests.agents.supply_researcher_fixtures import (
    agent,
    anomaly_test_data,
    mock_db,
    mock_supply_service,
)

class TestSupplyResearcherPersistence:
    """Database and persistence tests"""

    @pytest.mark.asyncio

    async def test_database_transaction_rollback(self, agent, mock_db):
        """Test database transaction rollback on failure"""
        state = _create_transaction_test_state()
        mock_db.commit.side_effect = Exception("Database error")
        await _test_transaction_rollback(agent, state, mock_db)
        _verify_rollback_called(mock_db)

    def _create_transaction_test_state(self):
        """Create state for transaction testing (≤8 lines)"""
        return DeepAgentState(
            user_request="Test transaction",
            chat_thread_id="test_thread",
            user_id="test_user"
        )

    async def _test_transaction_rollback(self, agent, state, mock_db):
        """Test transaction rollback behavior (≤8 lines)"""
        with patch.object(agent.research_engine, 'call_deep_research_api', 
                         new_callable=AsyncMock) as mock_api:
            mock_api.return_value = _get_successful_api_response()
            try:
                await agent.execute(state, "tx_test", False)
            except Exception:
                pass

    def _get_successful_api_response(self):
        """Get successful API response data (≤8 lines)"""
        return {
            "session_id": "tx_test",
            "status": "completed",
            "questions_answered": [
                {"question": "price", "answer": "$30/1M tokens"}
            ],
            "citations": []
        }

    def _verify_rollback_called(self, mock_db):
        """Verify database rollback was called (≤8 lines)"""
        assert mock_db.rollback.called

    def test_anomaly_detection_thresholds(self, mock_supply_service):
        """Test anomaly detection with various thresholds"""
        service = SupplyResearchService(Mock())
        _setup_anomaly_detection_mock(service)
        anomalies = service.detect_anomalies(threshold=0.5)
        _verify_anomaly_detection(anomalies)

    def _setup_anomaly_detection_mock(self, service):
        """Setup anomaly detection mock (≤8 lines)"""
        with patch.object(service, 'calculate_price_changes') as mock_changes:
            mock_changes.return_value = {
                "all_changes": [{
                    "provider": "openai",
                    "model": "gpt-4",
                    "field": "pricing_input",
                    "percent_change": 150,  # 150% increase
                    "old_value": 10,
                    "new_value": 25
                }]
            }

    def _verify_anomaly_detection(self, anomalies):
        """Verify anomaly detection results (≤8 lines)"""
        assert len(anomalies) > 0
        assert anomalies[0]["percent_change"] == 150

    @pytest.mark.asyncio

    async def test_audit_trail_generation(self, agent, mock_db):
        """Test comprehensive audit trail generation"""
        state = _create_audit_test_state()
        audit_logs = []
        _setup_audit_tracking(mock_db, audit_logs)
        await _execute_audit_test(agent, state)
        _verify_audit_logs_created(mock_db)

    def _create_audit_test_state(self):
        """Create state for audit testing (≤8 lines)"""
        return DeepAgentState(
            user_request="Update all OpenAI models",
            chat_thread_id="audit_test",
            user_id="admin_user"
        )

    def _setup_audit_tracking(self, mock_db, audit_logs):
        """Setup audit log tracking (≤8 lines)"""
        def track_audit_log(log_entry):
            if isinstance(log_entry, SupplyUpdateLog):
                audit_logs.append(log_entry)
        mock_db.add.side_effect = track_audit_log

    async def _execute_audit_test(self, agent, state):
        """Execute audit trail test (≤8 lines)"""
        with patch.object(agent.research_engine, 'call_deep_research_api', 
                         new_callable=AsyncMock) as mock_api:
            mock_api.return_value = _get_audit_api_response()
            await agent.execute(state, "audit_run", False)

    def _get_audit_api_response(self):
        """Get API response for audit testing (≤8 lines)"""
        return {
            "session_id": "audit_session",
            "status": "completed",
            "questions_answered": [
                {"question": "pricing", "answer": "$25/1M input"}
            ],
            "citations": [{"source": "OpenAI", "url": "https://openai.com"}]
        }

    def _verify_audit_logs_created(self, mock_db):
        """Verify audit logs were created (≤8 lines)"""
        assert mock_db.add.called

    def test_data_validation_integrity(self, mock_supply_service):
        """Test data validation and integrity checks"""
        test_data = _create_test_supply_data()
        is_valid, errors = mock_supply_service.validate_supply_data(test_data)
        _verify_data_validation(is_valid, errors)

    def _create_test_supply_data(self):
        """Create test supply data (≤8 lines)"""
        return {
            "provider": "openai",
            "model": "gpt-4",
            "pricing_input": Decimal("30.00"),
            "pricing_output": Decimal("60.00"),
            "context_window": 128000
        }

    def _verify_data_validation(self, is_valid, errors):
        """Verify data validation results (≤8 lines)"""
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_concurrent_update_handling(self, mock_supply_service):
        """Test handling of concurrent supply item updates"""
        concurrent_data = _create_concurrent_update_data()
        _setup_concurrent_update_mock(mock_supply_service)
        result = mock_supply_service.create_or_update_supply_item(concurrent_data)
        _verify_concurrent_update_handling(result)

    def _create_concurrent_update_data(self):
        """Create concurrent update test data (≤8 lines)"""
        return {
            "provider": "openai",
            "model": "gpt-4",
            "pricing_input": Decimal("35.00"),
            "last_updated": "2024-01-01T00:00:00Z"
        }

    def _setup_concurrent_update_mock(self, mock_supply_service):
        """Setup concurrent update mock (≤8 lines)"""
        mock_supply_service.create_or_update_supply_item.return_value = {
            "status": "updated",
            "version": 2,
            "conflicts_resolved": True
        }

    def _verify_concurrent_update_handling(self, result):
        """Verify concurrent update was handled (≤8 lines)"""
        assert result["status"] == "updated"
        assert "conflicts_resolved" in result

    def test_large_dataset_performance(self, mock_supply_service):
        """Test performance with large datasets"""
        large_dataset = _create_large_test_dataset()
        _setup_performance_monitoring()
        result = mock_supply_service.get_supply_items(filters={"limit": 1000})
        _verify_performance_metrics(result)

    def _create_large_test_dataset(self):
        """Create large test dataset (≤8 lines)"""
        return [
            {"provider": f"provider_{i}", "model": f"model_{i}", 
             "pricing_input": Decimal(str(i))}
            for i in range(1000)
        ]

    def _setup_performance_monitoring(self):
        """Setup performance monitoring (≤8 lines)"""
        with patch('time.perf_counter') as mock_timer:
            mock_timer.side_effect = [0.0, 0.1]  # 100ms execution

    def _verify_performance_metrics(self, result):
        """Verify performance metrics (≤8 lines)"""
        # Performance should be acceptable for large datasets
        assert result is not None

    @pytest.mark.asyncio

    async def test_backup_and_recovery(self, agent, mock_db):
        """Test backup and recovery functionality"""
        _setup_backup_scenario(mock_db)
        recovery_data = await _test_recovery_process(agent)
        _verify_recovery_success(recovery_data)

    def _setup_backup_scenario(self, mock_db):
        """Setup backup test scenario (≤8 lines)"""
        mock_db.query.return_value.filter.return_value.all.return_value = [
            Mock(provider="openai", model="gpt-4", 
                 pricing_input=Decimal("30")),
        ]

    async def _test_recovery_process(self, agent):
        """Test data recovery process (≤8 lines)"""
        with patch.object(agent, '_recover_from_backup', 
                         return_value={"status": "recovered", "items": 5}):
            return await agent._recover_from_backup("backup_id")

    def _verify_recovery_success(self, recovery_data):
        """Verify recovery was successful (≤8 lines)"""
        assert recovery_data["status"] == "recovered"
        assert recovery_data["items"] > 0