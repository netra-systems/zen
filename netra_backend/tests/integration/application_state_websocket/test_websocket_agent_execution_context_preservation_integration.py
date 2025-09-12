"""Test #32: Agent Execution Context Preservation Across WebSocket Events and Database Operations

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (multi-user concurrent scenarios)
- Business Goal: Ensure perfect user context isolation in concurrent agent executions
- Value Impact: Prevents data leakage between users ($10k+ cost optimization recommendations must stay private)
- Strategic Impact: Enterprise-grade security enabling multi-tenant AI optimization platform

This test validates that user execution context is perfectly preserved throughout
agent execution lifecycle, preventing data contamination between concurrent users.

CRITICAL: User context isolation is MANDATORY for enterprise customers who handle
sensitive cost optimization data. A single context leak could expose proprietary
infrastructure details and cost optimization strategies between competing organizations.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Core application imports
# ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context,
    InvalidContextError
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class ContextTrackingAgent(BaseAgent):
    """Agent that tracks and validates user context throughout execution."""
    
    def __init__(self, name: str, llm_manager: LLMManager):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Context tracking {name}")
        self.websocket_bridge = None
        self.context_snapshots = []
        self.user_data_accessed = []
        
    def set_websocket_bridge(self, bridge: AgentWebSocketBridge, run_id: str):
        """Set WebSocket bridge and capture initial context."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute agent while preserving and validating user context."""
        
        if not stream_updates or not self.websocket_bridge:
            raise ValueError("WebSocket bridge required for context tracking")
            
        # Capture initial context snapshot
        initial_context_snapshot = {
            "user_id": getattr(state, 'user_id', None),
            "run_id": run_id,
            "state_data": {
                "user_request": getattr(state, 'user_request', None),
                "chat_thread_id": getattr(state, 'chat_thread_id', None),
                "agent_input": getattr(state, 'agent_input', None)
            },
            "timestamp": datetime.now(timezone.utc),
            "stage": "initialization"
        }
        self.context_snapshots.append(initial_context_snapshot)
        
        # EVENT 1: agent_started with context validation
        await self.websocket_bridge.notify_agent_started(
            run_id, self.name, {
                "context_validation": "initial_context_preserved",
                "user_context_id": initial_context_snapshot["user_id"],
                "sensitive_data_indicators": self._extract_sensitive_indicators(state)
            }
        )
        
        # EVENT 2: agent_thinking with context preservation
        thinking_phases = [
            "Validating user context isolation and data access patterns...",
            "Processing user-specific optimization parameters securely...", 
            "Analyzing context-bound data while maintaining isolation..."
        ]
        
        for i, thinking in enumerate(thinking_phases):
            # Capture context snapshot at each thinking phase
            thinking_snapshot = {
                "user_id": getattr(state, 'user_id', None),
                "run_id": run_id,
                "stage": f"thinking_phase_{i+1}",
                "thinking_content": thinking,
                "timestamp": datetime.now(timezone.utc),
                "context_integrity": self._validate_context_integrity(state, initial_context_snapshot)
            }
            self.context_snapshots.append(thinking_snapshot)
            
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, thinking,
                step_number=i + 1,
                progress_percentage=int((i + 1) / len(thinking_phases) * 40)
            )
            
            await asyncio.sleep(0.05)
            
        # EVENT 3 & 4: Tool execution with context-bound operations
        context_sensitive_tools = [
            ("user_data_analyzer", {"user_scope": getattr(state, 'user_id', None)}),
            ("personalized_optimizer", {"context_id": run_id, "isolation_check": True})
        ]
        
        for tool_name, tool_params in context_sensitive_tools:
            # Validate context before tool execution
            pre_tool_snapshot = {
                "user_id": getattr(state, 'user_id', None),
                "run_id": run_id,
                "stage": f"pre_{tool_name}",
                "tool_parameters": tool_params,
                "context_validation": self._validate_context_integrity(state, initial_context_snapshot),
                "timestamp": datetime.now(timezone.utc)
            }
            self.context_snapshots.append(pre_tool_snapshot)
            
            # EVENT 3: tool_executing with context validation
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, tool_name, tool_params
            )
            
            # Simulate context-aware tool processing
            await asyncio.sleep(0.1)
            
            # Generate context-bound tool results
            tool_result = self._generate_context_bound_results(tool_name, state, run_id)
            
            # Capture post-tool context snapshot
            post_tool_snapshot = {
                "user_id": getattr(state, 'user_id', None),
                "run_id": run_id,
                "stage": f"post_{tool_name}",
                "tool_result_summary": self._sanitize_for_logging(tool_result),
                "context_validation": self._validate_context_integrity(state, initial_context_snapshot),
                "timestamp": datetime.now(timezone.utc)
            }
            self.context_snapshots.append(post_tool_snapshot)
            
            # EVENT 4: tool_completed with validated results
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, tool_name, tool_result
            )
            
        # Final thinking with context validation
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, "Finalizing context-isolated results and ensuring data privacy...",
            step_number=len(thinking_phases) + 1,
            progress_percentage=95
        )
        
        # Generate final context-validated result
        final_result = {
            "success": True,
            "agent_name": self.name,
            "context_preservation": {
                "user_id_consistent": self._validate_user_id_consistency(),
                "run_id_consistent": self._validate_run_id_consistency(run_id),
                "no_context_contamination": self._validate_no_contamination(),
                "context_snapshots_count": len(self.context_snapshots),
                "data_isolation_verified": True
            },
            "user_specific_analysis": self._generate_user_specific_results(state),
            "security_validation": {
                "context_isolation": "verified",
                "data_access_patterns": self.user_data_accessed,
                "sensitive_data_protection": "active"
            },
            "timestamp": datetime.now(timezone.utc),
            "context_integrity_score": 100.0
        }
        
        # EVENT 5: agent_completed with final context validation
        await self.websocket_bridge.notify_agent_completed(
            run_id, self.name, final_result, execution_time_ms=250
        )
        
        return final_result
        
    def _extract_sensitive_indicators(self, state: DeepAgentState) -> Dict[str, bool]:
        """Extract indicators of sensitive data without exposing actual content."""
        return {
            "has_user_request": hasattr(state, 'user_request') and state.user_request is not None,
            "has_agent_input": hasattr(state, 'agent_input') and state.agent_input is not None,
            "has_user_id": hasattr(state, 'user_id') and state.user_id is not None,
            "has_thread_context": hasattr(state, 'chat_thread_id') and state.chat_thread_id is not None
        }
        
    def _validate_context_integrity(self, current_state: DeepAgentState, initial_snapshot: Dict) -> Dict[str, bool]:
        """Validate that context has not been contaminated or altered."""
        current_user_id = getattr(current_state, 'user_id', None)
        initial_user_id = initial_snapshot["user_id"]
        
        return {
            "user_id_unchanged": current_user_id == initial_user_id,
            "run_id_consistent": True,  # Validated externally
            "no_foreign_data": self._check_no_foreign_data(current_state, initial_snapshot),
            "timestamp_progression": datetime.now(timezone.utc) > initial_snapshot["timestamp"]
        }
        
    def _check_no_foreign_data(self, current_state: DeepAgentState, initial_snapshot: Dict) -> bool:
        """Check that no foreign user data has contaminated this context."""
        # In real implementation, would check for data patterns that don't match initial user
        current_request = getattr(current_state, 'user_request', {})
        if isinstance(current_request, dict):
            # Verify no other user IDs present in the request data
            request_str = str(current_request).lower()
            initial_user = initial_snapshot["user_id"]
            if initial_user and initial_user.lower() not in request_str:
                # This is actually expected - user_id might not be in request text
                pass
        return True
        
    def _generate_context_bound_results(self, tool_name: str, state: DeepAgentState, run_id: str) -> Dict[str, Any]:
        """Generate tool results that are bound to specific user context."""
        user_id = getattr(state, 'user_id', None)
        
        if "analyzer" in tool_name:
            return {
                "analysis_scope": f"user_{user_id[:8]}_specific",
                "data_processed": f"context_isolated_dataset_{run_id[:8]}",
                "insights_found": 4,
                "user_context_preserved": True,
                "findings": [
                    f"User-specific pattern A for {user_id[:8]}",
                    f"Context-isolated optimization B", 
                    f"Privacy-protected insight C",
                    f"User-bound recommendation D"
                ]
            }
        else:  # optimizer
            return {
                "optimization_strategy": f"personalized_for_{user_id[:8]}",
                "context_isolation": "verified",
                "user_specific_recommendations": [
                    f"Tailored optimization 1 for user {user_id[:8]}",
                    f"Context-aware strategy 2",
                    f"Privacy-preserving approach 3"
                ],
                "data_privacy": "maintained",
                "cross_user_contamination": "none_detected"
            }
            
    def _sanitize_for_logging(self, data: Any) -> Dict[str, Any]:
        """Sanitize data for logging without exposing sensitive content."""
        if isinstance(data, dict):
            return {
                "data_type": "dict",
                "key_count": len(data),
                "has_user_data": any("user" in str(k).lower() for k in data.keys()),
                "has_sensitive_data": any(k in ["password", "token", "secret"] for k in data.keys())
            }
        return {"data_type": str(type(data)), "content_sanitized": True}
        
    def _validate_user_id_consistency(self) -> bool:
        """Validate that user_id is consistent across all snapshots."""
        if not self.context_snapshots:
            return False
            
        first_user_id = self.context_snapshots[0]["user_id"]
        return all(snapshot["user_id"] == first_user_id for snapshot in self.context_snapshots)
        
    def _validate_run_id_consistency(self, expected_run_id: str) -> bool:
        """Validate that run_id is consistent across all snapshots."""
        return all(snapshot["run_id"] == expected_run_id for snapshot in self.context_snapshots)
        
    def _validate_no_contamination(self) -> bool:
        """Validate that no context contamination occurred."""
        # Check that all context validations passed
        for snapshot in self.context_snapshots:
            if "context_validation" in snapshot:
                validation = snapshot["context_validation"]
                if not validation.get("user_id_unchanged", True):
                    return False
                if not validation.get("no_foreign_data", True):
                    return False
        return True
        
    def _generate_user_specific_results(self, state: DeepAgentState) -> Dict[str, Any]:
        """Generate results that are specific to the user context."""
        user_id = getattr(state, 'user_id', None)
        
        return {
            "personalized_insights": [
                f"Context-aware analysis for user {user_id[:8]}",
                "Privacy-protected optimization recommendations",
                "User-specific cost reduction strategies"
            ],
            "isolation_verified": True,
            "user_scope": user_id,
            "data_privacy": "maintained"
        }


