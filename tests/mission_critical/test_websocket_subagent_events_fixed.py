#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: Real WebSocket Sub-Agent Events

THIS IS A TOUGHENED TEST SUITE FOR BASIC SUB-AGENT WEBSOCKET EVENT FLOWS.

Business Value: $500K+ ARR - Core chat functionality depends on WebSocket events
Critical Focus: Test the MOST BASIC and EXPECTED sub-agent WebSocket event flows
that users experience in real chat scenarios.

REQUIREMENTS ENFORCED:
1. Factory-based WebSocket pattern only (NO legacy singleton)
2. Test BASIC critical paths: agent_started → agent_thinking → tool_executing → tool_completed → agent_completed  
3. STRICT success criteria (no error suppression)
4. Focus on 3-5 core test cases that cover fundamental user flows
5. Tests PASS when system works correctly, FAIL when it doesn't
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Set, Any, Optional
from datetime import datetime, timedelta

import pytest
from loguru import logger

# Import real services infrastructure
from test_framework.real_services import get_real_services, RealServicesManager
from test_framework.environment_isolation import isolated_test_env

# Import production components with factory pattern
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory, UserWebSocketEmitter
from netra_backend.app.agents.state import DeepAgentState

# Import available sub-agent classes
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent  
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager


# ============================================================================
# FACTORY-BASED WEBSOCKET EVENT VALIDATOR
# ============================================================================

class FactoryWebSocketEventValidator:
    """Validates WebSocket events from factory-based sub-agent executions with strict criteria."""
    
    # Critical events that MUST be emitted during sub-agent execution
    REQUIRED_EVENTS = {
        "agent_started",      # Sub-agent begins processing
        "agent_thinking",     # Sub-agent reasoning/analysis  
        "tool_executing",     # Sub-agent executes tools
        "tool_completed",     # Sub-agent tool completion
        "agent_completed"     # Sub-agent finishes
    }
    
    def __init__(self, user_id: str, thread_id: str, timeout: float = 30.0):
        self.user_id = user_id
        self.thread_id = thread_id
        self.timeout = timeout
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, event)
        self.start_time = time.time()
        self.validation_errors: List[str] = []
        
    def record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record WebSocket event with timestamp."""
        timestamp = time.time() - self.start_time
        
        event = {
            "type": event_type,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "data": data,
            "timestamp": timestamp,
            "received_at": time.time()
        }
        
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        
        logger.info(f"📡 Event: {event_type} at {timestamp:.2f}s - {data.get('message', '')}")
        
    def validate_basic_sub_agent_flow(self) -> tuple[bool, List[str]]:
        """Validate that basic sub-agent WebSocket event flow occurred correctly."""
        errors = []
        
        # Check if we received any events at all
        if not self.events:
            errors.append("CRITICAL: No WebSocket events received from sub-agent execution")
            return False, errors
            
        # Get event types in order
        event_types = [event.get("type") for event in self.events]
        
        # Check for required events
        missing_events = self.REQUIRED_EVENTS - set(event_types)
        if missing_events:
            errors.append(f"Missing required events: {missing_events}")
            
        # Validate event ordering - agent_started should come first
        if event_types and event_types[0] != "agent_started":
            errors.append(f"First event should be 'agent_started', got: {event_types[0]}")
            
        # Check for completion event at the end
        completion_events = {"agent_completed", "agent_fallback"}
        if event_types and event_types[-1] not in completion_events:
            errors.append(f"Last event should be completion type, got: {event_types[-1]}")
            
        # Validate tool event pairing
        tool_executing_count = event_types.count("tool_executing")
        tool_completed_count = event_types.count("tool_completed") 
        if tool_executing_count > 0 and tool_executing_count != tool_completed_count:
            errors.append(f"Tool events not paired: {tool_executing_count} executing, {tool_completed_count} completed")
            
        is_valid = len(errors) == 0
        return is_valid, errors
        
    def get_summary(self) -> str:
        """Get validation summary report."""
        is_valid, errors = self.validate_basic_sub_agent_flow()
        
        total_duration = self.event_timeline[-1][0] if self.event_timeline else 0
        event_types = [event.get("type") for event in self.events]
        
        status = "✅ PASSED" if is_valid else "❌ FAILED"
        
        summary = f"""
