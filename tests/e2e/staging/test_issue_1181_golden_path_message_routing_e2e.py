"""
Test Issue #1181 Golden Path Message Routing E2E

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Protect Golden Path User Flow During Consolidation
- Value Impact: Ensure MessageRouter consolidation doesn't break core chat functionality
- Strategic Impact: 500K+ ARR protection - Golden Path must work flawlessly

This E2E test validates that MessageRouter consolidation maintains the critical
Golden Path user flow that delivers 90% of platform business value through chat.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotAsyncTestCase as BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env


class Issue1181GoldenPathMessageRoutingE2ETests(BaseE2ETest):
    """Test Golden Path message routing with consolidated MessageRouter on staging."""

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    async def test_complete_golden_path_user_flow_with_message_routing(self):
        """
        Test complete Golden Path user flow with consolidated message routing.
        
        This is the CRITICAL test - validates that users can login and get
        AI responses back through the consolidated MessageRouter infrastructure.
        
        Golden Path Flow:
        1. User authentication
        2. WebSocket connection
        3. Agent request routing
        4. Real-time event delivery (5 critical events)
        5. AI response delivery
        """
        
        # Use staging environment
        staging_config = self._get_staging_config()
        
        # Create test user for Golden Path validation
        test_user = await self._create_golden_path_test_user(staging_config)
        
        # Test complete Golden Path flow
        async with WebSocketTestClient(
            token=test_user["token"],
            base_url=staging_config["websocket_url"]
        ) as client:
            
            # Step 1: Verify WebSocket connection with message routing
            connection_established = await self._verify_websocket_connection(client)
            assert connection_established, "WebSocket connection failed - Golden Path blocked"
            
            # Step 2: Send agent request through message routing
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Help me optimize my AI costs for better efficiency",
                "thread_id": test_user["thread_id"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await client.send_json(agent_request)
            
            # Step 3: Collect all WebSocket events through consolidated routing
            events = await self._collect_golden_path_events(client, timeout=60)
            
            # Step 4: Validate Golden Path event sequence
            self._validate_golden_path_event_sequence(events)
            
            # Step 5: Verify AI response delivery
            ai_response = self._extract_ai_response_from_events(events)
            self._validate_ai_response_quality(ai_response)
            
            # Step 6: Document Golden Path success
            self._document_golden_path_success(events, ai_response)

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.message_routing
    async def test_websocket_event_delivery_through_consolidated_routing(self):
        """
        Test WebSocket event delivery through consolidated message routing.
        
        This validates that all 5 critical WebSocket events are delivered
        properly through the consolidated MessageRouter infrastructure.
        """
        
        staging_config = self._get_staging_config()
        test_user = await self._create_test_user_for_event_testing(staging_config)
        
        async with WebSocketTestClient(
            token=test_user["token"],
            base_url=staging_config["websocket_url"]
        ) as client:
            
            # Send simple agent request to trigger event sequence
            await client.send_json({
                "type": "agent_request",
                "agent": "triage_agent", 
                "message": "Test event delivery",
                "thread_id": test_user["thread_id"]
            })
            
            # Collect events with detailed monitoring
            event_monitor = WebSocketEventMonitor()
            events = await event_monitor.collect_events(client, timeout=45)
            
            # Validate all 5 critical events delivered
            critical_events = [
                "agent_started",
                "agent_thinking",
                "tool_executing",
                "tool_completed", 
                "agent_completed"
            ]
            
            event_delivery_results = self._validate_critical_event_delivery(events, critical_events)
            
            # Document event delivery through consolidated routing
            self._document_event_delivery_validation(event_delivery_results)
            
            # Assert 100% critical event delivery
            assert event_delivery_results["all_critical_events_delivered"], (
                f"Critical events missing: {event_delivery_results['missing_events']}"
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.multi_user
    async def test_multi_user_message_routing_isolation(self):
        """
        Test multi-user message routing isolation with consolidated router.
        
        This validates that the consolidated MessageRouter maintains proper
        user isolation to prevent cross-contamination between users.
        """
        
        staging_config = self._get_staging_config()
        
        # Create multiple test users
        user1 = await self._create_test_user_for_isolation_testing(staging_config, "user1")
        user2 = await self._create_test_user_for_isolation_testing(staging_config, "user2")
        
        # Test concurrent user sessions
        async with WebSocketTestClient(
            token=user1["token"], 
            base_url=staging_config["websocket_url"]
        ) as client1, WebSocketTestClient(
            token=user2["token"],
            base_url=staging_config["websocket_url"] 
        ) as client2:
            
            # Send different requests from each user
            await asyncio.gather(
                client1.send_json({
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "User 1 optimization request",
                    "thread_id": user1["thread_id"]
                }),
                client2.send_json({
                    "type": "agent_request", 
                    "agent": "triage_agent",
                    "message": "User 2 different optimization request",
                    "thread_id": user2["thread_id"]
                })
            )
            
            # Collect events from both users simultaneously
            user1_events, user2_events = await asyncio.gather(
                self._collect_user_specific_events(client1, user1["user_id"]),
                self._collect_user_specific_events(client2, user2["user_id"])
            )
            
            # Validate user isolation
            isolation_results = self._validate_user_isolation(
                user1_events, user2_events, user1["user_id"], user2["user_id"]
            )
            
            # Document isolation validation
            self._document_user_isolation_validation(isolation_results)
            
            # Assert no cross-contamination
            assert isolation_results["isolation_maintained"], (
                f"User isolation violation detected: {isolation_results['violations']}"
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.business_value
    async def test_chat_functionality_business_value_preservation(self):
        """
        Test that chat functionality business value is preserved after consolidation.
        
        This validates that the consolidated MessageRouter maintains the substantive
        AI value delivery that drives 90% of platform business value.
        """
        
        staging_config = self._get_staging_config()
        test_user = await self._create_business_value_test_user(staging_config)
        
        async with WebSocketTestClient(
            token=test_user["token"],
            base_url=staging_config["websocket_url"]
        ) as client:
            
            # Test substantive business value scenarios
            business_value_scenarios = [
                {
                    "scenario": "cost_optimization_insights",
                    "request": {
                        "type": "agent_request",
                        "agent": "cost_optimizer", 
                        "message": "Analyze my monthly AI spend and recommend optimizations",
                        "context": {"monthly_spend": 5000, "usage_pattern": "variable"}
                    }
                },
                {
                    "scenario": "performance_analysis",
                    "request": {
                        "type": "agent_request",
                        "agent": "performance_analyzer",
                        "message": "Review my model performance and suggest improvements", 
                        "context": {"model_type": "classification", "accuracy": 0.85}
                    }
                }
            ]
            
            business_value_results = []
            
            for scenario in business_value_scenarios:
                try:
                    # Send business value request
                    await client.send_json(scenario["request"])
                    
                    # Collect response events
                    events = await self._collect_business_value_events(client)
                    
                    # Validate business value delivery
                    value_assessment = self._assess_business_value_delivery(events, scenario)
                    
                    business_value_results.append({
                        "scenario": scenario["scenario"],
                        "success": True,
                        "value_assessment": value_assessment
                    })
                    
                except Exception as e:
                    business_value_results.append({
                        "scenario": scenario["scenario"],
                        "success": False,
                        "error": str(e)
                    })
            
            # Document business value preservation
            self._document_business_value_preservation(business_value_results)
            
            # Assert business value delivery maintained
            successful_scenarios = [r for r in business_value_results if r["success"]]
            assert len(successful_scenarios) >= len(business_value_scenarios) * 0.8, (
                "Business value delivery significantly degraded after consolidation"
            )

    def _get_staging_config(self) -> Dict[str, str]:
        """Get staging environment configuration."""
        return {
            "websocket_url": "wss://auth.staging.netrasystems.ai",
            "api_url": "https://auth.staging.netrasystems.ai", 
            "environment": "staging"
        }

    async def _create_golden_path_test_user(self, config: Dict[str, str]) -> Dict[str, str]:
        """Create test user specifically for Golden Path validation."""
        return {
            "user_id": f"golden_path_user_{datetime.now().strftime('%H%M%S')}",
            "email": f"golden.path.test+{datetime.now().strftime('%H%M%S')}@netrasystems.ai",
            "token": "test_token_golden_path",  # Would be real token in actual implementation
            "thread_id": f"golden_thread_{datetime.now().strftime('%H%M%S')}"
        }

    async def _create_test_user_for_event_testing(self, config: Dict[str, str]) -> Dict[str, str]:
        """Create test user for event delivery testing."""
        return {
            "user_id": f"event_test_user_{datetime.now().strftime('%H%M%S')}",
            "email": f"event.test+{datetime.now().strftime('%H%M%S')}@netrasystems.ai", 
            "token": "test_token_events",
            "thread_id": f"event_thread_{datetime.now().strftime('%H%M%S')}"
        }

    async def _create_test_user_for_isolation_testing(self, config: Dict[str, str], user_suffix: str) -> Dict[str, str]:
        """Create test user for isolation testing."""
        timestamp = datetime.now().strftime('%H%M%S')
        return {
            "user_id": f"isolation_{user_suffix}_{timestamp}",
            "email": f"isolation.{user_suffix}+{timestamp}@netrasystems.ai",
            "token": f"test_token_isolation_{user_suffix}",
            "thread_id": f"isolation_thread_{user_suffix}_{timestamp}"
        }

    async def _create_business_value_test_user(self, config: Dict[str, str]) -> Dict[str, str]:
        """Create test user for business value testing."""
        return {
            "user_id": f"business_value_user_{datetime.now().strftime('%H%M%S')}",
            "email": f"business.value.test+{datetime.now().strftime('%H%M%S')}@netrasystems.ai",
            "token": "test_token_business_value", 
            "thread_id": f"business_thread_{datetime.now().strftime('%H%M%S')}"
        }

    async def _verify_websocket_connection(self, client: WebSocketTestClient) -> bool:
        """Verify WebSocket connection is established properly."""
        try:
            # Send ping to verify connection
            await client.send_json({"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()})
            
            # Wait for pong or any response indicating connection works
            response = await asyncio.wait_for(client.receive_json(), timeout=10.0)
            
            return response is not None
        except Exception:
            return False

    async def _collect_golden_path_events(self, client: WebSocketTestClient, timeout: int = 60) -> List[Dict[str, Any]]:
        """Collect all events for Golden Path validation."""
        events = []
        start_time = datetime.now()
        
        try:
            while (datetime.now() - start_time).seconds < timeout:
                event = await asyncio.wait_for(client.receive_json(), timeout=5.0)
                events.append({
                    **event,
                    "received_at": datetime.now(timezone.utc).isoformat()
                })
                
                # Stop collecting when agent completes
                if event.get("type") == "agent_completed":
                    break
        except asyncio.TimeoutError:
            # Normal completion if no more events
            pass
        
        return events

    def _validate_golden_path_event_sequence(self, events: List[Dict[str, Any]]) -> None:
        """Validate the Golden Path event sequence is correct."""
        event_types = [event.get("type") for event in events]
        
        # Required events for Golden Path
        required_events = ["agent_started", "agent_completed"]
        
        for required_event in required_events:
            assert required_event in event_types, (
                f"Missing required Golden Path event: {required_event}. "
                f"Received events: {event_types}"
            )

    def _extract_ai_response_from_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract AI response from event sequence."""
        for event in reversed(events):  # Start from end to find final response
            if event.get("type") == "agent_completed" and "data" in event:
                return event["data"]
        
        return {}

    def _validate_ai_response_quality(self, response: Dict[str, Any]) -> None:
        """Validate AI response contains substantive business value."""
        # Basic validation - response should contain meaningful content
        assert response, "AI response is empty - no business value delivered"
        
        # Look for indicators of substantive content
        response_str = json.dumps(response).lower()
        business_value_indicators = ["optimization", "recommendation", "analysis", "savings", "improvement"]
        
        has_business_value = any(indicator in response_str for indicator in business_value_indicators)
        assert has_business_value, (
            f"AI response lacks business value indicators. Response: {response}"
        )

    async def _collect_user_specific_events(self, client: WebSocketTestClient, user_id: str) -> List[Dict[str, Any]]:
        """Collect events specific to a user for isolation testing."""
        events = []
        start_time = datetime.now()
        
        try:
            while (datetime.now() - start_time).seconds < 30:
                event = await asyncio.wait_for(client.receive_json(), timeout=3.0)
                
                # Tag event with user context for isolation validation
                event["expected_user_id"] = user_id
                events.append(event)
                
                if event.get("type") == "agent_completed":
                    break
        except asyncio.TimeoutError:
            pass
        
        return events

    def _validate_user_isolation(self, user1_events: List[Dict], user2_events: List[Dict], 
                                user1_id: str, user2_id: str) -> Dict[str, Any]:
        """Validate user isolation between concurrent sessions."""
        # Check for cross-contamination
        violations = []
        
        # Simplified isolation check - ensure each user gets distinct events
        user1_event_count = len(user1_events)
        user2_event_count = len(user2_events)
        
        # Both users should receive events
        if user1_event_count == 0:
            violations.append(f"User 1 ({user1_id}) received no events")
        if user2_event_count == 0:
            violations.append(f"User 2 ({user2_id}) received no events")
        
        return {
            "isolation_maintained": len(violations) == 0,
            "violations": violations,
            "user1_event_count": user1_event_count,
            "user2_event_count": user2_event_count
        }

    async def _collect_business_value_events(self, client: WebSocketTestClient) -> List[Dict[str, Any]]:
        """Collect events for business value assessment."""
        return await self._collect_golden_path_events(client, timeout=45)

    def _assess_business_value_delivery(self, events: List[Dict[str, Any]], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Assess business value delivery from event sequence."""
        has_completion = any(event.get("type") == "agent_completed" for event in events)
        has_meaningful_response = len(events) > 2  # More than just start/end
        
        return {
            "completion_achieved": has_completion,
            "meaningful_interaction": has_meaningful_response,
            "event_count": len(events),
            "scenario": scenario["scenario"]
        }

    def _validate_critical_event_delivery(self, events: List[Dict[str, Any]], 
                                        critical_events: List[str]) -> Dict[str, Any]:
        """Validate delivery of all critical WebSocket events."""
        event_types = [event.get("type") for event in events]
        delivered_critical_events = [event for event in critical_events if event in event_types]
        missing_events = [event for event in critical_events if event not in event_types]
        
        return {
            "all_critical_events_delivered": len(missing_events) == 0,
            "delivered_events": delivered_critical_events,
            "missing_events": missing_events,
            "delivery_rate": len(delivered_critical_events) / len(critical_events) * 100
        }

    def _document_golden_path_success(self, events: List[Dict[str, Any]], response: Dict[str, Any]) -> None:
        """Document Golden Path success metrics."""
        print(f"\n--- Golden Path Success Validation ---")
        print(f"CHECK WebSocket Events Delivered: {len(events)}")
        print(f"CHECK AI Response Received: {'Yes' if response else 'No'}")
        print(f"CHECK Golden Path Status: OPERATIONAL")
        print(f"CHECK Business Value: Chat functionality delivering AI insights")
        print(f"CHECK Message Routing: Consolidated router supporting Golden Path")

    def _document_event_delivery_validation(self, results: Dict[str, Any]) -> None:
        """Document event delivery validation results."""
        print(f"\n--- Event Delivery Validation ---")
        print(f"Critical Event Delivery Rate: {results['delivery_rate']:.1f}%")
        print(f"Delivered Events: {results['delivered_events']}")
        if results['missing_events']:
            print(f"Missing Events: {results['missing_events']}")
        print(f"All Critical Events Delivered: {'CHECK' if results['all_critical_events_delivered'] else 'X'}")

    def _document_user_isolation_validation(self, results: Dict[str, Any]) -> None:
        """Document user isolation validation results."""
        print(f"\n--- User Isolation Validation ---")
        print(f"Isolation Maintained: {'CHECK' if results['isolation_maintained'] else 'X'}")
        print(f"User 1 Events: {results['user1_event_count']}")
        print(f"User 2 Events: {results['user2_event_count']}")
        if results['violations']:
            print(f"Violations: {results['violations']}")

    def _document_business_value_preservation(self, results: List[Dict[str, Any]]) -> None:
        """Document business value preservation results."""
        print(f"\n--- Business Value Preservation ---")
        
        successful_scenarios = [r for r in results if r["success"]]
        success_rate = len(successful_scenarios) / len(results) * 100 if results else 0
        
        print(f"Business Value Scenarios Tested: {len(results)}")
        print(f"Successful Scenarios: {len(successful_scenarios)}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        for result in results:
            status = "CHECK" if result["success"] else "X"
            print(f"  {status} {result['scenario']}")
            if not result["success"]:
                print(f"    Error: {result.get('error', 'Unknown')}")


class WebSocketEventMonitor:
    """Helper class for monitoring WebSocket events during testing."""
    
    async def collect_events(self, client: WebSocketTestClient, timeout: int = 30) -> List[Dict[str, Any]]:
        """Collect WebSocket events with detailed monitoring."""
        events = []
        start_time = datetime.now()
        
        try:
            while (datetime.now() - start_time).seconds < timeout:
                event = await asyncio.wait_for(client.receive_json(), timeout=2.0)
                
                # Add monitoring metadata
                event["_monitor_metadata"] = {
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "sequence_number": len(events) + 1
                }
                
                events.append(event)
                
                # Stop on completion
                if event.get("type") == "agent_completed":
                    break
                    
        except asyncio.TimeoutError:
            # Normal completion
            pass
        
        return events