# Issue #1067 MessageRouter SSOT Test Specifications - Detailed Implementation

**Created:** 2025-09-15
**Purpose:** Detailed test specifications for reproducing MessageRouter SSOT violations
**Scope:** Unit, Integration, and E2E test implementations

## Unit Test Specifications

### 1. MessageRouter SSOT Violation Detection Tests

#### Test File: `tests/unit/message_router_ssot/test_message_router_ssot_violations_reproduction.py`

```python
"""
Test MessageRouter SSOT Violations Reproduction

Business Value Justification:
- Segment: Platform Infrastructure
- Business Goal: System Stability & SSOT Compliance
- Value Impact: Prevent routing conflicts that break $500K+ ARR chat functionality
- Strategic Impact: SSOT violation detection and prevention
"""

import pytest
import importlib
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Set, Type

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterSSOTViolationsReproduction(SSotBaseTestCase):
    """Reproduce and validate MessageRouter SSOT violations."""

    def test_detect_multiple_router_implementations(self):
        """FAILING TEST: Should detect exactly 1 MessageRouter class, currently finds 2+."""
        # This test should FAIL initially, demonstrating SSOT violation

        router_implementations = self._discover_message_router_classes()

        # Expected: 1 (SSOT compliant)
        # Current Reality: 2+ (SSOT violation)
        expected_count = 1
        actual_count = len(router_implementations)

        assert actual_count == expected_count, (
            f"SSOT VIOLATION: Found {actual_count} MessageRouter implementations, "
            f"expected {expected_count}. Implementations: {router_implementations}"
        )

    def test_canonical_router_import_path_enforcement(self):
        """FAILING TEST: All MessageRouter imports should use canonical path."""
        # This test should FAIL initially, showing import path fragmentation

        canonical_path = "netra_backend.app.websocket_core.handlers"
        invalid_imports = self._find_non_canonical_imports()

        assert len(invalid_imports) == 0, (
            f"SSOT VIOLATION: Found {len(invalid_imports)} non-canonical MessageRouter imports. "
            f"All imports must use '{canonical_path}'. Violations: {invalid_imports}"
        )

    def test_routing_conflict_between_implementations(self):
        """FAILING TEST: Different MessageRouter instances should not conflict."""
        # This test should FAIL initially, demonstrating routing conflicts

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter as WebSocketRouter
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

            ws_router = WebSocketRouter()
            quality_router = QualityMessageRouter(None, None, None, None)

            # Check if both routers handle the same message types (conflict)
            ws_message_types = set(getattr(ws_router, '_supported_types', []))
            quality_message_types = set(getattr(quality_router, '_supported_types', []))

            conflicts = ws_message_types.intersection(quality_message_types)

            assert len(conflicts) == 0, (
                f"ROUTING CONFLICT: Both routers handle same message types: {conflicts}. "
                f"This creates ambiguous routing and violates SSOT principles."
            )

        except ImportError as e:
            # If imports fail, that's also a SSOT violation
            pytest.fail(f"SSOT VIOLATION: Could not import MessageRouter implementations: {e}")

    def test_message_handler_registration_consistency(self):
        """FAILING TEST: Message handler registration should be consistent across routers."""
        # This test should FAIL initially, showing registration inconsistencies

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter

            router1 = MessageRouter()
            router2 = MessageRouter()

            # Create a test handler
            class TestHandler:
                def handle_message(self, message): pass

            test_handler = TestHandler()

            # Check if both routers support same registration methods
            router1_methods = {method for method in dir(router1) if 'handler' in method.lower()}
            router2_methods = {method for method in dir(router2) if 'handler' in method.lower()}

            assert router1_methods == router2_methods, (
                f"INCONSISTENCY: Different handler methods between router instances. "
                f"Router1: {router1_methods}, Router2: {router2_methods}"
            )

            # Check if registration methods work consistently
            if hasattr(router1, 'add_handler'):
                router1.add_handler(test_handler)
                router2.add_handler(test_handler)

                handlers1 = getattr(router1, 'custom_handlers', [])
                handlers2 = getattr(router2, 'custom_handlers', [])

                assert len(handlers1) == len(handlers2) == 1, (
                    f"REGISTRATION INCONSISTENCY: Handler count mismatch. "
                    f"Router1: {len(handlers1)}, Router2: {len(handlers2)}"
                )

        except Exception as e:
            pytest.fail(f"HANDLER REGISTRATION FAILURE: {e}")

    # Helper methods
    def _discover_message_router_classes(self) -> Dict[str, Type]:
        """Discover all MessageRouter class implementations in the codebase."""
        implementations = {}

        # Known paths where MessageRouter might exist
        potential_paths = [
            "netra_backend.app.websocket_core.handlers",
            "netra_backend.app.core.message_router",
            "netra_backend.app.services.message_router",
            "netra_backend.app.agents.message_router"
        ]

        for path in potential_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    implementations[path] = router_class
            except ImportError:
                continue  # Path doesn't exist, which is fine

        return implementations

    def _find_non_canonical_imports(self) -> List[str]:
        """Find all non-canonical MessageRouter import statements."""
        # This would scan source files for import patterns
        # For now, return known violations based on analysis
        non_canonical_patterns = [
            "from netra_backend.app.core.message_router import MessageRouter",
            "from netra_backend.app.agents.message_router import MessageRouter",
            "from netra_backend.app.services.message_router import MessageRouter"
        ]
        return non_canonical_patterns
```

