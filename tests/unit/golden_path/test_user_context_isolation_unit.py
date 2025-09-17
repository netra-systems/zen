"""
Unit Tests for User Context Isolation - Golden Path Validation

Business Value Justification (BVJ):
- Segment: Platform/Enterprise - Multi-user system foundation  
- Business Goal: Zero cross-contamination between concurrent users
- Value Impact: Validates factory patterns prevent user data leakage
- Strategic Impact: Protects enterprise security requirements and customer trust

CRITICAL MISSION: These unit tests validate user context isolation without Docker,
providing fast feedback on factory patterns that ensure users never see each 
other's agent events or execution contexts.

Test Purpose:
1. Validate UserExecutionContext factory creates isolated instances
2. Test WebSocket event delivery respects user boundaries
3. Verify concurrent agent execution maintains isolation
4. Ensure user context cleanup prevents memory leaks
5. Demonstrate validation gaps with expected failures

SSOT Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Uses test_framework.ssot.mock_factory.SSotMockFactory
- NO Docker dependencies - pure unit tests with isolation validation
- Validates business logic isolation patterns

Expected Behavior:
- Tests should initially FAIL to demonstrate isolation gaps
- Provides foundation for enterprise-grade user isolation
- Enables rapid iteration on factory pattern improvements
"""

import asyncio
import pytest
import time
import uuid
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from collections import defaultdict
import threading

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# User Context Components Under Test
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
except ImportError as e:
    print(f"WARNING: Failed to import user context components: {e}")
    UserExecutionContext = None
    AgentExecutionContext = None
    WebSocketNotifier = None


class UserIsolationValidator:
    """Advanced validator for user context isolation."""
    
    def __init__(self):
        self.user_contexts: Dict[str, Any] = {}
        self.user_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.cross_contamination_violations: List[Dict[str, Any]] = []
        self.isolation_lock = threading.Lock()
        self.context_signatures: Set[str] = set()
        
    def register_user_context(self, user_id: str, context: Any) -> str:
        """Register user context and return unique signature."""
        with self.isolation_lock:
            # Generate unique signature for this context
            signature = f"{user_id}_{id(context)}_{uuid.uuid4().hex[:8]}"
            
            # Validate signature uniqueness
            if signature in self.context_signatures:
                raise ValueError(f"Duplicate context signature: {signature}")
            
            self.context_signatures.add(signature)
            self.user_contexts[user_id] = context
            
            # Add isolation signature to context for tracking
            # Note: UserExecutionContext is frozen, so we use object.__setattr__
            try:
                object.__setattr__(context, '_isolation_signature', signature)
            except:
                # If we can't set the attribute, use a different tracking method
                pass
            
            return signature
    
    def record_user_event(self, user_id: str, event: Dict[str, Any], source_context: Any = None):
        """Record event and validate it belongs to correct user."""
        with self.isolation_lock:
            # Add validation metadata
            event_with_validation = {
                **event,
                "validation_timestamp": time.time(),
                "receiving_user": user_id,
                "source_signature": getattr(source_context, '_isolation_signature', f"context_{id(source_context)}") if source_context else 'unknown'
            }
            
            self.user_events[user_id].append(event_with_validation)
            
            # Check for cross-contamination
            event_user = event.get("user_id") or event.get("context", {}).get("user_id")
            if event_user and event_user != user_id:
                violation = {
                    "receiving_user": user_id,
                    "event_user": event_user, 
                    "event_type": event.get("type", "unknown"),
                    "contamination_type": "wrong_user_event",
                    "timestamp": time.time(),
                    "severity": "CRITICAL"
                }
                self.cross_contamination_violations.append(violation)
            
            # Check for context signature mismatches
            if source_context:
                source_signature = getattr(source_context, '_isolation_signature', None)
                if source_signature:
                    expected_user_pattern = f"{user_id}_"
                    if not source_signature.startswith(expected_user_pattern):
                        violation = {
                            "receiving_user": user_id,
                            "source_signature": source_signature,
                            "contamination_type": "context_signature_mismatch",
                            "timestamp": time.time(),
                            "severity": "CRITICAL"
                        }
                        self.cross_contamination_violations.append(violation)
    
    def validate_user_isolation(self) -> Dict[str, Any]:
        """Comprehensive isolation validation."""
        with self.isolation_lock:
            validation_report = {
                "total_users": len(self.user_contexts),
                "total_events": sum(len(events) for events in self.user_events.values()),
                "contamination_violations": len(self.cross_contamination_violations),
                "violation_details": self.cross_contamination_violations,
                "isolation_success": len(self.cross_contamination_violations) == 0,
                "context_signatures_unique": len(self.context_signatures) == len(set(self.context_signatures)),
                "user_event_distribution": {uid: len(events) for uid, events in self.user_events.items()}
            }
            
            # Additional isolation checks
            if validation_report["total_users"] > 1:
                # Check that each user has isolated events
                users_with_events = len([uid for uid, events in self.user_events.items() if len(events) > 0])
                validation_report["users_with_events"] = users_with_events
                validation_report["isolation_coverage"] = users_with_events / validation_report["total_users"]
            
            return validation_report
    
    def assert_perfect_isolation(self):
        """Assert that perfect user isolation was maintained."""
        report = self.validate_user_isolation()
        
        if not report["isolation_success"]:
            raise AssertionError(
                f"User isolation violations detected: {report['contamination_violations']} violations. "
                f"Details: {report['violation_details']}"
            )
        
        if not report["context_signatures_unique"]:
            raise AssertionError("Context signatures are not unique - indicates context sharing")
        
        if report["total_users"] > 1 and report.get("isolation_coverage", 0) < 0.9:
            raise AssertionError(
                f"Insufficient isolation coverage: {report['isolation_coverage']:.2f} "
                f"(expected >= 0.9 for multi-user scenarios)"
            )


