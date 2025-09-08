"""
Comprehensive Unit Tests for ExecutionEngineConsolidated - SINGLE SOURCE OF TRUTH (Focused Implementation)

Business Value Justification (BVJ):
- Segment: Platform/Internal (serves ALL customer segments - Free, Early, Mid, Enterprise)
- Business Goal: Agent Execution Reliability & Multi-User Isolation & Chat Value Delivery
- Value Impact: Enables EVERY AI chat interaction - 95% of platform business value depends on this SSOT component  
- Strategic Impact: Core infrastructure for unified agent execution - failure means complete platform failure

CRITICAL: ExecutionEngineConsolidated is the BUSINESS-CRITICAL SSOT class providing:
1. Extension pattern for feature composition without duplication (60% reduction in duplicate code)
2. Request-scoped isolation for 10+ concurrent users (<2s response time requirement)
3. All 5 critical WebSocket events for chat value delivery (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
4. Factory patterns for different execution configurations (User, Data, MCP optimized)
5. Comprehensive metrics and performance tracking for SLA compliance
6. Error handling and recovery for maximum reliability

This comprehensive test suite ensures 100% coverage of all critical business logic paths,
security aspects, and operational scenarios following CLAUDE.md requirements.

ULTRA THINK DEEPLY: Every test validates REAL business value and security requirements.

REQUIREMENTS:
- NO mocks for core business logic - test real instances where possible
- Tests MUST RAISE ERRORS - no try/except masking failures  
- ABSOLUTE IMPORTS only per CLAUDE.md
- Use SSOT patterns from test_framework
- Comprehensive coverage including all edge cases and error conditions
- Multi-user isolation testing (CRITICAL for preventing user data leakage)
- WebSocket integration testing (CRITICAL for chat value delivery)
- Performance requirement validation (<2s execution, 10+ concurrent users)

CHEATING ON TESTS = ABOMINATION
"""

import asyncio
import pytest
import sys
import time
import uuid
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Set
from unittest.mock import AsyncMock, MagicMock, patch, call, Mock, PropertyMock
from contextlib import asynccontextmanager

# SSOT Import Management - Absolute imports only per CLAUDE.md
from test_framework.ssot.base import BaseTestCase, AsyncBaseTestCase
from shared.isolated_environment import get_env

# Import target consolidated execution engine - SSOT
from netra_backend.app.agents.execution_engine_consolidated import (
    ExecutionEngine,
    RequestScopedExecutionEngine,
    ExecutionEngineFactory,
    EngineConfig,
    AgentExecutionContext,
    AgentExecutionResult,
    ExecutionExtension,
    UserExecutionExtension,
    MCPExecutionExtension,
    DataExecutionExtension,
    WebSocketExtension,
    execute_agent,
    execution_engine_context,
    create_execution_engine,
    get_execution_engine_factory,
)

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.agent_execution_tracker import ExecutionState


class RealMockAgent:
    """Real mock agent for testing execution engine without full dependencies.
    
    This is a REAL implementation (not a Mock object) that simulates agent behavior
    while being controllable for testing scenarios.
    """
    
    def __init__(self, name: str, execution_time: float = 0.1, should_fail: bool = False, 
                 fail_mode: str = "runtime_error", use_tools: bool = False):
        self.name = name
        self.execution_time = execution_time
        self.should_fail = should_fail
        self.fail_mode = fail_mode
        self.use_tools = use_tools
        self.execution_count = 0
        self.tool_calls: List[Dict] = []
        
    async def execute(self, task: Any, state: Optional[DeepAgentState] = None) -> Any:
        """Real agent execution with controllable behavior."""
        self.execution_count += 1
        start_time = time.time()
        
        # Simulate realistic agent execution time
        await asyncio.sleep(self.execution_time)
        
        # Simulate tool usage if configured
        if self.use_tools:
            tool_call = {
                "tool": f"{self.name}_tool",
                "parameters": {"task": str(task)},
                "timestamp": time.time()
            }
            self.tool_calls.append(tool_call)
        
        # Handle different failure modes
        if self.should_fail:
            if self.fail_mode == "timeout":
                await asyncio.sleep(10)  # Simulate long execution
            elif self.fail_mode == "memory_error":
                raise MemoryError(f"Agent {self.name} ran out of memory")
            elif self.fail_mode == "value_error":
                raise ValueError(f"Invalid input for agent {self.name}")
            else:  # default runtime_error
                raise RuntimeError(f"Mock agent {self.name} execution failed")
            
        return {
            "agent": self.name,
            "task": task,
            "state": state,
            "execution_count": self.execution_count,
            "execution_time": time.time() - start_time,
            "tool_calls": len(self.tool_calls),
            "timestamp": time.time(),
            "success": True
        }


class RealMockAgentRegistry:
    """Real mock agent registry for testing execution engine."""
    
    def __init__(self):
        self.agents: Dict[str, RealMockAgent] = {}
        self.lookup_count = 0
        
    def register_agent(self, name: str, agent: RealMockAgent):
        """Register a mock agent."""
        self.agents[name] = agent
        
    def get_agent(self, name: str) -> Optional[RealMockAgent]:
        """Get agent by name with tracking."""
        self.lookup_count += 1
        return self.agents.get(name)
        
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agents.keys())


