"""
Single Source of Truth (SSOT) Mock Factory

This module provides the unified MockFactory that provides ALL mock implementations
across the entire test suite. It eliminates mock duplication and ensures consistency.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity  
Eliminates mock duplication, ensures consistent behavior, and reduces maintenance overhead.

CRITICAL: This is the ONLY source for mock objects in the system.
ALL test mocks must be created through MockFactory or its specialized methods.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch
from pathlib import Path

# Import SSOT environment management
from shared.isolated_environment import get_env

import logging
logger = logging.getLogger(__name__)


class MockRegistry:
    """Registry to track and manage mock objects for cleanup and verification."""
    
    def __init__(self):
        self.active_mocks: Dict[str, Any] = {}
        self.mock_call_history: List[Dict[str, Any]] = []
        self.cleanup_callbacks: List[callable] = []
    
    def register_mock(self, name: str, mock_obj: Any, cleanup_callback: Optional[callable] = None):
        """Register a mock object for tracking."""
        mock_id = f"{name}_{uuid.uuid4().hex[:8]}"
        self.active_mocks[mock_id] = {
            "name": name,
            "mock": mock_obj,
            "created_at": datetime.now(),
            "call_count": 0
        }
        
        if cleanup_callback:
            self.cleanup_callbacks.append(cleanup_callback)
            
        logger.debug(f"Registered mock: {mock_id} ({name})")
        return mock_id
    
    def get_mock(self, mock_id: str) -> Optional[Any]:
        """Get a registered mock by ID."""
        mock_info = self.active_mocks.get(mock_id)
        return mock_info["mock"] if mock_info else None
    
    def record_call(self, mock_id: str, method: str, args: tuple, kwargs: dict):
        """Record a mock call for analysis."""
        self.mock_call_history.append({
            "mock_id": mock_id,
            "method": method,
            "args": args,
            "kwargs": kwargs,
            "timestamp": datetime.now()
        })
        
        # Increment call count
        if mock_id in self.active_mocks:
            self.active_mocks[mock_id]["call_count"] += 1
    
    def get_call_history(self, mock_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get call history for a specific mock or all mocks."""
        if mock_id:
            return [call for call in self.mock_call_history if call["mock_id"] == mock_id]
        return self.mock_call_history.copy()
    
    def cleanup_all(self):
        """Clean up all registered mocks."""
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Mock cleanup callback failed: {e}")
        
        self.active_mocks.clear()
        self.mock_call_history.clear()
        self.cleanup_callbacks.clear()
        logger.debug("All mocks cleaned up")


