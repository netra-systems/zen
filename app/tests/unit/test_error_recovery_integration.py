"""Comprehensive tests for enhanced error recovery integration system."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.core.error_recovery_integration import (
    EnhancedErrorRecoverySystem,
    enhanced_recovery_system,
    recover_agent_operation,
    recover_database_operation,
    recover_api_operation
)
from app.core.error_recovery import OperationType
from app.core.error_codes import ErrorSeverity


class TestEnhancedErrorRecoverySystem:
    """Test cases for enhanced error recovery system."""
    
    @pytest.fixture
    def recovery_system(self):
        """Create recovery system instance for testing."""
        return EnhancedErrorRecoverySystem()
    
    @pytest.fixture
    def mock_error(self):
        """Create mock error for testing."""
        return ConnectionError("Test connection error")
    
    @pytest.mark.asyncio
    async def test_handle_agent_error_success(self, recovery_system, mock_error):
        """Test successful agent error handling."""
        # Mock dependencies
        recovery_system.error_aggregation.process_error = AsyncMock()
        recovery_system.circuit_breaker_registry.get_breaker = Mock()
        
        mock_breaker = AsyncMock()
        mock_breaker.call = AsyncMock(return_value={'status': 'recovered'})
        recovery_system.circuit_breaker_registry.get_breaker.return_value = mock_breaker
        
        # Test agent error handling
        result = await recovery_system.handle_agent_error(
            'triage', 'classify', mock_error, {'test': 'data'}, 'user123'
        )
        
        assert result == {'status': 'recovered'}
        recovery_system.error_aggregation.process_error.assert_called_once()
        recovery_system.circuit_breaker_registry.get_breaker.assert_called_with('agent_triage')
    
    @pytest.mark.asyncio
    async def test_handle_agent_error_degradation(self, recovery_system, mock_error):
        """Test agent error handling with degradation fallback."""
        # Mock circuit breaker to fail
        recovery_system.error_aggregation.process_error = AsyncMock()
        recovery_system.circuit_breaker_registry.get_breaker = Mock()
        recovery_system.degradation_manager.degrade_service = AsyncMock(
            return_value={'status': 'degraded'}
        )
        
        mock_breaker = AsyncMock()
        mock_breaker.call = AsyncMock(side_effect=Exception("Circuit breaker failed"))
        recovery_system.circuit_breaker_registry.get_breaker.return_value = mock_breaker
        
        # Test degradation fallback
        result = await recovery_system.handle_agent_error(
            'triage', 'classify', mock_error
        )
        
        assert result == {'status': 'degraded'}
        recovery_system.degradation_manager.degrade_service.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_database_error_success(self, recovery_system, mock_error):
        """Test successful database error handling."""
        # Mock dependencies
        recovery_system.error_aggregation.process_error = AsyncMock()
        recovery_system.circuit_breaker_registry.get_breaker = Mock()
        
        mock_breaker = AsyncMock()
        mock_breaker.call = AsyncMock(return_value={'status': 'recovered'})
        recovery_system.circuit_breaker_registry.get_breaker.return_value = mock_breaker
        
        # Test database error handling
        result = await recovery_system.handle_database_error(
            'users', 'insert', mock_error, {'id': 123}, 'tx456'
        )
        
        assert result == {'status': 'recovered'}
        recovery_system.error_aggregation.process_error.assert_called_once()
        recovery_system.circuit_breaker_registry.get_breaker.assert_called_with('db_users')
    
    @pytest.mark.asyncio
    async def test_handle_api_error_with_retry(self, recovery_system, mock_error):
        """Test API error handling with retry strategy."""
        # Mock dependencies
        recovery_system.error_aggregation.process_error = AsyncMock()
        recovery_system.circuit_breaker_registry.get_breaker = Mock()
        recovery_system.retry_manager.get_strategy = Mock()
        
        mock_breaker = AsyncMock()
        mock_breaker.call = AsyncMock(return_value={'status': 'retried', 'delay': 1.0})
        recovery_system.circuit_breaker_registry.get_breaker.return_value = mock_breaker
        
        mock_strategy = Mock()
        recovery_system.retry_manager.get_strategy.return_value = mock_strategy
        
        # Test API error handling
        result = await recovery_system.handle_api_error(
            '/api/test', 'GET', mock_error, 500
        )
        
        assert result == {'status': 'retried', 'delay': 1.0}
        recovery_system.retry_manager.get_strategy.assert_called_with(OperationType.EXTERNAL_API)
    
    @pytest.mark.asyncio
    async def test_handle_websocket_error(self, recovery_system, mock_error):
        """Test WebSocket error handling."""
        # Mock dependencies
        recovery_system.error_aggregation.process_error = AsyncMock()
        recovery_system.websocket_manager.recover_all_connections = AsyncMock(
            return_value={'recovered_connections': 2}
        )
        
        # Test WebSocket error handling
        result = await recovery_system.handle_websocket_error(
            'conn123', mock_error, {'reconnect': True}
        )
        
        assert result == {'recovered_connections': 2}
        recovery_system.error_aggregation.process_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_memory_exhaustion(self, recovery_system):
        """Test memory exhaustion handling."""
        # Mock dependencies
        recovery_system.memory_monitor.take_snapshot = AsyncMock()
        recovery_system.memory_monitor.check_and_recover = AsyncMock(return_value=[
            {'action': 'garbage_collect', 'memory_freed_mb': 100}
        ])
        
        # Test memory exhaustion handling
        result = await recovery_system.handle_memory_exhaustion({'threshold': 90})
        
        assert result is True
        recovery_system.memory_monitor.take_snapshot.assert_called_once()
        recovery_system.memory_monitor.check_and_recover.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_startup_recovery_system(self, recovery_system):
        """Test recovery system startup."""
        # Mock all startup methods
        recovery_system.error_aggregation.start_processing = AsyncMock()
        recovery_system.memory_monitor.start_monitoring = AsyncMock()
        recovery_system.database_registry.start_all_monitoring = AsyncMock()
        
        # Test startup
        await recovery_system.startup_recovery_system()
        
        recovery_system.error_aggregation.start_processing.assert_called_once()
        recovery_system.memory_monitor.start_monitoring.assert_called_once()
        recovery_system.database_registry.start_all_monitoring.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_recovery_system(self, recovery_system):
        """Test recovery system shutdown."""
        # Mock all shutdown methods
        recovery_system.error_aggregation.stop_processing = AsyncMock()
        recovery_system.memory_monitor.stop_monitoring = AsyncMock()
        recovery_system.database_registry.stop_all_monitoring = AsyncMock()
        recovery_system.websocket_manager.cleanup_all = AsyncMock()
        recovery_system.circuit_breaker_registry.cleanup_all = Mock()
        
        # Test shutdown
        await recovery_system.shutdown_recovery_system()
        
        recovery_system.error_aggregation.stop_processing.assert_called_once()
        recovery_system.memory_monitor.stop_monitoring.assert_called_once()
        recovery_system.database_registry.stop_all_monitoring.assert_called_once()
        recovery_system.websocket_manager.cleanup_all.assert_called_once()
        recovery_system.circuit_breaker_registry.cleanup_all.assert_called_once()
    
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
    
    @pytest.mark.asyncio
    async def test_execute_agent_recovery(self, recovery_system, mock_error):
        """Test agent recovery execution."""
        # Mock agent registry
        recovery_system.agent_registry.recover_agent_operation = AsyncMock(
            return_value={'recovery': 'success'}
        )
        
        # Test agent recovery
        result = await recovery_system._execute_agent_recovery(
            'triage', 'classify', mock_error, {'test': 'data'}, 'user123'
        )
        
        assert result == {'recovery': 'success'}
        recovery_system.agent_registry.recover_agent_operation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_database_recovery(self, recovery_system, mock_error):
        """Test database recovery execution."""
        # Test with rollback data
        result = await recovery_system._execute_database_recovery(
            'users', 'insert', mock_error, {'id': 123}, 'tx456'
        )
        
        assert result == {'status': 'rollback_queued', 'table': 'users'}
    
    @pytest.mark.asyncio
    async def test_execute_api_recovery_with_retry(self, recovery_system, mock_error):
        """Test API recovery execution with retry."""
        # Mock retry strategy
        mock_strategy = Mock()
        mock_strategy.should_retry.return_value = True
        mock_strategy.get_retry_delay.return_value = 2.0
        
        # Test API recovery
        with patch('asyncio.sleep') as mock_sleep:
            result = await recovery_system._execute_api_recovery(
                '/api/test', 'GET', mock_error, 500, mock_strategy
            )
        
        assert result == {'status': 'retried', 'delay': 2.0}
        mock_sleep.assert_called_once_with(2.0)
    
    @pytest.mark.asyncio
    async def test_execute_api_recovery_no_retry(self, recovery_system, mock_error):
        """Test API recovery when retry not allowed."""
        # Mock retry strategy to not retry
        mock_strategy = Mock()
        mock_strategy.should_retry.return_value = False
        
        # Test API recovery
        with pytest.raises(ConnectionError):
            await recovery_system._execute_api_recovery(
                '/api/test', 'GET', mock_error, 500, mock_strategy
            )
    
    def test_get_agent_type_enum(self, recovery_system):
        """Test agent type enum conversion."""
        from app.core.agent_recovery_strategies import AgentType
        
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


class TestConvenienceFunctions:
    """Test convenience functions for backward compatibility."""
    
    @pytest.mark.asyncio
    async def test_recover_agent_operation(self, mock_error):
        """Test convenience function for agent recovery."""
        with patch.object(enhanced_recovery_system, 'handle_agent_error') as mock_handle:
            mock_handle.return_value = {'status': 'recovered'}
            
            result = await recover_agent_operation(
                'triage', 'classify', mock_error, test='data'
            )
            
            assert result == {'status': 'recovered'}
            mock_handle.assert_called_once_with(
                'triage', 'classify', mock_error, {'test': 'data'}
            )
    
    @pytest.mark.asyncio
    async def test_recover_database_operation(self, mock_error):
        """Test convenience function for database recovery."""
        with patch.object(enhanced_recovery_system, 'handle_database_error') as mock_handle:
            mock_handle.return_value = {'status': 'recovered'}
            
            result = await recover_database_operation(
                'users', 'insert', mock_error, rollback_data={'id': 123}
            )
            
            assert result == {'status': 'recovered'}
            mock_handle.assert_called_once_with(
                'users', 'insert', mock_error, rollback_data={'id': 123}
            )
    
    @pytest.mark.asyncio
    async def test_recover_api_operation(self, mock_error):
        """Test convenience function for API recovery."""
        with patch.object(enhanced_recovery_system, 'handle_api_error') as mock_handle:
            mock_handle.return_value = {'status': 'recovered'}
            
            result = await recover_api_operation(
                '/api/test', 'GET', mock_error, status_code=500
            )
            
            assert result == {'status': 'recovered'}
            mock_handle.assert_called_once_with(
                '/api/test', 'GET', mock_error, status_code=500
            )


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_agent_error_with_memory_pressure(self):
        """Test agent error handling under memory pressure."""
        recovery_system = EnhancedErrorRecoverySystem()
        
        # Mock memory pressure detection
        recovery_system.memory_monitor.take_snapshot = AsyncMock()
        recovery_system.memory_monitor.check_and_recover = AsyncMock(return_value=[
            {'action': 'garbage_collect', 'memory_freed_mb': 50}
        ])
        
        # Mock error aggregation and circuit breaker
        recovery_system.error_aggregation.process_error = AsyncMock()
        recovery_system.circuit_breaker_registry.get_breaker = Mock()
        
        mock_breaker = AsyncMock()
        mock_breaker.call = AsyncMock(side_effect=Exception("Memory exhausted"))
        recovery_system.circuit_breaker_registry.get_breaker.return_value = mock_breaker
        
        # Mock degradation manager
        recovery_system.degradation_manager.degrade_service = AsyncMock(
            return_value={'status': 'degraded', 'reason': 'memory_pressure'}
        )
        
        # Test scenario
        error = MemoryError("Out of memory")
        result = await recovery_system.handle_agent_error('triage', 'classify', error)
        
        assert result['status'] == 'degraded'
        assert result['reason'] == 'memory_pressure'
    
    @pytest.mark.asyncio
    async def test_cascading_failure_scenario(self):
        """Test handling of cascading failures across components."""
        recovery_system = EnhancedErrorRecoverySystem()
        
        # Mock all components to fail
        recovery_system.error_aggregation.process_error = AsyncMock()
        
        # Database failure
        db_breaker = AsyncMock()
        db_breaker.call = AsyncMock(side_effect=Exception("Database down"))
        
        # API failure
        api_breaker = AsyncMock()
        api_breaker.call = AsyncMock(side_effect=Exception("API down"))
        
        # Mock circuit breaker registry
        def get_breaker_side_effect(name):
            if name.startswith('db_'):
                return db_breaker
            elif name.startswith('api_'):
                return api_breaker
            return Mock()
        
        recovery_system.circuit_breaker_registry.get_breaker.side_effect = get_breaker_side_effect
        
        # Mock degradation manager
        recovery_system.degradation_manager.global_degradation_level = Mock()
        
        async def degrade_service_side_effect(service_name, level, context):
            return {'status': 'degraded', 'service': service_name}
        
        recovery_system.degradation_manager.degrade_service.side_effect = degrade_service_side_effect
        
        # Test database failure
        db_error = ConnectionError("Database connection lost")
        db_result = await recovery_system.handle_database_error(
            'users', 'select', db_error
        )
        
        # Test API failure
        api_error = TimeoutError("API timeout")
        api_result = await recovery_system.handle_api_error(
            '/api/users', 'GET', api_error, 504
        )
        
        assert db_result['status'] == 'degraded'
        assert api_result['status'] == 'degraded'


@pytest.fixture
def mock_error():
    """Create mock error for testing."""
    return ConnectionError("Test connection error")