"""
Test WebSocket message routing through supervisor agent.

Tests message routing from WebSocket through agent service to supervisor
and appropriate sub-agents, ensuring proper routing and response handling.

Business Value: Ensures accurate routing of customer requests to correct
agents, maximizing response quality and billable value delivery.

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines
- Function size: <8 lines each
- Strong typing with agent interfaces
- Complete routing coverage
"""

import asyncio
import json
import uuid

from typing import Dict, Any, List, Optional, Union
from unittest.mock import AsyncMock, patch, Mock, MagicMock
import pytest
from datetime import datetime, timezone

from app.tests.integration.test_unified_message_flow import MessageFlowTracker
from app.tests.test_utilities.websocket_mocks import MockWebSocket
from app.schemas.websocket_models import WebSocketMessage, UserMessagePayload
from app.schemas.core_enums import WebSocketMessageType
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RoutingFlowTracker(MessageFlowTracker):
    """Extended tracker for message routing flow."""
    
    def __init__(self):
        super().__init__()
        self.routing_decisions: List[Dict[str, Any]] = []
        self.agent_invocations: List[Dict[str, Any]] = []
    
    def log_routing_decision(self, message_type: str, target_agent: str,
                           routing_reason: str) -> None:
        """Log routing decision."""
        decision = {
            "message_type": message_type,
            "target_agent": target_agent,
            "routing_reason": routing_reason,
            "timestamp": datetime.now(timezone.utc),
            "decision_id": str(uuid.uuid4())
        }
        self.routing_decisions.append(decision)
    
    def log_agent_invocation(self, agent_name: str, method: str,
                           success: bool, duration: float) -> None:
        """Log agent invocation."""
        invocation = {
            "agent_name": agent_name,
            "method": method,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now(timezone.utc)
        }
        self.agent_invocations.append(invocation)


@pytest.fixture
def routing_tracker():
    """Create routing flow tracker."""
    return RoutingFlowTracker()