class MockFactory:
    """
    Single Source of Truth (SSOT) factory for ALL mock objects in the test suite.
    
    This factory provides consistent, reusable mock implementations that eliminate
    duplication and ensure reliable test behavior across all 6,096 test files.
    
    Key Features:
    - Centralized mock creation and configuration
    - Automatic cleanup and resource management  
    - Call history tracking and verification
    - Service-specific mock implementations
    - Async mock support with proper cleanup
    - Environment isolation integration
    
    Usage:
        factory = MockFactory()
        db_mock = factory.create_database_mock()
        websocket_mock = factory.create_websocket_mock()
        llm_mock = factory.create_llm_mock()
    """
    
    def __init__(self, env: Optional[Any] = None):
        """Initialize MockFactory with environment integration."""
        self.env = env or get_env()
        self.registry = MockRegistry()
        self._test_data_cache: Dict[str, Any] = {}
        
        # Mock configuration from environment
        self.mock_config = {
            "enable_call_tracking": self.env.get("MOCK_ENABLE_CALL_TRACKING", "true").lower() == "true",
            "mock_timeout": int(self.env.get("MOCK_TIMEOUT_SECONDS", "30")),
            "enable_realistic_delays": self.env.get("MOCK_ENABLE_REALISTIC_DELAYS", "false").lower() == "true",
            "default_delay_ms": int(self.env.get("MOCK_DEFAULT_DELAY_MS", "100"))
        }
        
        logger.debug("MockFactory initialized with configuration", extra={"config": self.mock_config})
    
    def cleanup(self):
        """Clean up all mocks and resources."""
        self.registry.cleanup_all()
        self._test_data_cache.clear()
        logger.info("MockFactory cleanup completed")
    
    # ========== Core Mock Creation ==========
    
    def create_mock(self, spec: Optional[type] = None, **kwargs) -> Mock:
        """Create a basic mock with tracking."""
        mock_obj = Mock(spec=spec, **kwargs)
        mock_id = self.registry.register_mock("generic", mock_obj)
        
        if self.mock_config["enable_call_tracking"]:
            self._add_call_tracking(mock_obj, mock_id)
        
        return mock_obj
    
    def create_async_mock(self, spec: Optional[type] = None, **kwargs) -> AsyncMock:
        """Create an async mock with tracking."""
        mock_obj = AsyncMock(spec=spec, **kwargs)
        mock_id = self.registry.register_mock("async", mock_obj)
        
        if self.mock_config["enable_call_tracking"]:
            self._add_call_tracking(mock_obj, mock_id)
        
        return mock_obj
    
    def create_magic_mock(self, spec: Optional[type] = None, **kwargs) -> MagicMock:
        """Create a magic mock with tracking."""
        mock_obj = MagicMock(spec=spec, **kwargs)
        mock_id = self.registry.register_mock("magic", mock_obj)
        
        if self.mock_config["enable_call_tracking"]:
            self._add_call_tracking(mock_obj, mock_id)
        
        return mock_obj
    
    def create_property_mock(self, return_value: Any = None) -> PropertyMock:
        """Create a property mock."""
        mock_obj = PropertyMock(return_value=return_value)
        self.registry.register_mock("property", mock_obj)
        return mock_obj
    
    # ========== Database Mocks ==========
    
    def create_database_session_mock(self) -> AsyncMock:
        """Create a comprehensive database session mock."""
        session_mock = AsyncMock()
        
        # Configure common session methods
        session_mock.add = AsyncMock()
        session_mock.commit = AsyncMock()
        session_mock.rollback = AsyncMock()
        session_mock.close = AsyncMock()
        session_mock.refresh = AsyncMock()
        session_mock.merge = AsyncMock()
        session_mock.delete = AsyncMock()
        session_mock.flush = AsyncMock()
        
        # Query methods
        session_mock.execute = AsyncMock()
        session_mock.scalar = AsyncMock()
        session_mock.scalars = AsyncMock()
        session_mock.get = AsyncMock()
        
        # Context manager support
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        
        # Transaction support
        session_mock.begin = AsyncMock()
        session_mock.begin_nested = AsyncMock()
        
        mock_id = self.registry.register_mock("database_session", session_mock)
        return session_mock
    
    def create_database_result_mock(self, rows: List[Dict[str, Any]] = None) -> Mock:
        """Create a database query result mock."""
        rows = rows or []
        result_mock = Mock()
        
        # Configure result methods
        result_mock.fetchall = Mock(return_value=rows)
        result_mock.fetchone = Mock(return_value=rows[0] if rows else None)
        result_mock.fetchmany = Mock(side_effect=lambda size: rows[:size])
        result_mock.rowcount = len(rows)
        result_mock.lastrowid = rows[-1].get("id") if rows else None
        
        # Async versions
        result_mock.fetchall = AsyncMock(return_value=rows)
        result_mock.fetchone = AsyncMock(return_value=rows[0] if rows else None)
        
        self.registry.register_mock("database_result", result_mock)
        return result_mock
    
    def create_repository_mock(self, model_class: Optional[type] = None) -> AsyncMock:
        """Create a repository mock with CRUD operations."""
        repo_mock = AsyncMock()
        
        # Standard CRUD operations
        repo_mock.create = AsyncMock()
        repo_mock.get = AsyncMock()
        repo_mock.get_by_id = AsyncMock()
        repo_mock.get_all = AsyncMock(return_value=[])
        repo_mock.update = AsyncMock()
        repo_mock.delete = AsyncMock()
        repo_mock.exists = AsyncMock(return_value=False)
        repo_mock.count = AsyncMock(return_value=0)
        
        # Query operations
        repo_mock.find_by = AsyncMock(return_value=[])
        repo_mock.find_one_by = AsyncMock(return_value=None)
        repo_mock.search = AsyncMock(return_value=[])
        
        # Bulk operations
        repo_mock.bulk_create = AsyncMock()
        repo_mock.bulk_update = AsyncMock()
        repo_mock.bulk_delete = AsyncMock()
        
        if model_class:
            repo_mock.model_class = model_class
        
        self.registry.register_mock("repository", repo_mock)
        return repo_mock
    
    # ========== Service Mocks ==========
    
    def create_auth_service_mock(self) -> AsyncMock:
        """Create authentication service mock."""
        auth_mock = AsyncMock()
        
        # Authentication methods
        auth_mock.authenticate_user = AsyncMock(return_value=self._create_test_user())
        auth_mock.create_user = AsyncMock(return_value=self._create_test_user())
        auth_mock.verify_token = AsyncMock(return_value=True)
        auth_mock.generate_token = AsyncMock(return_value="test_token_123")
        auth_mock.refresh_token = AsyncMock(return_value="refreshed_token_123")
        auth_mock.logout_user = AsyncMock(return_value=True)
        
        # User management
        auth_mock.get_user = AsyncMock(return_value=self._create_test_user())
        auth_mock.update_user = AsyncMock(return_value=self._create_test_user())
        auth_mock.delete_user = AsyncMock(return_value=True)
        auth_mock.change_password = AsyncMock(return_value=True)
        
        # Validation
        auth_mock.validate_email = Mock(return_value=True)
        auth_mock.validate_password = Mock(return_value=(True, "Password is valid"))
        
        self.registry.register_mock("auth_service", auth_mock)
        return auth_mock
    
    def create_websocket_manager_mock(self) -> AsyncMock:
        """Create WebSocket manager mock."""
        ws_mock = AsyncMock()
        
        # Connection management
        ws_mock.connect = AsyncMock()
        ws_mock.disconnect = AsyncMock()
        ws_mock.get_connection = AsyncMock()
        ws_mock.is_connected = Mock(return_value=True)
        
        # Message handling
        ws_mock.send_message = AsyncMock()
        ws_mock.broadcast_message = AsyncMock()
        ws_mock.send_to_user = AsyncMock()
        ws_mock.send_to_thread = AsyncMock()
        
        # Event handling
        ws_mock.emit_event = AsyncMock()
        ws_mock.emit_agent_event = AsyncMock()
        ws_mock.emit_status_update = AsyncMock()
        
        # Agent notifications
        ws_mock.notify_agent_started = AsyncMock()
        ws_mock.notify_agent_thinking = AsyncMock()
        ws_mock.notify_tool_executing = AsyncMock()
        ws_mock.notify_tool_completed = AsyncMock()
        ws_mock.notify_agent_completed = AsyncMock()
        
        self.registry.register_mock("websocket_manager", ws_mock)
        return ws_mock
    
    def create_llm_client_mock(self) -> AsyncMock:
        """Create LLM client mock with realistic responses."""
        llm_mock = AsyncMock()
        
        # Chat completion
        llm_mock.create_completion = AsyncMock(return_value=self._create_test_llm_response())
        llm_mock.create_chat_completion = AsyncMock(return_value=self._create_test_chat_response())
        llm_mock.create_stream = AsyncMock(return_value=self._create_test_stream())
        
        # Model management
        llm_mock.list_models = AsyncMock(return_value=["gpt-4", "gpt-3.5-turbo", "claude-3"])
        llm_mock.get_model_info = AsyncMock(return_value={"name": "test-model", "version": "1.0"})
        
        # Token management
        llm_mock.count_tokens = Mock(return_value=100)
        llm_mock.estimate_cost = Mock(return_value=0.001)
        
        if self.mock_config["enable_realistic_delays"]:
            self._add_realistic_delays(llm_mock)
        
        self.registry.register_mock("llm_client", llm_mock)
        return llm_mock
    
    def create_redis_client_mock(self) -> Mock:
        """Create Redis client mock."""
        redis_mock = Mock()
        
        # String operations
        redis_mock.get = Mock(return_value=None)
        redis_mock.set = Mock(return_value=True)
        redis_mock.delete = Mock(return_value=1)
        redis_mock.exists = Mock(return_value=0)
        redis_mock.expire = Mock(return_value=True)
        redis_mock.ttl = Mock(return_value=-1)
        
        # Hash operations
        redis_mock.hget = Mock(return_value=None)
        redis_mock.hset = Mock(return_value=1)
        redis_mock.hgetall = Mock(return_value={})
        redis_mock.hdel = Mock(return_value=1)
        
        # List operations
        redis_mock.lpush = Mock(return_value=1)
        redis_mock.rpush = Mock(return_value=1)
        redis_mock.lpop = Mock(return_value=None)
        redis_mock.rpop = Mock(return_value=None)
        redis_mock.lrange = Mock(return_value=[])
        
        # Set operations
        redis_mock.sadd = Mock(return_value=1)
        redis_mock.srem = Mock(return_value=1)
        redis_mock.smembers = Mock(return_value=set())
        redis_mock.sismember = Mock(return_value=False)
        
        # Connection
        redis_mock.ping = Mock(return_value=True)
        redis_mock.close = Mock()
        
        # Pipeline
        redis_mock.pipeline = Mock(return_value=Mock())
        
        self.registry.register_mock("redis_client", redis_mock)
        return redis_mock
    
    # ========== Agent Mocks ==========
    
    def create_agent_mock(self, agent_type: str = "generic", agent_id: str = None, user_id: str = None) -> AsyncMock:
        """Create agent mock with standard interface."""
        agent_mock = AsyncMock()
        
        # Core agent methods
        agent_mock.initialize = AsyncMock()
        agent_mock.process_request = AsyncMock(return_value=self._create_test_agent_response())
        agent_mock.cleanup = AsyncMock()
        agent_mock.run = AsyncMock(return_value=self._create_test_agent_response())
        agent_mock.recover = AsyncMock(return_value=True)
        
        # State management
        agent_mock.get_state = AsyncMock(return_value={})
        agent_mock.set_state = AsyncMock()
        agent_mock.save_checkpoint = AsyncMock()
        agent_mock.load_checkpoint = AsyncMock()
        
        # Tool execution
        agent_mock.execute_tool = AsyncMock(return_value={"result": "tool_executed"})
        agent_mock.list_tools = Mock(return_value=["tool1", "tool2"])
        
        # Properties with configurable values
        agent_mock.agent_type = agent_type
        agent_mock.agent_id = agent_id or f"test_agent_{uuid.uuid4().hex[:8]}"
        agent_mock.user_id = user_id
        agent_mock.thread_id = None
        agent_mock.db_session = None
        agent_mock.is_busy = False
        agent_mock.last_activity = datetime.now()
        agent_mock.error_count = 0
        agent_mock.last_error = None
        agent_mock.should_fail = False
        agent_mock.failure_message = "Test failure"
        agent_mock.execution_time = 0.1
        
        # Agent state enum simulation
        from enum import Enum
        class AgentState(Enum):
            IDLE = "idle"
            ACTIVE = "active"
            RUNNING = "running"
            ERROR = "error"
            RECOVERING = "recovering"
        
        agent_mock.state = AgentState.IDLE
        agent_mock.AgentState = AgentState
        
        self.registry.register_mock(f"agent_{agent_type}", agent_mock)
        return agent_mock
    
    def create_orchestrator_mock(self) -> AsyncMock:
        """Create agent orchestrator mock."""
        orchestrator_mock = AsyncMock()
        
        # Orchestrator properties
        orchestrator_mock.agents = {}
        orchestrator_mock.agent_pool = []
        orchestrator_mock.error_threshold = 3
        orchestrator_mock.recovery_timeout = 5.0
        orchestrator_mock.retry_delay = 0.1
        orchestrator_mock.execution_timeout = 0.5
        orchestrator_mock.max_concurrent_agents = 10
        orchestrator_mock.max_pool_size = 5
        orchestrator_mock.metrics = {
            "agents_created": 0,
            "tasks_executed": 0, 
            "errors_handled": 0,
            "total_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "concurrent_peak": 0,
        }
        orchestrator_mock._active_agents_override = None
        
        # Orchestrator methods
        orchestrator_mock.get_or_create_agent = AsyncMock(return_value=self.create_agent_mock())
        orchestrator_mock.execute_agent_task = AsyncMock(return_value={"status": "completed"})
        orchestrator_mock.handle_agent_error = AsyncMock(return_value=True)
        orchestrator_mock.release_agent = AsyncMock()
        orchestrator_mock.get_orchestration_metrics = Mock(return_value=orchestrator_mock.metrics)
        
        # Active agents property simulation
        def get_active_agents():
            if orchestrator_mock._active_agents_override is not None:
                return orchestrator_mock._active_agents_override
            return len(orchestrator_mock.agents)
        
        def set_active_agents(value):
            orchestrator_mock._active_agents_override = value
            
        orchestrator_mock.active_agents = property(get_active_agents)
        orchestrator_mock.orchestration_metrics = property(lambda: orchestrator_mock.metrics)
        
        self.registry.register_mock("orchestrator", orchestrator_mock)
        return orchestrator_mock
    
    def create_tool_executor_mock(self) -> AsyncMock:
        """Create tool executor mock."""
        executor_mock = AsyncMock()
        
        # Tool execution
        executor_mock.execute_tool = AsyncMock(return_value={"success": True, "result": "executed"})
        executor_mock.validate_tool = Mock(return_value=True)
        executor_mock.get_tool_schema = Mock(return_value={})
        executor_mock.list_available_tools = Mock(return_value=["tool1", "tool2"])
        
        # Execution tracking
        executor_mock.get_execution_history = Mock(return_value=[])
        executor_mock.get_execution_stats = Mock(return_value={"total": 0, "successful": 0, "failed": 0})
        
        self.registry.register_mock("tool_executor", executor_mock)
        return executor_mock
    
    # ========== File System Mocks ==========
    
    def create_file_system_mock(self) -> Mock:
        """Create file system mock for Path and file operations."""
        fs_mock = Mock()
        
        # Path operations
        fs_mock.exists = Mock(return_value=True)
        fs_mock.is_file = Mock(return_value=True)
        fs_mock.is_dir = Mock(return_value=False)
        fs_mock.mkdir = Mock()
        fs_mock.unlink = Mock()
        fs_mock.rmdir = Mock()
        
        # File operations
        fs_mock.read_text = Mock(return_value="test content")
        fs_mock.write_text = Mock()
        fs_mock.read_bytes = Mock(return_value=b"test bytes")
        fs_mock.write_bytes = Mock()
        
        # Directory operations
        fs_mock.iterdir = Mock(return_value=[])
        fs_mock.glob = Mock(return_value=[])
        fs_mock.rglob = Mock(return_value=[])
        
        self.registry.register_mock("file_system", fs_mock)
        return fs_mock
    
    # ========== HTTP Client Mocks ==========
    
    def create_http_client_mock(self) -> AsyncMock:
        """Create HTTP client mock with realistic responses."""
        http_mock = AsyncMock()
        
        # HTTP methods
        http_mock.get = AsyncMock(return_value=self._create_test_http_response())
        http_mock.post = AsyncMock(return_value=self._create_test_http_response())
        http_mock.put = AsyncMock(return_value=self._create_test_http_response())
        http_mock.delete = AsyncMock(return_value=self._create_test_http_response())
        http_mock.patch = AsyncMock(return_value=self._create_test_http_response())
        
        # Session management
        http_mock.close = AsyncMock()
        http_mock.__aenter__ = AsyncMock(return_value=http_mock)
        http_mock.__aexit__ = AsyncMock(return_value=None)
        
        self.registry.register_mock("http_client", http_mock)
        return http_mock
    
    # ========== WebSocket Mocks ==========
    
    def create_websocket_connection_mock(self) -> AsyncMock:
        """Create WebSocket connection mock."""
        ws_mock = AsyncMock()
        
        # Connection state
        ws_mock.connected = True
        ws_mock.closed = False
        ws_mock.user_id = None
        ws_mock.thread_id = None
        ws_mock.connection_id = f"ws_{uuid.uuid4().hex[:8]}"
        
        # Connection methods
        ws_mock.connect = AsyncMock()
        ws_mock.disconnect = AsyncMock()
        ws_mock.close = AsyncMock()
        ws_mock.ping = AsyncMock()
        ws_mock.pong = AsyncMock()
        
        # Message methods
        ws_mock.send = AsyncMock()
        ws_mock.send_text = AsyncMock()
        ws_mock.send_json = AsyncMock()
        ws_mock.receive = AsyncMock()
        ws_mock.receive_text = AsyncMock()
        ws_mock.receive_json = AsyncMock()
        
        # Context manager support
        ws_mock.__aenter__ = AsyncMock(return_value=ws_mock)
        ws_mock.__aexit__ = AsyncMock(return_value=None)
        
        self.registry.register_mock("websocket_connection", ws_mock)
        return ws_mock
    
    def create_websocket_server_mock(self) -> AsyncMock:
        """Create WebSocket server mock for testing high-volume scenarios."""
        server_mock = AsyncMock()
        
        # Server properties
        server_mock.connections = {}
        server_mock.message_queue = []
        server_mock.is_running = True
        server_mock.port = 8765
        server_mock.host = "localhost"
        
        # Server methods
        server_mock.start = AsyncMock()
        server_mock.stop = AsyncMock()
        server_mock.broadcast = AsyncMock()
        server_mock.send_to_connection = AsyncMock()
        server_mock.get_connection = AsyncMock()
        server_mock.add_connection = AsyncMock()
        server_mock.remove_connection = AsyncMock()
        
        self.registry.register_mock("websocket_server", server_mock)
        return server_mock
    
    # ========== Service Manager Mocks ==========
    
    def create_service_manager_mock(self) -> AsyncMock:
        """Create service manager mock."""
        manager_mock = AsyncMock()
        
        # Service tracking
        manager_mock.services = {}
        manager_mock.health_status = {}
        manager_mock.service_configs = {}
        
        # Service management methods
        manager_mock.start_service = AsyncMock(return_value=True)
        manager_mock.stop_service = AsyncMock(return_value=True)
        manager_mock.restart_service = AsyncMock(return_value=True)
        manager_mock.get_service_status = AsyncMock(return_value="running")
        manager_mock.list_services = Mock(return_value=[])
        manager_mock.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Service discovery
        manager_mock.register_service = AsyncMock()
        manager_mock.discover_service = AsyncMock()
        manager_mock.get_service_endpoint = Mock(return_value="http://localhost:8000")
        
        self.registry.register_mock("service_manager", manager_mock)
        return manager_mock
    
    def create_service_factory_mock(self) -> Mock:
        """Create service factory mock."""
        factory_mock = Mock()
        
        # Factory methods
        factory_mock.create_service = Mock(return_value=self.create_service_manager_mock())
        factory_mock.get_service = Mock(return_value=self.create_service_manager_mock())
        factory_mock.create_database_service = Mock(return_value=self.create_database_session_mock())
        factory_mock.create_auth_service = Mock(return_value=self.create_auth_service_mock())
        factory_mock.create_websocket_service = Mock(return_value=self.create_websocket_manager_mock())
        
        # Service registry
        factory_mock.registered_services = {}
        factory_mock.register = Mock()
        factory_mock.unregister = Mock()
        factory_mock.list_registered = Mock(return_value=[])
        
        self.registry.register_mock("service_factory", factory_mock)
        return factory_mock
    
    # ========== Environment and Configuration Mocks ==========
    
    def create_config_loader_mock(self) -> Mock:
        """Create configuration loader mock."""
        config_mock = Mock()
        
        # Configuration data
        config_mock.config_data = {}
        config_mock.environment = "test"
        config_mock.config_file_path = "/test/config.yaml"
        
        # Configuration methods
        config_mock.load = Mock(return_value=config_mock.config_data)
        config_mock.get = Mock(side_effect=lambda key, default=None: config_mock.config_data.get(key, default))
        config_mock.set = Mock(side_effect=lambda key, value: config_mock.config_data.update({key: value}))
        config_mock.reload = Mock()
        config_mock.save = Mock()
        
        # Environment-specific methods
        config_mock.load_environment = Mock(return_value=config_mock.config_data)
        config_mock.get_database_url = Mock(return_value="postgresql://test:test@localhost:5432/test_db")
        config_mock.get_redis_url = Mock(return_value="redis://localhost:6379/0")
        
        self.registry.register_mock("config_loader", config_mock)
        return config_mock
    
    def create_environment_mock(self) -> Mock:
        """Create environment mock for testing."""
        env_mock = Mock()
        
        # Environment variables
        env_mock.env_vars = {
            "ENVIRONMENT": "test",
            "DEBUG": "true",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
            "REDIS_URL": "redis://localhost:6379/0"
        }
        
        # Environment methods
        env_mock.get = Mock(side_effect=lambda key, default=None: env_mock.env_vars.get(key, default))
        env_mock.set = Mock(side_effect=lambda key, value: env_mock.env_vars.update({key: value}))
        env_mock.get_bool = Mock(side_effect=lambda key, default=False: str(env_mock.env_vars.get(key, default)).lower() == "true")
        env_mock.get_int = Mock(side_effect=lambda key, default=0: int(env_mock.env_vars.get(key, default)))
        env_mock.get_float = Mock(side_effect=lambda key, default=0.0: float(env_mock.env_vars.get(key, default)))
        
        # Environment validation
        env_mock.validate_required = Mock(return_value=True)
        env_mock.get_missing_vars = Mock(return_value=[])
        
        self.registry.register_mock("environment", env_mock)
        return env_mock
    
    # ========== Specialized Mock Utilities ==========
    
    def create_context_manager_mock(self, return_value: Any = None) -> AsyncMock:
        """Create an async context manager mock."""
        cm_mock = AsyncMock()
        cm_mock.__aenter__ = AsyncMock(return_value=return_value or cm_mock)
        cm_mock.__aexit__ = AsyncMock(return_value=None)
        
        self.registry.register_mock("context_manager", cm_mock)
        return cm_mock
    
    def create_generator_mock(self, items: List[Any] = None) -> Mock:
        """Create a generator mock."""
        items = items or []
        
        def generator():
            for item in items:
                yield item
        
        gen_mock = Mock()
        gen_mock.__iter__ = Mock(return_value=generator())
        gen_mock.__next__ = Mock(side_effect=lambda: next(generator()))
        
        self.registry.register_mock("generator", gen_mock)
        return gen_mock
    
    def create_async_generator_mock(self, items: List[Any] = None) -> AsyncMock:
        """Create an async generator mock."""
        items = items or []
        
        async def async_generator():
            for item in items:
                yield item
        
        agen_mock = AsyncMock()
        agen_mock.__aiter__ = Mock(return_value=async_generator())
        agen_mock.__anext__ = AsyncMock(side_effect=lambda: async_generator().__anext__())
        
        self.registry.register_mock("async_generator", agen_mock)
        return agen_mock
    
    # ========== Test Data Creation ==========
    
    def _create_test_user(self) -> Dict[str, Any]:
        """Create test user data."""
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        return {
            "id": user_id,
            "email": f"{user_id}@test.com",
            "username": f"testuser_{user_id}",
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "is_verified": True
        }
    
    def _create_test_llm_response(self) -> Dict[str, Any]:
        """Create test LLM response data."""
        return {
            "id": f"resp_{uuid.uuid4().hex[:8]}",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the LLM mock."
                },
                "finish_reason": "stop",
                "index": 0
            }],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 20,
                "total_tokens": 70
            },
            "model": "test-model",
            "created": int(time.time())
        }
    
    def _create_test_chat_response(self) -> Dict[str, Any]:
        """Create test chat response data."""
        return {
            "message": "This is a test chat response.",
            "metadata": {
                "tokens_used": 25,
                "response_time": 0.5,
                "model": "test-model"
            }
        }
    
    async def _create_test_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Create test streaming response."""
        chunks = [
            {"delta": {"content": "This "}},
            {"delta": {"content": "is "}},
            {"delta": {"content": "a "}},
            {"delta": {"content": "test "}},
            {"delta": {"content": "stream."}}
        ]
        
        for chunk in chunks:
            if self.mock_config["enable_realistic_delays"]:
                await asyncio.sleep(0.01)
            yield chunk
    
    def _create_test_agent_response(self) -> Dict[str, Any]:
        """Create test agent response data."""
        return {
            "response": "Test agent response",
            "status": "completed",
            "execution_time": 1.5,
            "tools_used": ["tool1"],
            "metadata": {
                "agent_type": "test",
                "version": "1.0"
            }
        }
    
    def _create_test_http_response(self) -> Mock:
        """Create test HTTP response mock."""
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json = Mock(return_value={"status": "success"})
        response_mock.text = "Success"
        response_mock.content = b"Success"
        response_mock.headers = {"Content-Type": "application/json"}
        return response_mock
    
    # ========== Mock Enhancement Utilities ==========
    
    def _add_call_tracking(self, mock_obj: Any, mock_id: str):
        """Add call tracking to a mock object."""
        original_call = mock_obj.__call__
        
        def tracked_call(*args, **kwargs):
            self.registry.record_call(mock_id, "__call__", args, kwargs)
            return original_call(*args, **kwargs)
        
        mock_obj.__call__ = tracked_call
    
    def _add_realistic_delays(self, mock_obj: AsyncMock):
        """Add realistic delays to async mock methods."""
        delay_ms = self.mock_config["default_delay_ms"] / 1000.0
        
        for attr_name in dir(mock_obj):
            attr = getattr(mock_obj, attr_name)
            if isinstance(attr, AsyncMock) and not attr_name.startswith('_'):
                original_method = attr
                
                async def delayed_method(*args, **kwargs):
                    await asyncio.sleep(delay_ms)
                    return await original_method(*args, **kwargs)
                
                setattr(mock_obj, attr_name, delayed_method)
    
    # ========== Mock Verification ==========
    
    def verify_mock_calls(self, mock_obj: Any, expected_calls: List[tuple]) -> bool:
        """Verify that a mock was called with expected arguments."""
        actual_calls = mock_obj.call_args_list
        return actual_calls == expected_calls
    
    def get_mock_call_count(self, mock_obj: Any) -> int:
        """Get the number of times a mock was called."""
        return mock_obj.call_count
    
    def reset_mock(self, mock_obj: Any):
        """Reset a mock's call history."""
        mock_obj.reset_mock()
    
    def reset_all_mocks(self):
        """Reset all registered mocks."""
        for mock_info in self.registry.active_mocks.values():
            if hasattr(mock_info["mock"], "reset_mock"):
                mock_info["mock"].reset_mock()
        
        self.registry.mock_call_history.clear()
        logger.debug("All mocks reset")


