"""Unit tests for error recovery integration system error handling.

This module tests the EnhancedErrorRecoverySystem class from 
netra_backend.app.core.error_recovery_integration focusing on error handling capabilities.
"""

import asyncio
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest

try:
    from netra_backend.app.core.error_recovery_integration import EnhancedErrorRecoverySystem
    from netra_backend.app.core.error_codes import ErrorSeverity
except ImportError:
    pytest.skip("Error recovery integration modules have missing dependencies", allow_module_level=True)


class TestEnhancedErrorRecoverySystemErrorHandling:
    """Test error handling capabilities of EnhancedErrorRecoverySystem."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.recovery_system = EnhancedErrorRecoverySystem()
    
    def test_system_initialization(self):
        """Test that recovery system initializes all required components."""
        # Verify core managers are initialized
        assert hasattr(self.recovery_system, 'retry_manager')
        assert hasattr(self.recovery_system, 'circuit_breaker_registry')
        assert hasattr(self.recovery_system, 'degradation_manager')
        assert hasattr(self.recovery_system, 'memory_monitor')
        assert hasattr(self.recovery_system, 'websocket_manager')
        assert hasattr(self.recovery_system, 'database_registry')
        assert hasattr(self.recovery_system, 'error_aggregation')
        
        # Verify legacy compatibility
        assert hasattr(self.recovery_system, 'agent_registry')
        assert hasattr(self.recovery_system, 'error_logger')
        
        # Verify recovery stats
        assert hasattr(self.recovery_system, 'recovery_stats')
        assert isinstance(self.recovery_system.recovery_stats, dict)
        assert 'total_recoveries' in self.recovery_system.recovery_stats
        assert 'successful_recoveries' in self.recovery_system.recovery_stats
        assert 'failed_recoveries' in self.recovery_system.recovery_stats
    
    def test_error_severity_determination(self):
        """Test error severity determination logic."""
        # Test critical errors
        memory_error = MemoryError("Out of memory")
        severity = self.recovery_system._determine_severity(memory_error)
        assert severity == ErrorSeverity.CRITICAL
        
        # Test high severity errors
        connection_error = ConnectionError("Connection failed")
        severity = self.recovery_system._determine_severity(connection_error)
        assert severity == ErrorSeverity.HIGH
        
        # Test medium severity errors
        timeout_error = TimeoutError("Request timed out")
        severity = self.recovery_system._determine_severity(timeout_error)
        assert severity == ErrorSeverity.MEDIUM
        
        # Test unknown error types default to medium
        unknown_error = RuntimeError("Unknown error")
        severity = self.recovery_system._determine_severity(unknown_error)
        assert severity == ErrorSeverity.MEDIUM
    
    def test_http_status_code_severity_mapping(self):
        """Test HTTP status code to severity mapping."""
        # Test server errors (5xx) are high severity
        severity = self.recovery_system._determine_severity_from_status(500)
        assert severity == ErrorSeverity.HIGH
        
        severity = self.recovery_system._determine_severity_from_status(503)
        assert severity == ErrorSeverity.HIGH
        
        # Test client errors (4xx) are medium severity
        severity = self.recovery_system._determine_severity_from_status(400)
        assert severity == ErrorSeverity.MEDIUM
        
        severity = self.recovery_system._determine_severity_from_status(404)
        assert severity == ErrorSeverity.MEDIUM
        
        # Test success codes (2xx/3xx) are low severity
        severity = self.recovery_system._determine_severity_from_status(200)
        assert severity == ErrorSeverity.LOW
        
        severity = self.recovery_system._determine_severity_from_status(301)
        assert severity == ErrorSeverity.LOW
        
        # Test None status code defaults to medium
        severity = self.recovery_system._determine_severity_from_status(None)
        assert severity == ErrorSeverity.MEDIUM
    
    def test_agent_type_enum_mapping(self):
        """Test agent type string to enum conversion."""
        from netra_backend.app.core.agent_recovery_strategies_main import AgentType
        
        # Test basic agent types
        agent_type = self.recovery_system._get_agent_type_enum('triage')
        assert agent_type == AgentType.TRIAGE
        
        agent_type = self.recovery_system._get_agent_type_enum('data_analysis')
        assert agent_type == AgentType.DATA_ANALYSIS
        
        # Test advanced agent types
        agent_type = self.recovery_system._get_agent_type_enum('corpus_admin')
        assert agent_type == AgentType.CORPUS_ADMIN
        
        agent_type = self.recovery_system._get_agent_type_enum('supervisor')
        assert agent_type == AgentType.SUPERVISOR
        
        # Test unknown agent type returns None
        agent_type = self.recovery_system._get_agent_type_enum('unknown_agent')
        assert agent_type is None
    
    def test_error_data_preparation_for_agents(self):
        """Test error data preparation for agent errors."""
        error = ValueError("Test error")
        context_data = {'key': 'value'}
        user_id = 'user123'
        
        error_data = self.recovery_system._prepare_error_data(
            'triage', 'process_request', error, context_data, user_id
        )
        
        assert error_data['error_type'] == 'ValueError'
        assert error_data['module'] == 'agent_triage'
        assert error_data['function'] == 'process_request'
        assert error_data['message'] == 'Test error'
        assert error_data['user_id'] == 'user123'
        assert error_data['context'] == context_data
        assert 'timestamp' in error_data
    
    def test_error_data_preparation_for_database(self):
        """Test error data preparation for database errors."""
        error = ConnectionError("Database connection failed")
        
        error_data = self.recovery_system._prepare_database_error_data(
            'users', 'insert', error, 'tx123'
        )
        
        assert error_data['error_type'] == 'ConnectionError'
        assert error_data['module'] == 'database'
        assert error_data['function'] == 'insert'
        assert error_data['message'] == 'Database connection failed'
        assert error_data['table_name'] == 'users'
        assert error_data['transaction_id'] == 'tx123'
    
    def test_error_data_preparation_for_api(self):
        """Test error data preparation for API errors."""
        error = TimeoutError("API timeout")
        
        error_data = self.recovery_system._prepare_api_error_data(
            '/api/users', 'GET', error, 503
        )
        
        assert error_data['error_type'] == 'TimeoutError'
        assert error_data['module'] == 'api'
        assert error_data['function'] == 'GET'
        assert error_data['message'] == 'API timeout'
        assert error_data['endpoint'] == '/api/users'
        assert error_data['status_code'] == 503
    
    def test_error_data_preparation_for_websocket(self):
        """Test error data preparation for WebSocket errors."""
        error = ConnectionResetError("Connection reset")
        
        error_data = self.recovery_system._prepare_websocket_error_data(
            'conn123', error
        )
        
        assert error_data['error_type'] == 'ConnectionResetError'
        assert error_data['module'] == 'websocket'
        assert error_data['function'] == 'connection'
        assert error_data['message'] == 'Connection reset'
        assert error_data['connection_id'] == 'conn123'
    
    def test_database_rollback_execution(self):
        """Test database rollback execution logic."""
        result = self.recovery_system._execute_database_rollback('users')
        
        assert result['status'] == 'rollback_queued'
        assert result['table'] == 'users'
    
    def test_recovery_context_building_for_agents(self):
        """Test recovery context building for agent operations."""
        from netra_backend.app.core.error_recovery import OperationType
        
        error = RuntimeError("Agent failed")
        context = self.recovery_system._build_recovery_context(
            'triage', 'process_request', error
        )
        
        assert context.operation_id == 'triage_process_request'
        assert context.operation_type == OperationType.AGENT_EXECUTION
        assert context.error == error
        assert context.metadata['agent_type'] == 'triage'
        assert context.metadata['operation'] == 'process_request'
        assert context.severity == ErrorSeverity.MEDIUM  # Default for RuntimeError
    
    def test_recovery_context_building_for_api(self):
        """Test recovery context building for API operations."""
        from netra_backend.app.core.error_recovery import OperationType
        
        error = TimeoutError("API timeout")
        context = self.recovery_system._build_api_recovery_context(
            '/api/data', 'POST', error, 504
        )
        
        assert context.operation_id == 'POST_/api/data'
        assert context.operation_type == OperationType.EXTERNAL_API
        assert context.error == error
        assert context.metadata['endpoint'] == '/api/data'
        assert context.metadata['method'] == 'POST'
        assert context.metadata['status_code'] == 504
        assert context.severity == ErrorSeverity.HIGH  # 5xx status code
    
    def test_recovery_metrics_structure(self):
        """Test that recovery metrics return expected structure."""
        metrics = self.recovery_system.get_recovery_metrics()
        
        # Verify basic metrics
        assert 'recovery_stats' in metrics
        assert 'circuit_breakers' in metrics
        assert 'degradation_status' in metrics
        
        # Verify extended metrics
        assert 'memory_status' in metrics
        assert 'websocket_status' in metrics
        assert 'database_status' in metrics
        assert 'error_aggregation' in metrics
        
        # Verify recovery stats structure
        recovery_stats = metrics['recovery_stats']
        assert 'total_recoveries' in recovery_stats
        assert 'successful_recoveries' in recovery_stats
        assert 'failed_recoveries' in recovery_stats
        assert 'recovery_by_type' in recovery_stats
        assert 'recovery_by_strategy' in recovery_stats
    
    def test_database_recovery_logic_with_rollback_data(self):
        """Test database recovery logic when rollback data is provided."""
        rollback_data = {'action': 'rollback', 'checkpoint': 'cp123'}
        error = ConnectionError("DB connection lost")
        
        result = self.recovery_system._handle_database_recovery_logic(
            rollback_data, 'orders', error
        )
        
        assert result['status'] == 'rollback_queued'
        assert result['table'] == 'orders'
    
    def test_database_recovery_logic_without_rollback_data(self):
        """Test database recovery logic when no rollback data is provided."""
        error = ConnectionError("DB connection lost")
        
        with pytest.raises(ConnectionError, match="DB connection lost"):
            self.recovery_system._handle_database_recovery_logic(
                None, 'orders', error
            )
    
    @pytest.mark.asyncio
    async def test_memory_exhaustion_handling(self):
        """Test memory exhaustion handling."""
        with patch.object(self.recovery_system.memory_monitor, 'take_snapshot') as mock_snapshot, \
             patch.object(self.recovery_system.memory_monitor, 'check_and_recover') as mock_recover:
            
            # Mock successful recovery
            mock_snapshot.return_value = {'memory_usage': 0.8}
            mock_recover.return_value = True
            
            result = await self.recovery_system.handle_memory_exhaustion()
            
            assert result is True
            mock_snapshot.assert_called_once()
            mock_recover.assert_called_once()
    
    def test_error_handling_edge_cases(self):
        """Test error handling for edge cases and invalid inputs."""
        # Test with None context data
        error_data = self.recovery_system._prepare_error_data(
            'triage', 'test', ValueError("test"), None, None
        )
        assert error_data['context'] == {}
        assert error_data['user_id'] is None
        
        # Test with empty context data
        error_data = self.recovery_system._prepare_error_data(
            'triage', 'test', ValueError("test"), {}, "user123"
        )
        assert error_data['context'] == {}
        assert error_data['user_id'] == "user123"


if __name__ == "__main__":
    pytest.main([__file__])
