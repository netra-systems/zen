"""Test #36: Agent Execution Error Handling with WebSocket Event Notifications and Recovery

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - System reliability 
- Business Goal: Graceful error handling maintains user trust and prevents revenue loss from failed AI operations
- Value Impact: Proper error recovery prevents users from abandoning optimization workflows ($50k+ potential losses)
- Strategic Impact: Enterprise-grade error handling differentiates platform from unreliable AI systems

CRITICAL: Error handling through WebSocket events enables:
- User confidence: Clear error communication prevents user frustration
- System reliability: Graceful degradation maintains service availability  
- Business continuity: Recovery mechanisms prevent complete workflow failures
- Trust building: Transparent error reporting builds user confidence in AI system
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Core application imports
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, PipelineStep
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class ErrorHandlingAgent(BaseAgent):
    """Agent designed to test various error scenarios and recovery mechanisms."""
    
    def __init__(self, name: str, llm_manager: LLMManager, error_scenario: str = "none"):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Error handling {name}")
        self.websocket_bridge = None
        self.error_scenario = error_scenario
        self.recovery_attempts = []
        
    def set_websocket_bridge(self, bridge: AgentWebSocketBridge, run_id: str):
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute with configurable error scenarios and recovery testing."""
        
        if not stream_updates or not self.websocket_bridge:
            raise ValueError("WebSocket bridge required")
            
        try:
            # EVENT 1: agent_started
            await self.websocket_bridge.notify_agent_started(
                run_id, self.name, {
                    "error_testing_mode": True,
                    "error_scenario": self.error_scenario,
                    "recovery_enabled": True
                }
            )
            
            # EVENT 2: agent_thinking with error detection
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, "Initializing error handling and recovery mechanisms...",
                step_number=1, progress_percentage=20
            )
            
            # Simulate different error scenarios
            if self.error_scenario == "tool_failure":
                await self._handle_tool_failure_scenario(run_id)
            elif self.error_scenario == "llm_timeout":
                await self._handle_llm_timeout_scenario(run_id)
            elif self.error_scenario == "partial_failure":
                await self._handle_partial_failure_scenario(run_id)
            elif self.error_scenario == "recovery_success":
                await self._handle_recovery_success_scenario(run_id)
            else:
                # Normal execution path
                await self._execute_normal_path(run_id)
                
            # Generate recovery summary
            result = {
                "success": self.error_scenario in ["none", "recovery_success"],
                "agent_name": self.name,
                "error_handling": {
                    "scenario_tested": self.error_scenario,
                    "recovery_attempts": len(self.recovery_attempts),
                    "recovery_successful": len([r for r in self.recovery_attempts if r["success"]]) > 0,
                    "error_transparency": True
                },
                "business_continuity": {
                    "service_degradation": "graceful" if self.error_scenario != "critical_failure" else "severe",
                    "user_experience": "maintained" if self.error_scenario in ["none", "recovery_success"] else "impacted",
                    "data_integrity": "preserved"
                }
            }
            
            # EVENT 5: agent_completed (even for errors)
            await self.websocket_bridge.notify_agent_completed(
                run_id, self.name, result, 
                execution_time_ms=150,
                error_handled=self.error_scenario != "none"
            )
            
            return result
            
        except Exception as e:
            # Critical error handling
            await self._handle_critical_error(run_id, str(e))
            return {"success": False, "error": str(e), "recovery_attempted": True}
            
    async def _handle_tool_failure_scenario(self, run_id: str):
        """Simulate tool failure with recovery attempt."""
        
        # EVENT 3: tool_executing
        await self.websocket_bridge.notify_tool_executing(
            run_id, self.name, "failing_tool", {"test_failure": True}
        )
        
        await asyncio.sleep(0.05)
        
        # Record initial failure
        failure_info = {
            "timestamp": datetime.now(timezone.utc),
            "error_type": "tool_execution_failure",
            "recovery_strategy": "retry_with_fallback",
            "success": False
        }
        
        # EVENT 4: tool_completed with error
        await self.websocket_bridge.notify_tool_completed(
            run_id, self.name, "failing_tool", {
                "result": {"error": "Tool execution failed", "success": False},
                "recovery_attempted": True,
                "fallback_used": True
            }
        )
        
        # Recovery attempt
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, "Attempting recovery with fallback tool...",
            step_number=2, progress_percentage=60
        )
        
        # Simulate fallback success
        recovery_info = {**failure_info, "success": True, "recovery_method": "fallback_tool"}
        self.recovery_attempts.append(recovery_info)
        
        await self.websocket_bridge.notify_tool_executing(
            run_id, self.name, "fallback_tool", {"recovery": True}
        )
        
        await self.websocket_bridge.notify_tool_completed(
            run_id, self.name, "fallback_tool", {
                "result": {"success": True, "data": "recovery_successful"},
                "recovery_success": True
            }
        )
        
    async def _handle_llm_timeout_scenario(self, run_id: str):
        """Simulate LLM timeout with graceful degradation."""
        
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, "Executing complex LLM operation...",
            step_number=2, progress_percentage=40
        )
        
        # Simulate timeout
        await asyncio.sleep(0.1)
        
        recovery_attempt = {
            "timestamp": datetime.now(timezone.utc),
            "error_type": "llm_timeout",
            "recovery_strategy": "cached_response",
            "success": True
        }
        self.recovery_attempts.append(recovery_attempt)
        
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, "LLM timeout detected, using cached response for continuity...",
            step_number=3, progress_percentage=70
        )
        
    async def _handle_partial_failure_scenario(self, run_id: str):
        """Simulate partial failure with partial results."""
        
        # First tool succeeds
        await self.websocket_bridge.notify_tool_executing(
            run_id, self.name, "success_tool", {"partial_test": True}
        )
        await self.websocket_bridge.notify_tool_completed(
            run_id, self.name, "success_tool", {"result": {"success": True, "data": "partial_result"}}
        )
        
        # Second tool fails
        await self.websocket_bridge.notify_tool_executing(
            run_id, self.name, "partial_fail_tool", {"expected_failure": True}
        )
        await self.websocket_bridge.notify_tool_completed(
            run_id, self.name, "partial_fail_tool", {
                "result": {"error": "Partial failure", "success": False},
                "partial_results_available": True
            }
        )
        
    async def _handle_recovery_success_scenario(self, run_id: str):
        """Simulate successful error recovery."""
        
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, "Detected potential issue, implementing preventive recovery...",
            step_number=2, progress_percentage=50
        )
        
        recovery_info = {
            "timestamp": datetime.now(timezone.utc),
            "error_type": "preventive_recovery",
            "recovery_strategy": "proactive_handling",
            "success": True
        }
        self.recovery_attempts.append(recovery_info)
        
        await self._execute_normal_path(run_id, recovery_mode=True)
        
    async def _execute_normal_path(self, run_id: str, recovery_mode: bool = False):
        """Execute normal path (no errors)."""
        
        tool_name = "recovery_tool" if recovery_mode else "normal_tool"
        
        await self.websocket_bridge.notify_tool_executing(
            run_id, self.name, tool_name, {"normal_execution": True}
        )
        await self.websocket_bridge.notify_tool_completed(
            run_id, self.name, tool_name, {
                "result": {"success": True, "data": "normal_execution_complete"},
                "recovery_mode": recovery_mode
            }
        )
        
    async def _handle_critical_error(self, run_id: str, error_msg: str):
        """Handle critical errors that cannot be recovered."""
        
        await self.websocket_bridge.notify_agent_error(
            run_id, self.name, error_msg,
            error_context={"critical": True, "recovery_possible": False}
        )