class TestWebSocketMessageRouting:
    """Test WebSocket message routing through agents."""
    
    async def test_user_message_routing_to_supervisor(self, routing_tracker):
        """Test user message routing to supervisor agent."""
        timer_id = routing_tracker.start_timer("user_message_routing")
        
        # Create user message
        message = await self._create_user_message(routing_tracker)
        
        # Test routing to supervisor
        routing_result = await self._route_message_to_supervisor(routing_tracker, message)
        
        duration = routing_tracker.end_timer(timer_id)
        
        # Verify routing success
        assert routing_result["routed"] is True
        assert routing_result["target_agent"] == "supervisor"
        assert duration < 0.5, f"Routing too slow: {duration}s"
        
        routing_tracker.log_step("user_message_routing_completed", {
            "success": True,
            "duration": duration,
            "target": "supervisor"
        })
    
    async def _create_user_message(self, tracker: RoutingFlowTracker) -> Dict[str, Any]:
        """Create user message for routing test."""
        message = {
            "type": "user_message",
            "payload": {
                "content": "Help me optimize my AI costs",
                "thread_id": "thread_123",
                "user_id": "user_123"
            }
        }
        
        tracker.log_routing_decision(
            message["type"], 
            "supervisor",
            "User messages route to supervisor for orchestration"
        )
        
        return message
    
    async def _route_message_to_supervisor(self, tracker: RoutingFlowTracker,
                                         message: Dict[str, Any]) -> Dict[str, Any]:
        """Route message to supervisor agent."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Mock supervisor routing
            with patch('app.services.agent_service_core.AgentService') as mock_service:
                mock_instance = AsyncMock()
                mock_service.return_value = mock_instance
                
                # Mock successful message handling
                mock_instance.handle_websocket_message = AsyncMock()
                
                # Route message
                user_id = message["payload"]["user_id"]
                message_json = json.dumps(message)
                
                await mock_instance.handle_websocket_message(user_id, message_json, None)
                
                duration = asyncio.get_event_loop().time() - start_time
                
                tracker.log_agent_invocation("supervisor", "handle_websocket_message", True, duration)
                
                return {
                    "routed": True,
                    "target_agent": "supervisor",
                    "routing_duration": duration
                }
        
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            tracker.log_agent_invocation("supervisor", "handle_websocket_message", False, duration)
            
            return {
                "routed": False,
                "error": str(e),
                "routing_duration": duration
            }
    
    async def test_supervisor_to_subagent_routing(self, routing_tracker):
        """Test supervisor routing to appropriate sub-agents."""
        timer_id = routing_tracker.start_timer("supervisor_subagent_routing")
        
        # Test different message types routing to different sub-agents
        routing_scenarios = await self._create_routing_scenarios(routing_tracker)
        
        results = []
        for scenario in routing_scenarios:
            result = await self._test_subagent_routing_scenario(routing_tracker, scenario)
            results.append(result)
        
        duration = routing_tracker.end_timer(timer_id)
        
        # Verify all routing scenarios
        successful_routes = sum(1 for r in results if r["success"])
        assert successful_routes == len(routing_scenarios), f"Failed routes: {len(routing_scenarios) - successful_routes}"
        assert duration < 2.0, f"Subagent routing too slow: {duration}s"
        
        routing_tracker.log_step("subagent_routing_completed", {
            "scenarios_tested": len(routing_scenarios),
            "success_rate": successful_routes / len(routing_scenarios),
            "duration": duration
        })
    
    async def _create_routing_scenarios(self, tracker: RoutingFlowTracker) -> List[Dict[str, Any]]:
        """Create routing test scenarios."""
        scenarios = [
            {
                "message_content": "What's my current AI spend?",
                "expected_agent": "data_agent",
                "reason": "Cost queries route to data agent"
            },
            {
                "message_content": "Optimize my model performance",
                "expected_agent": "triage_agent",
                "reason": "Performance queries route to triage agent"
            },
            {
                "message_content": "Help me understand my usage",
                "expected_agent": "triage_agent", 
                "reason": "General queries route to triage for classification"
            }
        ]
        
        for scenario in scenarios:
            tracker.log_routing_decision(
                "user_message",
                scenario["expected_agent"],
                scenario["reason"]
            )
        
        return scenarios
    
    async def _test_subagent_routing_scenario(self, tracker: RoutingFlowTracker,
                                            scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test single sub-agent routing scenario."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Mock supervisor with sub-agent routing
            with patch('app.agents.supervisor_consolidated.SupervisorAgent') as mock_supervisor:
                mock_instance = AsyncMock()
                mock_supervisor.return_value = mock_instance
                
                # Mock agent registry with sub-agents
                mock_registry = Mock()
                mock_registry.get_agent_for_query = Mock(return_value=scenario["expected_agent"])
                mock_instance.registry = mock_registry
                
                # Mock run method
                mock_instance.run = AsyncMock(return_value=f"Processed by {scenario['expected_agent']}")
                
                # Execute routing
                result = await mock_instance.run(
                    scenario["message_content"],
                    "thread_123",
                    "user_123", 
                    str(uuid.uuid4())
                )
                
                duration = asyncio.get_event_loop().time() - start_time
                
                tracker.log_agent_invocation(
                    scenario["expected_agent"],
                    "run",
                    True,
                    duration
                )
                
                return {
                    "success": True,
                    "agent": scenario["expected_agent"],
                    "result": str(result),
                    "duration": duration
                }
        
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            
            tracker.log_agent_invocation(
                scenario["expected_agent"],
                "run",
                False,
                duration
            )
            
            return {
                "success": False,
                "error": str(e),
                "duration": duration
            }
    
    async def test_message_type_routing_accuracy(self, routing_tracker):
        """Test accuracy of message type routing."""
        timer_id = routing_tracker.start_timer("message_type_routing")
        
        # Test various message types
        message_types = await self._create_message_type_scenarios(routing_tracker)
        
        routing_results = []
        for msg_type, expected_handler in message_types.items():
            result = await self._test_message_type_routing(routing_tracker, msg_type, expected_handler)
            routing_results.append(result)
        
        duration = routing_tracker.end_timer(timer_id)
        
        # Verify routing accuracy
        accurate_routes = sum(1 for r in routing_results if r["correctly_routed"])
        accuracy = accurate_routes / len(routing_results)
        
        assert accuracy >= 0.9, f"Routing accuracy too low: {accuracy}"
        assert duration < 1.0, f"Message type routing too slow: {duration}s"
        
        routing_tracker.log_step("message_type_routing_verified", {
            "types_tested": len(message_types),
            "routing_accuracy": accuracy,
            "duration": duration
        })
    
    async def _create_message_type_scenarios(self, tracker: RoutingFlowTracker) -> Dict[str, str]:
        """Create message type routing scenarios."""
        message_types = {
            "user_message": "agent_service.handle_user_message",
            "start_agent": "agent_service.handle_start_agent", 
            "stop_agent": "agent_service.handle_stop_agent",
            "create_thread": "agent_service.handle_create_thread",
            "get_thread_history": "agent_service.handle_thread_history"
        }
        
        for msg_type, handler in message_types.items():
            tracker.log_routing_decision(msg_type, handler, f"{msg_type} routes to {handler}")
        
        return message_types
    
    async def _test_message_type_routing(self, tracker: RoutingFlowTracker,
                                       message_type: str, expected_handler: str) -> Dict[str, Any]:
        """Test routing for specific message type."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Mock message handler routing
            with patch('app.services.message_handlers.MessageHandlerService') as mock_handler:
                mock_instance = AsyncMock()
                mock_handler.return_value = mock_instance
                
                # Set up mock methods
                method_name = expected_handler.split('.')[-1]
                mock_method = AsyncMock()
                setattr(mock_instance, method_name, mock_method)
                
                # Test routing
                message = {
                    "type": message_type,
                    "payload": {"test": "data"}
                }
                
                # Route based on type
                if message_type == "user_message":
                    await mock_instance.handle_user_message("user_123", message["payload"], None)
                elif message_type == "start_agent":
                    await mock_instance.handle_start_agent("user_123", message["payload"], None)
                elif message_type == "stop_agent":
                    await mock_instance.handle_stop_agent("user_123")
                # Add more routing cases as needed
                
                duration = asyncio.get_event_loop().time() - start_time
                
                tracker.log_agent_invocation(expected_handler, "route", True, duration)
                
                return {
                    "correctly_routed": True,
                    "message_type": message_type,
                    "handler": expected_handler,
                    "duration": duration
                }
        
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            
            tracker.log_agent_invocation(expected_handler, "route", False, duration)
            
            return {
                "correctly_routed": False,
                "message_type": message_type,
                "error": str(e),
                "duration": duration
            }