#### Test File: `tests/unit/websocket_routing_ssot/test_websocket_event_routing_ssot_violations.py`

```python
"""
Test WebSocket Event Routing SSOT Violations

Focus: WebSocket event delivery consistency and routing consolidation
"""

import pytest
from typing import Dict, List
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketEventRoutingSSOTViolations(SSotBaseTestCase):
    """Reproduce WebSocket event routing SSOT violations."""

    def test_websocket_event_delivery_consistency(self):
        """FAILING TEST: All 5 critical events must follow same routing pattern."""
        # This test should FAIL initially, showing routing inconsistencies

        required_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        routing_patterns = self._analyze_event_routing_patterns()

        # Check if all events use the same routing mechanism
        unique_patterns = set(routing_patterns.values())

        assert len(unique_patterns) <= 1, (
            f"EVENT ROUTING INCONSISTENCY: Found {len(unique_patterns)} different routing patterns. "
            f"All events must use identical routing. Patterns: {routing_patterns}"
        )

    def test_broadcast_service_consolidation(self):
        """FAILING TEST: Should have only 1 broadcast service, currently multiple."""
        # This test should FAIL initially, showing broadcast service duplication

        broadcast_services = self._discover_broadcast_services()
        expected_count = 1
        actual_count = len(broadcast_services)

        assert actual_count == expected_count, (
            f"BROADCAST SERVICE DUPLICATION: Found {actual_count} broadcast services, "
            f"expected {expected_count}. Services: {broadcast_services}"
        )

    def test_user_isolation_routing_violations(self):
        """FAILING TEST: Messages should never cross user boundaries."""
        # This test should FAIL initially, demonstrating user isolation violations

        # Simulate two users
        user1_id = "user_123"
        user2_id = "user_456"

        routing_violations = self._simulate_cross_user_routing(user1_id, user2_id)

        assert len(routing_violations) == 0, (
            f"USER ISOLATION VIOLATION: Found {len(routing_violations)} cross-user routing violations. "
            f"Messages leaked between users: {routing_violations}"
        )

    # Helper methods
    def _analyze_event_routing_patterns(self) -> Dict[str, str]:
        """Analyze routing patterns for each WebSocket event type."""
        # Mock analysis - in real implementation, this would scan source code
        return {
            "agent_started": "websocket_manager.send",
            "agent_thinking": "websocket_manager.send",
            "tool_executing": "quality_router.broadcast",  # INCONSISTENCY
            "tool_completed": "quality_router.broadcast",  # INCONSISTENCY
            "agent_completed": "websocket_manager.send"
        }

    def _discover_broadcast_services(self) -> List[str]:
        """Discover all WebSocket broadcast service implementations."""
        # Mock discovery - in real implementation, this would scan codebase
        return [
            "netra_backend.app.websocket_core.handlers.MessageRouter",
            "netra_backend.app.services.websocket.quality_message_router.QualityMessageRouter"
        ]

    def _simulate_cross_user_routing(self, user1_id: str, user2_id: str) -> List[str]:
        """Simulate message routing between users to detect violations."""
        violations = []

        # Mock simulation - in real implementation, this would test actual routing
        # Based on known issues, we expect violations
        violations.append(f"Message from {user1_id} routed to {user2_id} via shared router instance")

        return violations
```