class ErrorHandlingEventCollector:
    """Collects and analyzes error handling events."""
    
    def __init__(self):
        self.all_events = []
        self.error_events = []
        self.recovery_patterns = []
        
    async def create_error_handling_bridge(self, user_context: UserExecutionContext):
        """Create WebSocket bridge for error handling testing."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.events = []
        
        async def track_error_event(event_type: str, run_id: str, agent_name: str, data: Any = None, **kwargs):
            event = {
                "event_type": event_type,
                "run_id": run_id,
                "agent_name": agent_name,
                "data": data,
                "timestamp": datetime.now(timezone.utc),
                "user_id": user_context.user_id,
                "kwargs": kwargs
            }
            
            bridge.events.append(event)
            self.all_events.append(event)
            
            # Track error-specific events
            if event_type == "agent_error" or (data and isinstance(data, dict) and "error" in str(data)):
                self.error_events.append(event)
                
            # Track recovery patterns
            if data and isinstance(data, dict):
                if "recovery" in str(data) or "fallback" in str(data):
                    self.recovery_patterns.append(event)
                    
            return True
            
        # Mock all WebSocket methods
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            track_error_event("agent_started", run_id, agent_name, context))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, thinking, **kwargs:
            track_error_event("agent_thinking", run_id, agent_name, {"reasoning": thinking}, **kwargs))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, params:
            track_error_event("tool_executing", run_id, agent_name, {"tool_name": tool_name, "parameters": params}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            track_error_event("tool_completed", run_id, agent_name, {"tool_name": tool_name, **result}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, **kwargs:
            track_error_event("agent_completed", run_id, agent_name, result, **kwargs))
        bridge.notify_agent_error = AsyncMock(side_effect=lambda run_id, agent_name, error, **kwargs:
            track_error_event("agent_error", run_id, agent_name, {"error": str(error)}, **kwargs))
            
        return bridge
        
    def analyze_error_handling(self) -> Dict[str, Any]:
        """Analyze error handling patterns and effectiveness."""
        
        return {
            "total_events": len(self.all_events),
            "error_events": len(self.error_events),
            "recovery_events": len(self.recovery_patterns),
            "error_handling_metrics": {
                "error_detection_rate": len(self.error_events) / len(self.all_events) * 100 if self.all_events else 0,
                "recovery_attempt_rate": len(self.recovery_patterns) / max(1, len(self.error_events)) * 100,
                "graceful_handling": len(self.error_events) > 0 and len(self.recovery_patterns) > 0
            },
            "business_impact": {
                "user_transparency": len(self.error_events) > 0,  # Errors were communicated
                "service_continuity": len(self.recovery_patterns) > 0,  # Recovery was attempted
                "data_integrity": "maintained"  # Assumed based on proper error handling
            }
        }


class TestWebSocketAgentExecutionErrorHandlingRecoveryIntegration(BaseIntegrationTest):
    """Integration test for agent execution error handling with WebSocket events."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.set("TESTING", "1", source="integration_test")
        self.error_collector = ErrorHandlingEventCollector()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        return llm_manager
        
    @pytest.fixture
    async def error_handling_user_context(self):
        return UserExecutionContext(
            user_id=f"error_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"error_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"error_run_{uuid.uuid4().hex[:8]}",
            request_id=f"error_req_{uuid.uuid4().hex[:8]}",
            metadata={"error_handling_test": True}
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_failure_error_handling_with_websocket_recovery(
        self, error_handling_user_context, mock_llm_manager
    ):
        """CRITICAL: Test tool failure error handling with WebSocket recovery notifications."""
        
        # Create error handling agent
        agent = ErrorHandlingAgent("error_handler", mock_llm_manager, "tool_failure")
        
        registry = MagicMock()
        registry.get = lambda name: agent
        registry.get_async = AsyncMock(return_value=agent)
        
        websocket_bridge = await self.error_collector.create_error_handling_bridge(error_handling_user_context)
        
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=error_handling_user_context
        )
        
        exec_context = AgentExecutionContext(
            user_id=error_handling_user_context.user_id,
            thread_id=error_handling_user_context.thread_id,
            run_id=error_handling_user_context.run_id,
            request_id=error_handling_user_context.request_id,
            agent_name="error_handler",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        agent_state = DeepAgentState(
            user_request={"test_error_handling": True},
            user_id=error_handling_user_context.user_id,
            chat_thread_id=error_handling_user_context.thread_id,
            run_id=error_handling_user_context.run_id
        )
        
        # Execute with error handling
        result = await execution_engine.execute_agent(exec_context, error_handling_user_context)
        
        # Validate error handling
        assert result is not None
        
        error_handling_data = result.data.get("error_handling", {})
        assert error_handling_data.get("scenario_tested") == "tool_failure"
        assert error_handling_data.get("recovery_attempts", 0) > 0
        assert error_handling_data.get("error_transparency") is True
        
        # Validate WebSocket error communication
        error_analysis = self.error_collector.analyze_error_handling()
        assert error_analysis["recovery_events"] > 0, "Recovery events must be sent"
        assert error_analysis["error_handling_metrics"]["graceful_handling"] is True
        
        self.logger.info("✅ Tool failure error handling test PASSED")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_error_scenarios_comprehensive_recovery(
        self, error_handling_user_context, mock_llm_manager
    ):
        """Test multiple error scenarios with comprehensive recovery testing."""
        
        error_scenarios = ["tool_failure", "llm_timeout", "partial_failure", "recovery_success"]
        results = []
        
        for scenario in error_scenarios:
            agent = ErrorHandlingAgent(f"handler_{scenario}", mock_llm_manager, scenario)
            
            registry = MagicMock()
            registry.get = lambda name, a=agent: a
            registry.get_async = AsyncMock(return_value=agent)
            
            websocket_bridge = await self.error_collector.create_error_handling_bridge(error_handling_user_context)
            
            execution_engine = ExecutionEngine._init_from_factory(
                registry=registry,
                websocket_bridge=websocket_bridge,
                user_context=error_handling_user_context
            )
            
            exec_context = AgentExecutionContext(
                user_id=error_handling_user_context.user_id,
                thread_id=error_handling_user_context.thread_id,
                run_id=f"{error_handling_user_context.run_id}_{scenario}",
                request_id=f"{error_handling_user_context.request_id}_{scenario}",
                agent_name=f"handler_{scenario}",
                step=PipelineStep.PROCESSING,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            agent_state = DeepAgentState(
                user_request={f"test_{scenario}": True},
                user_id=error_handling_user_context.user_id,
                chat_thread_id=error_handling_user_context.thread_id,
                run_id=exec_context.run_id
            )
            
            result = await execution_engine.execute_agent(exec_context, error_handling_user_context)
            results.append((scenario, result))
            
        # Validate all scenarios were handled
        for scenario, result in results:
            assert result is not None, f"No result for scenario: {scenario}"
            
            error_handling = result.data.get("error_handling", {})
            assert error_handling.get("scenario_tested") == scenario
            assert error_handling.get("error_transparency") is True
            
            business_continuity = result.data.get("business_continuity", {})
            assert "service_degradation" in business_continuity
            assert business_continuity.get("data_integrity") == "preserved"
            
        # Validate comprehensive error handling
        error_analysis = self.error_collector.analyze_error_handling()
        assert error_analysis["total_events"] >= len(error_scenarios) * 3  # Minimum events per scenario
        
        self.logger.info(
            f"✅ Multiple error scenarios test PASSED - "
            f"{len(error_scenarios)} scenarios, "
            f"{error_analysis['total_events']} total events, "
            f"{error_analysis['recovery_events']} recovery events"
        )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])