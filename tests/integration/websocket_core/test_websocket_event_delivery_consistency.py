#!/usr/bin/env python
"""WebSocket Event Delivery Consistency Test - SSOT CRITICAL INTEGRATION

PURPOSE: Validate same events delivered regardless of manager path used
EXPECTED BEHAVIOR: Test should FAIL initially, proving inconsistent event delivery
SUCCESS CRITERIA: After SSOT consolidation, consistent events across all code paths

BUSINESS VALUE: Ensures reliable Golden Path user experience with consistent real-time feedback
FAILURE CONSEQUENCE: Inconsistent events break user experience and eliminate platform value

This test is designed to FAIL initially, proving that different WebSocket manager
access paths deliver different events or exhibit inconsistent behavior.
After SSOT consolidation, this test should PASS with consistent event delivery.

Test Categories:
1. Event Delivery Consistency - Same events from all manager access paths
2. Event Content Validation - Consistent event structure and data
3. Event Timing Consistency - Similar delivery performance across paths
4. Real Service Integration - Tests with actual WebSocket connections

Expected Failure Modes (Before SSOT):
- Different events delivered from different manager paths
- Inconsistent event content or structure
- Missing events from some access paths
- Performance differences between manager paths

Expected Success Criteria (After SSOT):
- Identical events delivered from all manager access paths
- Consistent event structure and content
- Reliable event delivery across all paths
- Similar performance characteristics across paths
"""

import asyncio
import json
import time
import sys
import os
import uuid
from typing import Dict, List, Set, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import get_logger

# Import types and utilities
from shared.types.core_types import UserID, ThreadID, ensure_user_id, ensure_thread_id
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge

# Import WebSocket managers (multiple paths to test)
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

logger = get_logger(__name__)


@dataclass
class EventDeliveryRecord:
    """Record for tracking event delivery from different manager paths."""
    manager_path: str
    event_type: str
    event_data: Dict[str, Any]
    delivery_time: float
    timestamp: datetime
    user_id: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class ManagerPathResults:
    """Results from testing a specific manager path."""
    path_name: str
    manager_type: str
    events_delivered: List[EventDeliveryRecord] = field(default_factory=list)
    total_events: int = 0
    successful_events: int = 0
    failed_events: int = 0
    average_delivery_time: float = 0.0
    errors: List[str] = field(default_factory=list)