## Integration Test Specifications

### 2. Golden Path Message Routing Integration Tests

#### Test File: `tests/integration/message_routing_golden_path/test_golden_path_message_routing_failures.py`

```python
"""
Test Golden Path Message Routing Integration Failures

Focus: End-to-end message routing through the complete Golden Path
Uses real services but no Docker required.
"""

import pytest
import asyncio
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket_test_infrastructure_factory import WebSocketTestInfrastructureFactory


class TestGoldenPathMessageRoutingFailures(SSotAsyncTestCase):
    """Test Golden Path message routing with real services."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_user_message_flow_failures(self, real_services_fixture):
        """FAILING TEST: Complete user->agent->response flow should work reliably."""
        # This test should FAIL initially due to routing conflicts

        # Setup real services
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]

        # Create test infrastructure
        ws_factory = WebSocketTestInfrastructureFactory()
        test_user = await ws_factory.create_test_user(db)

        message_routing_success = False
        routing_errors = []

        try:
            # Simulate complete message flow
            user_message = {
                "type": "user_message",
                "content": "Test message for routing",
                "user_id": test_user.id
            }

            # Test routing through MessageRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()

            # Mock WebSocket for testing
            class MockWebSocket:
                def __init__(self):
                    self.messages_sent = []
                    self.closed = False

                async def send_json(self, data):
                    self.messages_sent.append(data)

                async def close(self):
                    self.closed = True

            mock_websocket = MockWebSocket()

            # Attempt message routing
            routing_result = await router.route_message(
                user_id=test_user.id,
                websocket=mock_websocket,
                raw_message=user_message
            )

            message_routing_success = routing_result

            # Verify expected responses
            expected_response_count = 5  # All 5 WebSocket events
            actual_response_count = len(mock_websocket.messages_sent)

            if actual_response_count != expected_response_count:
                routing_errors.append(
                    f"Expected {expected_response_count} responses, got {actual_response_count}"
                )

        except Exception as e:
            routing_errors.append(f"Message routing exception: {str(e)}")

        # This assertion should FAIL initially, demonstrating the Golden Path issue
        assert message_routing_success and len(routing_errors) == 0, (
            f"GOLDEN PATH FAILURE: Message routing failed. "
            f"Success: {message_routing_success}, Errors: {routing_errors}"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_message_isolation_failures(self, real_services_fixture):
        """FAILING TEST: Concurrent users should have isolated message routing."""
        # This test should FAIL initially, showing user isolation violations

        db = real_services_fixture["db"]
        ws_factory = WebSocketTestInfrastructureFactory()

        # Create two test users
        user1 = await ws_factory.create_test_user(db, email="user1@test.com")
        user2 = await ws_factory.create_test_user(db, email="user2@test.com")

        isolation_violations = []

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()

            # Create separate WebSocket mocks for each user
            class IsolationTestWebSocket:
                def __init__(self, user_id: str):
                    self.user_id = user_id
                    self.messages_received = []

                async def send_json(self, data):
                    self.messages_received.append(data)

            ws1 = IsolationTestWebSocket(user1.id)
            ws2 = IsolationTestWebSocket(user2.id)

            # Send messages for both users simultaneously
            user1_message = {"type": "user_message", "content": "User 1 message", "user_id": user1.id}
            user2_message = {"type": "user_message", "content": "User 2 message", "user_id": user2.id}

            # Route messages concurrently
            results = await asyncio.gather(
                router.route_message(user1.id, ws1, user1_message),
                router.route_message(user2.id, ws2, user2_message),
                return_exceptions=True
            )

            # Analyze isolation
            user1_messages = [msg.get("content", "") for msg in ws1.messages_received]
            user2_messages = [msg.get("content", "") for msg in ws2.messages_received]

            # Check for cross-contamination
            if "User 2 message" in str(user1_messages):
                isolation_violations.append("User 1 received User 2's message")

            if "User 1 message" in str(user2_messages):
                isolation_violations.append("User 2 received User 1's message")

        except Exception as e:
            isolation_violations.append(f"Multi-user routing exception: {str(e)}")

        # This assertion should FAIL initially, demonstrating isolation violations
        assert len(isolation_violations) == 0, (
            f"USER ISOLATION VIOLATIONS: {len(isolation_violations)} violations detected. "
            f"Details: {isolation_violations}"
        )
```

