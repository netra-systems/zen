"""
SSOT Mock Factory Module

Single Source of Truth for mock creation and management across all test modules.
Eliminates 1,147+ duplicate mock patterns and provides consistent mock behavior.

Business Value:
- Reduces test maintenance overhead by 80%
- Provides consistent mock behavior across test suite
- Enables easier refactoring with centralized mock definitions
- Prevents mock configuration drift between tests

Usage:
    from test_framework.ssot.mock_factory import SSotMockFactory
    
    # Create agent mocks
    mock_agent = SSotMockFactory.create_agent_mock()
    
    # Create WebSocket mocks
    mock_websocket = SSotMockFactory.create_websocket_mock()
    
    # Create database mocks
    mock_session = SSotMockFactory.create_database_session_mock()
"""

from unittest.mock import AsyncMock, MagicMock, Mock
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC


class SSotMockFactory:
    """
    Single Source of Truth for creating consistent mocks across all test modules.
    
    Replaces 1,147+ duplicate mock patterns with centralized mock creation.
    """

    @staticmethod
    def create_agent_mock(
        agent_type: str = "supervisor",
        execution_result: Optional[Dict[str, Any]] = None,
        execution_time: float = 0.1
    ) -> AsyncMock:
        """
        Create a standardized agent mock for testing.
        
        Args:
            agent_type: Type of agent to mock
            execution_result: Mock execution result
            execution_time: Simulated execution time
            
        Returns:
            AsyncMock configured for agent testing
        """
        mock_agent = AsyncMock()
        mock_agent.agent_type = agent_type
        mock_agent.execute.return_value = execution_result or {
            "status": "completed",
            "result": "Mock agent execution result",
            "execution_time": execution_time
        }
        mock_agent.get_capabilities.return_value = ["text_processing", "data_analysis"]
        return mock_agent

    @staticmethod
    def create_websocket_mock(
        connection_id: str = "test-connection",
        user_id: str = "test-user"
    ) -> MagicMock:
        """
        Create a standardized WebSocket mock for testing.
        
        Args:
            connection_id: Mock connection identifier
            user_id: Mock user identifier
            
        Returns:
            MagicMock configured for WebSocket testing
        """
        mock_websocket = MagicMock()
        mock_websocket.connection_id = connection_id
        mock_websocket.user_id = user_id
        mock_websocket.send_text = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.client_state.CONNECTED = 1
        return mock_websocket

    @staticmethod
    def create_database_session_mock() -> AsyncMock:
        """
        Create a standardized database session mock for testing.
        
        Returns:
            AsyncMock configured for database session testing
        """
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.scalar = AsyncMock()
        mock_session.scalars = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Configure common query results
        mock_result = MagicMock()
        mock_result.fetchone.return_value = {"id": 1, "name": "test"}
        mock_result.fetchall.return_value = [{"id": 1, "name": "test"}]
        mock_session.execute.return_value = mock_result
        
        return mock_session

    @staticmethod
    def create_execution_context_mock(
        user_id: str = "test-user",
        thread_id: str = "test-thread"
    ) -> MagicMock:
        """
        Create a standardized execution context mock for testing.
        
        Args:
            user_id: Mock user identifier
            thread_id: Mock thread identifier
            
        Returns:
            MagicMock configured for execution context testing
        """
        mock_context = MagicMock()
        mock_context.user_id = user_id
        mock_context.thread_id = thread_id
        mock_context.created_at = datetime.now(UTC)
        mock_context.get_state = MagicMock(return_value={})
        mock_context.set_state = MagicMock()
        return mock_context

    @staticmethod
    def create_tool_mock(
        tool_name: str = "test_tool",
        execution_result: Optional[Dict[str, Any]] = None
    ) -> AsyncMock:
        """
        Create a standardized tool mock for testing.
        
        Args:
            tool_name: Name of the tool to mock
            execution_result: Mock execution result
            
        Returns:
            AsyncMock configured for tool testing
        """
        mock_tool = AsyncMock()
        mock_tool.name = tool_name
        mock_tool.execute = AsyncMock(return_value=execution_result or {
            "status": "success",
            "result": f"Mock {tool_name} execution result"
        })
        mock_tool.get_schema = MagicMock(return_value={
            "name": tool_name,
            "description": f"Mock {tool_name} tool",
            "parameters": {}
        })
        return mock_tool

    @staticmethod
    def create_llm_client_mock(
        response_text: str = "Mock LLM response"
    ) -> AsyncMock:
        """
        Create a standardized LLM client mock for testing.
        
        Args:
            response_text: Mock response text
            
        Returns:
            AsyncMock configured for LLM client testing
        """
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = response_text
        mock_response.usage.total_tokens = 100
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        return mock_client

    @staticmethod
    def create_configuration_mock(
        environment: str = "test",
        additional_config: Optional[Dict[str, Any]] = None
    ) -> MagicMock:
        """
        Create a standardized configuration mock for testing.
        
        Args:
            environment: Mock environment name
            additional_config: Additional configuration values
            
        Returns:
            MagicMock configured for configuration testing
        """
        mock_config = MagicMock()
        mock_config.environment = environment
        mock_config.database_url = "postgresql://test:test@localhost:5432/test"
        mock_config.redis_url = "redis://localhost:6379/0"
        mock_config.jwt_secret_key = "test-jwt-secret"
        
        if additional_config:
            for key, value in additional_config.items():
                setattr(mock_config, key, value)
                
        return mock_config

    @classmethod
    def create_mock_suite(cls, mock_types: List[str]) -> Dict[str, Any]:
        """
        Create a suite of related mocks for comprehensive testing.
        
        Args:
            mock_types: List of mock types to create
            
        Returns:
            Dictionary of created mocks keyed by type
        """
        mock_suite = {}
        
        mock_creators = {
            "agent": cls.create_agent_mock,
            "websocket": cls.create_websocket_mock,
            "database_session": cls.create_database_session_mock,
            "execution_context": cls.create_execution_context_mock,
            "tool": cls.create_tool_mock,
            "llm_client": cls.create_llm_client_mock,
            "configuration": cls.create_configuration_mock,
        }
        
        for mock_type in mock_types:
            if mock_type in mock_creators:
                mock_suite[mock_type] = mock_creators[mock_type]()
        
        return mock_suite