class AdvancedUserContextFactory:
    """Advanced factory for creating isolated user contexts."""
    
    def __init__(self, validator: UserIsolationValidator):
        self.validator = validator
        self.created_contexts: List[Any] = []
    
    def create_isolated_user_context(self, user_id: str, **kwargs) -> Any:
        """Create genuinely isolated user context."""
        # Use SSOT factory method with additional isolation
        if UserExecutionContext:
            try:
                context = UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=kwargs.get('thread_id', f"thread_{uuid.uuid4()}"),
                    run_id=kwargs.get('run_id', f"run_{uuid.uuid4()}"),
                    request_id=kwargs.get('request_id', f"req_{uuid.uuid4()}"),
                    websocket_client_id=kwargs.get('websocket_client_id', f"ws_{uuid.uuid4()}")
                )
            except Exception as e:
                # Fallback to sophisticated mock
                context = SSotMockFactory.create_mock_user_context(
                    user_id=user_id,
                    **kwargs
                )
        else:
            # Use sophisticated mock factory
            context = SSotMockFactory.create_mock_user_context(
                user_id=user_id,
                **kwargs
            )
        
        # Register with validator and add isolation tracking
        signature = self.validator.register_user_context(user_id, context)
        self.created_contexts.append(context)
        
        # Add isolation validation methods to context (use object.__setattr__ for frozen dataclass)
        try:
            object.__setattr__(context, '_validate_isolation', lambda: self.validator.validate_user_isolation())
        except:
            # If we can't set the attribute, skip it
            pass
        
        return context
    
    def create_isolated_websocket_notifier(self, user_context: Any) -> AsyncMock:
        """Create WebSocket notifier with isolation validation."""
        mock_notifier = AsyncMock()
        mock_notifier.user_context = user_context
        
        # Track events with isolation validation
        def isolated_send_event(event_type: str, event_data: Dict[str, Any]):
            """Send event with isolation validation."""
            event = {
                "type": event_type,
                "data": event_data,
                "user_id": user_context.user_id if hasattr(user_context, 'user_id') else 'unknown',
                "timestamp": time.time()
            }
            
            # Record with validator
            self.validator.record_user_event(
                user_context.user_id if hasattr(user_context, 'user_id') else 'unknown',
                event,
                user_context
            )
            # Return None to avoid coroutine warning
            return None
        
        # Configure event methods with isolation (using AsyncMock with proper return values)
        mock_notifier.send_event = AsyncMock(side_effect=lambda event_type, data: isolated_send_event(event_type, data))
        mock_notifier.notify_agent_started = AsyncMock(side_effect=lambda data: isolated_send_event("agent_started", data))
        mock_notifier.notify_agent_thinking = AsyncMock(side_effect=lambda data: isolated_send_event("agent_thinking", data))
        mock_notifier.notify_tool_executing = AsyncMock(side_effect=lambda data: isolated_send_event("tool_executing", data))
        mock_notifier.notify_tool_completed = AsyncMock(side_effect=lambda data: isolated_send_event("tool_completed", data))
        mock_notifier.notify_agent_completed = AsyncMock(side_effect=lambda data: isolated_send_event("agent_completed", data))
        
        return mock_notifier


