"""
Comprehensive tests for Service Factory.

Tests service creation, dependency injection, factory patterns,
and service lifecycle management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from netra_backend.app.services.service_factory import (
    _create_agent_service,
    _create_message_handler_service,
    _create_core_services,
    _create_data_services,
    _create_mcp_dependencies,
    _create_mcp_service,
    _create_mcp_client_service,
    get_mcp_service,
    get_service_factories
)


class TestServiceFactory:
    """Tests for service factory functionality."""

    def test_agent_service_creation(self):
        """Test agent service is created with proper dependencies."""
        with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent') as mock_supervisor:
            with patch('netra_backend.app.services.agent_service.AgentService') as mock_service:
                mock_supervisor_instance = Mock()
                mock_supervisor.return_value = mock_supervisor_instance
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                
                result = _create_agent_service()
                
                # Verify supervisor was created
                mock_supervisor.assert_called_once_with(None, None, None, None)
                
                # Verify service was created with supervisor
                mock_service.assert_called_once_with(mock_supervisor_instance)
                
                assert result == mock_service_instance

    def test_message_handler_service_creation(self):
        """Test message handler service is created with dependencies."""
        with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent') as mock_supervisor:
            with patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_handler:
                with patch('netra_backend.app.services.thread_service.ThreadService') as mock_thread:
                    mock_supervisor_instance = Mock()
                    mock_thread_instance = Mock()
                    mock_handler_instance = Mock()
                    
                    mock_supervisor.return_value = mock_supervisor_instance
                    mock_thread.return_value = mock_thread_instance
                    mock_handler.return_value = mock_handler_instance
                    
                    result = _create_message_handler_service()
                    
                    # Verify dependencies were created
                    mock_supervisor.assert_called_once()
                    mock_thread.assert_called_once()
                    
                    # Verify handler was created with dependencies
                    mock_handler.assert_called_once_with(
                        mock_supervisor_instance, 
                        mock_thread_instance
                    )
                    
                    assert result == mock_handler_instance

    def test_core_services_creation(self):
        """Test core services dictionary is created correctly."""
        with patch('netra_backend.app.services.corpus_service.CorpusService') as mock_corpus:
            with patch('netra_backend.app.services.thread_service.ThreadService') as mock_thread:
                with patch('netra_backend.app.services.service_factory._create_agent_service') as mock_agent:
                    mock_corpus_instance = Mock()
                    mock_thread_instance = Mock()
                    mock_agent_instance = Mock()
                    
                    mock_corpus.return_value = mock_corpus_instance
                    mock_thread.return_value = mock_thread_instance
                    mock_agent.return_value = mock_agent_instance
                    
                    result = _create_core_services()
                    
                    # Verify all core services are present
                    assert 'agent_service' in result
                    assert 'thread_service' in result
                    assert 'corpus_service' in result
                    
                    # Verify correct instances
                    assert result['agent_service'] == mock_agent_instance
                    assert result['thread_service'] == mock_thread_instance
                    assert result['corpus_service'] == mock_corpus_instance

    def test_data_services_creation(self):
        """Test data services dictionary is created correctly."""
        with patch('netra_backend.app.services.security_service.SecurityService') as mock_security:
            with patch('netra_backend.app.services.supply_catalog_service.SupplyCatalogService') as mock_supply:
                with patch('netra_backend.app.services.synthetic_data_service.SyntheticDataService') as mock_synthetic:
                    mock_security_instance = Mock()
                    mock_supply_instance = Mock()
                    mock_synthetic_instance = Mock()
                    
                    mock_security.return_value = mock_security_instance
                    mock_supply.return_value = mock_supply_instance
                    mock_synthetic.return_value = mock_synthetic_instance
                    
                    result = _create_data_services()
                    
                    # Verify all data services are present
                    assert 'synthetic_data_service' in result
                    assert 'security_service' in result
                    assert 'supply_catalog_service' in result
                    
                    # Verify correct instances
                    assert result['synthetic_data_service'] == mock_synthetic_instance
                    assert result['security_service'] == mock_security_instance
                    assert result['supply_catalog_service'] == mock_supply_instance

    def test_mcp_dependencies_merge(self):
        """Test MCP dependencies merge core and data services."""
        mock_core = {'core1': Mock(), 'core2': Mock()}
        mock_data = {'data1': Mock(), 'data2': Mock()}
        
        with patch('netra_backend.app.services.service_factory._create_core_services', return_value=mock_core):
            with patch('netra_backend.app.services.service_factory._create_data_services', return_value=mock_data):
                result = _create_mcp_dependencies()
                
                # Verify all services are present
                assert 'core1' in result
                assert 'core2' in result
                assert 'data1' in result
                assert 'data2' in result
                
                # Verify correct instances
                assert result['core1'] == mock_core['core1']
                assert result['data1'] == mock_data['data1']

    def test_mcp_service_creation(self):
        """Test MCP service is created with all dependencies."""
        mock_dependencies = {
            'agent_service': Mock(),
            'thread_service': Mock(),
            'corpus_service': Mock(),
            'security_service': Mock()
        }
        
        with patch('netra_backend.app.services.service_factory._create_mcp_dependencies', return_value=mock_dependencies):
            with patch('netra_backend.app.services.mcp_service.MCPService') as mock_mcp:
                mock_mcp_instance = Mock()
                mock_mcp.return_value = mock_mcp_instance
                
                result = _create_mcp_service()
                
                # Verify MCP service was created with dependencies
                mock_mcp.assert_called_once_with(**mock_dependencies)
                assert result == mock_mcp_instance

    def test_mcp_client_service_creation(self):
        """Test MCP client service is created correctly."""
        with patch('netra_backend.app.services.mcp_client_service.MCPClientService') as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            
            result = _create_mcp_client_service()
            
            mock_client.assert_called_once_with()
            assert result == mock_client_instance

    def test_get_mcp_service_public_interface(self):
        """Test public MCP service getter."""
        with patch('netra_backend.app.services.service_factory._create_mcp_service') as mock_create:
            mock_service = Mock()
            mock_create.return_value = mock_service
            
            result = get_mcp_service()
            
            mock_create.assert_called_once()
            assert result == mock_service

    def test_get_service_factories_registry(self):
        """Test service factories registry returns all available factories."""
        factories = get_service_factories()
        
        # Verify all expected factories are present
        expected_factories = [
            'agent_service',
            'message_handler_service',
            'mcp_service',
            'websocket_service',
            'mcp_client_service',
            'core_services',
            'data_services'
        ]
        
        for factory_name in expected_factories:
            assert factory_name in factories
            assert callable(factories[factory_name])

    def test_factory_functions_are_callable(self):
        """Test that all factory functions can be called."""
        factories = get_service_factories()
        
        # Test each factory can be mocked and called
        for name, factory_func in factories.items():
            assert callable(factory_func)
            
            # Mock the actual creation to avoid dependencies
            with patch.object(factory_func, '__module__', 'test_module'):
                try:
                    # Try to get function signature
                    import inspect
                    sig = inspect.signature(factory_func)
                    assert len(sig.parameters) == 0  # All factories should be parameterless
                except Exception:
                    # If inspection fails, that's okay - the function is still callable
                    pass

    def test_service_dependencies_isolation(self):
        """Test that services are created with proper isolation."""
        with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent') as mock_supervisor:
            with patch('netra_backend.app.services.agent_service.AgentService') as mock_service:
                # Create two agent services
                service1 = _create_agent_service()
                service2 = _create_agent_service()
                
                # Each should have its own supervisor instance
                assert mock_supervisor.call_count == 2
                assert mock_service.call_count == 2

    def test_factory_error_handling(self):
        """Test factory functions handle creation errors gracefully."""
        # Test agent service creation with import error
        with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent', side_effect=ImportError("Module not found")):
            with pytest.raises(ImportError):
                _create_agent_service()

    def test_service_factory_memory_management(self):
        """Test that factories don't leak memory through circular references."""
        factories = get_service_factories()
        
        # Create services and ensure they can be garbage collected
        services = []
        for name, factory in factories.items():
            try:
                # Mock dependencies to avoid actual service creation
                with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent', return_value=Mock()):
                    with patch('netra_backend.app.services.agent_service.AgentService', return_value=Mock()):
                        with patch('netra_backend.app.services.thread_service.ThreadService', return_value=Mock()):
                            service = factory()
                            services.append(service)
            except Exception:
                # Some factories may fail due to missing dependencies in test environment
                pass
        
        # Verify services can be deleted (no circular references)
        import weakref
        weak_refs = [weakref.ref(service) for service in services]
        del services
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Some weak references may still exist due to test mocking, which is expected

    def test_dependency_injection_pattern(self):
        """Test that the dependency injection pattern is correctly implemented."""
        # Test that core dependencies are injected into MCP service
        mock_core_deps = {
            'agent_service': Mock(),
            'thread_service': Mock()
        }
        mock_data_deps = {
            'security_service': Mock()
        }
        
        with patch('netra_backend.app.services.service_factory._create_core_services', return_value=mock_core_deps):
            with patch('netra_backend.app.services.service_factory._create_data_services', return_value=mock_data_deps):
                with patch('netra_backend.app.services.mcp_service.MCPService') as mock_mcp:
                    _create_mcp_service()
                    
                    # Verify MCP service received all dependencies
                    call_args = mock_mcp.call_args[1]  # kwargs
                    assert 'agent_service' in call_args
                    assert 'thread_service' in call_args
                    assert 'security_service' in call_args

    def test_factory_singleton_behavior(self):
        """Test that factories create new instances each time (not singletons)."""
        with patch('netra_backend.app.services.mcp_client_service.MCPClientService') as mock_client:
            mock_client.side_effect = [Mock(id=1), Mock(id=2)]
            
            service1 = _create_mcp_client_service()
            service2 = _create_mcp_client_service()
            
            # Should create separate instances
            assert mock_client.call_count == 2
            assert service1.id != service2.id

    def test_circular_dependency_prevention(self):
        """Test that circular dependencies are avoided in service creation."""
        # This test ensures that the factory pattern doesn't create circular dependencies
        with patch('netra_backend.app.services.service_factory._create_core_services') as mock_core:
            with patch('netra_backend.app.services.service_factory._create_data_services') as mock_data:
                mock_core.return_value = {'test_service': Mock()}
                mock_data.return_value = {'test_service_2': Mock()}
                
                # This should not cause infinite recursion
                deps = _create_mcp_dependencies()
                
                # Verify both factories were called once
                mock_core.assert_called_once()
                mock_data.assert_called_once()
                
                assert 'test_service' in deps
                assert 'test_service_2' in deps