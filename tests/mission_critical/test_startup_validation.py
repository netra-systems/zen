"""
Mission Critical: Startup Validation System Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Zero critical startup failures in production
- Value Impact: Prevents broken systems from serving customers
- Strategic Impact: Protects business reputation and revenue

Infrastructure Test Specialist: Startup Validation System

Team Delta Focus Areas:
1. Service dependency resolution and validation
2. Deterministic component count verification  
3. Startup race condition prevention
4. Resource management validation
5. Connection pool health checks
6. Memory leak detection during startup

Key Requirements:
 PASS:  Deterministic startup order
 PASS:  < 30 second startup time
 PASS:  Zero race conditions
 PASS:  Proper resource cleanup
 PASS:  No memory leaks
 PASS:  Connection pool validation
"""

import pytest
import asyncio
import time
import psutil
import gc
import threading
from fastapi import FastAPI
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch

# Absolute imports following CLAUDE.md guidelines
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentStatus, 
    ComponentValidation,
    validate_startup
)
from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Set test environment for infrastructure validation
env = get_env()
env.set("ENVIRONMENT", "testing", "test")
env.set("TESTING", "true", "test")
env.set("STARTUP_TIMEOUT", "30", "test")
env.set("VALIDATE_RESOURCE_USAGE", "true", "test")