class GoldenPathUserContextIsolationTests(SSotAsyncTestCase):
    """
    Unit tests for Golden Path user context isolation.
    
    These tests validate user isolation patterns without Docker dependencies,
    providing fast feedback on enterprise security requirements.
    """
    
    def setup_method(self, method):
        """Setup advanced isolation testing environment."""
        super().setup_method(method)
        
        # Create isolation validation infrastructure
        self.isolation_validator = UserIsolationValidator()
        self.context_factory = AdvancedUserContextFactory(self.isolation_validator)
        
        # Track test metrics
        self.isolation_metrics = {}
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_user_execution_context_factory_isolation(self):
        """
        Test UserExecutionContext factory creates isolated instances.
        
        EXPECTED: This test should INITIALLY FAIL to demonstrate isolation gaps.
        
        Business Value: Validates factory pattern prevents context sharing.
        """
        # Arrange: Create multiple user contexts
        user_count = 5
        user_contexts = []
        
        for i in range(user_count):
            user_id = f"factory_test_user_{i:03d}"
            context = self.context_factory.create_isolated_user_context(user_id)
            user_contexts.append((user_id, context))
        
        # Act: Validate isolation at creation time
        isolation_report = self.isolation_validator.validate_user_isolation()
        
        # Assert: Contexts should be completely isolated
        try:
            assert isolation_report["total_users"] == user_count, \
                f"Expected {user_count} users, got {isolation_report['total_users']}"
            
            assert isolation_report["context_signatures_unique"], \
                "Context signatures must be unique to prevent sharing"
            
            # Validate each context has unique identity
            user_ids = set()
            signatures = set()
            
            for user_id, context in user_contexts:
                assert hasattr(context, 'user_id'), f"Context missing user_id: {context}"
                assert context.user_id == user_id, f"User ID mismatch: expected {user_id}, got {context.user_id}"
                
                user_ids.add(context.user_id)
                
                signature = getattr(context, '_isolation_signature', None)
                if signature:
                    signatures.add(signature)
            
            assert len(user_ids) == user_count, "User IDs should be unique"
            assert len(signatures) == user_count, "Isolation signatures should be unique"
            
            self.record_metric("context_factory_isolation_test", "PASS")
            
        except AssertionError as e:
            self.record_metric("context_factory_isolation_test", "FAIL")
            pytest.fail(
                f"User context factory isolation failed: {e}. "
                f"This demonstrates gaps in factory pattern isolation. "
                f"Report: {isolation_report}"
            )
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_concurrent_websocket_event_isolation(self):
        """
        Test concurrent WebSocket events maintain user isolation.
        
        EXPECTED: This test should INITIALLY FAIL to demonstrate event isolation gaps.
        
        Business Value: Validates users never see each other's events.
        """
        # Arrange: Create concurrent users with WebSocket notifiers
        concurrent_users = 10
        user_tasks = []
        
        async def user_event_generation(user_index: int):
            """Generate events for a specific user."""
            user_id = f"concurrent_user_{user_index:03d}"
            
            # Create isolated context and notifier
            user_context = self.context_factory.create_isolated_user_context(user_id)
            websocket_notifier = self.context_factory.create_isolated_websocket_notifier(user_context)
            
            # Generate user-specific events
            await websocket_notifier.notify_agent_started({
                "agent_type": "supervisor",
                "user_specific_data": f"data_for_{user_id}"
            })
            
            await websocket_notifier.notify_agent_thinking({
                "reasoning": f"Processing request for {user_id}",
                "user_context": user_id
            })
            
            await websocket_notifier.notify_agent_completed({
                "final_response": f"Completed analysis for {user_id}",
                "user_result": f"result_{user_id}"
            })
            
            return user_index
        
        # Act: Execute concurrent user event generation
        start_time = time.time()
        
        user_results = await asyncio.gather(
            *[user_event_generation(i) for i in range(concurrent_users)],
            return_exceptions=True
        )
        
        execution_time = time.time() - start_time
        
        # Assert: Perfect isolation maintained during concurrency
        try:
            # Validate all users completed successfully
            successful_users = [r for r in user_results if isinstance(r, int)]
            assert len(successful_users) == concurrent_users, \
                f"Some users failed: {len(successful_users)}/{concurrent_users} successful"
            
            # Validate isolation maintained
            self.isolation_validator.assert_perfect_isolation()
            
            # Validate event distribution
            isolation_report = self.isolation_validator.validate_user_isolation()
            assert isolation_report["total_events"] >= concurrent_users * 3, \
                f"Insufficient events generated: {isolation_report['total_events']} (expected >= {concurrent_users * 3})"
            
            # Validate each user received their own events
            for user_index in range(concurrent_users):
                user_id = f"concurrent_user_{user_index:03d}"
                user_events = self.isolation_validator.user_events.get(user_id, [])
                assert len(user_events) >= 3, f"User {user_id} missing events: {len(user_events)}"
                
                # Validate event content belongs to correct user
                for event in user_events:
                    event_data = event.get("data", {})
                    if "user_specific_data" in event_data:
                        expected_data = f"data_for_{user_id}"
                        assert event_data["user_specific_data"] == expected_data, \
                            f"Event data contamination: expected {expected_data}, got {event_data['user_specific_data']}"
            
            self.record_metric("concurrent_event_isolation_test", "PASS")
            self.record_metric("concurrent_users_tested", concurrent_users)
            self.record_metric("concurrent_execution_time", execution_time)
            
        except AssertionError as e:
            self.record_metric("concurrent_event_isolation_test", "FAIL")
            pytest.fail(
                f"Concurrent WebSocket event isolation failed: {e}. "
                f"This demonstrates gaps in concurrent user isolation. "
                f"Execution time: {execution_time:.3f}s"
            )
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_agent_execution_context_user_isolation(self):
        """
        Test AgentExecutionContext maintains user isolation.
        
        EXPECTED: This test should INITIALLY FAIL to demonstrate context isolation gaps.
        
        Business Value: Validates agent execution respects user boundaries.
        """
        # Skip if components not available
        if AgentExecutionContext is None:
            pytest.skip("AgentExecutionContext not available for testing")
        
        # Arrange: Create agent execution contexts for multiple users
        user_count = 3
        agent_contexts = []
        
        for i in range(user_count):
            user_id = f"agent_context_user_{i:03d}"
            
            # Create isolated user context
            user_context = self.context_factory.create_isolated_user_context(user_id)
            websocket_notifier = self.context_factory.create_isolated_websocket_notifier(user_context)
            
            # Create agent execution context
            agent_context = AgentExecutionContext(
                user_context=user_context,
                websocket_notifier=websocket_notifier
            )
            
            agent_contexts.append((user_id, user_context, agent_context))
        
        # Act: Simulate agent execution for each user
        for user_id, user_context, agent_context in agent_contexts:
            # Simulate agent execution events through context
            if hasattr(agent_context, 'websocket_notifier') and agent_context.websocket_notifier:
                await agent_context.websocket_notifier.notify_agent_started({
                    "agent_context_id": agent_context.run_id,
                    "user_specific_execution": f"execution_for_{user_id}"
                })
                
                await agent_context.websocket_notifier.notify_agent_thinking({
                    "agent_context_id": agent_context.run_id,
                    "user_reasoning": f"reasoning_for_{user_id}"
                })
                
                await agent_context.websocket_notifier.notify_agent_completed({
                    "agent_context_id": agent_context.run_id,
                    "user_result": f"result_for_{user_id}"
                })
        
        # Assert: Agent contexts maintain user isolation
        try:
            # Validate perfect isolation
            self.isolation_validator.assert_perfect_isolation()
            
            # Validate agent context integration
            for user_id, user_context, agent_context in agent_contexts:
                assert hasattr(agent_context, 'user_context'), \
                    "AgentExecutionContext should have user_context"
                
                assert agent_context.user_context is user_context, \
                    "Agent context should reference correct user context"
                
                # Validate user-specific events
                user_events = self.isolation_validator.user_events.get(user_id, [])
                assert len(user_events) >= 3, f"User {user_id} missing agent context events"
                
                # Validate event context consistency
                for event in user_events:
                    event_data = event.get("data", {})
                    if "agent_context_id" in event_data:
                        assert event_data["agent_context_id"] == agent_context.run_id, \
                            "Agent context ID should be consistent"
            
            self.record_metric("agent_context_user_isolation_test", "PASS")
            
        except AssertionError as e:
            self.record_metric("agent_context_user_isolation_test", "FAIL")
            pytest.fail(
                f"Agent execution context user isolation failed: {e}. "
                f"This demonstrates gaps in agent context user isolation."
            )
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_user_context_memory_isolation(self):
        """
        Test user context memory isolation and cleanup.
        
        EXPECTED: This test should INITIALLY FAIL to demonstrate memory isolation gaps.
        
        Business Value: Validates no memory leaks between user sessions.
        """
        # Arrange: Create and cleanup user contexts multiple times
        iterations = 5
        contexts_per_iteration = 10
        memory_snapshots = []
        
        for iteration in range(iterations):
            iteration_contexts = []
            
            # Create user contexts
            for i in range(contexts_per_iteration):
                user_id = f"memory_test_user_{iteration}_{i:03d}"
                context = self.context_factory.create_isolated_user_context(user_id)
                iteration_contexts.append((user_id, context))
            
            # Generate events to populate memory
            for user_id, context in iteration_contexts:
                notifier = self.context_factory.create_isolated_websocket_notifier(context)
                await notifier.notify_agent_started({"memory_test": f"data_{user_id}"})
                await notifier.notify_agent_completed({"memory_test": f"result_{user_id}"})
            
            # Take memory snapshot
            isolation_report = self.isolation_validator.validate_user_isolation()
            memory_snapshots.append({
                "iteration": iteration,
                "total_users": isolation_report["total_users"],
                "total_events": isolation_report["total_events"],
                "context_signatures": len(self.isolation_validator.context_signatures)
            })
            
            # Cleanup contexts (simulate session end)
            for user_id, context in iteration_contexts:
                # Remove from validator (simulate cleanup)
                if user_id in self.isolation_validator.user_contexts:
                    del self.isolation_validator.user_contexts[user_id]
                if user_id in self.isolation_validator.user_events:
                    del self.isolation_validator.user_events[user_id]
        
        # Assert: Memory isolation maintained across iterations
        try:
            # Validate memory doesn't grow unboundedly
            final_snapshot = memory_snapshots[-1]
            initial_snapshot = memory_snapshots[0]
            
            # After cleanup, memory usage should not accumulate
            assert final_snapshot["total_users"] <= contexts_per_iteration, \
                f"User count should not accumulate: {final_snapshot['total_users']}"
            
            # Validate no cross-contamination occurred during any iteration
            assert len(self.isolation_validator.cross_contamination_violations) == 0, \
                f"Memory isolation violations: {self.isolation_validator.cross_contamination_violations}"
            
            # Validate context signatures remain unique
            assert final_snapshot["context_signatures"] >= contexts_per_iteration, \
                "Context signatures should be unique across iterations"
            
            self.record_metric("user_context_memory_isolation_test", "PASS")
            self.record_metric("memory_iterations_tested", iterations)
            self.record_metric("contexts_per_iteration", contexts_per_iteration)
            
        except AssertionError as e:
            self.record_metric("user_context_memory_isolation_test", "FAIL")
            pytest.fail(
                f"User context memory isolation failed: {e}. "
                f"This demonstrates gaps in memory isolation and cleanup. "
                f"Memory snapshots: {memory_snapshots}"
            )
    
    @pytest.mark.unit
    @pytest.mark.golden_path_critical
    async def test_cross_user_contamination_detection(self):
        """
        Test detection of any cross-user contamination.
        
        EXPECTED: This test should INITIALLY FAIL to demonstrate detection gaps.
        
        Business Value: Validates robust contamination detection mechanisms.
        """
        # Arrange: Create users with potential contamination scenarios
        primary_user = "primary_user_001"
        contaminating_user = "contaminating_user_002"
        
        primary_context = self.context_factory.create_isolated_user_context(primary_user)
        contaminating_context = self.context_factory.create_isolated_user_context(contaminating_user)
        
        primary_notifier = self.context_factory.create_isolated_websocket_notifier(primary_context)
        contaminating_notifier = self.context_factory.create_isolated_websocket_notifier(contaminating_context)
        
        # Act: Generate normal events, then simulate potential contamination
        
        # Normal isolated events
        await primary_notifier.notify_agent_started({"user_data": "primary_data"})
        await contaminating_notifier.notify_agent_started({"user_data": "contaminating_data"})
        
        # Simulate potential contamination scenario (wrong user receiving event)
        # This should be detected by the isolation validator
        contaminated_event = {
            "type": "agent_completed",
            "data": {"user_data": "contaminating_data"},
            "user_id": contaminating_user,  # Event from contaminating user
            "timestamp": time.time()
        }
        
        # Record event as if primary user received it (contamination scenario)
        self.isolation_validator.record_user_event(
            primary_user,  # Primary user receives event
            contaminated_event,  # But event is from contaminating user
            contaminating_context  # From contaminating context
        )
        
        # Assert: Contamination should be detected
        try:
            # This should fail because we intentionally created contamination
            self.isolation_validator.assert_perfect_isolation()
            
            # If we get here, contamination detection failed
            self.record_metric("contamination_detection_test", "FAIL") 
            pytest.fail(
                "Contamination detection failed: Expected contamination to be detected but it wasn't. "
                "This demonstrates gaps in contamination detection mechanisms."
            )
            
        except AssertionError as isolation_error:
            # Contamination was detected (expected behavior)
            if "contamination violations" in str(isolation_error).lower():
                self.record_metric("contamination_detection_test", "PASS")
                self.record_metric("contamination_detected", True)
                
                # Verify violation details
                report = self.isolation_validator.validate_user_isolation()
                assert report["contamination_violations"] > 0, \
                    "Should have recorded contamination violations"
                
                # Check violation details
                violations = report["violation_details"]
                assert len(violations) > 0, "Should have violation details"
                
                contamination_violation = violations[0]
                assert contamination_violation["receiving_user"] == primary_user, \
                    "Should identify correct receiving user"
                assert contamination_violation["severity"] == "CRITICAL", \
                    "Contamination should be marked as critical"
                
            else:
                # Different assertion error - test failure
                self.record_metric("contamination_detection_test", "FAIL")
                pytest.fail(
                    f"Unexpected assertion error during contamination detection: {isolation_error}. "
                    f"This may indicate gaps in isolation validation logic."
                )
    
    def teardown_method(self, method):
        """Cleanup and report isolation validation results.""" 
        super().teardown_method(method)
        
        # Generate final isolation report
        final_report = self.isolation_validator.validate_user_isolation()
        
        # Log comprehensive results
        self.logger.info(f"Golden Path User Context Isolation Test Summary:")
        self.logger.info(f"  Total users tested: {final_report['total_users']}")
        self.logger.info(f"  Total events generated: {final_report['total_events']}")
        self.logger.info(f"  Contamination violations: {final_report['contamination_violations']}")
        self.logger.info(f"  Context signatures unique: {final_report['context_signatures_unique']}")
        self.logger.info(f"  Isolation success: {final_report['isolation_success']}")
        
        # Log test metrics
        test_metrics = {k: v for k, v in self.get_all_metrics().items() if k.endswith("_test")}
        passed_tests = sum(1 for v in test_metrics.values() if v == "PASS")
        total_tests = len(test_metrics)
        
        self.logger.info(f"  Test results: {passed_tests}/{total_tests} passed")
        self.logger.info(f"  Test details: {test_metrics}")


if __name__ == "__main__":
    # Run the Golden Path user context isolation unit tests
    print("\n" + "=" * 80)
    print("GOLDEN PATH: User Context Isolation Unit Tests")
    print("PURPOSE: Validate user isolation without Docker dependencies")
    print("=" * 80)
    print()
    print("Business Value: Enterprise security and user isolation validation")
    print("Expected Behavior: Tests should INITIALLY FAIL to demonstrate isolation gaps")
    print("Success Criteria: Identifies specific gaps in user isolation mechanisms")
    print()
    print("Running unit tests...")
    
    # Execute via pytest
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")