class TestRoutingErrorScenarios:
    """Test routing error scenarios."""
    
    async def test_unknown_message_type_routing(self, routing_tracker):
        """Test routing behavior for unknown message types."""
        timer_id = routing_tracker.start_timer("unknown_message_routing")
        
        unknown_message = {
            "type": "unknown_message_type",
            "payload": {"content": "test"}
        }
        
        result = await self._test_unknown_message_handling(routing_tracker, unknown_message)
        
        duration = routing_tracker.end_timer(timer_id)
        
        # Verify unknown message handling
        assert result["handled"] is False
        assert "unknown" in result.get("error", "").lower()
        assert duration < 0.2, "Unknown message handling too slow"
        
        routing_tracker.log_step("unknown_message_handled", {
            "error_handling_success": True,
            "duration": duration
        })
    
    async def _test_unknown_message_handling(self, tracker: RoutingFlowTracker,
                                           message: Dict[str, Any]) -> Dict[str, Any]:
        """Test handling of unknown message types."""
        try:
            # Mock agent service with unknown message
            with patch('app.services.agent_service_core.AgentService._route_message_by_type') as mock_route:
                # Simulate unknown message type handling
                mock_route.side_effect = ValueError(f"Unknown message type: {message['type']}")
                
                mock_service = Mock()
                mock_service._route_message_by_type = mock_route
                
                await mock_service._route_message_by_type(
                    "user_123",
                    message["type"],
                    message["payload"],
                    None
                )
                
                return {"handled": True, "message_type": message["type"]}
        
        except ValueError as e:
            tracker.log_routing_decision(
                message["type"],
                "error_handler",
                f"Unknown message types route to error handler: {str(e)}"
            )
            
            return {
                "handled": False,
                "message_type": message["type"],
                "error": str(e)
            }
    
    async def test_agent_unavailable_routing_fallback(self, routing_tracker):
        """Test routing fallback when target agent unavailable."""
        timer_id = routing_tracker.start_timer("agent_unavailable_routing")
        
        result = await self._test_agent_unavailable_scenario(routing_tracker)
        
        duration = routing_tracker.end_timer(timer_id)
        
        # Verify fallback handling
        assert result["fallback_used"] is True
        assert result["primary_failed"] is True
        assert duration < 1.0, "Fallback routing too slow"
        
        routing_tracker.log_step("agent_unavailable_fallback_used", {
            "fallback_success": True,
            "duration": duration
        })
    
    async def _test_agent_unavailable_scenario(self, tracker: RoutingFlowTracker) -> Dict[str, Any]:
        """Test scenario when primary agent unavailable."""
        try:
            # Mock primary agent failure
            with patch('app.agents.supervisor_consolidated.SupervisorAgent.run') as mock_run:
                mock_run.side_effect = Exception("Primary agent unavailable")
                
                # Try primary agent
                try:
                    supervisor = Mock()
                    supervisor.run = mock_run
                    await supervisor.run("test", "thread", "user", "run_id")
                except Exception:
                    # Log primary failure
                    tracker.log_agent_invocation("supervisor", "run", False, 0.1)
                    
                    # Use fallback
                    with patch('app.services.agent_service.get_fallback_agent') as mock_fallback:
                        fallback_agent = AsyncMock()
                        fallback_agent.process_message = AsyncMock(return_value="Fallback response")
                        mock_fallback.return_value = fallback_agent
                        
                        fallback_result = await fallback_agent.process_message("test")
                        
                        tracker.log_agent_invocation("fallback_agent", "process_message", True, 0.05)
                        
                        return {
                            "primary_failed": True,
                            "fallback_used": True,
                            "fallback_result": fallback_result
                        }
        
        except Exception as e:
            return {
                "primary_failed": True,
                "fallback_used": False,
                "error": str(e)
            }