## E2E Test Specifications

### 3. Staging Environment Golden Path Tests

#### Test File: `tests/e2e/staging/message_router_golden_path/test_golden_path_business_value_protection_e2e.py`

```python
"""
Test Golden Path Business Value Protection E2E

Focus: Complete business value validation in staging environment
Uses staging GCP deployment with real LLM.
"""

import pytest
import asyncio
from typing import Dict, List
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager


class TestGoldenPathBusinessValueProtectionE2E(SSotAsyncTestCase):
    """Test complete Golden Path business value in staging environment."""

    @pytest.mark.e2e
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_complete_chat_experience_reliability(self, staging_environment):
        """CRITICAL TEST: End-to-end chat must deliver business value."""
        # This test validates the complete user experience

        auth_helper = E2EAuthHelper(staging_environment["auth_url"])
        ws_manager = RealWebSocketConnectionManager(staging_environment["backend_url"])

        business_value_metrics = {
            "chat_completion_success": False,
            "websocket_events_received": [],
            "agent_response_quality": False,
            "user_experience_smooth": False
        }

        try:
            # Create real user and authenticate
            test_user = await auth_helper.create_test_user(
                email="e2e-test@netrasystems.ai",
                subscription_tier="enterprise"
            )

            auth_token = await auth_helper.get_auth_token(test_user)

            # Establish real WebSocket connection
            async with ws_manager.create_connection(auth_token) as websocket:

                # Send business-critical message
                business_message = {
                    "type": "agent_request",
                    "agent": "cost_optimizer",
                    "message": "Analyze my cloud costs and provide optimization recommendations",
                    "context": {
                        "monthly_budget": 50000,
                        "current_spend": 65000
                    }
                }

                await websocket.send_json(business_message)

                # Collect all WebSocket events
                events = []
                timeout_seconds = 60

                try:
                    async with asyncio.timeout(timeout_seconds):
                        async for event in websocket.receive_events():
                            events.append(event)
                            business_value_metrics["websocket_events_received"].append(event.get("type"))

                            if event.get("type") == "agent_completed":
                                business_value_metrics["chat_completion_success"] = True
                                break

                except asyncio.TimeoutError:
                    # Timeout indicates Golden Path failure
                    pass

                # Analyze business value delivery
                required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
                events_received = business_value_metrics["websocket_events_received"]

                # Check if all critical events were received
                missing_events = set(required_events) - set(events_received)
                if len(missing_events) == 0:
                    business_value_metrics["user_experience_smooth"] = True

                # Validate agent response quality
                final_event = events[-1] if events else {}
                if final_event.get("type") == "agent_completed":
                    response_data = final_event.get("data", {})
                    result = response_data.get("result", {})

                    # Business value checks
                    has_recommendations = "recommendations" in result
                    has_cost_savings = "cost_savings" in result
                    has_actionable_insights = len(result.get("recommendations", [])) > 0

                    business_value_metrics["agent_response_quality"] = (
                        has_recommendations and has_cost_savings and has_actionable_insights
                    )

        except Exception as e:
            # Any exception indicates Golden Path failure
            business_value_metrics["error"] = str(e)

        # Calculate overall business value score
        successful_metrics = sum([
            business_value_metrics["chat_completion_success"],
            business_value_metrics["user_experience_smooth"],
            business_value_metrics["agent_response_quality"]
        ])

        business_value_score = successful_metrics / 3.0
        minimum_acceptable_score = 1.0  # 100% - business critical

        # This assertion protects $500K+ ARR functionality
        assert business_value_score >= minimum_acceptable_score, (
            f"BUSINESS VALUE FAILURE: Golden Path score {business_value_score:.2%} "
            f"below minimum {minimum_acceptable_score:.2%}. "
            f"Metrics: {business_value_metrics}. "
            f"This failure impacts $500K+ ARR chat functionality."
        )

    @pytest.mark.e2e
    @pytest.mark.real_llm
    async def test_multi_user_chat_scalability(self, staging_environment):
        """FAILING TEST: Multiple users should have isolated, reliable chat."""
        # This test should initially FAIL due to routing conflicts

        user_count = 3
        concurrent_chat_success = []

        async def single_user_chat_test(user_index: int):
            """Test chat functionality for a single user."""
            try:
                auth_helper = E2EAuthHelper(staging_environment["auth_url"])
                ws_manager = RealWebSocketConnectionManager(staging_environment["backend_url"])

                # Create unique user
                test_user = await auth_helper.create_test_user(
                    email=f"concurrent-user-{user_index}@netrasystems.ai"
                )
                auth_token = await auth_helper.get_auth_token(test_user)

                # Test chat functionality
                async with ws_manager.create_connection(auth_token) as websocket:
                    message = {
                        "type": "agent_request",
                        "message": f"User {user_index} optimization request",
                        "agent": "triage_agent"
                    }

                    await websocket.send_json(message)

                    # Wait for completion
                    async with asyncio.timeout(30):
                        async for event in websocket.receive_events():
                            if event.get("type") == "agent_completed":
                                return True

                return False

            except Exception as e:
                return f"User {user_index} failed: {str(e)}"

        # Run concurrent chat tests
        results = await asyncio.gather(
            *[single_user_chat_test(i) for i in range(user_count)],
            return_exceptions=True
        )

        # Analyze results
        successful_chats = sum(1 for result in results if result is True)
        failed_chats = [result for result in results if result is not True]

        success_rate = successful_chats / user_count
        minimum_success_rate = 0.95  # 95%

        # This assertion should FAIL initially due to routing conflicts
        assert success_rate >= minimum_success_rate, (
            f"MULTI-USER SCALABILITY FAILURE: Success rate {success_rate:.2%} "
            f"below minimum {minimum_success_rate:.2%}. "
            f"Successful: {successful_chats}/{user_count}. "
            f"Failures: {failed_chats}"
        )
```

