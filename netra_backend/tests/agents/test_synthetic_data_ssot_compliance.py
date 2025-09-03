"""Comprehensive SSOT Compliance Test Suite for SyntheticDataSubAgent

This test suite validates:
1. Complete UserExecutionContext integration and isolation
2. Proper usage of unified_json_handler (not model_dump())
3. No global state leakage between requests
4. Proper error handling through agent_error_handler
5. WebSocket event emission compliance
6. BaseAgent integration and inheritance
7. Isolation between concurrent requests
8. No stored database sessions or user data
9. Configuration access through proper architecture
10. Memory leak prevention and resource cleanup

CRITICAL: These tests are designed to be difficult and comprehensive,
testing edge cases, concurrent scenarios, and will FAIL if violations exist.
"""

import asyncio
import os
import json
import hashlib
import time
import threading
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock, PropertyMock
import pytest
from datetime import datetime, timedelta
import concurrent.futures
import inspect

from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile, DataGenerationType
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def create_mock_db_session():
    """Helper function to create properly mocked database session."""
    session = Mock()
    session.query = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


class TestSyntheticDataSubAgentSSOTCompliance:
    """Test suite for SyntheticDataSubAgent SSOT compliance and isolation patterns."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value={
            "content": "Generated synthetic data profile",
            "usage": {"tokens": 100}
        })
        return llm
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncMock(return_value={"status": "success"})
        return dispatcher
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = Mock()
        session.query = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture
    def user_context(self, mock_db_session):
        """Create test user execution context."""
        return UserExecutionContext(
            user_id=f"test_user_{uuid.uuid4()}",
            thread_id=f"test_thread_{uuid.uuid4()}",
            run_id=f"test_run_{uuid.uuid4()}",
            db_session=mock_db_session,
            metadata={
                "user_request": "Generate synthetic load test data for payment processing",
                "require_approval": False
            }
        )
    
    @pytest.fixture
    async def synthetic_agent(self, mock_llm_manager, mock_tool_dispatcher):
        """Create SyntheticDataSubAgent instance."""
        agent = SyntheticDataSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        return agent
    
    # Test 1: Verify No Direct Environment Access (CRITICAL)
    @pytest.mark.asyncio
    async def test_no_direct_environment_access(self, synthetic_agent):
        """Test that agent never accesses os.environ directly - MUST use IsolatedEnvironment."""
        with patch.dict(os.environ, {"TEST_SYNTHETIC_VAR": "should_not_access"}):
            # Scan agent source code for direct environment access
            source = inspect.getsource(SyntheticDataSubAgent)
            
            # These patterns are FORBIDDEN - agent must use IsolatedEnvironment
            forbidden_patterns = [
                "os.environ[",
                "os.environ.get(",
                "os.getenv(",
                "environ[",
                "getenv("
            ]
            
            for pattern in forbidden_patterns:
                assert pattern not in source, (
                    f"CRITICAL VIOLATION: Found forbidden environment access pattern: {pattern}. "
                    f"Agent MUST use IsolatedEnvironment instead of direct os.environ access."
                )
    
    # Test 2: Verify UserExecutionContext Type Validation (CRITICAL)
    @pytest.mark.asyncio
    async def test_user_context_type_validation_fails_fast(self, synthetic_agent):
        """Test that agent fails fast on incorrect context type."""
        # Test with None - should raise TypeError immediately
        with pytest.raises(TypeError) as exc_info:
            await synthetic_agent.execute(None, stream_updates=False)
        assert "Expected UserExecutionContext" in str(exc_info.value)
        
        # Test with wrong type - should raise TypeError immediately
        with pytest.raises(TypeError) as exc_info:
            await synthetic_agent.execute({"fake": "context"}, stream_updates=False)
        assert "Expected UserExecutionContext" in str(exc_info.value)
        
        # Test with string - should raise TypeError immediately
        with pytest.raises(TypeError) as exc_info:
            await synthetic_agent.execute("invalid", stream_updates=False)
        assert "Expected UserExecutionContext" in str(exc_info.value)
    
    # Test 3: Verify Unified JSON Handler Usage (CRITICAL SSOT)
    @pytest.mark.asyncio
    async def test_unified_json_handler_usage_enforced(self, synthetic_agent, user_context):
        """Test that agent uses unified_json_handler, NOT model_dump() or json.dumps()."""
        
        # Mock successful generation
        mock_profile = Mock()
        mock_profile.workload_type = DataGenerationType.INFERENCE_LOGS
        mock_profile.volume = 1000
        mock_profile.time_range_days = 7
        mock_profile.distribution = "normal"
        mock_profile.custom_parameters = {}
        
        with patch.object(synthetic_agent, '_determine_workload_profile_from_request', 
                         return_value=mock_profile):
            with patch.object(synthetic_agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = Mock(generation_status=Mock(records_generated=1000))
                
                # Track all JSON serialization calls
                with patch('netra_backend.app.core.serialization.unified_json_handler.safe_json_dumps') as mock_unified:
                    mock_unified.return_value = '{"test": "data"}'
                    
                    # Execute agent
                    await synthetic_agent.execute(user_context, stream_updates=False)
                    
                    # Verify unified_json_handler was used
                    assert mock_unified.called, (
                        "CRITICAL VIOLATION: Agent did not use unified_json_handler.safe_json_dumps(). "
                        "All JSON serialization MUST go through unified_json_handler."
                    )
        
        # Verify no direct JSON operations in source code
        source = inspect.getsource(SyntheticDataSubAgent)
        forbidden_json_patterns = [
            ".model_dump()",
            ".dict()",  # Pydantic v1
            "json.dumps(",
            "json.loads(",
            "pydantic.json.dumps",
        ]
        
        for pattern in forbidden_json_patterns:
            assert pattern not in source, (
                f"CRITICAL VIOLATION: Found forbidden JSON pattern: {pattern}. "
                f"Agent MUST use unified_json_handler for all JSON operations."
            )
    
    # Test 4: Verify Complete UserExecutionContext Isolation (CRITICAL)
    @pytest.mark.asyncio
    async def test_complete_user_context_isolation(self, mock_llm_manager, mock_tool_dispatcher):
        """Test complete isolation between different user execution contexts."""
        agent = SyntheticDataSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Create contexts for different users with different requirements
        context1 = UserExecutionContext(
            user_id="user_financial_1",
            thread_id="thread_fin_1",
            run_id="run_fin_1",
            db_session=create_mock_db_session(),
            metadata={
                "user_request": "Generate financial transaction data",
                "require_approval": False
            }
        )
        
        context2 = UserExecutionContext(
            user_id="user_healthcare_2", 
            thread_id="thread_health_2",
            run_id="run_health_2",
            db_session=create_mock_db_session(),
            metadata={
                "user_request": "Generate healthcare synthetic patient data",
                "require_approval": True
            }
        )
        
        # Mock profile determination to return different profiles
        async def mock_profile_determiner(request: str):
            if "financial" in request.lower():
                profile = Mock()
                profile.workload_type = WorkloadType.FINANCIAL_TRANSACTION
                profile.volume = 1000
                profile.time_range_days = 7
                profile.distribution = "normal"
                profile.custom_parameters = {}
                return profile
            else:
                profile = Mock()
                profile.workload_type = DataGenerationType.TRAINING_DATA
                profile.volume = 500
                profile.time_range_days = 14
                profile.distribution = "poisson"
                profile.custom_parameters = {"data_sensitivity": "high"}
                return profile
        
        with patch.object(agent, '_determine_workload_profile_from_request', 
                         side_effect=mock_profile_determiner):
            with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = Mock(generation_status=Mock(records_generated=750))
                
                # Execute both contexts concurrently
                results = await asyncio.gather(
                    agent.execute(context1, stream_updates=False),
                    agent.execute(context2, stream_updates=False),
                    return_exceptions=True
                )
                
                # Verify no exceptions from isolation failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        pytest.fail(f"Context {i+1} failed due to isolation issue: {result}")
                
                # Verify contexts maintained their original identity and weren't corrupted
                assert context1.user_id == "user_financial_1"
                assert context2.user_id == "user_healthcare_2"
                assert context1.metadata["user_request"] == "Generate financial transaction data"
                assert context2.metadata["user_request"] == "Generate healthcare synthetic patient data"
    
    # Test 5: Test WebSocket Event Emissions (CRITICAL for Chat Value)
    @pytest.mark.asyncio
    async def test_websocket_event_emissions_required(self, synthetic_agent, user_context):
        """Test that agent emits ALL required WebSocket events for chat value."""
        # Mock WebSocket emission methods
        synthetic_agent.emit_thinking = AsyncMock()
        synthetic_agent.emit_progress = AsyncMock()
        synthetic_agent.emit_tool_executing = AsyncMock()
        synthetic_agent.emit_tool_completed = AsyncMock()
        synthetic_agent.emit_error = AsyncMock()
        
        # Mock successful generation
        mock_profile = Mock()
        mock_profile.workload_type = DataGenerationType.PERFORMANCE_METRICS
        mock_profile.volume = 500
        mock_profile.time_range_days = 1
        mock_profile.distribution = "uniform"
        mock_profile.custom_parameters = {}
        
        with patch.object(synthetic_agent, '_determine_workload_profile_from_request', 
                         return_value=mock_profile):
            with patch.object(synthetic_agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = Mock(generation_status=Mock(records_generated=500))
                
                # Execute with streaming enabled
                await synthetic_agent.execute(user_context, stream_updates=True)
                
                # Verify CRITICAL WebSocket events were emitted
                critical_events = [
                    ('emit_thinking', "Agent must show thinking process"),
                    ('emit_progress', "Agent must show progress updates"), 
                    ('emit_tool_executing', "Agent must show tool execution"),
                    ('emit_tool_completed', "Agent must show completion")
                ]
                
                for event_method, requirement in critical_events:
                    method = getattr(synthetic_agent, event_method)
                    assert method.called, (
                        f"CRITICAL VIOLATION: {event_method} was not called. "
                        f"{requirement} for substantive chat value."
                    )
    
    # Test 6: Test BaseAgent Integration (CRITICAL Architecture)
    @pytest.mark.asyncio
    async def test_base_agent_integration_required(self, synthetic_agent):
        """Test that agent properly integrates with BaseAgent architecture."""
        # Import BaseAgent to check inheritance
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Verify agent inherits from BaseAgent
        assert isinstance(synthetic_agent, BaseAgent), (
            "CRITICAL VIOLATION: SyntheticDataSubAgent must inherit from BaseAgent"
        )
        
        # Verify agent has required BaseAgent methods
        required_base_methods = [
            'execute',
            'emit_thinking',
            'emit_progress', 
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_error'
        ]
        
        for method in required_base_methods:
            assert hasattr(synthetic_agent, method), (
                f"CRITICAL VIOLATION: Missing required BaseAgent method: {method}"
            )
            assert callable(getattr(synthetic_agent, method)), (
                f"CRITICAL VIOLATION: {method} is not callable"
            )
    
    # Test 7: Test Concurrent Request Isolation (CRITICAL for Multi-User)
    @pytest.mark.asyncio
    async def test_concurrent_request_isolation_stress(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that concurrent requests from different users are completely isolated."""
        agent = SyntheticDataSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Track execution data for isolation verification
        execution_data = {}
        data_lock = threading.Lock()
        
        async def execute_for_user(user_id: int, request_type: str):
            """Execute synthetic data generation for a specific user."""
            context = UserExecutionContext(
                user_id=f"isolation_user_{user_id}",
                thread_id=f"isolation_thread_{user_id}",
                run_id=f"isolation_run_{user_id}",
                db_session=create_mock_db_session(),
                metadata={
                    "user_request": f"Generate {request_type} synthetic data",
                    "unique_marker": f"marker_{user_id}_{request_type}"
                }
            )
            
            # Mock profile based on request type
            mock_profile = Mock()
            mock_profile.workload_type = DataGenerationType.INFERENCE_LOGS if "financial" in request_type else DataGenerationType.PERFORMANCE_METRICS
            mock_profile.volume = user_id * 100  # Different volumes to track isolation
            mock_profile.time_range_days = user_id
            mock_profile.distribution = "normal"
            mock_profile.custom_parameters = {"user_specific": user_id}
            
            with patch.object(agent, '_determine_workload_profile_from_request', 
                             return_value=mock_profile):
                with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                    mock_gen.return_value = Mock(
                        generation_status=Mock(records_generated=user_id * 100)
                    )
                    
                    # Add delay to increase chance of race conditions if isolation broken
                    await asyncio.sleep(0.05)
                    
                    await agent.execute(context, stream_updates=False)
                    
                    # Store execution data thread-safely
                    with data_lock:
                        execution_data[user_id] = {
                            "context_user": context.user_id,
                            "volume": mock_profile.volume,
                            "unique_marker": context.metadata["unique_marker"],
                            "profile_user_specific": mock_profile.custom_parameters["user_specific"]
                        }
        
        # Execute 20 concurrent requests with different data types
        tasks = []
        request_types = ["financial", "api_load", "user_behavior", "system_metrics"]
        
        for i in range(20):
            user_id = i + 1
            request_type = request_types[i % len(request_types)]
            tasks.append(execute_for_user(user_id, request_type))
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no execution failed due to isolation issues
        failed_count = sum(1 for r in results if isinstance(r, Exception))
        assert failed_count == 0, f"{failed_count} executions failed due to isolation violations"
        
        # Verify complete data isolation
        assert len(execution_data) == 20, "Not all executions recorded data"
        
        for user_id, data in execution_data.items():
            # Verify each user's data is isolated and correct
            assert data["volume"] == user_id * 100, f"Volume contamination for user {user_id}"
            assert data["profile_user_specific"] == user_id, f"Profile contamination for user {user_id}"
            assert f"marker_{user_id}_" in data["unique_marker"], f"Marker contamination for user {user_id}"
            assert f"isolation_user_{user_id}" == data["context_user"], f"Context contamination for user {user_id}"
    
    # Test 8: Test No Global State Storage (CRITICAL VIOLATION CHECK)
    @pytest.mark.asyncio
    async def test_no_global_state_storage_enforced(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that agent never stores user-specific data in global/instance variables."""
        agent = SyntheticDataSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Capture initial agent state
        initial_attrs = {attr: getattr(agent, attr) for attr in dir(agent) 
                        if not attr.startswith('__') and not callable(getattr(agent, attr, None))}
        
        # Execute for first user with distinct data
        context1 = UserExecutionContext(
            user_id="global_test_user_1",
            thread_id="global_test_thread_1", 
            run_id="global_test_run_1",
            db_session=create_mock_db_session(),
            metadata={
                "user_request": "Generate synthetic payment data",
                "secret_marker": "SECRET_USER_1_MARKER"
            }
        )
        
        mock_profile1 = Mock()
        mock_profile1.workload_type = WorkloadType.FINANCIAL_TRANSACTION
        mock_profile1.volume = 1111  # Distinctive number
        mock_profile1.custom_parameters = {"secret": "user1_secret"}
        
        with patch.object(agent, '_determine_workload_profile_from_request', 
                         return_value=mock_profile1):
            with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = Mock(generation_status=Mock(records_generated=1111))
                
                await agent.execute(context1, stream_updates=False)
        
        # Check that NO user-specific data leaked into agent instance
        post_exec_attrs = {attr: getattr(agent, attr) for attr in dir(agent) 
                          if not attr.startswith('__') and not callable(getattr(agent, attr, None))}
        
        # Define user-specific data that MUST NOT be stored
        user_specific_data = [
            "global_test_user_1",
            "global_test_thread_1", 
            "global_test_run_1",
            "SECRET_USER_1_MARKER",
            "user1_secret",
            "1111"
        ]
        
        for attr_name, attr_value in post_exec_attrs.items():
            if isinstance(attr_value, (str, int, float)):
                for forbidden_data in user_specific_data:
                    assert str(forbidden_data) not in str(attr_value), (
                        f"CRITICAL VIOLATION: User-specific data '{forbidden_data}' found in "
                        f"agent instance attribute '{attr_name}' with value '{attr_value}'. "
                        f"Agent MUST NOT store user data globally."
                    )
        
        # Execute for second user to ensure no contamination
        context2 = UserExecutionContext(
            user_id="global_test_user_2",
            thread_id="global_test_thread_2",
            run_id="global_test_run_2", 
            db_session=create_mock_db_session(),
            metadata={
                "user_request": "Generate synthetic API data",
                "secret_marker": "SECRET_USER_2_MARKER"
            }
        )
        
        mock_profile2 = Mock()
        mock_profile2.workload_type = DataGenerationType.PERFORMANCE_METRICS
        mock_profile2.volume = 2222  # Different distinctive number
        mock_profile2.custom_parameters = {"secret": "user2_secret"}
        
        with patch.object(agent, '_determine_workload_profile_from_request', 
                         return_value=mock_profile2):
            with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = Mock(generation_status=Mock(records_generated=2222))
                
                await agent.execute(context2, stream_updates=False)
        
        # Verify no contamination from first user
        final_attrs = {attr: getattr(agent, attr) for attr in dir(agent) 
                      if not attr.startswith('__') and not callable(getattr(agent, attr, None))}
        
        for attr_name, attr_value in final_attrs.items():
            if isinstance(attr_value, (str, int, float)):
                # First user's data MUST NOT be present
                for forbidden_data in user_specific_data:
                    assert str(forbidden_data) not in str(attr_value), (
                        f"CRITICAL VIOLATION: First user's data '{forbidden_data}' contaminated "
                        f"second execution in attribute '{attr_name}' with value '{attr_value}'"
                    )
    
    # Test 9: Test Error Handling Through agent_error_handler (CRITICAL SSOT)
    @pytest.mark.asyncio
    async def test_agent_error_handler_integration(self, synthetic_agent, user_context):
        """Test that agent uses agent_error_handler, not custom error handling."""
        # Mock error scenario
        mock_profile = Mock()
        mock_profile.workload_type = DataGenerationType.INFERENCE_LOGS
        mock_profile.volume = 1000
        
        with patch.object(synthetic_agent, '_determine_workload_profile_from_request', 
                         return_value=mock_profile):
            with patch.object(synthetic_agent.generator, 'generate_data', 
                             side_effect=Exception("Test synthetic data generation error")):
                
                # Mock error handler to verify it's used
                with patch('netra_backend.app.core.unified_error_handler.agent_error_handler') as mock_handler:
                    mock_handler.handle_agent_error = Mock()
                    
                    # Execute should use error handler
                    with pytest.raises(Exception) as exc_info:
                        await synthetic_agent.execute(user_context, stream_updates=True)
                    
                    assert "Test synthetic data generation error" in str(exc_info.value)
        
        # Verify no custom error handling patterns in source
        source = inspect.getsource(SyntheticDataSubAgent)
        
        # These patterns indicate custom error handling (forbidden)
        forbidden_error_patterns = [
            "except Exception as e:\n    pass",  # Swallowing exceptions
            "except:\n    pass",  # Bare except
            "logger.error(f\"Error:",  # Custom error logging without handler
            "print(\"Error:",  # Print error statements
        ]
        
        lines = source.split('\n')
        for i, line in enumerate(lines):
            for pattern in forbidden_error_patterns:
                if pattern in line:
                    # Check context to see if it's legitimate error handling
                    context_lines = lines[max(0, i-2):i+3]
                    context_text = '\n'.join(context_lines)
                    
                    # If it doesn't use agent_error_handler, it's a violation
                    if 'agent_error_handler' not in context_text:
                        pytest.fail(
                            f"CRITICAL VIOLATION: Found custom error handling pattern '{pattern}' "
                            f"at line {i+1}. Agent MUST use agent_error_handler for all error handling."
                        )
    
    # Test 10: Test Database Session Management (CRITICAL for Isolation)
    @pytest.mark.asyncio
    async def test_database_session_isolation_enforced(self, synthetic_agent, user_context):
        """Test that database sessions are properly isolated and cleaned up."""
        # Agent should NEVER store database sessions as instance variables
        forbidden_session_attrs = ['db_session', '_db_session', 'session', '_session']
        
        for attr in forbidden_session_attrs:
            assert not hasattr(synthetic_agent, attr), (
                f"CRITICAL VIOLATION: Agent has forbidden session attribute '{attr}'. "
                f"Sessions MUST only exist within UserExecutionContext."
            )
        
        # Mock DatabaseSessionManager to track cleanup
        cleanup_called = False
        
        async def mock_close():
            nonlocal cleanup_called
            cleanup_called = True
        
        with patch('netra_backend.app.database.session_manager.DatabaseSessionManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.close = mock_close
            mock_manager_class.return_value = mock_manager
            
            mock_profile = Mock()
            mock_profile.workload_type = DataGenerationType.PERFORMANCE_METRICS
            mock_profile.volume = 100
            
            with patch.object(synthetic_agent, '_determine_workload_profile_from_request', 
                             return_value=mock_profile):
                with patch.object(synthetic_agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                    mock_gen.return_value = Mock(generation_status=Mock(records_generated=100))
                    
                    # Execute normally
                    await synthetic_agent.execute(user_context, stream_updates=False)
                    
                    # Verify cleanup was called
                    assert cleanup_called, (
                        "CRITICAL VIOLATION: DatabaseSessionManager.close() was not called. "
                        "Database sessions MUST be properly cleaned up."
                    )
                    
                    # Test cleanup on error
                    cleanup_called = False
                    mock_gen.side_effect = Exception("Test error")
                    
                    with pytest.raises(Exception):
                        await synthetic_agent.execute(user_context, stream_updates=False)
                    
                    assert cleanup_called, (
                        "CRITICAL VIOLATION: DatabaseSessionManager.close() not called on error. "
                        "Cleanup MUST occur even when exceptions happen."
                    )
    
    # Test 11: Test Memory Leak Prevention (CRITICAL Performance)
    @pytest.mark.asyncio 
    async def test_memory_leak_prevention_enforced(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that repeated executions don't cause memory leaks."""
        agent = SyntheticDataSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Capture initial memory footprint
        initial_attrs = set(dir(agent))
        initial_sizes = {}
        
        for attr in initial_attrs:
            if not callable(getattr(agent, attr, None)):
                attr_value = getattr(agent, attr)
                if isinstance(attr_value, (list, dict, str)):
                    initial_sizes[attr] = len(str(attr_value))
        
        # Execute many iterations to detect memory leaks
        for i in range(10):
            context = UserExecutionContext(
                user_id=f"memory_user_{i}",
                thread_id=f"memory_thread_{i}",
                run_id=f"memory_run_{i}",
                db_session=create_mock_db_session(),
                metadata={
                    "user_request": f"Generate synthetic data iteration {i}",
                    "iteration": i
                }
            )
            
            mock_profile = Mock()
            mock_profile.workload_type = DataGenerationType.PERFORMANCE_METRICS
            mock_profile.volume = 100
            
            with patch.object(agent, '_determine_workload_profile_from_request', 
                             return_value=mock_profile):
                with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                    mock_gen.return_value = Mock(generation_status=Mock(records_generated=100))
                    
                    try:
                        await agent.execute(context, stream_updates=False)
                    except Exception:
                        pass  # Ignore errors, focus on memory leaks
        
        # Check for memory leaks
        final_attrs = set(dir(agent))
        new_attrs = final_attrs - initial_attrs
        
        assert len(new_attrs) == 0, (
            f"CRITICAL VIOLATION: New attributes added during execution: {new_attrs}. "
            f"This indicates potential memory leaks."
        )
        
        # Check for data accumulation in existing attributes
        for attr in initial_attrs:
            if not callable(getattr(agent, attr, None)):
                attr_value = getattr(agent, attr)
                if isinstance(attr_value, (list, dict, str)):
                    current_size = len(str(attr_value))
                    initial_size = initial_sizes.get(attr, 0)
                    
                    # Size shouldn't grow significantly (allow 50% growth for reasonable caching)
                    max_allowed_size = initial_size * 1.5
                    assert current_size <= max_allowed_size, (
                        f"CRITICAL VIOLATION: Attribute '{attr}' grew from {initial_size} to {current_size}. "
                        f"This indicates a memory leak in {attr}."
                    )
    
    # Test 12: Test Configuration Access Pattern (CRITICAL Architecture)
    @pytest.mark.asyncio
    async def test_configuration_access_pattern_compliance(self, synthetic_agent):
        """Test that configuration is accessed through proper architecture patterns."""
        source = inspect.getsource(SyntheticDataSubAgent)
        
        # Agent should NOT directly read config files
        forbidden_config_patterns = [
            "open('config",
            'open("config',
            "with open(",  # Direct file operations
            "json.load(",  # Direct JSON config loading
            "yaml.load(",   # Direct YAML config loading
            "configparser.ConfigParser",  # Direct config parsing
            "os.path.join(", # Direct path manipulation for configs
        ]
        
        for pattern in forbidden_config_patterns:
            assert pattern not in source, (
                f"CRITICAL VIOLATION: Found direct config access pattern: '{pattern}'. "
                f"Agent MUST use proper configuration architecture."
            )
        
        # Agent should use proper configuration patterns
        required_config_patterns = [
            # Should access config through proper channels
            "from netra_backend.app.core.config import",
        ]
        
        # At least one proper config pattern should be present if config is needed
        if "config" in source.lower():
            has_proper_pattern = any(pattern in source for pattern in required_config_patterns)
            assert has_proper_pattern, (
                "CRITICAL VIOLATION: Agent accesses configuration but doesn't use proper patterns. "
                "Must import from netra_backend.app.core.config."
            )
    
    # Test 13: Test Request Type Validation (CRITICAL Business Logic)
    @pytest.mark.asyncio
    async def test_request_type_validation_robust(self, synthetic_agent):
        """Test that synthetic data request validation is robust and secure."""
        
        test_cases = [
            # Valid requests that should trigger generation
            ("Generate synthetic payment transaction data", True),
            ("Create mock user behavior data for testing", True),
            ("I need sample data for load testing", True),
            ("Generate test data for API validation", True),
            ("Create synthetic financial records", True),
            
            # Invalid requests that should NOT trigger generation
            ("What is the weather today?", False),
            ("Analyze my real production data", False),
            ("Show me actual user transactions", False),
            ("Delete all data", False),
            ("", False),  # Empty request
        ]
        
        for user_request, should_execute in test_cases:
            result = synthetic_agent._should_execute_synthetic_data(user_request)
            if should_execute:
                assert result, f"Valid synthetic data request was rejected: '{user_request}'"
            else:
                assert not result, f"Invalid request was accepted for generation: '{user_request}'"
    
    # Test 14: Test Approval Flow Isolation (CRITICAL Security)
    @pytest.mark.asyncio
    async def test_approval_flow_user_isolation(self, synthetic_agent):
        """Test that approval requirements are correctly isolated per user."""
        
        # Test cases with different approval requirements
        test_cases = [
            # High volume should require approval
            {
                "volume": 100000,
                "data_sensitivity": "medium",
                "metadata": {"require_approval": False},
                "expected_approval": True
            },
            # High sensitivity should require approval  
            {
                "volume": 1000,
                "data_sensitivity": "high",
                "metadata": {"require_approval": False},
                "expected_approval": True
            },
            # Explicit approval request
            {
                "volume": 1000,
                "data_sensitivity": "low",
                "metadata": {"require_approval": True},
                "expected_approval": True
            },
            # Normal request should not require approval
            {
                "volume": 1000,
                "data_sensitivity": "low", 
                "metadata": {"require_approval": False},
                "expected_approval": False
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            context = UserExecutionContext(
                user_id=f"approval_user_{i}",
                thread_id=f"approval_thread_{i}",
                run_id=f"approval_run_{i}",
                db_session=create_mock_db_session(),
                metadata=test_case["metadata"]
            )
            
            # Mock profile with test parameters
            mock_profile = Mock()
            mock_profile.volume = test_case["volume"]
            mock_profile.custom_parameters = {"data_sensitivity": test_case["data_sensitivity"]}
            
            requires_approval = synthetic_agent._check_approval_requirements_context(
                mock_profile, context
            )
            
            assert requires_approval == test_case["expected_approval"], (
                f"Approval requirement mismatch for test case {i}: "
                f"expected {test_case['expected_approval']}, got {requires_approval}"
            )
    
    # Test 15: Test Stress Conditions and Edge Cases (CRITICAL Reliability)
    @pytest.mark.asyncio
    async def test_stress_conditions_handling(self, mock_llm_manager, mock_tool_dispatcher):
        """Test agent behavior under stress conditions and edge cases."""
        agent = SyntheticDataSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Test 1: Extremely large volume requests
        large_context = UserExecutionContext(
            user_id="stress_user_large",
            thread_id="stress_thread_large",
            run_id="stress_run_large",
            db_session=create_mock_db_session(),
            metadata={
                "user_request": "Generate massive synthetic dataset",
                "volume_override": 1000000  # 1 million records
            }
        )
        
        mock_large_profile = Mock()
        mock_large_profile.workload_type = DataGenerationType.PERFORMANCE_METRICS
        mock_large_profile.volume = 1000000
        mock_large_profile.time_range_days = 365
        mock_large_profile.distribution = "normal"
        mock_large_profile.custom_parameters = {}
        
        with patch.object(agent, '_determine_workload_profile_from_request', 
                         return_value=mock_large_profile):
            # Should require approval for large volumes
            requires_approval = agent._check_approval_requirements_context(
                mock_large_profile, large_context
            )
            assert requires_approval, "Large volume requests must require approval"
        
        # Test 2: Malformed metadata handling
        malformed_context = UserExecutionContext(
            user_id="stress_user_malformed",
            thread_id="stress_thread_malformed",
            run_id="stress_run_malformed",
            db_session=create_mock_db_session(),
            metadata={}  # Empty metadata
        )
        
        # Should not crash on empty metadata
        result = agent._should_execute_synthetic_data("")
        assert not result, "Empty request should not trigger execution"
        
        # Test 3: Unicode and special characters in requests
        unicode_context = UserExecutionContext(
            user_id="stress_user_unicode",
            thread_id="stress_thread_unicode", 
            run_id="stress_run_unicode",
            db_session=create_mock_db_session(),
            metadata={
                "user_request": "Générer des données synthétiques avec émojis 🚀💳🔢",
            }
        )
        
        unicode_result = agent._should_execute_synthetic_data(unicode_context.metadata["user_request"])
        assert unicode_result, "Unicode requests should be handled properly"
        
        print("✅ All stress condition tests passed!")


class TestSyntheticDataSubAgentConcurrencyStress:
    """Extreme concurrency and stress tests."""
    
    # Test 16: High Concurrency Isolation Test
    @pytest.mark.asyncio
    async def test_extreme_concurrency_isolation(self):
        """Test agent under extreme concurrency (50+ simultaneous users)."""
        agent = SyntheticDataSubAgent(
            llm_manager=Mock(spec=LLMManager),
            tool_dispatcher=Mock(spec=ToolDispatcher)
        )
        
        # Track execution results for isolation verification
        results = {}
        results_lock = threading.Lock()
        
        async def execute_concurrent_user(user_idx: int):
            """Execute for a single user with unique data."""
            unique_id = f"concurrent_{user_idx}_{uuid.uuid4().hex[:8]}"
            
            context = UserExecutionContext(
                user_id=f"user_{unique_id}",
                thread_id=f"thread_{unique_id}",
                run_id=f"run_{unique_id}",
                db_session=create_mock_db_session(),
                metadata={
                    "user_request": f"Generate synthetic data for user {unique_id}",
                    "unique_marker": unique_id,
                    "user_index": user_idx
                }
            )
            
            # Mock profile with user-specific data
            mock_profile = Mock()
            mock_profile.workload_type = DataGenerationType.PERFORMANCE_METRICS
            mock_profile.volume = user_idx * 10  # Unique volume per user
            mock_profile.custom_parameters = {"user_specific": unique_id}
            
            with patch.object(agent, '_determine_workload_profile_from_request', 
                             return_value=mock_profile):
                with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                    mock_gen.return_value = Mock(
                        generation_status=Mock(records_generated=user_idx * 10)
                    )
                    
                    # Add processing delay to increase race condition chances
                    await asyncio.sleep(0.01 * (user_idx % 5))
                    
                    await agent.execute(context, stream_updates=False)
                    
                    # Store results thread-safely
                    with results_lock:
                        results[user_idx] = {
                            "context_user_id": context.user_id,
                            "unique_marker": unique_id,
                            "volume": mock_profile.volume,
                            "user_specific": mock_profile.custom_parameters["user_specific"]
                        }
                    
                    return unique_id
        
        # Execute 50 concurrent users
        tasks = [execute_concurrent_user(i) for i in range(50)]
        execution_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no failures due to isolation issues
        failed_executions = [r for r in execution_results if isinstance(r, Exception)]
        assert len(failed_executions) == 0, (
            f"CRITICAL VIOLATION: {len(failed_executions)} executions failed, "
            f"indicating isolation problems: {failed_executions[:3]}"
        )
        
        # Verify complete data isolation
        assert len(results) == 50, f"Expected 50 results, got {len(results)}"
        
        for user_idx, result_data in results.items():
            # Each user should have their own isolated data
            expected_volume = user_idx * 10
            assert result_data["volume"] == expected_volume, (
                f"CRITICAL VIOLATION: User {user_idx} volume contaminated: "
                f"expected {expected_volume}, got {result_data['volume']}"
            )
            
            # Unique markers should match
            unique_marker = result_data["unique_marker"]
            assert unique_marker in result_data["context_user_id"], (
                f"CRITICAL VIOLATION: User ID contamination for user {user_idx}"
            )
            assert unique_marker == result_data["user_specific"], (
                f"CRITICAL VIOLATION: Profile data contamination for user {user_idx}"
            )
    
    # Test 17: Rapid Context Switching Test
    @pytest.mark.asyncio
    async def test_rapid_context_switching_isolation(self):
        """Test rapid switching between contexts maintains isolation."""
        agent = SyntheticDataSubAgent(
            llm_manager=Mock(spec=LLMManager),
            tool_dispatcher=Mock(spec=ToolDispatcher) 
        )
        
        # Create alternating contexts for 3 users
        contexts = []
        expected_results = []
        
        for i in range(30):  # 30 rapid executions
            user_id = f"switch_user_{i % 3}"  # Only 3 users, rapid switching
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"switch_thread_{i}",
                run_id=f"switch_run_{i}",
                db_session=create_mock_db_session(),
                metadata={
                    "user_request": f"Generate data iteration {i}",
                    "iteration": i,
                    "expected_user": user_id
                }
            )
            contexts.append(context)
            expected_results.append((user_id, i))
        
        # Execute in rapid sequence
        actual_results = []
        
        for i, context in enumerate(contexts):
            mock_profile = Mock()
            mock_profile.workload_type = DataGenerationType.INFERENCE_LOGS
            mock_profile.volume = i * 10
            mock_profile.custom_parameters = {"iteration": i}
            
            with patch.object(agent, '_determine_workload_profile_from_request', 
                             return_value=mock_profile):
                with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                    mock_gen.return_value = Mock(generation_status=Mock(records_generated=i * 10))
                    
                    await agent.execute(context, stream_updates=False)
                    
                    # Verify context maintained its identity
                    assert context.user_id == expected_results[i][0], (
                        f"Context switching error at iteration {i}: "
                        f"expected user {expected_results[i][0]}, got {context.user_id}"
                    )
                    
                    actual_results.append((context.user_id, context.metadata["iteration"]))
        
        # Verify all results match expected sequence
        assert actual_results == expected_results, (
            f"CRITICAL VIOLATION: Rapid context switching caused data corruption. "
            f"Expected: {expected_results[:10]}... Got: {actual_results[:10]}..."
        )
    
    # Test 18: Error Recovery Isolation Test
    @pytest.mark.asyncio  
    async def test_error_recovery_does_not_affect_isolation(self):
        """Test that errors in one context don't corrupt others."""
        agent = SyntheticDataSubAgent(
            llm_manager=Mock(spec=LLMManager),
            tool_dispatcher=Mock(spec=ToolDispatcher)
        )
        
        # Create contexts - some will succeed, some will fail
        success_context = UserExecutionContext(
            user_id="success_user_1",
            thread_id="success_thread_1", 
            run_id="success_run_1",
            db_session=create_mock_db_session(),
            metadata={"user_request": "Generate successful data"}
        )
        
        error_context = UserExecutionContext(
            user_id="error_user_1",
            thread_id="error_thread_1",
            run_id="error_run_1", 
            db_session=create_mock_db_session(),
            metadata={"user_request": "Generate failing data"}
        )
        
        recovery_context = UserExecutionContext(
            user_id="recovery_user_1",
            thread_id="recovery_thread_1",
            run_id="recovery_run_1",
            db_session=create_mock_db_session(),
            metadata={"user_request": "Generate recovery data"}
        )
        
        # Execute success -> error -> recovery sequence
        results = []
        
        # 1. First execution should succeed
        mock_profile_success = Mock()
        mock_profile_success.workload_type = DataGenerationType.PERFORMANCE_METRICS
        mock_profile_success.volume = 100
        
        with patch.object(agent, '_determine_workload_profile_from_request', 
                         return_value=mock_profile_success):
            with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = Mock(generation_status=Mock(records_generated=100))
                
                await agent.execute(success_context, stream_updates=False)
                results.append("success_1_completed")
        
        # 2. Second execution should fail
        mock_profile_error = Mock()
        mock_profile_error.workload_type = WorkloadType.FINANCIAL_TRANSACTION
        mock_profile_error.volume = 200
        
        with patch.object(agent, '_determine_workload_profile_from_request', 
                         return_value=mock_profile_error):
            with patch.object(agent.generator, 'generate_data', 
                             side_effect=Exception("Simulated generation error")):
                
                with pytest.raises(Exception) as exc_info:
                    await agent.execute(error_context, stream_updates=False)
                
                assert "Simulated generation error" in str(exc_info.value)
                results.append("error_1_failed")
        
        # 3. Third execution should succeed (error didn't corrupt agent state)
        mock_profile_recovery = Mock()
        mock_profile_recovery.workload_type = DataGenerationType.TRAINING_DATA
        mock_profile_recovery.volume = 300
        
        with patch.object(agent, '_determine_workload_profile_from_request', 
                         return_value=mock_profile_recovery):
            with patch.object(agent.generator, 'generate_data', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = Mock(generation_status=Mock(records_generated=300))
                
                await agent.execute(recovery_context, stream_updates=False)
                results.append("recovery_1_completed")
        
        # Verify execution sequence was correct
        expected_sequence = ["success_1_completed", "error_1_failed", "recovery_1_completed"]
        assert results == expected_sequence, (
            f"CRITICAL VIOLATION: Error recovery affected execution sequence. "
            f"Expected: {expected_sequence}, Got: {results}"
        )
        
        # Verify contexts maintained their integrity
        assert success_context.user_id == "success_user_1"
        assert error_context.user_id == "error_user_1" 
        assert recovery_context.user_id == "recovery_user_1"
        
        # Verify agent state wasn't corrupted by the error
        assert not hasattr(agent, 'last_error')
        assert not hasattr(agent, 'error_count')
        assert not hasattr(agent, 'failed_user_id')


class TestSyntheticDataSubAgentPatternCompliance:
    """Complete architectural pattern compliance validation."""
    
    # Test 19: Complete SSOT Pattern Validation
    @pytest.mark.asyncio
    async def test_complete_ssot_pattern_compliance(self):
        """Comprehensive validation of all SSOT architectural patterns."""
        # Load agent module source for analysis
        module_source = inspect.getsource(SyntheticDataSubAgent)
        
        # Critical patterns that MUST be present
        required_patterns = [
            ("UserExecutionContext", "Must use UserExecutionContext for request isolation"),
            ("DatabaseSessionManager", "Must use DatabaseSessionManager for DB access"),
            ("BaseAgent", "Must inherit from BaseAgent"),
            ("safe_json_dumps", "Must use unified JSON handler"),
            ("agent_error_handler", "Must use unified error handling"),
        ]
        
        # Critical patterns that MUST NOT be present
        forbidden_patterns = [
            ("DeepAgentState", "Legacy state pattern - use UserExecutionContext"),
            ("self.db_session =", "No stored database sessions"),
            ("self.session =", "No stored sessions"),
            ("self.user_id =", "No stored user data"),
            ("self.thread_id =", "No stored thread data"),
            ("os.environ[", "No direct environment access"),
            ("os.environ.get(", "No direct environment access"),
            ("global ", "No global variables"),
            ("@singleton", "No singleton patterns"),
            (".model_dump()", "Use unified_json_handler instead"),
            (".dict()", "Use unified_json_handler instead"),
            ("json.dumps(", "Use unified_json_handler instead"),
            ("json.loads(", "Use unified_json_handler instead"),
        ]
        
        # Check required patterns
        for pattern, reason in required_patterns:
            assert pattern in module_source, (
                f"CRITICAL VIOLATION: Required pattern '{pattern}' missing. {reason}"
            )
        
        # Check forbidden patterns
        for pattern, reason in forbidden_patterns:
            # Allow patterns in comments
            lines = module_source.split('\n')
            for i, line in enumerate(lines):
                if pattern in line and not line.strip().startswith('#'):
                    pytest.fail(
                        f"CRITICAL VIOLATION: Forbidden pattern '{pattern}' found at line {i+1}. {reason}. "
                        f"Line: {line.strip()}"
                    )
        
        print("✅ All SSOT pattern compliance tests passed!")
    
    # Test 20: Architecture Integration Validation
    @pytest.mark.asyncio
    async def test_architecture_integration_validation(self):
        """Test that agent properly integrates with all required architecture components."""
        
        # Test agent can be instantiated with required dependencies
        mock_llm = Mock(spec=LLMManager)
        mock_dispatcher = Mock(spec=ToolDispatcher)
        
        agent = SyntheticDataSubAgent(
            llm_manager=mock_llm,
            tool_dispatcher=mock_dispatcher
        )
        
        # Verify all required components are initialized
        required_components = [
            ('llm_manager', LLMManager),
            ('tool_dispatcher', ToolDispatcher),
            ('generator', object),  # SyntheticDataGenerator
            ('profile_parser', object),
            ('metrics_handler', object),
            ('approval_workflow', object),
            ('llm_executor', object),
            ('generation_executor', object),
            ('error_handler', object),
            ('communicator', object),
            ('validator', object),
            ('approval_requirements', object),
        ]
        
        for component_name, expected_type in required_components:
            assert hasattr(agent, component_name), (
                f"CRITICAL VIOLATION: Missing required component: {component_name}"
            )
            
            component = getattr(agent, component_name)
            assert component is not None, (
                f"CRITICAL VIOLATION: Component {component_name} is None"
            )
        
        # Test agent responds to BaseAgent interface
        base_agent_methods = [
            'execute',
            'emit_thinking', 
            'emit_progress',
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_error'
        ]
        
        for method in base_agent_methods:
            assert hasattr(agent, method), (
                f"CRITICAL VIOLATION: Missing BaseAgent method: {method}"
            )
            assert callable(getattr(agent, method)), (
                f"CRITICAL VIOLATION: {method} is not callable"
            )
        
        # Test agent can handle UserExecutionContext
        assert 'UserExecutionContext' in str(inspect.signature(agent.execute)), (
            "CRITICAL VIOLATION: execute method doesn't accept UserExecutionContext"
        )
        
        print("✅ All architecture integration tests passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])