"""
Test startup validation system for deterministic component counts.

This test ensures that the startup validation system properly detects
and warns about components with zero counts during startup.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, Mock, patch
from fastapi import FastAPI

from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentStatus,
    ComponentValidation,
    validate_startup
)


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app with various startup states."""
    app = FastAPI()
    app.state = MagicMock()
    return app


@pytest.fixture
def validator():
    """Create a startup validator instance."""
    return StartupValidator()


class TestStartupValidation:
    """Test the startup validation system."""
    
    @pytest.mark.asyncio
    async def test_zero_agents_detected(self, mock_app, validator):
        """Test that zero agents are properly detected and warned about."""
        # Setup mock with zero agents
        mock_app.state.agent_supervisor = MagicMock()
        mock_app.state.agent_supervisor.registry = MagicMock()
        mock_app.state.agent_supervisor.registry.agents = {}  # Zero agents
        
        # Run validation
        success, report = await validator.validate_startup(mock_app)
        
        # Check that validation detected the issue
        assert 'Agents' in report['categories']
        agent_validations = report['categories']['Agents']
        
        # Find agent registry validation
        registry_validation = None
        for v in agent_validations:
            if v['name'] == 'Agent Registry':
                registry_validation = v
                break
        
        assert registry_validation is not None
        assert registry_validation['actual'] == 0
        assert registry_validation['expected'] > 0
        assert registry_validation['status'] in ['critical', 'warning']
        
        # Should not be successful with zero agents
        assert not success or report['critical_failures'] > 0
    
    @pytest.mark.asyncio
    async def test_zero_tools_detected(self, mock_app, validator):
        """Test that zero tools are properly detected."""
        # Setup mock with zero tools
        mock_app.state.tool_dispatcher = MagicMock()
        mock_app.state.tool_dispatcher.tools = []  # Zero tools
        mock_app.state.tool_dispatcher._websocket_enhanced = False
        
        # Run validation
        success, report = await validator.validate_startup(mock_app)
        
        # Check tools validation
        assert 'Tools' in report['categories']
        tool_validations = report['categories']['Tools']
        
        # Find tool dispatcher validation
        dispatcher_validation = None
        for v in tool_validations:
            if v['name'] == 'Tool Dispatcher':
                dispatcher_validation = v
                break
        
        assert dispatcher_validation is not None
        assert dispatcher_validation['actual'] == 0
        assert dispatcher_validation['expected'] >= 1
    
    @pytest.mark.asyncio
    async def test_missing_websocket_handlers_detected(self, mock_app, validator):
        """Test that missing WebSocket handlers are detected."""
        # Setup WebSocket manager with no handlers
        ws_manager = MagicMock()
        ws_manager.active_connections = []
        ws_manager.message_handlers = []  # Zero handlers
        
        with patch('netra_backend.app.core.startup_validation.get_websocket_manager', return_value=ws_manager):
            success, report = await validator.validate_startup(mock_app)
            
            # Check WebSocket validation
            assert 'WebSocket' in report['categories']
            ws_validations = report['categories']['WebSocket']
            
            # Find WebSocket manager validation
            manager_validation = None
            for v in ws_validations:
                if v['name'] == 'WebSocket Manager':
                    manager_validation = v
                    break
            
            assert manager_validation is not None
            assert manager_validation['metadata']['handlers'] == 0
            assert manager_validation['status'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_null_services_detected(self, mock_app, validator):
        """Test that None services are properly detected."""
        # Set critical services to None
        mock_app.state.llm_manager = None
        mock_app.state.key_manager = None
        mock_app.state.thread_service = None
        
        # Run validation
        success, report = await validator.validate_startup(mock_app)
        
        # Check services validation
        assert 'Services' in report['categories']
        service_validations = report['categories']['Services']
        
        # Count None services
        none_services = [v for v in service_validations 
                        if v['actual'] == 0 and v['expected'] == 1]
        
        assert len(none_services) >= 3  # At least the 3 we set to None
        
        # Should not be successful with critical services as None
        assert not success or report['critical_failures'] > 0
    
    @pytest.mark.asyncio
    async def test_healthy_startup(self, mock_app, validator):
        """Test validation with all components properly initialized."""
        # Setup healthy mock state
        mock_app.state.agent_supervisor = MagicMock()
        mock_app.state.agent_supervisor.registry = MagicMock()
        mock_app.state.agent_supervisor.registry.agents = {
            'triage': Mock(),
            'data': Mock(),
            'optimization': Mock(),
            'actions': Mock(),
            'reporting': Mock(),
            'data_helper': Mock(),
            'synthetic_data': Mock(),
            'corpus_admin': Mock(),
        }
        
        mock_app.state.tool_dispatcher = MagicMock()
        mock_app.state.tool_dispatcher.tools = [Mock() for _ in range(5)]
        mock_app.state.tool_dispatcher._websocket_enhanced = True
        
        mock_app.state.llm_manager = Mock()
        mock_app.state.key_manager = Mock()
        mock_app.state.security_service = Mock()
        mock_app.state.redis_manager = Mock()
        mock_app.state.thread_service = Mock()
        mock_app.state.agent_service = Mock()
        mock_app.state.db_session_factory = Mock()
        
        # Mock WebSocket manager
        ws_manager = MagicMock()
        ws_manager.active_connections = []
        ws_manager.message_handlers = [Mock() for _ in range(3)]
        
        with patch('netra_backend.app.core.startup_validation.get_websocket_manager', return_value=ws_manager):
            success, report = await validator.validate_startup(mock_app)
            
            # Should be successful
            assert success
            assert report['critical_failures'] == 0
            assert report['status_counts']['healthy'] > 0
            
            # Check no zero counts for critical components
            for category, components in report['categories'].items():
                for component in components:
                    if component['critical'] and component['expected'] > 0:
                        assert component['actual'] > 0, f"{component['name']} has zero count"
    
    @pytest.mark.asyncio
    async def test_report_generation(self, mock_app, validator):
        """Test that validation report is properly generated."""
        # Run validation
        success, report = await validator.validate_startup(mock_app)
        
        # Check report structure
        assert 'timestamp' in report
        assert 'duration' in report
        assert 'total_validations' in report
        assert 'status_counts' in report
        assert 'critical_failures' in report
        assert 'categories' in report
        assert 'overall_health' in report
        
        # Check status counts
        status_counts = report['status_counts']
        assert 'healthy' in status_counts
        assert 'warning' in status_counts
        assert 'critical' in status_counts
        assert 'failed' in status_counts
        assert 'not_checked' in status_counts
        
        # Sum of status counts should equal total validations
        total_from_counts = sum(status_counts.values())
        assert total_from_counts == report['total_validations']
    
    def test_component_status_determination(self, validator):
        """Test that component status is correctly determined."""
        # Test zero count critical
        status = validator._get_status(0, 5, is_critical=True)
        assert status == ComponentStatus.CRITICAL
        
        # Test zero count non-critical
        status = validator._get_status(0, 5, is_critical=False)
        assert status == ComponentStatus.WARNING
        
        # Test insufficient count
        status = validator._get_status(3, 5, is_critical=True)
        assert status == ComponentStatus.WARNING
        
        # Test healthy count
        status = validator._get_status(5, 5, is_critical=True)
        assert status == ComponentStatus.HEALTHY
        
        # Test above expected
        status = validator._get_status(7, 5, is_critical=True)
        assert status == ComponentStatus.HEALTHY


@pytest.mark.asyncio
async def test_integration_with_deterministic_startup():
    """Test that validation integrates with deterministic startup."""
    from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError
    
    # Create mock app
    app = FastAPI()
    app.state = MagicMock()
    
    # Create orchestrator
    orchestrator = StartupOrchestrator(app)
    
    # Mock the startup phases to set up a failing state
    with patch.object(orchestrator, '_phase1_foundation', return_value=None):
        with patch.object(orchestrator, '_phase2_core_services', return_value=None):
            with patch.object(orchestrator, '_phase3_chat_pipeline', return_value=None):
                with patch.object(orchestrator, '_phase4_optional_services', return_value=None):
                    # Set up app state with zero agents for validation to detect
                    app.state.db_session_factory = Mock()
                    app.state.redis_manager = Mock()
                    app.state.llm_manager = Mock()
                    app.state.agent_supervisor = Mock()
                    app.state.agent_supervisor.registry = Mock()
                    app.state.agent_supervisor.registry.agents = {}  # Zero agents
                    app.state.thread_service = Mock()
                    app.state.tool_dispatcher = Mock()
                    
                    # Phase 5 validation should detect the zero agents
                    with pytest.raises(DeterministicStartupError) as exc_info:
                        await orchestrator._phase5_validation()
                    
                    # Should fail due to validation
                    assert "validation failed" in str(exc_info.value).lower() or \
                           "critical failures" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])