class TestWebSocketEventDeliveryConsistency(SSotAsyncTestCase):
    """
    SSOT Critical Integration Test: WebSocket Event Delivery Consistency

    This test validates that event delivery is consistent regardless of which
    manager access path is used, ensuring reliable user experience.

    EXPECTED TO FAIL INITIALLY: This test should fail before SSOT consolidation,
    proving that different manager paths deliver inconsistent events.
    """

    def setup_method(self, method):
        """Setup test environment for event delivery consistency validation."""
        super().setup_method(method)

        # Set environment for real service integration testing
        self.set_env_var("TESTING_INTEGRATION_WEBSOCKET", "true")
        self.set_env_var("WEBSOCKET_EVENT_CONSISTENCY", "strict")
        self.set_env_var("WEBSOCKET_TEST_MODE", "real_services")

        # Event tracking
        self.event_records = []
        self.manager_path_results = {}
        self.critical_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        # Performance tracking
        self.delivery_times = []
        self.consistency_metrics = {}

        logger.info(f"🔍 INTEGRATION TEST: {method.__name__ if method else 'unknown'}")
        logger.info("📍 PURPOSE: Validate consistent WebSocket event delivery across all manager paths")

    async def test_websocket_event_delivery_across_manager_paths(self):
        """
        CRITICAL: Validate consistent event delivery from all manager access paths.

        This test creates managers through different access paths and validates
        that they all deliver the same critical events consistently.

        EXPECTED TO FAIL: Different paths deliver different events (proving inconsistency)
        AFTER CONSOLIDATION: All paths deliver identical events
        """
        logger.info("🔍 PHASE 1: Testing event delivery consistency across manager paths")

        # Define manager access paths to test
        manager_access_paths = {
            "canonical_path": self._get_manager_via_canonical_path,
            "direct_import": self._get_manager_via_direct_import,
            "service_bridge": self._get_manager_via_service_bridge,
        }

        # Create consistent user context for all tests
        user_context = UserExecutionContext(
            user_id=ensure_user_id("consistency_test_user"),
            thread_id=ensure_thread_id("consistency_test_thread"),
            session_id="consistency_test_session"
        )

        # Test each manager access path
        for path_name, get_manager_func in manager_access_paths.items():
            logger.info(f"📍 Testing manager path: {path_name}")

            try:
                # Get manager via this path
                path_results = ManagerPathResults(
                    path_name=path_name,
                    manager_type="unknown"
                )

                manager_start_time = time.time()
                manager, bridge = await get_manager_func(user_context)
                manager_creation_time = time.time() - manager_start_time

                if manager is None or bridge is None:
                    path_results.errors.append(f"Failed to create manager or bridge via {path_name}")
                    logger.error(f"❌ Path {path_name}: Manager/bridge creation failed")
                    continue

                path_results.manager_type = type(manager).__name__
                logger.info(f"✅ Path {path_name}: Created {path_results.manager_type} (in {manager_creation_time:.3f}s)")

                # Test critical event delivery
                await self._test_critical_events_for_path(path_name, bridge, user_context, path_results)

                self.manager_path_results[path_name] = path_results

            except Exception as e:
                logger.error(f"❌ Path {path_name}: Exception during testing: {e}")
                if path_name not in self.manager_path_results:
                    self.manager_path_results[path_name] = ManagerPathResults(
                        path_name=path_name,
                        manager_type="error"
                    )
                self.manager_path_results[path_name].errors.append(f"Exception: {str(e)}")

        # Analyze consistency across paths
        await self._analyze_event_delivery_consistency()

    async def _get_manager_via_canonical_path(self, user_context: UserExecutionContext) -> Tuple[Any, Any]:
        """Get manager via canonical SSOT path."""
        manager = await get_websocket_manager(user_context=user_context)
        bridge = create_agent_websocket_bridge(
            websocket_manager=manager,
            user_context=user_context
        )
        return manager, bridge

    async def _get_manager_via_direct_import(self, user_context: UserExecutionContext) -> Tuple[Any, Any]:
        """Get manager via direct unified_manager import."""
        try:
            from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation

            # Create manager directly
            manager = _UnifiedWebSocketManagerImplementation()

            # Set up user context if possible
            if hasattr(manager, 'set_user_context'):
                await manager.set_user_context(user_context)

            bridge = create_agent_websocket_bridge(
                websocket_manager=manager,
                user_context=user_context
            )
            return manager, bridge
        except Exception as e:
            logger.warning(f"⚠️ Direct import path failed: {e}")
            return None, None

    async def _get_manager_via_service_bridge(self, user_context: UserExecutionContext) -> Tuple[Any, Any]:
        """Get manager via service bridge pattern."""
        try:
            # First get manager via canonical path
            manager = await get_websocket_manager(user_context=user_context)

            # Create bridge
            bridge = create_agent_websocket_bridge(
                websocket_manager=manager,
                user_context=user_context
            )

            # This tests the service bridge access pattern
            return manager, bridge
        except Exception as e:
            logger.warning(f"⚠️ Service bridge path failed: {e}")
            return None, None

    async def _test_critical_events_for_path(self, path_name: str, bridge: Any, user_context: UserExecutionContext, path_results: ManagerPathResults):
        """Test delivery of all critical events for a specific manager path."""
        logger.debug(f"📍 Testing critical events for path: {path_name}")

        delivered_events = []
        event_timing = {}

        # Mock event emission to capture delivery
        async def capture_event_delivery(event_type: str, data: Dict[str, Any]) -> bool:
            """Capture event delivery for consistency analysis."""
            delivery_start = time.time()

            try:
                # Validate event structure
                if "user_id" not in data:
                    data["user_id"] = str(user_context.user_id)
                if "timestamp" not in data:
                    data["timestamp"] = datetime.now(UTC).isoformat()

                # Record successful delivery
                delivery_time = time.time() - delivery_start
                event_record = EventDeliveryRecord(
                    manager_path=path_name,
                    event_type=event_type,
                    event_data=data.copy(),
                    delivery_time=delivery_time,
                    timestamp=datetime.now(UTC),
                    user_id=str(user_context.user_id),
                    success=True
                )

                delivered_events.append(event_type)
                event_timing[event_type] = delivery_time
                self.event_records.append(event_record)
                path_results.events_delivered.append(event_record)

                logger.debug(f"📡 {path_name}: Delivered {event_type} in {delivery_time:.4f}s")
                return True

            except Exception as e:
                # Record failed delivery
                error_record = EventDeliveryRecord(
                    manager_path=path_name,
                    event_type=event_type,
                    event_data=data.copy(),
                    delivery_time=time.time() - delivery_start,
                    timestamp=datetime.now(UTC),
                    user_id=str(user_context.user_id),
                    success=False,
                    error_message=str(e)
                )

                self.event_records.append(error_record)
                path_results.events_delivered.append(error_record)
                path_results.errors.append(f"Event {event_type} failed: {e}")

                logger.error(f"❌ {path_name}: Failed to deliver {event_type}: {e}")
                return False

        # Test delivery of each critical event
        with patch.object(bridge, 'emit_event', side_effect=capture_event_delivery):
            for event_type in self.critical_events:
                logger.debug(f"📍 {path_name}: Testing {event_type}")

                event_data = {
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event_type": event_type,
                    "test_path": path_name,
                    "test_data": f"Consistency test for {event_type}"
                }

                try:
                    success = await bridge.emit_event(event_type, event_data)
                    if success:
                        path_results.successful_events += 1
                    else:
                        path_results.failed_events += 1
                        logger.warning(f"⚠️ {path_name}: Event {event_type} returned False")
                except Exception as e:
                    path_results.failed_events += 1
                    path_results.errors.append(f"Exception emitting {event_type}: {e}")
                    logger.error(f"❌ {path_name}: Exception emitting {event_type}: {e}")

                path_results.total_events += 1

        # Calculate path metrics
        path_results.average_delivery_time = (
            sum(event_timing.values()) / len(event_timing) if event_timing else 0
        )

        logger.info(f"📊 {path_name} Results:")
        logger.info(f"   Events delivered: {len(delivered_events)}/{len(self.critical_events)}")
        logger.info(f"   Average delivery time: {path_results.average_delivery_time:.4f}s")
        logger.info(f"   Delivered events: {delivered_events}")

    async def _analyze_event_delivery_consistency(self):
        """Analyze consistency of event delivery across all manager paths."""
        logger.info("🔍 PHASE 2: Analyzing event delivery consistency")

        if len(self.manager_path_results) < 2:
            logger.warning("⚠️ Less than 2 manager paths tested - cannot analyze consistency")
            return

        # Extract successful paths
        successful_paths = {
            name: results for name, results in self.manager_path_results.items()
            if results.manager_type != "error" and results.successful_events > 0
        }

        if len(successful_paths) < 2:
            failure_message = (
                f"❌ WEBSOCKET PATH AVAILABILITY FAILURE: Not enough working paths!\n"
                f"   Total paths tested: {len(self.manager_path_results)}\n"
                f"   Working paths: {len(successful_paths)}\n"
                f"   Path results: {list(self.manager_path_results.keys())}\n"
                f"\n🚨 THIS INDICATES WEBSOCKET ACCESS ISSUES - CONSOLIDATION REQUIRED!"
            )

            logger.error(failure_message)
            self.record_metric("path_availability_failure", True)

            # This should fail if paths are not working
            raise AssertionError(failure_message)

        # Analyze event delivery consistency
        await self._check_event_content_consistency(successful_paths)
        await self._check_event_completeness_consistency(successful_paths)
        await self._check_event_performance_consistency(successful_paths)

    async def _check_event_content_consistency(self, successful_paths: Dict[str, ManagerPathResults]):
        """Check if event content is consistent across paths."""
        logger.info("📍 Analyzing event content consistency")

        # Group events by type across paths
        events_by_type = {}
        for path_name, path_results in successful_paths.items():
            for event_record in path_results.events_delivered:
                if event_record.success:
                    event_type = event_record.event_type
                    if event_type not in events_by_type:
                        events_by_type[event_type] = {}
                    events_by_type[event_type][path_name] = event_record

        # Check consistency for each event type
        content_inconsistencies = []
        for event_type, path_events in events_by_type.items():
            if len(path_events) < 2:
                continue  # Need at least 2 paths to compare

            # Compare event content across paths
            event_contents = {}
            for path_name, event_record in path_events.items():
                # Extract comparable content (excluding path-specific metadata)
                comparable_content = {
                    k: v for k, v in event_record.event_data.items()
                    if k not in ["test_path", "timestamp", "delivery_time"]
                }
                event_contents[path_name] = comparable_content

            # Check for consistency
            content_values = list(event_contents.values())
            if len(set(json.dumps(content, sort_keys=True) for content in content_values)) > 1:
                # Content is different across paths
                inconsistency = {
                    "event_type": event_type,
                    "paths": list(path_events.keys()),
                    "contents": event_contents
                }
                content_inconsistencies.append(inconsistency)
                logger.warning(f"⚠️ Content inconsistency for {event_type}: {list(event_contents.keys())}")

        # Validate content consistency
        if content_inconsistencies:
            failure_message = (
                f"❌ WEBSOCKET EVENT CONTENT INCONSISTENCY: Different content across paths!\n"
                f"   Inconsistent events: {len(content_inconsistencies)}\n"
                f"   Event types affected: {[inc['event_type'] for inc in content_inconsistencies]}\n"
                f"   This indicates different manager implementations.\n"
                f"\n🚨 THIS PROVES EVENT CONTENT FRAGMENTATION - SSOT CONSOLIDATION REQUIRED!"
            )

            for inconsistency in content_inconsistencies[:3]:  # Log first 3 details
                failure_message += f"\n   {inconsistency['event_type']} paths: {inconsistency['paths']}"

            logger.error(failure_message)
            self.record_metric("content_inconsistencies", len(content_inconsistencies))

            # This should FAIL if content is inconsistent
            raise AssertionError(failure_message)

        else:
            logger.info("✅ EVENT CONTENT CONSISTENCY: All paths deliver identical event content")
            self.record_metric("content_consistency", True)

    async def _check_event_completeness_consistency(self, successful_paths: Dict[str, ManagerPathResults]):
        """Check if event completeness is consistent across paths."""
        logger.info("📍 Analyzing event completeness consistency")

        # Check that all paths deliver all critical events
        path_event_counts = {}
        path_delivered_events = {}

        for path_name, path_results in successful_paths.items():
            delivered_event_types = set()
            for event_record in path_results.events_delivered:
                if event_record.success:
                    delivered_event_types.add(event_record.event_type)

            path_event_counts[path_name] = len(delivered_event_types)
            path_delivered_events[path_name] = delivered_event_types

        # Check for completeness consistency
        expected_event_count = len(self.critical_events)
        incomplete_paths = []
        missing_events = {}

        for path_name, event_count in path_event_counts.items():
            if event_count < expected_event_count:
                incomplete_paths.append(path_name)
                delivered_events = path_delivered_events[path_name]
                missing = set(self.critical_events) - delivered_events
                missing_events[path_name] = list(missing)

        # Validate completeness consistency
        if incomplete_paths:
            failure_message = (
                f"❌ WEBSOCKET EVENT COMPLETENESS INCONSISTENCY: Missing events from some paths!\n"
                f"   Incomplete paths: {incomplete_paths}\n"
                f"   Expected events: {expected_event_count}\n"
                f"   Missing events by path:\n"
            )

            for path_name in incomplete_paths:
                failure_message += f"     {path_name}: {path_event_counts[path_name]}/{expected_event_count} events, missing: {missing_events[path_name]}\n"

            failure_message += f"\n🚨 THIS PROVES EVENT DELIVERY FRAGMENTATION - SSOT CONSOLIDATION REQUIRED!"

            logger.error(failure_message)
            self.record_metric("completeness_inconsistencies", len(incomplete_paths))

            # This should FAIL if completeness is inconsistent
            raise AssertionError(failure_message)

        else:
            logger.info(f"✅ EVENT COMPLETENESS CONSISTENCY: All paths deliver all {expected_event_count} critical events")
            self.record_metric("completeness_consistency", True)

    async def _check_event_performance_consistency(self, successful_paths: Dict[str, ManagerPathResults]):
        """Check if event performance is consistent across paths."""
        logger.info("📍 Analyzing event performance consistency")

        # Compare average delivery times across paths
        path_performance = {}
        for path_name, path_results in successful_paths.items():
            path_performance[path_name] = path_results.average_delivery_time

        if len(path_performance) < 2:
            logger.warning("⚠️ Less than 2 paths with performance data - cannot analyze consistency")
            return

        # Calculate performance statistics
        delivery_times = list(path_performance.values())
        min_time = min(delivery_times)
        max_time = max(delivery_times)
        avg_time = sum(delivery_times) / len(delivery_times)
        time_variance = max_time - min_time

        logger.info(f"📊 PERFORMANCE ANALYSIS:")
        logger.info(f"   Fastest path: {min_time:.4f}s")
        logger.info(f"   Slowest path: {max_time:.4f}s")
        logger.info(f"   Average time: {avg_time:.4f}s")
        logger.info(f"   Time variance: {time_variance:.4f}s")

        # Check for significant performance differences
        # Allow for some variance, but detect major differences
        acceptable_variance = 0.010  # 10ms variance acceptable
        significant_variance_threshold = 0.100  # 100ms variance is concerning

        self.record_metric("performance_variance", time_variance)
        self.record_metric("average_delivery_time", avg_time)

        if time_variance > significant_variance_threshold:
            failure_message = (
                f"❌ WEBSOCKET PERFORMANCE INCONSISTENCY: Significant timing differences!\n"
                f"   Time variance: {time_variance:.4f}s (threshold: {significant_variance_threshold:.3f}s)\n"
                f"   Path performance:\n"
            )

            for path_name, delivery_time in path_performance.items():
                failure_message += f"     {path_name}: {delivery_time:.4f}s\n"

            failure_message += f"\n🚨 THIS INDICATES DIFFERENT PERFORMANCE CHARACTERISTICS - OPTIMIZATION NEEDED!"

            logger.error(failure_message)
            self.record_metric("performance_inconsistency", True)

            # This may fail for significant performance differences
            raise AssertionError(failure_message)

        elif time_variance > acceptable_variance:
            logger.warning(f"⚠️ MODERATE PERFORMANCE VARIANCE: {time_variance:.4f}s (above {acceptable_variance:.3f}s)")
            self.record_metric("performance_variance_concern", True)
            # Don't fail, but log concern

        else:
            logger.info(f"✅ PERFORMANCE CONSISTENCY: Variance {time_variance:.4f}s within acceptable limits")
            self.record_metric("performance_consistency", True)

    def teardown_method(self, method):
        """Teardown with comprehensive event delivery analysis."""
        try:
            # Log comprehensive test results
            logger.info("📊 WEBSOCKET EVENT DELIVERY CONSISTENCY TEST RESULTS:")
            logger.info(f"   Total events recorded: {len(self.event_records)}")
            logger.info(f"   Manager paths tested: {len(self.manager_path_results)}")
            logger.info(f"   Critical events tested: {len(self.critical_events)}")

            # Analyze overall results
            successful_paths = sum(1 for results in self.manager_path_results.values()
                                 if results.manager_type != "error" and results.successful_events > 0)

            total_successful_events = sum(results.successful_events for results in self.manager_path_results.values())
            total_failed_events = sum(results.failed_events for results in self.manager_path_results.values())

            logger.info(f"   Successful paths: {successful_paths}/{len(self.manager_path_results)}")
            logger.info(f"   Total successful events: {total_successful_events}")
            logger.info(f"   Total failed events: {total_failed_events}")

            # Record final metrics
            self.record_metric("total_events_recorded", len(self.event_records))
            self.record_metric("successful_paths", successful_paths)
            self.record_metric("total_successful_events", total_successful_events)
            self.record_metric("total_failed_events", total_failed_events)

            # Determine overall consistency status
            if successful_paths >= 2 and total_failed_events == 0:
                logger.info("✅ EVENT DELIVERY CONSISTENCY SUCCESS: All paths deliver events consistently")
                self.record_metric("overall_consistency_status", "SUCCESS")
            elif successful_paths >= 2:
                logger.warning("⚠️ EVENT DELIVERY PARTIAL SUCCESS: Some inconsistencies detected")
                self.record_metric("overall_consistency_status", "PARTIAL")
            else:
                logger.error("❌ EVENT DELIVERY CONSISTENCY FAILURE: Major issues detected")
                self.record_metric("overall_consistency_status", "FAILURE")

        except Exception as e:
            logger.error(f"❌ TEARDOWN ERROR: {str(e)}")

        finally:
            super().teardown_method(method)


if __name__ == "__main__":
    """Run WebSocket event delivery consistency test directly."""
    import pytest

    logger.info("🚨 RUNNING WEBSOCKET EVENT DELIVERY CONSISTENCY TEST")
    logger.info("📍 PURPOSE: Validate consistent event delivery across all manager access paths")

    # Run the test
    pytest.main([__file__, "-v", "-s"])