# ========== Specialized Mock Factories ==========

class DatabaseMockFactory:
    """Specialized factory for database-related mocks."""
    
    def __init__(self, main_factory: MockFactory):
        self.main_factory = main_factory
    
    def create_user_repository_mock(self) -> AsyncMock:
        """Create user repository mock."""
        return self.main_factory.create_repository_mock()
    
    def create_thread_repository_mock(self) -> AsyncMock:
        """Create thread repository mock.""" 
        return self.main_factory.create_repository_mock()
    
    def create_message_repository_mock(self) -> AsyncMock:
        """Create message repository mock."""
        return self.main_factory.create_repository_mock()


class ServiceMockFactory:
    """Specialized factory for service-related mocks."""
    
    def __init__(self, main_factory: MockFactory):
        self.main_factory = main_factory
    
    def create_thread_service_mock(self) -> AsyncMock:
        """Create thread service mock."""
        service_mock = AsyncMock()
        
        # Thread operations
        service_mock.create_thread = AsyncMock(return_value={"id": "thread_123"})
        service_mock.get_thread = AsyncMock(return_value={"id": "thread_123"})
        service_mock.update_thread = AsyncMock(return_value={"id": "thread_123"})
        service_mock.delete_thread = AsyncMock(return_value=True)
        
        # Message operations
        service_mock.create_message = AsyncMock(return_value={"id": "msg_123"})
        service_mock.get_messages = AsyncMock(return_value=[])
        
        self.main_factory.registry.register_mock("thread_service", service_mock)
        return service_mock


