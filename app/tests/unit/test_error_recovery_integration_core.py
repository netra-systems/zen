"""Core Tests - Split from test_error_recovery_integration.py"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from app.core.error_recovery_integration import (
from app.core.error_recovery import OperationType
from app.core.error_codes import ErrorSeverity
from app.core.agent_recovery_types import AgentType

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def test_determine_severity(self, recovery_system):
        """Test error severity determination."""
        assert recovery_system._determine_severity(MemoryError()) == ErrorSeverity.CRITICAL
        assert recovery_system._determine_severity(ConnectionError()) == ErrorSeverity.HIGH
        assert recovery_system._determine_severity(TimeoutError()) == ErrorSeverity.MEDIUM
        assert recovery_system._determine_severity(ValueError()) == ErrorSeverity.HIGH
        assert recovery_system._determine_severity(RuntimeError()) == ErrorSeverity.MEDIUM

    def test_determine_severity_from_status(self, recovery_system):
        """Test severity determination from HTTP status codes."""
        assert recovery_system._determine_severity_from_status(500) == ErrorSeverity.HIGH
        assert recovery_system._determine_severity_from_status(502) == ErrorSeverity.HIGH
        assert recovery_system._determine_severity_from_status(404) == ErrorSeverity.MEDIUM
        assert recovery_system._determine_severity_from_status(429) == ErrorSeverity.MEDIUM
        assert recovery_system._determine_severity_from_status(200) == ErrorSeverity.LOW
        assert recovery_system._determine_severity_from_status(None) == ErrorSeverity.MEDIUM

    def test_get_recovery_metrics(self, recovery_system):
        """Test recovery metrics collection."""
        # Mock all metric sources
        recovery_system.circuit_breaker_registry.get_all_metrics = Mock(return_value={})
        recovery_system.degradation_manager.get_degradation_status = Mock(return_value={})
        recovery_system.memory_monitor.get_memory_status = Mock(return_value={})
        recovery_system.websocket_manager.get_all_status = Mock(return_value={})
        recovery_system.database_registry.get_global_status = Mock(return_value={})
        recovery_system.error_aggregation.get_system_status = Mock(return_value={})
        
        # Test metrics collection
        metrics = recovery_system.get_recovery_metrics()
        
        assert 'recovery_stats' in metrics
        assert 'circuit_breakers' in metrics
        assert 'degradation_status' in metrics
        assert 'memory_status' in metrics
        assert 'websocket_status' in metrics
        assert 'database_status' in metrics
        assert 'error_aggregation' in metrics

    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()

    def mock_error(self):
        """Create mock error for testing."""
        return ConnectionError("Test connection error")

    def test_prepare_error_data(self, recovery_system):
        """Test error data preparation."""
        error = ValueError("Test error")
        
        result = recovery_system._prepare_error_data(
            'triage', 'classify', error, {'key': 'value'}, 'user123'
        )
        
        assert result['error_type'] == 'ValueError'
        assert result['module'] == 'agent_triage'
        assert result['function'] == 'classify'
        assert result['message'] == 'Test error'
        assert result['user_id'] == 'user123'
        assert result['context'] == {'key': 'value'}
        assert isinstance(result['timestamp'], datetime)

    def test_get_agent_type_enum(self, recovery_system):
        """Test agent type enum conversion."""
        from app.core.agent_recovery_types import AgentType
        
        assert recovery_system._get_agent_type_enum('triage') == AgentType.TRIAGE
        assert recovery_system._get_agent_type_enum('data_analysis') == AgentType.DATA_ANALYSIS
        assert recovery_system._get_agent_type_enum('unknown') is None

    def test_determine_severity(self, recovery_system):
        """Test error severity determination."""
        assert recovery_system._determine_severity(MemoryError()) == ErrorSeverity.CRITICAL
        assert recovery_system._determine_severity(ConnectionError()) == ErrorSeverity.HIGH
        assert recovery_system._determine_severity(TimeoutError()) == ErrorSeverity.MEDIUM
        assert recovery_system._determine_severity(ValueError()) == ErrorSeverity.HIGH
        assert recovery_system._determine_severity(RuntimeError()) == ErrorSeverity.MEDIUM

    def test_determine_severity_from_status(self, recovery_system):
        """Test severity determination from HTTP status codes."""
        assert recovery_system._determine_severity_from_status(500) == ErrorSeverity.HIGH
        assert recovery_system._determine_severity_from_status(502) == ErrorSeverity.HIGH
        assert recovery_system._determine_severity_from_status(404) == ErrorSeverity.MEDIUM
        assert recovery_system._determine_severity_from_status(429) == ErrorSeverity.MEDIUM
        assert recovery_system._determine_severity_from_status(200) == ErrorSeverity.LOW
        assert recovery_system._determine_severity_from_status(None) == ErrorSeverity.MEDIUM

    def test_get_recovery_metrics(self, recovery_system):
        """Test recovery metrics collection."""
        # Mock all metric sources
        recovery_system.circuit_breaker_registry.get_all_metrics = Mock(return_value={})
        recovery_system.degradation_manager.get_degradation_status = Mock(return_value={})
        recovery_system.memory_monitor.get_memory_status = Mock(return_value={})
        recovery_system.websocket_manager.get_all_status = Mock(return_value={})
        recovery_system.database_registry.get_global_status = Mock(return_value={})
        recovery_system.error_aggregation.get_system_status = Mock(return_value={})
        
        # Test metrics collection
        metrics = recovery_system.get_recovery_metrics()
        
        assert 'recovery_stats' in metrics
        assert 'circuit_breakers' in metrics
        assert 'degradation_status' in metrics
        assert 'memory_status' in metrics
        assert 'websocket_status' in metrics
        assert 'database_status' in metrics
        assert 'error_aggregation' in metrics