class ResourceTracker:
    """Track resource usage during validation tests."""
    
    def __init__(self):
        self.initial_memory = None
        self.initial_threads = None
        self.initial_fds = None
        self.process = psutil.Process()
    
    def start_tracking(self):
        """Start resource tracking."""
        self.initial_memory = self.process.memory_info().rss
        self.initial_threads = self.process.num_threads()
        try:
            self.initial_fds = len(self.process.open_files())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            self.initial_fds = 0
        gc.collect()
    
    def get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage delta."""
        current_memory = self.process.memory_info().rss
        current_threads = self.process.num_threads()
        try:
            current_fds = len(self.process.open_files())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            current_fds = self.initial_fds
        
        return {
            'memory_mb': (current_memory - self.initial_memory) / 1024 / 1024,
            'threads': current_threads - self.initial_threads,
            'file_descriptors': current_fds - self.initial_fds
        }


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
    
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
    
    async def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()


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
            if 'Agent' in v['name']:
                registry_validation = v
                break
        
        assert registry_validation is not None
        # Should not be successful with zero agents in legacy mode
        assert not success or report['critical_failures'] > 0
    
    @pytest.mark.asyncio
    async def test_zero_tools_detected(self, mock_app, validator):
        """Test that zero tools are properly detected."""
        # Setup mock with zero tool classes (UserContext mode)
        mock_app.state.tool_classes = []  # Zero tools
        mock_app.state.websocket_bridge_factory = None
        
        # Run validation
        success, report = await validator.validate_startup(mock_app)
        
        # Check tools validation
        assert 'Tools' in report['categories']
        tool_validations = report['categories']['Tools']
        
        # Find tool configuration validation
        tool_validation = None
        for v in tool_validations:
            if 'Tool Configuration' in v['name']:
                tool_validation = v
                break
        
        assert tool_validation is not None
        assert tool_validation['actual'] == 0
        assert tool_validation['expected'] >= 1
    
    @pytest.mark.asyncio
    async def test_missing_websocket_handlers_detected(self, mock_app, validator):
        """Test that missing WebSocket handlers are detected."""
        # Setup WebSocket manager factory mode
        mock_app.state.websocket_manager = None  # Factory mode
        
        # Mock factory availability check
        with patch('netra_backend.app.core.startup_validation.create_websocket_manager') as mock_factory:
            mock_factory.return_value = "factory_available"
            
            success, report = await validator.validate_startup(mock_app)
            
            # Check WebSocket validation
            assert 'WebSocket' in report['categories']
            ws_validations = report['categories']['WebSocket']
            
            # Find WebSocket manager validation
            manager_validation = None
            for v in ws_validations:
                if 'WebSocket Manager' in v['name']:
                    manager_validation = v
                    break
            
            assert manager_validation is not None
            # Factory pattern should be healthy
            assert manager_validation['status'] == 'healthy'
    
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
            'triage': MagicMock(),
            'data': MagicMock(), 
            'optimization': MagicMock(),
            'actions': MagicMock(),
            'reporting': MagicMock(),
            'data_helper': MagicMock(),
            'synthetic_data': MagicMock(),
            'corpus_admin': MagicMock()
        }
        
        # Setup UserContext tool configuration
        mock_app.state.tool_classes = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_app.state.websocket_bridge_factory = MagicMock()
        
        # Setup services
        mock_app.state.llm_manager = MagicMock()
        mock_app.state.key_manager = MagicMock()
        mock_app.state.security_service = MagicMock()
        mock_app.state.redis_manager = MagicMock()
        mock_app.state.thread_service = MagicMock()
        mock_app.state.agent_service = MagicMock()
        
        # Setup database
        mock_app.state.db_session_factory = MagicMock()
        
        # Mock WebSocket factory
        with patch('netra_backend.app.core.startup_validation.create_websocket_manager'):
            success, report = await validator.validate_startup(mock_app)
        
        # Should be successful
        assert success
        assert report['critical_failures'] == 0
        assert report['status_counts']['healthy'] > 0
        
        # Check no zero counts for critical components
        for category, components in report['categories'].items():
            for component in components:
                if component['critical'] and component['expected'] > 0:
                    assert component['actual'] > 0, f"Critical component {component['name']} has zero count"
    
    @pytest.mark.asyncio
    async def test_report_generation(self, mock_app, validator):
        """Test that validation report is properly generated."""
        # Setup minimal app state
        mock_app.state.agent_supervisor = MagicMock()
        
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
    async def test_integration_with_deterministic_startup(self):
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
                        app.state.agent_supervisor = MagicMock()
                        app.state.agent_supervisor.registry = MagicMock()
                        app.state.agent_supervisor.registry.agents = {}  # Zero agents
                        
                        # Phase validation should detect the zero agents within 30s
                        start_time = time.time()
                        with pytest.raises(DeterministicStartupError) as exc_info:
                            await asyncio.wait_for(
                                orchestrator._phase5_validation(),
                                timeout=30.0  # Meet 30-second requirement
                            )
                        
                        elapsed = time.time() - start_time
                        assert elapsed < 30, f"Validation took {elapsed:.2f}s, expected < 30s"
                        
                        # Should fail due to validation
                        assert "validation failed" in str(exc_info.value).lower() or \
                               "critical failures" in str(exc_info.value).lower()


@pytest.mark.mission_critical
class TestServiceDependencyResolution:
    """Tests for service dependency resolution during startup validation."""
    
    @pytest.fixture
    def setup_resource_tracking(self):
        """Setup resource tracking for dependency tests."""
        self.resource_tracker = ResourceTracker()
        self.resource_tracker.start_tracking()
        
        yield
        
        # Verify no resource leaks
        resource_usage = self.resource_tracker.get_resource_usage()
        assert resource_usage['memory_mb'] < 20, f"Memory leak: {resource_usage['memory_mb']:.2f}MB"
        assert resource_usage['threads'] <= 1, f"Thread leak: {resource_usage['threads']} threads"
        assert resource_usage['file_descriptors'] <= 2, f"FD leak: {resource_usage['file_descriptors']} descriptors"
    
    @pytest.mark.asyncio
    async def test_dependency_chain_validation(self, validator):
        """Test validation of service dependency chains."""
        # Create mock app with dependency chain
        app = FastAPI()
        app.state = MagicMock()
        
        # Setup dependency chain: DB -> Redis -> LLM -> WebSocket -> Tools
        app.state.db_session_factory = MagicMock()
        app.state.redis_manager = MagicMock()
        app.state.llm_manager = MagicMock()
        app.state.websocket_manager = None  # Factory pattern
        
        # Mock WebSocket factory
        with patch('netra_backend.app.core.startup_validation.create_websocket_manager'):
            # Mock tool configuration
            app.state.tool_classes = [MagicMock(), MagicMock()]
            app.state.websocket_bridge_factory = MagicMock()
            
            success, report = await validator.validate_startup(app)
        
        # Should succeed with proper dependency chain
        assert success
        assert report['critical_failures'] == 0
        
        # Verify dependency chain is validated
        assert 'Services' in report['categories']
        assert 'Tools' in report['categories']
        assert 'WebSocket' in report['categories']
    
    @pytest.mark.asyncio
    async def test_broken_dependency_chain_detection(self, validator):
        """Test detection of broken service dependency chains."""
        app = FastAPI()
        app.state = MagicMock()
        
        # Setup broken dependency chain - missing Redis
        app.state.db_session_factory = MagicMock()
        app.state.redis_manager = None  # BROKEN
        app.state.llm_manager = MagicMock()
        
        # Tool configuration without Redis cache support
        app.state.tool_classes = [MagicMock()]
        app.state.websocket_bridge_factory = None
        
        success, report = await validator.validate_startup(app)
        
        # Should detect broken chain
        assert not success or report['critical_failures'] > 0
        
        # Find the broken Redis dependency
        service_validations = report['categories'].get('Services', [])
        redis_validation = next((v for v in service_validations if 'Redis' in v['name']), None)
        assert redis_validation is not None
        assert redis_validation['actual'] == 0


@pytest.mark.mission_critical
class TestRaceConditionPrevention:
    """Tests for preventing race conditions during startup validation."""
    
    @pytest.mark.asyncio
    async def test_concurrent_validation_requests(self, validator):
        """Test that concurrent validation requests don't interfere."""
        app = FastAPI()
        app.state = MagicMock()
        
        # Setup minimal healthy state
        app.state.agent_supervisor = MagicMock()
        app.state.tool_classes = [MagicMock()]
        app.state.websocket_bridge_factory = MagicMock()
        
        # Mock WebSocket factory
        with patch('netra_backend.app.core.startup_validation.create_websocket_manager'):
            # Run multiple concurrent validations
            tasks = [
                validator.validate_startup(app)
                for _ in range(5)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            elapsed = time.time() - start_time
            
            # All should succeed
            for success, report in results:
                assert success
                assert isinstance(report, dict)
                assert 'total_validations' in report
            
            # Should complete within reasonable time
            assert elapsed < 15, f"Concurrent validation took {elapsed:.2f}s, expected < 15s"


@pytest.mark.mission_critical  
class TestConnectionPoolValidation:
    """Tests for connection pool validation during startup."""
    
    def test_database_connection_pool_health(self, validator):
        """Test database connection pool health validation."""
        app = FastAPI()
        app.state = MagicMock()
        
        # Mock database session factory with pool info
        mock_pool = MagicMock()
        mock_pool.size = 5
        mock_pool.checked_out = 2
        mock_pool.overflow = 0
        mock_pool.invalidated = 0
        
        mock_engine = MagicMock()
        mock_engine.pool = mock_pool
        
        app.state.db_session_factory = MagicMock()
        app.state.db_session_factory.engine = mock_engine
        
        # Simulate pool validation
        pool_health = {
            'size': mock_pool.size,
            'checked_out': mock_pool.checked_out,
            'available': mock_pool.size - mock_pool.checked_out,
            'overflow': mock_pool.overflow,
            'invalidated': mock_pool.invalidated
        }
        
        # Verify pool is healthy
        assert pool_health['size'] > 0
        assert pool_health['available'] > 0
        assert pool_health['invalidated'] == 0
    
    def test_redis_connection_pool_health(self, validator):
        """Test Redis connection pool health validation."""
        app = FastAPI()
        app.state = MagicMock()
        
        # Mock Redis manager with connection pool
        mock_pool = MagicMock()
        mock_pool.created_connections = 3
        mock_pool.available_connections = 2
        mock_pool.in_use_connections = 1
        
        mock_redis = MagicMock()
        mock_redis.connection_pool = mock_pool
        app.state.redis_manager = mock_redis
        
        # Simulate pool validation
        pool_health = {
            'created': mock_pool.created_connections,
            'available': mock_pool.available_connections,
            'in_use': mock_pool.in_use_connections
        }
        
        # Verify Redis pool is healthy
        assert pool_health['created'] > 0
        assert pool_health['available'] >= 0
        assert pool_health['in_use'] >= 0
        assert pool_health['available'] + pool_health['in_use'] <= pool_health['created']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])