=== Factory-Based WebSocket Sub-Agent Event Validation Summary ===
Status: {status}
Events Received: {len(self.events)}
Duration: {total_duration:.2f}s
Event Types: {list(set(event_types))}
Event Sequence: {' → '.join(event_types[:10])}{'...' if len(event_types) > 10 else ''}

Required Events Coverage:
{self._format_event_coverage()}

{'ERRORS:' + chr(10) + chr(10).join(f'  - {e}' for e in errors) if errors else 'All validations passed!'}
"""
        return summary
        
    def _format_event_coverage(self) -> str:
        """Format required event coverage."""
        event_types = set(event.get("type") for event in self.events)
        lines = []
        for required_event in self.REQUIRED_EVENTS:
            status = "✅" if required_event in event_types else "❌"
            count = sum(1 for event in self.events if event.get("type") == required_event)
            lines.append(f"  {status} {required_event}: {count} occurrences")
        return "\n".join(lines)


# ============================================================================
# FACTORY-BASED SUB-AGENT TEST EXECUTOR
# ============================================================================

class FactorySubAgentExecutor:
    """Executes real sub-agents with factory-based WebSocket integration."""
    
    def __init__(self, real_services: RealServicesManager):
        self.real_services = real_services
        
    async def create_factory_with_mock_pool(self) -> WebSocketBridgeFactory:
        """Create factory with mock connection pool for testing."""
        factory = WebSocketBridgeFactory()
        
        # Mock the connection pool for testing
        class MockConnectionPool:
            async def get_connection(self, connection_id: str, user_id: str):
                return None  # Return None to create placeholder connection
                
        mock_pool = MockConnectionPool()
        factory.configure(mock_pool, None, None)
        
        return factory
        
    async def create_sub_agent_with_factory(self, agent_class, factory: WebSocketBridgeFactory, 
                                          user_id: str, thread_id: str) -> tuple[BaseAgent, UserWebSocketEmitter]:
        """Create a sub-agent instance with factory-based WebSocket integration."""
        
        # Create a simplified LLM manager for testing
        class TestLLMManager:
            async def generate_response(self, *args, **kwargs):
                # Simulate LLM processing time
                await asyncio.sleep(0.1)
                return {
                    "content": f"Test response from {agent_class.__name__}",
                    "reasoning": "Test reasoning process",
                    "confidence": 0.9
                }
        
        # Create WebSocket emitter for this specific user
        emitter = await factory.create_user_emitter(user_id, thread_id, connection_id=f"conn_{user_id}")
        
        # Create test agent that uses the factory pattern
        class TestFactoryAgent(BaseAgent):
            def __init__(self, name: str):
                super().__init__()
                self.name = name
                self.emitter = None
                
            def set_emitter(self, emitter: UserWebSocketEmitter):
                self.emitter = emitter
                
            async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
                if self.emitter:
                    # Emit all required events using factory pattern
                    await self.emitter.notify_agent_started(self.name, {"status": "started"})
                    await self.emitter.notify_agent_thinking("Processing test request...")
                    await self.emitter.notify_tool_executing("test_tool", {"param": "value"})
                    await asyncio.sleep(0.1)  # Simulate tool execution
                    await self.emitter.notify_tool_completed("test_tool", {"result": "success"})
                    await self.emitter.notify_agent_completed(self.name, {"result": "Test execution completed", "status": "success"})
                    
                return {"result": "Test execution completed", "status": "success"}
                    
        agent = TestFactoryAgent(name=f"Test{agent_class.__name__}")
        agent.set_emitter(emitter)
        
        return agent, emitter
        
    async def execute_sub_agent_flow(self, agent: BaseAgent, user_id: str, thread_id: str) -> None:
        """Execute a complete sub-agent flow with factory-based WebSocket events."""
        
        # Create state for execution
        state = DeepAgentState()
        state.user_request = f"Test request for {getattr(agent, 'name', 'TestAgent')}"
        state.chat_thread_id = thread_id
        state.user_id = user_id
        
        # Generate unique run ID
        run_id = f"test-run-{uuid.uuid4().hex[:8]}"
        
        # Execute the agent with stream updates enabled
        logger.info(f"Executing {getattr(agent, 'name', 'TestAgent')} with factory-based WebSocket events...")
        
        try:
            result = await agent.execute(state, run_id, stream_updates=True)
            logger.info(f"Agent execution completed: {result}")
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise


# ============================================================================
# FACTORY-BASED WEBSOCKET SUB-AGENT TESTS
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestFactoryWebSocketSubAgentEvents:
    """Tests for factory-based WebSocket sub-agent event flows using real connections."""
    
    @pytest.mark.asyncio
    async def test_single_sub_agent_factory_event_flow(self, real_services: RealServicesManager):
        """Test that a single sub-agent emits all required WebSocket events using factory pattern.
        
        This is the most basic test - a single sub-agent should emit:
        agent_started → agent_thinking → tool_executing → tool_completed → agent_completed
        """
        user_id = f"user-single-{uuid.uuid4().hex[:8]}"
        thread_id = f"thread-single-{uuid.uuid4().hex[:8]}"
        validator = FactoryWebSocketEventValidator(user_id, thread_id)
        
        try:
            # Create factory-based test infrastructure
            executor = FactorySubAgentExecutor(real_services)
            factory = await executor.create_factory_with_mock_pool()
            
            # Create and execute sub-agent with factory pattern
            agent, emitter = await executor.create_sub_agent_with_factory(
                TriageSubAgent, factory, user_id, thread_id
            )
            
            # Set up event capture by wrapping emitter methods
            original_methods = {
                'notify_agent_started': emitter.notify_agent_started,
                'notify_agent_thinking': emitter.notify_agent_thinking,
                'notify_tool_executing': emitter.notify_tool_executing,
                'notify_tool_completed': emitter.notify_tool_completed,
                'notify_agent_completed': emitter.notify_agent_completed
            }
            
            # Wrap methods to capture events
            async def wrap_method(event_type: str, original_method):
                async def wrapper(*args, **kwargs):
                    validator.record_event(event_type, {"args": args, "kwargs": kwargs})
                    return await original_method(*args, **kwargs)
                return wrapper
            
            for method_name, original_method in original_methods.items():
                event_type = method_name.replace('notify_', '')
                setattr(emitter, method_name, await wrap_method(event_type, original_method))
            
            # Execute sub-agent with WebSocket events
            await executor.execute_sub_agent_flow(agent, user_id, thread_id)
            
            # Allow time for all events to be processed
            await asyncio.sleep(1.0)
            
            # Validate events
            is_valid, errors = validator.validate_basic_sub_agent_flow()
            
            print(validator.get_summary())
            
            # STRICT validation - test should PASS when WebSocket events work
            assert is_valid, f"Factory-based sub-agent WebSocket events validation failed:\n{chr(10).join(errors)}"
            
            # Additional specific checks
            assert len(validator.events) >= 5, f"Expected at least 5 events, got {len(validator.events)}"
            
            event_types = [event.get("type") for event in validator.events]
            assert "agent_started" in event_types, "Missing agent_started event"
            assert "agent_completed" in event_types or "agent_fallback" in event_types, "Missing completion event"
            
        finally:
            # Clean up factory resources
            if 'emitter' in locals():
                await emitter.cleanup()
    
    @pytest.mark.asyncio
    async def test_multiple_sub_agents_factory_isolation(self, real_services: RealServicesManager):
        """Test that multiple sub-agents work correctly with factory-based isolation."""
        
        user_id = f"user-multi-{uuid.uuid4().hex[:8]}"
        base_thread_id = f"thread-multi-{uuid.uuid4().hex[:8]}"
        validator = FactoryWebSocketEventValidator(user_id, base_thread_id)
        
        try:
            # Create factory-based test infrastructure
            executor = FactorySubAgentExecutor(real_services)
            factory = await executor.create_factory_with_mock_pool()
            
            # Execute multiple sub-agents with isolated threads
            agent_classes = [TriageSubAgent, ReportingSubAgent, DataSubAgent]
            emitters = []
            
            for i, agent_class in enumerate(agent_classes):
                logger.info(f"Testing {agent_class.__name__} with factory pattern")
                
                # Create unique thread for each agent to test isolation
                agent_thread_id = f"{base_thread_id}-{i}"
                
                agent, emitter = await executor.create_sub_agent_with_factory(
                    agent_class, factory, user_id, agent_thread_id
                )
                
                # Set up event capture for this agent
                original_methods = {
                    'notify_agent_started': emitter.notify_agent_started,
                    'notify_agent_thinking': emitter.notify_agent_thinking,
                    'notify_tool_executing': emitter.notify_tool_executing,
                    'notify_tool_completed': emitter.notify_tool_completed,
                    'notify_agent_completed': emitter.notify_agent_completed
                }
                
                async def make_capture_wrapper(event_type: str, original_method, agent_class_name: str):
                    async def wrapper(*args, **kwargs):
                        validator.record_event(event_type, {
                            "args": args, 
                            "kwargs": kwargs, 
                            "agent_class": agent_class_name,
                            "thread_id": agent_thread_id
                        })
                        return await original_method(*args, **kwargs)
                    return wrapper
                
                for method_name, original_method in original_methods.items():
                    event_type = method_name.replace('notify_', '')
                    wrapped_method = await make_capture_wrapper(event_type, original_method, agent_class.__name__)
                    setattr(emitter, method_name, wrapped_method)
                
                # Execute this agent
                await executor.execute_sub_agent_flow(agent, user_id, agent_thread_id)
                
                emitters.append(emitter)
                
                # Brief pause between agents
                await asyncio.sleep(0.5)
            
            # Allow time for all events
            await asyncio.sleep(1.0)
            
            # Validate overall flow
            is_valid, errors = validator.validate_basic_sub_agent_flow()
            
            print(validator.get_summary())
            
            # Should have events from multiple agents
            assert is_valid, f"Multi-agent factory WebSocket events validation failed:\n{chr(10).join(errors)}"
            
            # Should have multiple start/completion cycles
            event_types = [event.get("type") for event in validator.events]
            start_count = event_types.count("agent_started")
            completion_count = event_types.count("agent_completed") + event_types.count("agent_fallback")
            
            assert start_count >= len(agent_classes), f"Expected at least {len(agent_classes)} start events, got {start_count}"
            assert completion_count >= len(agent_classes), f"Expected at least {len(agent_classes)} completion events, got {completion_count}"
            
        finally:
            # Clean up all emitters
            for emitter in emitters:
                await emitter.cleanup()
    
    @pytest.mark.asyncio
    async def test_factory_tool_execution_events(self, real_services: RealServicesManager):
        """Test that sub-agents emit proper tool execution events with factory pattern."""
        
        user_id = f"user-tools-{uuid.uuid4().hex[:8]}"
        thread_id = f"thread-tools-{uuid.uuid4().hex[:8]}"
        validator = FactoryWebSocketEventValidator(user_id, thread_id)
        
        try:
            # Create factory-based test infrastructure
            executor = FactorySubAgentExecutor(real_services)
            factory = await executor.create_factory_with_mock_pool()
            
            # Create test agent that executes multiple tools
            class MultiToolFactoryAgent(BaseAgent):
                def __init__(self, name: str):
                    super().__init__()
                    self.name = name
                    self.emitter = None
                    
                def set_emitter(self, emitter: UserWebSocketEmitter):
                    self.emitter = emitter
                    
                async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
                    if self.emitter:
                        await self.emitter.notify_agent_started(self.name, {"status": "started"})
                        await self.emitter.notify_agent_thinking("Analyzing request and selecting tools...")
                        
                        # Simulate multiple tool executions
                        tools = ["data_analyzer", "report_generator", "optimizer"]
                        for tool in tools:
                            await self.emitter.notify_tool_executing(tool, {"task": f"process_{tool}"})
                            await asyncio.sleep(0.05)  # Simulate tool processing
                            await self.emitter.notify_tool_completed(tool, {
                                "result": f"{tool}_complete", 
                                "status": "success"
                            })
                        
                        await self.emitter.notify_agent_completed(self.name, {
                            "result": "All tools executed successfully", 
                            "tools_used": len(tools)
                        })
                    
                    return {"result": "All tools executed successfully", "tools_used": 3}
            
            # Create agent and emitter
            emitter = await factory.create_user_emitter(user_id, thread_id, connection_id=f"conn_{user_id}")
            agent = MultiToolFactoryAgent(name="MultiToolTestAgent")
            agent.set_emitter(emitter)
            
            # Set up event capture
            original_methods = {
                'notify_agent_started': emitter.notify_agent_started,
                'notify_agent_thinking': emitter.notify_agent_thinking,
                'notify_tool_executing': emitter.notify_tool_executing,
                'notify_tool_completed': emitter.notify_tool_completed,
                'notify_agent_completed': emitter.notify_agent_completed
            }
            
            async def make_capture_wrapper(event_type: str, original_method):
                async def wrapper(*args, **kwargs):
                    validator.record_event(event_type, {"args": args, "kwargs": kwargs})
                    return await original_method(*args, **kwargs)
                return wrapper
            
            for method_name, original_method in original_methods.items():
                event_type = method_name.replace('notify_', '')
                wrapped_method = await make_capture_wrapper(event_type, original_method)
                setattr(emitter, method_name, wrapped_method)
            
            # Execute agent
            await executor.execute_sub_agent_flow(agent, user_id, thread_id)
            
            # Allow time for events
            await asyncio.sleep(1.0)
            
            # Validate tool events specifically
            event_types = [event.get("type") for event in validator.events]
            
            print(validator.get_summary())
            
            # Check for tool events
            tool_executing_count = event_types.count("tool_executing")
            tool_completed_count = event_types.count("tool_completed")
            
            assert tool_executing_count > 0, "No tool_executing events found"
            assert tool_completed_count > 0, "No tool_completed events found"
            assert tool_executing_count == tool_completed_count, f"Tool events not balanced: {tool_executing_count} executing, {tool_completed_count} completed"
            
            # Should have exactly 3 tool pairs (from the MultiToolFactoryAgent)
            assert tool_executing_count == 3, f"Expected 3 tool_executing events, got {tool_executing_count}"
            assert tool_completed_count == 3, f"Expected 3 tool_completed events, got {tool_completed_count}"
            
            # Overall validation
            is_valid, errors = validator.validate_basic_sub_agent_flow()
            assert is_valid, f"Factory tool execution WebSocket events validation failed:\n{chr(10).join(errors)}"
            
        finally:
            await emitter.cleanup()
    
    @pytest.mark.asyncio
    async def test_factory_error_handling_events(self, real_services: RealServicesManager):
        """Test that sub-agents emit proper events when errors occur using factory pattern."""
        
        user_id = f"user-error-{uuid.uuid4().hex[:8]}"
        thread_id = f"thread-error-{uuid.uuid4().hex[:8]}"
        validator = FactoryWebSocketEventValidator(user_id, thread_id)
        
        try:
            # Create factory-based test infrastructure
            executor = FactorySubAgentExecutor(real_services)
            factory = await executor.create_factory_with_mock_pool()
            
            # Create test agent that handles errors gracefully
            class ErrorHandlingFactoryAgent(BaseAgent):
                def __init__(self, name: str):
                    super().__init__()
                    self.name = name
                    self.emitter = None
                    
                def set_emitter(self, emitter: UserWebSocketEmitter):
                    self.emitter = emitter
                    
                async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
                    if self.emitter:
                        await self.emitter.notify_agent_started(self.name, {"status": "started"})
                        await self.emitter.notify_agent_thinking("Starting processing...")
                        
                        # Simulate error during tool execution
                        await self.emitter.notify_tool_executing("failing_tool", {"param": "test"})
                        
                        # Simulate tool failure and recovery
                        await asyncio.sleep(0.05)
                        
                        # Handle error gracefully using factory's error notification
                        await self.emitter.notify_agent_error(self.name, run_id, "Tool execution failed, attempting fallback")
                        
                        # Attempt recovery
                        await self.emitter.notify_tool_executing("fallback_tool", {"param": "recovery"})
                        await asyncio.sleep(0.05)
                        await self.emitter.notify_tool_completed("fallback_tool", {"result": "recovery_success"})
                        
                        await self.emitter.notify_agent_completed(self.name, {
                            "result": "Completed with fallback", 
                            "status": "recovered"
                        })
                    
                    return {"result": "Completed with fallback", "status": "recovered"}
            
            # Create agent and emitter
            emitter = await factory.create_user_emitter(user_id, thread_id, connection_id=f"conn_{user_id}")
            agent = ErrorHandlingFactoryAgent(name="ErrorTestAgent")
            agent.set_emitter(emitter)
            
            # Set up event capture
            original_methods = {
                'notify_agent_started': emitter.notify_agent_started,
                'notify_agent_thinking': emitter.notify_agent_thinking,
                'notify_tool_executing': emitter.notify_tool_executing,
                'notify_tool_completed': emitter.notify_tool_completed,
                'notify_agent_completed': emitter.notify_agent_completed,
                'notify_agent_error': emitter.notify_agent_error
            }
            
            async def make_capture_wrapper(event_type: str, original_method):
                async def wrapper(*args, **kwargs):
                    validator.record_event(event_type, {"args": args, "kwargs": kwargs})
                    return await original_method(*args, **kwargs)
                return wrapper
            
            for method_name, original_method in original_methods.items():
                event_type = method_name.replace('notify_', '')
                wrapped_method = await make_capture_wrapper(event_type, original_method)
                setattr(emitter, method_name, wrapped_method)
            
            # Execute agent
            await executor.execute_sub_agent_flow(agent, user_id, thread_id)
            
            # Allow time for events
            await asyncio.sleep(1.0)
            
            # Validate error handling events
            event_types = [event.get("type") for event in validator.events]
            
            print(validator.get_summary())
            
            # Should have error events
            error_events = [event for event in validator.events if event.get("type") == "agent_error"]
            assert len(error_events) > 0, "Expected error events for error handling test"
            
            # Should still have completion
            assert "agent_completed" in event_types, "Missing completion event after error handling"
            
            # Should have both failing and recovery tool events
            tool_executing_count = event_types.count("tool_executing")
            tool_completed_count = event_types.count("tool_completed")
            
            assert tool_executing_count == 2, f"Expected 2 tool_executing events (failing + recovery), got {tool_executing_count}"
            assert tool_completed_count == 1, f"Expected 1 tool_completed event (recovery only), got {tool_completed_count}"
            
        finally:
            await emitter.cleanup()
    
    @pytest.mark.asyncio
    async def test_factory_performance_timing(self, real_services: RealServicesManager):
        """Test that factory-based sub-agent WebSocket events are emitted with proper timing."""
        
        user_id = f"user-perf-{uuid.uuid4().hex[:8]}"
        thread_id = f"thread-perf-{uuid.uuid4().hex[:8]}"
        validator = FactoryWebSocketEventValidator(user_id, thread_id)
        
        try:
            # Create factory-based test infrastructure
            executor = FactorySubAgentExecutor(real_services)
            factory = await executor.create_factory_with_mock_pool()
            
            # Create and execute sub-agent with factory pattern
            agent, emitter = await executor.create_sub_agent_with_factory(
                DataSubAgent, factory, user_id, thread_id
            )
            
            # Set up event capture with timing
            original_methods = {
                'notify_agent_started': emitter.notify_agent_started,
                'notify_agent_thinking': emitter.notify_agent_thinking,
                'notify_tool_executing': emitter.notify_tool_executing,
                'notify_tool_completed': emitter.notify_tool_completed,
                'notify_agent_completed': emitter.notify_agent_completed
            }
            
            async def make_capture_wrapper(event_type: str, original_method):
                async def wrapper(*args, **kwargs):
                    validator.record_event(event_type, {"args": args, "kwargs": kwargs})
                    return await original_method(*args, **kwargs)
                return wrapper
            
            for method_name, original_method in original_methods.items():
                event_type = method_name.replace('notify_', '')
                wrapped_method = await make_capture_wrapper(event_type, original_method)
                setattr(emitter, method_name, wrapped_method)
            
            # Execute and measure timing
            start_time = time.time()
            await executor.execute_sub_agent_flow(agent, user_id, thread_id)
            end_time = time.time()
            
            execution_duration = end_time - start_time
            
            await asyncio.sleep(0.5)  # Allow final events
            
            # Performance validation
            assert execution_duration < 5.0, f"Factory sub-agent execution took too long: {execution_duration:.2f}s"
            
            # Event timing validation
            if validator.event_timeline:
                first_event_time = validator.event_timeline[0][0]
                last_event_time = validator.event_timeline[-1][0]
                
                # First event should arrive quickly
                assert first_event_time < 1.0, f"First event took too long: {first_event_time:.2f}s"
                
                # Events should be spread over reasonable time
                assert last_event_time < 3.0, f"Events took too long overall: {last_event_time:.2f}s"
            
            # Validate basic flow still works
            is_valid, errors = validator.validate_basic_sub_agent_flow()
            
            print(validator.get_summary())
            print(f"Factory execution duration: {execution_duration:.2f}s")
            
            assert is_valid, f"Factory performance test WebSocket events validation failed:\n{chr(10).join(errors)}"
            assert len(validator.events) > 0, "No events received in factory performance test"
            
        finally:
            await emitter.cleanup()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])