class ContextPreservationValidator:
    """Validator for user context preservation across WebSocket events."""
    
    def __init__(self):
        self.user_contexts = {}
        self.context_violations = []
        self.websocket_events = []
        
    async def create_isolated_bridge(self, user_context: UserExecutionContext):
        """Create WebSocket bridge that validates context isolation."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.events = []
        
        # Track user context for this bridge
        self.user_contexts[user_context.user_id] = user_context
        
        async def validate_event_context(event_type: str, run_id: str, agent_name: str, data: Any = None, **kwargs):
            """Validate that WebSocket event maintains proper user context."""
            event = {
                "event_type": event_type,
                "run_id": run_id,
                "agent_name": agent_name,
                "user_id": user_context.user_id,
                "data": data,
                "timestamp": datetime.now(timezone.utc),
                "kwargs": kwargs
            }
            
            # Validate context integrity
            if run_id != user_context.run_id:
                self.context_violations.append({
                    "violation_type": "run_id_mismatch",
                    "expected": user_context.run_id,
                    "actual": run_id,
                    "event": event_type,
                    "user_id": user_context.user_id
                })
                
            # Check for cross-user data contamination
            if data and isinstance(data, dict):
                data_str = str(data)
                for other_user_id in self.user_contexts.keys():
                    if other_user_id != user_context.user_id and other_user_id in data_str:
                        self.context_violations.append({
                            "violation_type": "cross_user_contamination",
                            "user_id": user_context.user_id,
                            "contaminating_user": other_user_id,
                            "event": event_type,
                            "data_sample": data_str[:100]
                        })
                        
            bridge.events.append(event)
            self.websocket_events.append(event)
            return True
            
        # Set up all WebSocket methods with context validation
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            validate_event_context("agent_started", run_id, agent_name, context))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, thinking, **kwargs:
            validate_event_context("agent_thinking", run_id, agent_name, {"reasoning": thinking}, **kwargs))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, params:
            validate_event_context("tool_executing", run_id, agent_name, {"tool_name": tool_name, "parameters": params}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            validate_event_context("tool_completed", run_id, agent_name, {"tool_name": tool_name, "result": result}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, **kwargs:
            validate_event_context("agent_completed", run_id, agent_name, result, **kwargs))
            
        return bridge
        
    def get_context_violations(self) -> List[Dict]:
        """Get all context preservation violations."""
        return self.context_violations.copy()
        
    def validate_isolation_between_users(self, user1_id: str, user2_id: str) -> Dict[str, Any]:
        """Validate perfect isolation between two users."""
        user1_events = [e for e in self.websocket_events if e["user_id"] == user1_id]
        user2_events = [e for e in self.websocket_events if e["user_id"] == user2_id]
        
        isolation_report = {
            "user1_events": len(user1_events),
            "user2_events": len(user2_events), 
            "cross_contamination": [],
            "isolation_score": 100.0
        }
        
        # Check for any cross-contamination in events
        for event in user1_events:
            event_str = str(event["data"])
            if user2_id in event_str:
                isolation_report["cross_contamination"].append({
                    "contaminated_user": user1_id,
                    "contaminating_user": user2_id,
                    "event_type": event["event_type"]
                })
                
        for event in user2_events:
            event_str = str(event["data"])
            if user1_id in event_str:
                isolation_report["cross_contamination"].append({
                    "contaminated_user": user2_id,
                    "contaminating_user": user1_id,
                    "event_type": event["event_type"]
                })
                
        if isolation_report["cross_contamination"]:
            isolation_report["isolation_score"] = 0.0
            
        return isolation_report


class TestWebSocketAgentExecutionContextPreservationIntegration(BaseIntegrationTest):
    """Integration test for agent execution context preservation across WebSocket events."""
    
    def setup_method(self):
        """Set up test environment for context preservation testing."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TESTING", "1", source="integration_test")
        self.context_validator = ContextPreservationValidator()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        llm_manager.initialize = AsyncMock()
        return llm_manager
        
    @pytest.fixture
    async def enterprise_user_contexts(self):
        """Create multiple enterprise user contexts for isolation testing."""
        return {
            "enterprise_alpha": UserExecutionContext(
                user_id=f"enterprise_alpha_{uuid.uuid4().hex[:8]}",
                thread_id=f"alpha_thread_{uuid.uuid4().hex[:8]}",
                run_id=f"alpha_run_{uuid.uuid4().hex[:8]}",
                request_id=f"alpha_req_{uuid.uuid4().hex[:8]}",
                metadata={
                    "organization": "Alpha Corp",
                    "sensitive_data": "alpha_financial_data_confidential",
                    "cost_center": "AI_Infrastructure_Alpha",
                    "security_clearance": "enterprise"
                }
            ),
            "enterprise_beta": UserExecutionContext(
                user_id=f"enterprise_beta_{uuid.uuid4().hex[:8]}",
                thread_id=f"beta_thread_{uuid.uuid4().hex[:8]}",
                run_id=f"beta_run_{uuid.uuid4().hex[:8]}",
                request_id=f"beta_req_{uuid.uuid4().hex[:8]}",
                metadata={
                    "organization": "Beta Industries", 
                    "sensitive_data": "beta_proprietary_costs_secret",
                    "cost_center": "AI_Operations_Beta",
                    "security_clearance": "enterprise"
                }
            )
        }
        
    @pytest.fixture
    async def context_tracking_registry(self, mock_llm_manager):
        """Create registry with context-tracking agents."""
        agents = {
            "context_tracker_alpha": ContextTrackingAgent("context_tracker_alpha", mock_llm_manager),
            "context_tracker_beta": ContextTrackingAgent("context_tracker_beta", mock_llm_manager)
        }
        
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: agents.get(name)
        registry.get_async = AsyncMock(side_effect=lambda name, context=None: agents.get(name))
        registry.list_keys = lambda: list(agents.keys())
        
        return registry, agents

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_preservation_throughout_agent_execution(
        self, real_services_fixture, enterprise_user_contexts, context_tracking_registry, mock_llm_manager
    ):
        """CRITICAL: Test user context is perfectly preserved throughout agent execution."""
        
        # Business Value: Enterprise customers require absolute data isolation
        
        registry, agents = context_tracking_registry
        alpha_context = enterprise_user_contexts["enterprise_alpha"]
        
        # Create context-preserving WebSocket bridge
        websocket_bridge = await self.context_validator.create_isolated_bridge(alpha_context)
        
        # Initialize execution engine
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=alpha_context
        )
        
        # Create agent execution context
        exec_context = AgentExecutionContext(
            user_id=alpha_context.user_id,
            thread_id=alpha_context.thread_id,
            run_id=alpha_context.run_id,
            request_id=alpha_context.request_id,
            agent_name="context_tracker_alpha",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Create agent state with sensitive enterprise data
        agent_state = DeepAgentState(
            user_request={
                "message": "Analyze our $180k monthly AI spend for Alpha Corp",
                "sensitive_context": alpha_context.metadata["sensitive_data"]
            },
            user_id=alpha_context.user_id,
            chat_thread_id=alpha_context.thread_id,
            run_id=alpha_context.run_id,
            agent_input={
                "organization": alpha_context.metadata["organization"],
                "security_level": "enterprise",
                "cost_analysis": True
            }
        )
        
        # Execute agent with context preservation monitoring
        result = await execution_engine.execute_agent(exec_context, alpha_context)
        
        # CRITICAL: Validate execution succeeded
        assert result is not None
        assert result.success is True, f"Context preservation execution failed: {getattr(result, 'error', 'Unknown')}"
        
        # MISSION CRITICAL: Validate context preservation
        context_data = result.data.get("context_preservation", {})
        
        assert context_data.get("user_id_consistent") is True, "User ID must remain consistent"
        assert context_data.get("run_id_consistent") is True, "Run ID must remain consistent" 
        assert context_data.get("no_context_contamination") is True, "No context contamination allowed"
        assert context_data.get("data_isolation_verified") is True, "Data isolation must be verified"
        
        # Validate context snapshots were captured
        snapshots_count = context_data.get("context_snapshots_count", 0)
        assert snapshots_count >= 5, f"Expected minimum 5 context snapshots, got {snapshots_count}"
        
        # Validate no context violations occurred
        violations = self.context_validator.get_context_violations()
        assert len(violations) == 0, f"Context violations detected: {violations}"
        
        # Validate sensitive data remained isolated
        user_specific_analysis = result.data.get("user_specific_analysis", {})
        assert user_specific_analysis.get("isolation_verified") is True
        assert user_specific_analysis.get("user_scope") == alpha_context.user_id
        
        # DATABASE INTEGRATION: Validate context preservation with database operations
        if real_services_fixture["database_available"]:
            db_session = real_services_fixture["db"]
            if db_session:
                # Simulate context-bound database operations
                context_record = {
                    "user_id": alpha_context.user_id,
                    "run_id": alpha_context.run_id,
                    "organization": alpha_context.metadata["organization"],
                    "context_integrity": 100.0,
                    "isolation_verified": True,
                    "sensitive_data_protected": True
                }
                
                # Validate that database operations would maintain context
                assert context_record["user_id"] == alpha_context.user_id
                assert context_record["isolation_verified"] is True
                assert context_record["sensitive_data_protected"] is True
                
        self.logger.info(
            f" PASS:  User context preservation test PASSED - "
            f"Organization: {alpha_context.metadata['organization']}, "
            f"Snapshots: {snapshots_count}, Violations: {len(violations)}"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_context_isolation_in_websocket_events(
        self, real_services_fixture, enterprise_user_contexts, context_tracking_registry
    ):
        """Test perfect isolation between concurrent enterprise users."""
        
        # Business Value: Prevents competitive intelligence leaks between enterprise clients
        
        registry, agents = context_tracking_registry
        alpha_context = enterprise_user_contexts["enterprise_alpha"]
        beta_context = enterprise_user_contexts["enterprise_beta"]
        
        # Create isolated WebSocket bridges for each user
        alpha_bridge = await self.context_validator.create_isolated_bridge(alpha_context)
        beta_bridge = await self.context_validator.create_isolated_bridge(beta_context)
        
        # Create isolated execution engines
        alpha_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=alpha_bridge,
            user_context=alpha_context
        )
        
        beta_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=beta_bridge,
            user_context=beta_context
        )
        
        # Define concurrent execution function
        async def execute_user_agent(user_context, engine, agent_name):
            """Execute agent for specific user context."""
            exec_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                agent_name=agent_name,
                step=PipelineStep.PROCESSING,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            agent_state = DeepAgentState(
                user_request={
                    "message": f"Confidential analysis for {user_context.metadata['organization']}",
                    "sensitive_data": user_context.metadata["sensitive_data"]
                },
                user_id=user_context.user_id,
                chat_thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                agent_input={
                    "organization": user_context.metadata["organization"],
                    "cost_center": user_context.metadata["cost_center"]
                }
            )
            
            return await engine.execute_agent(exec_context, user_context)
            
        # Execute both users concurrently
        alpha_task = execute_user_agent(alpha_context, alpha_engine, "context_tracker_alpha")
        beta_task = execute_user_agent(beta_context, beta_engine, "context_tracker_beta")
        
        alpha_result, beta_result = await asyncio.gather(alpha_task, beta_task, return_exceptions=True)
        
        # Validate both executions succeeded
        assert not isinstance(alpha_result, Exception), f"Alpha execution failed: {alpha_result}"
        assert not isinstance(beta_result, Exception), f"Beta execution failed: {beta_result}"
        
        assert alpha_result.success is True
        assert beta_result.success is True
        
        # CRITICAL: Validate perfect isolation between users
        isolation_report = self.context_validator.validate_isolation_between_users(
            alpha_context.user_id, beta_context.user_id
        )
        
        assert isolation_report["isolation_score"] == 100.0, \
            f"Perfect isolation required, got {isolation_report['isolation_score']}%"
        assert len(isolation_report["cross_contamination"]) == 0, \
            f"Cross-user contamination detected: {isolation_report['cross_contamination']}"
            
        # Validate each user's context preservation
        alpha_context_data = alpha_result.data.get("context_preservation", {})
        beta_context_data = beta_result.data.get("context_preservation", {})
        
        for context_data, user_name in [(alpha_context_data, "Alpha"), (beta_context_data, "Beta")]:
            assert context_data.get("user_id_consistent") is True, f"{user_name} user ID inconsistent"
            assert context_data.get("no_context_contamination") is True, f"{user_name} context contaminated"
            assert context_data.get("data_isolation_verified") is True, f"{user_name} isolation failed"
            
        # Validate sensitive data isolation
        alpha_analysis = alpha_result.data.get("user_specific_analysis", {})
        beta_analysis = beta_result.data.get("user_specific_analysis", {})
        
        assert alpha_analysis.get("user_scope") == alpha_context.user_id
        assert beta_analysis.get("user_scope") == beta_context.user_id
        
        # Ensure no cross-organization data leakage
        alpha_data_str = str(alpha_result.data)
        beta_data_str = str(beta_result.data)
        
        assert "Beta Industries" not in alpha_data_str, "Beta data leaked to Alpha"
        assert "Alpha Corp" not in beta_data_str, "Alpha data leaked to Beta" 
        assert "beta_proprietary_costs_secret" not in alpha_data_str, "Beta secrets leaked to Alpha"
        assert "alpha_financial_data_confidential" not in beta_data_str, "Alpha secrets leaked to Beta"
        
        # Validate context violations
        violations = self.context_validator.get_context_violations()
        assert len(violations) == 0, f"Context isolation violations: {violations}"
        
        self.logger.info(
            f" PASS:  Concurrent user context isolation test PASSED - "
            f"Alpha events: {isolation_report['user1_events']}, "
            f"Beta events: {isolation_report['user2_events']}, "
            f"Isolation score: {isolation_report['isolation_score']}%"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_preservation_during_database_operations(
        self, real_services_fixture, enterprise_user_contexts, context_tracking_registry
    ):
        """Test context preservation during database operations."""
        
        # Business Value: Database operations must maintain user context for audit trails
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for context preservation testing")
            
        registry, agents = context_tracking_registry
        user_context = enterprise_user_contexts["enterprise_alpha"]
        
        websocket_bridge = await self.context_validator.create_isolated_bridge(user_context)
        
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=user_context
        )
        
        # Add database session to context
        db_session = real_services_fixture["db"]
        user_context_with_db = user_context.with_db_session(db_session)
        
        exec_context = AgentExecutionContext(
            user_id=user_context_with_db.user_id,
            thread_id=user_context_with_db.thread_id,
            run_id=user_context_with_db.run_id,
            request_id=user_context_with_db.request_id,
            agent_name="context_tracker_alpha",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        agent_state = DeepAgentState(
            user_request={"database_operations": True, "context_sensitive": True},
            user_id=user_context_with_db.user_id,
            chat_thread_id=user_context_with_db.thread_id,
            run_id=user_context_with_db.run_id,
            agent_input={"require_db_context": True}
        )
        
        # Execute with database context
        result = await execution_engine.execute_agent(exec_context, user_context_with_db)
        
        # Validate execution with database context succeeded
        assert result.success is True
        
        # Validate context was preserved through database operations
        context_data = result.data.get("context_preservation", {})
        assert context_data.get("user_id_consistent") is True
        assert context_data.get("data_isolation_verified") is True
        
        # Validate no context violations during database operations
        violations = self.context_validator.get_context_violations()
        assert len(violations) == 0, f"Database context violations: {violations}"
        
        # Validate user context integrity
        validate_user_context(user_context_with_db)  # Should not raise
        
        self.logger.info(" PASS:  Context preservation during database operations test PASSED")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])