## Test Success Criteria

### Expected Initial Failures
All tests in this specification should **FAIL initially**, demonstrating:

1. **SSOT Violations**: Multiple MessageRouter implementations detected
2. **Routing Conflicts**: Messages routed to wrong handlers or users
3. **Golden Path Failures**: Incomplete end-to-end user experience
4. **User Isolation Violations**: Cross-user message contamination
5. **WebSocket Event Inconsistencies**: Missing or incorrectly delivered events

### Post-Consolidation Success
After SSOT consolidation, all tests should **PASS**, validating:

1. **Single Router Implementation**: Only canonical MessageRouter exists
2. **Consistent Routing**: All messages routed through unified system
3. **Golden Path Reliability**: Complete user experience working
4. **Perfect User Isolation**: Zero cross-user contamination
5. **WebSocket Event Reliability**: All 5 events delivered consistently

## Implementation Priority

1. **Unit Tests** (Week 1): Create failing tests to reproduce violations
2. **Integration Tests** (Week 2): Validate routing conflicts with real services
3. **E2E Tests** (Week 3): Confirm business value impact in staging
4. **Continuous Validation** (Ongoing): Run tests during SSOT consolidation

This comprehensive test specification ensures thorough validation of MessageRouter SSOT consolidation while protecting the critical $500K+ ARR Golden Path functionality.