# ========== Global Mock Factory Instance ==========

_global_mock_factory: Optional[MockFactory] = None


def get_mock_factory() -> MockFactory:
    """Get the global MockFactory instance."""
    global _global_mock_factory
    if _global_mock_factory is None:
        _global_mock_factory = MockFactory()
    return _global_mock_factory


def cleanup_global_mocks():
    """Clean up the global mock factory."""
    global _global_mock_factory
    if _global_mock_factory:
        _global_mock_factory.cleanup()
        _global_mock_factory = None


# ========== Context Managers for Mock Management ==========

class MockContext:
    """Context manager for automatic mock cleanup."""
    
    def __init__(self, factory: Optional[MockFactory] = None):
        self.factory = factory or get_mock_factory()
        self.created_mocks: List[Any] = []
    
    def __enter__(self):
        return self.factory
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up mocks created during context
        for mock_obj in self.created_mocks:
            if hasattr(mock_obj, 'reset_mock'):
                mock_obj.reset_mock()


# Export SSOT mock factory components
__all__ = [
    'MockFactory',
    'SSotMockFactory',  # Alias for MockFactory for test compatibility
    'MockRegistry',
    'DatabaseMockFactory', 
    'ServiceMockFactory',
    'MockContext',
    'get_mock_factory',
    'cleanup_global_mocks'
]

# Alias for backwards compatibility with tests expecting SSotMockFactory
SSotMockFactory = MockFactory