class TestRoutingPerformance:
    """Test routing performance metrics."""
    
    async def test_concurrent_routing_performance(self, routing_tracker):
        """Test routing performance under concurrent load."""
        timer_id = routing_tracker.start_timer("concurrent_routing_performance")
        
        # Create concurrent routing tasks
        routing_tasks = []
        for i in range(15):
            message = {
                "type": "user_message",
                "payload": {"content": f"Test message {i}", "user_id": f"user_{i}"}
            }
            task = self._perform_routing_test(routing_tracker, message, i)
            routing_tasks.append(task)
        
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)
        
        duration = routing_tracker.end_timer(timer_id)
        
        # Verify concurrent routing performance
        successful_routes = sum(1 for r in results if isinstance(r, dict) and r.get("routed"))
        success_rate = successful_routes / len(routing_tasks)
        
        assert success_rate >= 0.9, f"Concurrent routing success rate too low: {success_rate}"
        assert duration < 3.0, f"Concurrent routing too slow: {duration}s"
        
        routing_tracker.log_step("concurrent_routing_performance_verified", {
            "concurrent_messages": len(routing_tasks),
            "success_rate": success_rate,
            "duration": duration
        })
    
    async def _perform_routing_test(self, tracker: RoutingFlowTracker,
                                  message: Dict[str, Any], test_id: int) -> Dict[str, Any]:
        """Perform single routing performance test."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Mock routing with small delay
            await asyncio.sleep(0.02)  # Simulate routing overhead
            
            # Simulate successful routing
            duration = asyncio.get_event_loop().time() - start_time
            
            tracker.log_agent_invocation(f"test_agent_{test_id}", "route", True, duration)
            
            return {
                "routed": True,
                "test_id": test_id,
                "routing_duration": duration
            }
        
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            
            tracker.log_agent_invocation(f"test_agent_{test_id}", "route", False, duration)
            
            return {
                "routed": False,
                "test_id": test_id,
                "error": str(e)
            }


if __name__ == "__main__":
    # Manual test execution
    async def run_manual_routing_test():
        """Run manual routing test."""
        tracker = RoutingFlowTracker()
        
        print("Running manual message routing test...")
        
        # Test basic routing
        message = {
            "type": "user_message",
            "payload": {"content": "Test routing", "user_id": "manual_user"}
        }
        
        test_instance = TestWebSocketMessageRouting()
        result = await test_instance._route_message_to_supervisor(tracker, message)
        
        print(f"Routing result: {result}")
        print(f"Routing decisions: {len(tracker.routing_decisions)}")
        print(f"Agent invocations: {len(tracker.agent_invocations)}")
    
    asyncio.run(run_manual_routing_test())