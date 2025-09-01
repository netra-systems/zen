"""
Test MCP Service Initialization Fix

Verifies that MCP service initialization is deterministic and stable.
Tests the fix for the missing agent_service argument issue.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock

from netra_backend.app.services.service_factory import _create_mcp_service, get_mcp_service
from netra_backend.app.services.mcp_service import MCPService
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.routes.mcp.service_factory import (
    get_mcp_service as get_mcp_service_route,
    _build_mcp_service_instance
)


class TestMCPServiceInitialization:
    """Test MCP service initialization after fix."""
    
    def test_mcp_service_requires_agent_service(self):
        """Test that MCP service creation fails without agent_service."""
        with pytest.raises(ValueError) as exc_info:
            _create_mcp_service(agent_service=None)
        
        assert "agent_service is required" in str(exc_info.value)
    
    def test_mcp_service_creation_with_mock_agent(self):
        """Test MCP service creation with mock agent service."""
        # Create mock agent service
        mock_agent = Mock(spec=AgentService)
        
        # Create MCP service - should not raise
        mcp_service = _create_mcp_service(agent_service=mock_agent)
        
        # Verify it's an MCPService instance
        assert isinstance(mcp_service, MCPService)
        assert mcp_service.agent_service == mock_agent
    
    def test_route_service_factory_builds_correctly(self):
        """Test that route service factory builds MCP service correctly."""
        # Create mocks for all required services
        mock_agent = Mock(spec=AgentService)
        mock_thread = Mock()
        mock_corpus = Mock()
        mock_security = Mock()
        
        # Build MCP service instance
        mcp_service = _build_mcp_service_instance(
            agent_service=mock_agent,
            thread_service=mock_thread,
            corpus_service=mock_corpus,
            security_service=mock_security
        )
        
        # Verify it's properly initialized
        assert isinstance(mcp_service, MCPService)
        assert mcp_service.agent_service == mock_agent
        assert mcp_service.thread_service == mock_thread
        assert mcp_service.corpus_service == mock_corpus
        assert mcp_service.security_service == mock_security
    
    @pytest.mark.asyncio
    async def test_route_get_mcp_service_with_dependencies(self):
        """Test that route get_mcp_service works with proper dependencies."""
        # Create mocks
        mock_agent = Mock(spec=AgentService)
        mock_thread = Mock()
        mock_corpus = Mock()
        mock_security = Mock()
        
        # Call the async function
        mcp_service = await get_mcp_service_route(
            agent_service=mock_agent,
            thread_service=mock_thread,
            corpus_service=mock_corpus,
            security_service=mock_security
        )
        
        # Verify service is created correctly
        assert isinstance(mcp_service, MCPService)
        assert mcp_service.agent_service == mock_agent
    
    def test_mcp_service_has_all_required_attributes(self):
        """Test that MCP service has all required attributes after initialization."""
        # Create mocks for all services
        mock_agent = Mock(spec=AgentService)
        mock_thread = Mock()
        mock_corpus = Mock()
        mock_security = Mock()
        mock_synthetic = Mock()
        mock_supply = Mock()
        
        # Create MCP service with all dependencies
        from netra_backend.app.services.mcp_service import MCPService
        
        mcp_service = MCPService(
            agent_service=mock_agent,
            thread_service=mock_thread,
            corpus_service=mock_corpus,
            synthetic_data_service=mock_synthetic,
            security_service=mock_security,
            supply_catalog_service=mock_supply,
            llm_manager=None
        )
        
        # Verify all services are assigned
        assert hasattr(mcp_service, 'agent_service')
        assert hasattr(mcp_service, 'thread_service')
        assert hasattr(mcp_service, 'corpus_service')
        assert hasattr(mcp_service, 'synthetic_data_service')
        assert hasattr(mcp_service, 'security_service')
        assert hasattr(mcp_service, 'supply_catalog_service')
        assert hasattr(mcp_service, 'client_repository')
        assert hasattr(mcp_service, 'execution_repository')
        assert hasattr(mcp_service, 'mcp_server')
    
    def test_service_factory_get_mcp_service_with_agent(self):
        """Test service factory get_mcp_service with agent_service provided."""
        mock_agent = Mock(spec=AgentService)
        
        # Call get_mcp_service with agent_service
        mcp_service = get_mcp_service(agent_service=mock_agent)
        
        # Verify service is created
        assert isinstance(mcp_service, MCPService)
        assert mcp_service.agent_service == mock_agent


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])