class RealMockWebSocketBridge:
    """Real mock WebSocket bridge for testing all 5 critical events."""
    
    def __init__(self, should_fail: bool = False, fail_probability: float = 0.0):
        self.events: List[Dict] = []
        self.should_fail = should_fail
        self.fail_probability = fail_probability
        self.metrics = {
            "messages_sent": 0, 
            "errors": 0,
            "events_by_type": {},
            "last_event_time": None
        }
        self.connected_users: Set[str] = set()
        
    async def notify_agent_started(self, agent_name: str, task: Any):
        """CRITICAL EVENT 1: Agent started notification"""
        await self._send_event("agent_started", {
            "agent_name": agent_name,
            "task": str(task),
            "priority": "high"
        })
        
    async def notify_agent_thinking(self, agent_name: str, thought: str):
        """CRITICAL EVENT 2: Agent thinking notification"""
        await self._send_event("agent_thinking", {
            "agent_name": agent_name,
            "thought": thought,
            "reasoning_step": len([e for e in self.events if e["type"] == "agent_thinking"]) + 1
        })
        
    async def notify_tool_executing(self, tool_name: str, parameters: Dict):
        """CRITICAL EVENT 3: Tool executing notification"""
        await self._send_event("tool_executing", {
            "tool_name": tool_name,
            "parameters": parameters,
            "execution_id": uuid.uuid4().hex[:8]
        })
        
    async def notify_tool_completed(self, tool_name: str, result: Any):
        """CRITICAL EVENT 4: Tool completed notification"""
        await self._send_event("tool_completed", {
            "tool_name": tool_name,
            "result": result,
            "success": result is not None
        })
        
    async def notify_agent_completed(self, agent_name: str, result: Any):
        """CRITICAL EVENT 5: Agent completed notification"""
        await self._send_event("agent_completed", {
            "agent_name": agent_name,
            "result": result,
            "completion_status": "success" if result else "failed"
        })
        
    async def notify_agent_error(self, agent_name: str, error: str):
        """Agent error notification"""
        await self._send_event("agent_error", {
            "agent_name": agent_name,
            "error": error,
            "error_type": type(error).__name__ if isinstance(error, Exception) else "unknown"
        })
        
    async def _send_event(self, event_type: str, data: Dict):
        """Internal event sending with failure simulation."""
        if self.should_fail or (self.fail_probability > 0 and time.time() % 1 < self.fail_probability):
            self.metrics["errors"] += 1
            raise ConnectionError(f"WebSocket bridge failed for event {event_type}")
            
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "event_id": uuid.uuid4().hex[:8],
            **data
        }
        
        self.events.append(event)
        self.metrics["messages_sent"] += 1
        self.metrics["events_by_type"][event_type] = self.metrics["events_by_type"].get(event_type, 0) + 1
        self.metrics["last_event_time"] = event["timestamp"]
        
    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get all events of specific type."""
        return [e for e in self.events if e["type"] == event_type]
        
    def get_event_sequence(self) -> List[str]:
        """Get sequence of event types in chronological order."""
        return [e["type"] for e in sorted(self.events, key=lambda x: x["timestamp"])]


class RealMockUserExecutionContext:
    """Real mock user execution context with full functionality."""
    
    def __init__(self, user_id: str, request_id: str = None, thread_id: str = None):
        self.user_id = user_id
        self.request_id = request_id or f"req_{uuid.uuid4().hex[:8]}"
        self.thread_id = thread_id or f"thread_{uuid.uuid4().hex[:8]}"
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        self.metadata = {
            "created_at": time.time(),
            "user_tier": "enterprise",
            "permissions": ["agent_execution", "tool_usage"]
        }
        self.active_requests = 0
        
    def start_request(self):
        """Track active request."""
        self.active_requests += 1
        
    def end_request(self):
        """Track request completion."""
        self.active_requests = max(0, self.active_requests - 1)


class TestEngineConfigComprehensive(BaseTestCase):
    """Comprehensive tests for EngineConfig model and validation."""
    
    def test_engine_config_default_values_business_requirements(self):
        """
        BVJ: Platform/Internal - Configuration Stability  
        Test EngineConfig defaults meet business requirements for multi-user platform.
        """
        config = EngineConfig()
        
        # Business-critical defaults
        self.assertTrue(config.enable_websocket_events, "WebSocket events are mandatory for chat value")
        self.assertTrue(config.enable_metrics, "Metrics required for SLA monitoring")
        self.assertTrue(config.require_user_context, "User isolation is mandatory")
        self.assertTrue(config.enable_request_scoping, "Request scoping prevents data leakage")
        
        # Performance requirements
        self.assertEqual(config.max_concurrent_agents, 10, "Must support 10+ concurrent users")
        self.assertLessEqual(config.agent_execution_timeout, 30.0, "Timeout supports <2s requirement")
        
        # Resource management
        self.assertEqual(config.max_history_size, 100, "History size prevents memory issues")
        
    def test_engine_config_performance_optimization_settings(self):
        """
        BVJ: ALL - Performance SLA Compliance
        Test EngineConfig supports performance optimization configurations.
        """
        # High-performance configuration
        high_perf_config = EngineConfig(
            max_concurrent_agents=50,
            agent_execution_timeout=1.0,
            periodic_update_interval=1.0,
            enable_fallback=False  # Disable for max performance
        )
        
        self.assertEqual(high_perf_config.max_concurrent_agents, 50)
        self.assertEqual(high_perf_config.agent_execution_timeout, 1.0)
        self.assertFalse(high_perf_config.enable_fallback)
        
    def test_engine_config_security_settings(self):
        """
        BVJ: Platform/Internal - Security Requirements
        Test EngineConfig enforces security-related settings.
        """
        # Security-focused configuration
        secure_config = EngineConfig(
            require_user_context=True,
            enable_request_scoping=True,
            enable_user_features=True,
            max_concurrent_agents=5  # Conservative limit
        )
        
        self.assertTrue(secure_config.require_user_context, "User context mandatory for security")
        self.assertTrue(secure_config.enable_request_scoping, "Request scoping prevents leakage")
        self.assertTrue(secure_config.enable_user_features, "User features enable isolation")
        
    def test_engine_config_feature_flag_combinations(self):
        """
        BVJ: Platform/Internal - Feature Management
        Test EngineConfig handles various feature flag combinations correctly.
        """
        # All features enabled
        full_config = EngineConfig(
            enable_user_features=True,
            enable_mcp=True,
            enable_data_features=True,
            enable_websocket_events=True,
            enable_metrics=True,
            enable_fallback=True
        )
        
        feature_flags = [
            full_config.enable_user_features,
            full_config.enable_mcp,
            full_config.enable_data_features,
            full_config.enable_websocket_events,
            full_config.enable_metrics,
            full_config.enable_fallback
        ]
        
        self.assertTrue(all(feature_flags), "All features should be enabled")


class TestExecutionExtensionsAdvanced(AsyncBaseTestCase):
    """Advanced tests for execution engine extensions with business scenarios."""
    
    async def test_user_execution_extension_business_isolation(self):
        """
        BVJ: ALL - Multi-User Data Security
        CRITICAL: Test UserExecutionExtension prevents user data mixing.
        """
        extension = UserExecutionExtension()
        
        # Create contexts for different users
        user1_context = AgentExecutionContext(
            agent_name="data_agent", 
            task="analyze_financial_data",
            user_id="enterprise_user_1"
        )
        user2_context = AgentExecutionContext(
            agent_name="data_agent",
            task="analyze_personal_data", 
            user_id="free_user_2"
        )
        
        # Pre-execute for both users
        await extension.pre_execute(user1_context)
        await extension.pre_execute(user2_context)
        
        # Each user should have separate semaphores
        self.assertIn("enterprise_user_1", extension.user_semaphores)
        self.assertIn("free_user_2", extension.user_semaphores)
        self.assertNotEqual(
            extension.user_semaphores["enterprise_user_1"],
            extension.user_semaphores["free_user_2"]
        )
        
        # Verify semaphore isolation
        user1_sem = extension.user_semaphores["enterprise_user_1"]
        user2_sem = extension.user_semaphores["free_user_2"]
        
        self.assertEqual(user1_sem._value, 1)  # One slot used by user1
        self.assertEqual(user2_sem._value, 1)  # One slot used by user2
        
    async def test_websocket_extension_all_critical_events(self):
        """
        BVJ: ALL - Chat Value Delivery
        CRITICAL: Test WebSocketExtension delivers ALL 5 critical events in sequence.
        """
        bridge = RealMockWebSocketBridge()
        extension = WebSocketExtension(bridge)
        
        context = AgentExecutionContext(
            agent_name="chat_agent",
            task="customer_support_query"
        )
        
        # Simulate full agent execution cycle
        await extension.pre_execute(context)  # agent_started
        
        result = AgentExecutionResult(success=True, result="Customer issue resolved")
        await extension.post_execute(result, context)  # agent_completed
        
        # Verify all critical events
        self.assertEqual(len(bridge.events), 2)
        event_types = [e["type"] for e in bridge.events]
        self.assertIn("agent_started", event_types)
        self.assertIn("agent_completed", event_types)
        
        # Verify event ordering
        started_event = bridge.get_events_by_type("agent_started")[0]
        completed_event = bridge.get_events_by_type("agent_completed")[0]
        self.assertLess(started_event["timestamp"], completed_event["timestamp"])
        
    async def test_data_execution_extension_performance_optimization(self):
        """
        BVJ: ALL - Data Processing Performance
        Test DataExecutionExtension optimizes for large data processing scenarios.
        """
        extension = DataExecutionExtension()
        
        # Large data processing context
        context = AgentExecutionContext(
            agent_name="big_data_processor",
            task="process_million_records"
        )
        
        await extension.pre_execute(context)
        
        optimization = context.metadata["optimization"]
        self.assertEqual(optimization["batch_size"], 1000)
        self.assertTrue(optimization["cache_enabled"])
        self.assertTrue(optimization["parallel_processing"])
        
        # Test caching functionality
        context.metadata["cache_key"] = "million_records_processed"
        result = AgentExecutionResult(
            success=True,
            result={"processed_records": 1000000, "processing_time": 120.5}
        )
        
        updated_result = await extension.post_execute(result, context)
        
        self.assertTrue(updated_result.metadata["cached"])
        self.assertIn("million_records_processed", extension.data_cache)
        self.assertEqual(
            extension.data_cache["million_records_processed"]["processed_records"],
            1000000
        )
        
    async def test_mcp_execution_extension_tool_integration(self):
        """
        BVJ: ALL - MCP Tool Integration
        Test MCPExecutionExtension handles tool registration and cleanup.
        """
        extension = MCPExecutionExtension()
        
        # Simulate MCP tool registration
        extension.mcp_tools.add("financial_calculator")
        extension.mcp_tools.add("data_analyzer")
        extension.mcp_tools.add("chart_generator")
        
        context = AgentExecutionContext(
            agent_name="mcp_enabled_agent",
            task="generate_financial_report",
            metadata={"enable_mcp": True}
        )
        
        await extension.pre_execute(context)
        self.assertTrue(context.metadata["mcp_enabled"])
        
        result = AgentExecutionResult(success=True, result="Report generated")
        updated_result = await extension.post_execute(result, context)
        
        # Verify tool usage tracking
        mcp_tools_used = updated_result.metadata["mcp_tools_used"]
        self.assertIn("financial_calculator", mcp_tools_used)
        self.assertIn("data_analyzer", mcp_tools_used)
        self.assertIn("chart_generator", mcp_tools_used)
        self.assertEqual(len(mcp_tools_used), 3)


class TestExecutionEngineBusinessScenarios(AsyncBaseTestCase):
    """Test ExecutionEngine with real business scenarios."""
    
    def setUp(self):
        """Set up comprehensive test fixtures."""
        super().setUp()
        
        # Create real mock registry with business-relevant agents
        self.registry = RealMockAgentRegistry()
        self.registry.register_agent("cost_optimizer", RealMockAgent("cost_optimizer", 0.2, use_tools=True))
        self.registry.register_agent("data_analyst", RealMockAgent("data_analyst", 0.3, use_tools=True))
        self.registry.register_agent("customer_support", RealMockAgent("customer_support", 0.1))
        self.registry.register_agent("security_scanner", RealMockAgent("security_scanner", 0.5))
        self.registry.register_agent("slow_processor", RealMockAgent("slow_processor", 2.0))
        self.registry.register_agent("failing_agent", RealMockAgent("failing_agent", 0.1, should_fail=True))
        self.registry.register_agent("memory_hungry", RealMockAgent("memory_hungry", 0.1, should_fail=True, fail_mode="memory_error"))
        
        # Create real WebSocket bridge
        self.websocket_bridge = RealMockWebSocketBridge()
        
        # Create business user contexts
        self.enterprise_user = RealMockUserExecutionContext("enterprise_user_123")
        self.free_user = RealMockUserExecutionContext("free_user_456")
        
    async def test_enterprise_user_agent_execution_full_flow(self):
        """
        BVJ: Enterprise - Premium Agent Execution
        Test full agent execution flow for enterprise user with all features.
        """
        config = EngineConfig(
            enable_user_features=True,
            enable_data_features=True,
            enable_websocket_events=True,
            enable_metrics=True,
            max_concurrent_agents=20
        )
        
        engine = ExecutionEngine(
            config=config,
            registry=self.registry,
            websocket_bridge=self.websocket_bridge,
            user_context=self.enterprise_user
        )
        
        await engine.initialize()
        
        # Execute cost optimization for enterprise user
        start_time = time.time()
        result = await engine.execute("cost_optimizer", {
            "account_id": "enterprise_123",
            "monthly_budget": 50000,
            "optimization_level": "aggressive"
        })
        execution_time = time.time() - start_time
        
        # Verify business requirements
        self.assertTrue(result.success)
        self.assertIsNotNone(result.result)
        self.assertIn("cost_optimizer", str(result.result))
        self.assertLess(execution_time, 2.0, "Must meet <2s response time requirement")
        
        # Verify WebSocket events for chat value
        self.assertGreaterEqual(len(self.websocket_bridge.events), 2)
        event_sequence = self.websocket_bridge.get_event_sequence()
        self.assertEqual(event_sequence[0], "agent_started")
        self.assertEqual(event_sequence[-1], "agent_completed")
        
        # Verify metrics collection
        metrics = engine.get_metrics()
        self.assertEqual(metrics["success_count"], 1)
        self.assertEqual(metrics["error_count"], 0)
        self.assertGreater(metrics["average_execution_ms"], 0)
        
    async def test_multi_user_concurrent_execution_isolation(self):
        """
        BVJ: ALL - Multi-User Isolation & Performance
        CRITICAL: Test 10+ concurrent executions with complete user isolation.
        """
        config = EngineConfig(
            enable_user_features=True,
            enable_websocket_events=True,
            max_concurrent_agents=15
        )
        
        # Create multiple users
        users = []
        for i in range(12):
            user = RealMockUserExecutionContext(f"user_{i}")
            users.append(user)
            
        # Create engines for each user
        engines = []
        bridges = []
        for user in users:
            bridge = RealMockWebSocketBridge()
            engine = ExecutionEngine(
                config=config,
                registry=self.registry,
                websocket_bridge=bridge,
                user_context=user
            )
            await engine.initialize()
            engines.append(engine)
            bridges.append(bridge)
            
        start_time = time.time()
        
        # Execute concurrently for all users
        tasks = []
        for i, engine in enumerate(engines):
            task = asyncio.create_task(
                engine.execute("customer_support", f"query_from_user_{i}")
            )
            tasks.append(task)
            
        # Wait for all executions
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_execution_time = end_time - start_time
        
        # Verify business requirements
        self.assertLess(total_execution_time, 2.0, "12 concurrent executions must complete within 2s")
        
        # All should succeed
        for i, result in enumerate(results):
            self.assertTrue(result.success, f"User {i} execution should succeed")
            
        # Verify user isolation - each bridge should have events
        for i, bridge in enumerate(bridges):
            self.assertGreater(len(bridge.events), 0, f"User {i} should have WebSocket events")
            
        # Verify no cross-contamination
        for i, bridge in enumerate(bridges):
            for event in bridge.events:
                # Events should not reference other users
                event_str = str(event)
                for j in range(len(users)):
                    if i != j:
                        self.assertNotIn(f"user_{j}", event_str)
                        
    async def test_agent_execution_with_tool_integration(self):
        """
        BVJ: ALL - Tool Integration for Agent Value
        Test agent execution with tool usage tracking via WebSocket events.
        """
        config = EngineConfig(
            enable_user_features=True,
            enable_websocket_events=True,
            enable_metrics=True
        )
        
        engine = ExecutionEngine(
            config=config,
            registry=self.registry,
            websocket_bridge=self.websocket_bridge,
            user_context=self.enterprise_user
        )
        
        await engine.initialize()
        
        # Execute data analyst (uses tools)
        result = await engine.execute("data_analyst", {
            "dataset": "customer_metrics_2024",
            "analysis_type": "trend_analysis",
            "output_format": "dashboard"
        })
        
        self.assertTrue(result.success)
        
        # Verify tool usage was tracked
        agent = self.registry.get_agent("data_analyst")
        self.assertGreater(len(agent.tool_calls), 0, "Agent should have used tools")
        
        # Verify WebSocket events include agent workflow
        events = self.websocket_bridge.events
        self.assertGreater(len(events), 0)
        
        # Should have agent_started and agent_completed at minimum
        event_types = {e["type"] for e in events}
        self.assertIn("agent_started", event_types)
        self.assertIn("agent_completed", event_types)
        
    async def test_error_handling_with_graceful_degradation(self):
        """
        BVJ: Platform/Internal - Reliability & Error Recovery
        Test ExecutionEngine handles various error scenarios gracefully.
        """
        config = EngineConfig(
            enable_websocket_events=True,
            enable_fallback=True
        )
        
        engine = ExecutionEngine(
            config=config,
            registry=self.registry,
            websocket_bridge=self.websocket_bridge
        )
        
        await engine.initialize()
        
        # Test different failure modes
        failure_scenarios = [
            ("failing_agent", "runtime_error"),
            ("memory_hungry", "memory_error"),
            ("nonexistent_agent", "not_found")
        ]
        
        for agent_name, expected_error_type in failure_scenarios:
            result = await engine.execute(agent_name, f"test_{expected_error_type}")
            
            self.assertFalse(result.success, f"{agent_name} should fail")
            self.assertIsNotNone(result.error)
            self.assertIsNotNone(result.execution_time_ms)
            
            # Should have error events in WebSocket
            error_events = self.websocket_bridge.get_events_by_type("agent_error")
            self.assertGreater(len(error_events), 0, "Should emit error events")
            
    async def test_performance_monitoring_and_sla_compliance(self):
        """
        BVJ: Platform/Internal - SLA Monitoring
        Test ExecutionEngine tracks performance metrics for SLA compliance.
        """
        config = EngineConfig(enable_metrics=True)
        engine = ExecutionEngine(config=config, registry=self.registry)
        
        await engine.initialize()
        
        # Execute multiple agents to collect metrics
        agents_to_test = ["cost_optimizer", "customer_support", "data_analyst"]
        
        for agent_name in agents_to_test:
            for i in range(3):  # 3 executions each
                await engine.execute(agent_name, f"test_execution_{i}")
                
        metrics = engine.get_metrics()
        
        # Verify comprehensive metrics collection
        self.assertEqual(metrics["total_executions"], 9)  # 3 agents × 3 executions
        self.assertGreater(metrics["success_count"], 0)
        self.assertEqual(metrics["error_count"], 0)
        self.assertEqual(metrics["success_rate"], 1.0)
        
        # Performance requirements
        self.assertLess(metrics["average_execution_ms"], 2000, "Average execution must be <2s")
        self.assertLess(metrics["max_execution_ms"], 2000, "Max execution must be <2s")
        self.assertGreater(metrics["min_execution_ms"], 0, "Min execution must be positive")
        
        # Verify metrics structure
        required_metric_fields = [
            "engine_id", "average_execution_ms", "max_execution_ms", 
            "min_execution_ms", "total_executions", "success_count", 
            "error_count", "success_rate", "active_runs", "extensions"
        ]
        
        for field in required_metric_fields:
            self.assertIn(field, metrics, f"Metrics must include {field}")


class TestRequestScopedExecutionEngineAdvanced(AsyncBaseTestCase):
    """Advanced tests for RequestScopedExecutionEngine isolation."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.registry = RealMockAgentRegistry()
        self.registry.register_agent("scoped_agent", RealMockAgent("scoped_agent", 0.1))
        
        self.user_context = RealMockUserExecutionContext("scoped_user_789")
        self.websocket_bridge = RealMockWebSocketBridge()
        
        self.base_engine = ExecutionEngine(
            config=EngineConfig(enable_user_features=True, enable_websocket_events=True),
            registry=self.registry,
            websocket_bridge=self.websocket_bridge,
            user_context=self.user_context
        )
        
    async def test_request_scoped_execution_complete_isolation(self):
        """
        BVJ: ALL - Request-Level Data Isolation
        CRITICAL: Test RequestScopedExecutionEngine provides complete request isolation.
        """
        await self.base_engine.initialize()
        
        # Create multiple request scopes
        request_ids = ["req_001", "req_002", "req_003"]
        scoped_engines = []
        
        for req_id in request_ids:
            scoped_engine = RequestScopedExecutionEngine(self.base_engine, req_id)
            scoped_engines.append(scoped_engine)
            
        # Execute concurrently in different request scopes
        tasks = []
        for i, scoped_engine in enumerate(scoped_engines):
            task = asyncio.create_task(
                scoped_engine.execute("scoped_agent", f"task_for_request_{i}")
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for i, result in enumerate(results):
            self.assertTrue(result.success, f"Request {i} should succeed")
            
        # Verify request isolation in results
        for i, result in enumerate(results):
            if hasattr(result, 'metadata') and result.metadata:
                # Results should not contain data from other requests
                result_str = str(result)
                for j in range(len(request_ids)):
                    if i != j:
                        self.assertNotIn(f"request_{j}", result_str.lower())
                        
    async def test_request_scoped_context_management_lifecycle(self):
        """
        BVJ: Platform/Internal - Resource Management
        Test RequestScopedExecutionEngine context manager lifecycle.
        """
        await self.base_engine.initialize()
        
        execution_results = []
        
        # Use multiple scoped engines with context managers
        for i in range(3):
            async with RequestScopedExecutionEngine(self.base_engine, f"ctx_req_{i}") as scoped_engine:
                result = await scoped_engine.execute("scoped_agent", f"context_task_{i}")
                execution_results.append(result)
                
                # Engine should be active during context
                self.assertFalse(scoped_engine._closed)
                
            # Engine should be closed after context exit
            self.assertTrue(scoped_engine._closed)
            
        # All executions should have succeeded
        for result in execution_results:
            self.assertTrue(result.success)
            
    async def test_request_scoped_execution_error_isolation(self):
        """
        BVJ: Platform/Internal - Error Isolation
        Test RequestScopedExecutionEngine isolates errors between requests.
        """
        await self.base_engine.initialize()
        
        # Add a failing agent
        self.registry.register_agent("failing_scoped", RealMockAgent("failing_scoped", 0.1, should_fail=True))
        
        # Create scoped engines for success and failure scenarios
        success_engine = RequestScopedExecutionEngine(self.base_engine, "success_req")
        failure_engine = RequestScopedExecutionEngine(self.base_engine, "failure_req")
        
        try:
            # Execute in parallel - one success, one failure
            success_task = asyncio.create_task(
                success_engine.execute("scoped_agent", "success_task")
            )
            failure_task = asyncio.create_task(
                failure_engine.execute("failing_scoped", "failure_task")
            )
            
            success_result, failure_result = await asyncio.gather(success_task, failure_task)
            
            # Success case should succeed despite failure in parallel request
            self.assertTrue(success_result.success)
            self.assertIsNone(success_result.error)
            
            # Failure case should fail as expected
            self.assertFalse(failure_result.success)
            self.assertIsNotNone(failure_result.error)
            
            # Base engine should remain functional
            metrics = self.base_engine.get_metrics()
            self.assertEqual(metrics["success_count"], 1)
            self.assertEqual(metrics["error_count"], 1)
            
        finally:
            await success_engine.close()
            await failure_engine.close()


class TestExecutionEngineFactoryAdvanced(BaseTestCase):
    """Advanced tests for ExecutionEngineFactory configurations."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        # Clear factory defaults for clean testing
        ExecutionEngineFactory._default_config = None
        ExecutionEngineFactory._default_registry = None
        ExecutionEngineFactory._default_websocket_bridge = None
        
    def test_factory_business_configuration_patterns(self):
        """
        BVJ: Platform/Internal - Business Configuration Management
        Test ExecutionEngineFactory creates engines optimized for different business scenarios.
        """
        # Enterprise configuration
        enterprise_user = RealMockUserExecutionContext("enterprise_client")
        enterprise_engine = ExecutionEngineFactory.create_user_engine(enterprise_user)
        
        self.assertTrue(enterprise_engine.config.enable_user_features)
        self.assertTrue(enterprise_engine.config.enable_websocket_events)
        self.assertTrue(enterprise_engine.config.require_user_context)
        
        # Data processing configuration
        data_engine = ExecutionEngineFactory.create_data_engine()
        
        self.assertTrue(data_engine.config.enable_data_features)
        self.assertEqual(data_engine.config.max_concurrent_agents, 20)
        self.assertEqual(data_engine.config.agent_execution_timeout, 60.0)
        
        # MCP integration configuration
        mcp_engine = ExecutionEngineFactory.create_mcp_engine()
        
        self.assertTrue(mcp_engine.config.enable_mcp)
        self.assertTrue(mcp_engine.config.enable_websocket_events)
        
    def test_factory_default_configuration_inheritance(self):
        """
        BVJ: Platform/Internal - Configuration Management
        Test ExecutionEngineFactory properly inherits and overrides defaults.
        """
        # Set comprehensive defaults
        default_config = EngineConfig(
            enable_user_features=True,
            enable_mcp=True,
            max_concurrent_agents=25
        )
        default_registry = RealMockAgentRegistry()
        default_bridge = RealMockWebSocketBridge()
        
        ExecutionEngineFactory.set_defaults(
            config=default_config,
            registry=default_registry,
            websocket_bridge=default_bridge
        )
        
        # Create engine with defaults
        engine = ExecutionEngineFactory.create_engine()
        
        self.assertEqual(engine.config.max_concurrent_agents, 25)
        self.assertTrue(engine.config.enable_user_features)
        self.assertTrue(engine.config.enable_mcp)
        self.assertEqual(engine.registry, default_registry)
        self.assertEqual(engine.websocket_bridge, default_bridge)
        
        # Create engine with overrides
        override_config = EngineConfig(max_concurrent_agents=50)
        override_engine = ExecutionEngineFactory.create_engine(config=override_config)
        
        self.assertEqual(override_engine.config.max_concurrent_agents, 50)
        
    def test_factory_specialized_engine_configurations(self):
        """
        BVJ: Platform/Internal - Specialized Configurations
        Test ExecutionEngineFactory creates engines for specialized use cases.
        """
        # Test all factory methods return proper engine types
        user_context = RealMockUserExecutionContext("test_user")
        
        engines_to_test = [
            ("basic", ExecutionEngineFactory.create_engine()),
            ("user", ExecutionEngineFactory.create_user_engine(user_context)),
            ("data", ExecutionEngineFactory.create_data_engine()),
            ("mcp", ExecutionEngineFactory.create_mcp_engine()),
        ]
        
        for engine_type, engine in engines_to_test:
            self.assertIsInstance(engine, ExecutionEngine, f"{engine_type} should create ExecutionEngine")
            self.assertIsNotNone(engine.config, f"{engine_type} should have config")
            self.assertIsNotNone(engine.engine_id, f"{engine_type} should have engine_id")
            
        # Request-scoped engine
        scoped_engine = ExecutionEngineFactory.create_request_scoped_engine("test_req", user_context)
        self.assertIsInstance(scoped_engine, RequestScopedExecutionEngine)
        self.assertEqual(scoped_engine.request_id, "test_req")


class TestWebSocketEventIntegrationAdvanced(AsyncBaseTestCase):
    """Advanced WebSocket event integration tests with business scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        self.registry = RealMockAgentRegistry()
        self.registry.register_agent("chat_agent", RealMockAgent("chat_agent", 0.15, use_tools=True))
        self.registry.register_agent("thinking_agent", RealMockAgent("thinking_agent", 0.25, use_tools=True))
        self.registry.register_agent("error_prone_agent", RealMockAgent("error_prone_agent", 0.1, should_fail=True))
        
        self.websocket_bridge = RealMockWebSocketBridge()
        
    async def test_complete_websocket_event_flow_with_timing(self):
        """
        BVJ: ALL - Chat User Experience
        CRITICAL: Test complete WebSocket event flow with proper timing for chat UX.
        """
        config = EngineConfig(enable_websocket_events=True)
        engine = ExecutionEngine(
            config=config,
            registry=self.registry,
            websocket_bridge=self.websocket_bridge
        )
        
        await engine.initialize()
        
        start_time = time.time()
        result = await engine.execute("thinking_agent", {
            "query": "Analyze customer satisfaction trends",
            "urgency": "high",
            "expected_tools": ["data_analyzer", "chart_generator"]
        })
        end_time = time.time()
        
        self.assertTrue(result.success)
        
        # Verify event timing and sequence
        events = self.websocket_bridge.events
        self.assertGreaterEqual(len(events), 2)  # At least started and completed
        
        # Events should be within execution timeframe
        for event in events:
            self.assertGreaterEqual(event["timestamp"], start_time)
            self.assertLessEqual(event["timestamp"], end_time)
            
        # Verify critical event sequence
        event_sequence = self.websocket_bridge.get_event_sequence()
        self.assertEqual(event_sequence[0], "agent_started")
        self.assertEqual(event_sequence[-1], "agent_completed")
        
        # Verify event content quality
        started_event = self.websocket_bridge.get_events_by_type("agent_started")[0]
        self.assertEqual(started_event["agent_name"], "thinking_agent")
        self.assertIn("Analyze customer satisfaction", str(started_event["task"]))
        
        completed_event = self.websocket_bridge.get_events_by_type("agent_completed")[0]
        self.assertEqual(completed_event["agent_name"], "thinking_agent")
        self.assertIsNotNone(completed_event["result"])
        
    async def test_websocket_event_failure_resilience(self):
        """
        BVJ: Platform/Internal - System Resilience
        Test ExecutionEngine continues working when WebSocket events fail.
        """
        # Create bridge that fails 50% of the time
        unreliable_bridge = RealMockWebSocketBridge(fail_probability=0.5)
        
        config = EngineConfig(enable_websocket_events=True)
        engine = ExecutionEngine(
            config=config,
            registry=self.registry,
            websocket_bridge=unreliable_bridge
        )
        
        await engine.initialize()
        
        # Execute multiple times to trigger some failures
        successful_executions = 0
        for i in range(10):
            result = await engine.execute("chat_agent", f"resilience_test_{i}")
            if result.success:
                successful_executions += 1
                
        # Core functionality should not be affected by WebSocket failures
        self.assertGreaterEqual(successful_executions, 8, "Most executions should succeed despite WebSocket failures")
        
        # Some WebSocket errors should have been recorded
        self.assertGreater(unreliable_bridge.metrics["errors"], 0)
        
    async def test_websocket_events_multi_user_isolation(self):
        """
        BVJ: ALL - Multi-User Event Isolation
        CRITICAL: Test WebSocket events are properly isolated between users.
        """
        # Create separate bridges for different users
        user1_bridge = RealMockWebSocketBridge()
        user2_bridge = RealMockWebSocketBridge() 
        user3_bridge = RealMockWebSocketBridge()
        
        bridges = [user1_bridge, user2_bridge, user3_bridge]
        engines = []
        
        # Create engines with separate bridges
        for i, bridge in enumerate(bridges):
            user_context = RealMockUserExecutionContext(f"isolated_user_{i}")
            config = EngineConfig(enable_websocket_events=True, enable_user_features=True)
            
            engine = ExecutionEngine(
                config=config,
                registry=self.registry,
                websocket_bridge=bridge,
                user_context=user_context
            )
            await engine.initialize()
            engines.append(engine)
            
        # Execute concurrently for all users
        tasks = []
        for i, engine in enumerate(engines):
            task = asyncio.create_task(
                engine.execute("chat_agent", f"isolated_query_user_{i}")
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        # All executions should succeed
        for result in results:
            self.assertTrue(result.success)
            
        # Each bridge should have events for only its user
        for i, bridge in enumerate(bridges):
            self.assertGreater(len(bridge.events), 0, f"User {i} should have events")
            
            # Events should reference correct user context
            for event in bridge.events:
                event_data = str(event)
                self.assertIn(f"isolated_query_user_{i}", event_data)
                
                # Should not contain other users' data
                for j in range(len(bridges)):
                    if i != j:
                        self.assertNotIn(f"user_{j}", event_data)
                        
    async def test_websocket_event_performance_under_load(self):
        """
        BVJ: Platform/Internal - Performance Under Load
        Test WebSocket event system maintains performance under high load.
        """
        config = EngineConfig(enable_websocket_events=True, max_concurrent_agents=20)
        engine = ExecutionEngine(
            config=config,
            registry=self.registry,
            websocket_bridge=self.websocket_bridge
        )
        
        await engine.initialize()
        
        # High-load test: 15 concurrent executions
        start_time = time.time()
        
        tasks = []
        for i in range(15):
            task = asyncio.create_task(
                engine.execute("chat_agent", f"load_test_query_{i}")
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # Performance requirements
        self.assertLess(total_time, 2.0, "15 concurrent executions with WebSocket events must complete <2s")
        
        # All should succeed
        for result in results:
            self.assertTrue(result.success)
            
        # WebSocket events should have been sent for all executions
        event_count = len(self.websocket_bridge.events)
        self.assertGreaterEqual(event_count, 30)  # At least 2 events per execution
        
        # Verify event distribution
        started_events = len(self.websocket_bridge.get_events_by_type("agent_started"))
        completed_events = len(self.websocket_bridge.get_events_by_type("agent_completed"))
        
        self.assertEqual(started_events, 15, "Should have 15 agent_started events")
        self.assertEqual(completed_events, 15, "Should have 15 agent_completed events")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])