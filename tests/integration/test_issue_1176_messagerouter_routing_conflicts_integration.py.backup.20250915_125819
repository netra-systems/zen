"""
MessageRouter Routing Conflicts Integration Tests - Issue #1176

Integration tests for MessageRouter fragmentation conflicts in real execution contexts.
These tests expose the "works individually but fails together" pattern.

Priority: P0 BLOCKER
Business Impact: $500K+ ARR protection - core WebSocket messaging reliability
"""

import pytest
import unittest
import asyncio
import time
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor
import threading

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
class TestMessageRouterConcurrentRoutingConflicts(SSotAsyncTestCase):
    """Integration tests for MessageRouter conflicts in concurrent execution."""

    async def asyncSetUp(self):
        """Set up async test environment."""
        await super().asyncSetUp()
        self.core_router = None
        self.quality_router = None
        self.routing_results = []
        self.conflict_events = []

    async def test_concurrent_message_routing_conflicts(self):
        """
        Test that concurrent message routing between different routers creates conflicts.
        
        Expected Failure: Messages routed to wrong handlers due to router conflicts.
        """
        logger.info("Testing concurrent message routing conflicts...")
        
        # Set up both routers
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            self.core_router = MessageRouter()
            logger.info("Core MessageRouter initialized")
        except Exception as e:
            self.fail(f"Could not initialize core MessageRouter: {e}")
        
        try:
            # Mock quality router dependencies
            import importlib
            quality_module = importlib.import_module('netra_backend.app.services.websocket.quality_message_router')
            QualityMessageRouter = getattr(quality_module, 'QualityMessageRouter')
            
            mock_supervisor = Mock()
            mock_db_session_factory = Mock()
            mock_quality_gate_service = Mock()
            mock_monitoring_service = Mock()
            
            self.quality_router = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
            logger.info("Quality MessageRouter initialized")
        except Exception as e:
            self.skipTest(f"Could not initialize QualityMessageRouter: {e}")
        
        # Create concurrent message routing scenario
        messages = [
            {"type": "START_AGENT", "data": {"user_id": "user1", "query": "test1"}, "message_id": "msg1"},
            {"type": "START_AGENT", "data": {"user_id": "user2", "query": "test2"}, "message_id": "msg2"},
            {"type": "agent_started", "data": {"agent_id": "agent1"}, "message_id": "msg3"},
            {"type": "quality_check", "data": {"status": "pending"}, "message_id": "msg4"},
            {"type": "user_message", "data": {"content": "hello"}, "message_id": "msg5"},
        ]
        
        # Simulate concurrent routing
        routing_tasks = []
        for i, message in enumerate(messages):
            task = asyncio.create_task(self._route_message_concurrently(message, i))
            routing_tasks.append(task)
        
        # Wait for all routing attempts
        routing_results = await asyncio.gather(*routing_tasks, return_exceptions=True)
        
        # Analyze results for conflicts
        conflicts_detected = []
        successful_routes = []
        failed_routes = []
        
        for i, result in enumerate(routing_results):
            if isinstance(result, Exception):
                failed_routes.append((i, messages[i], str(result)))
                logger.error(f"Message routing failed for {messages[i]['message_id']}: {result}")
            else:
                successful_routes.append((i, messages[i], result))
                
                # Check for routing conflicts (same message handled by multiple routers)
                if result.get('core_handled') and result.get('quality_handled'):
                    conflicts_detected.append({
                        'message': messages[i],
                        'conflict_type': 'dual_handling',
                        'details': result
                    })
                    logger.warning(f"ROUTING CONFLICT: Message {messages[i]['message_id']} handled by both routers")
        
        logger.info(f"Routing test results:")
        logger.info(f"  Successful routes: {len(successful_routes)}")
        logger.info(f"  Failed routes: {len(failed_routes)}")
        logger.info(f"  Conflicts detected: {len(conflicts_detected)}")
        
        # If conflicts detected, test fails as expected
        if conflicts_detected:
            conflict_details = "; ".join([f"{c['message']['message_id']}: {c['conflict_type']}" for c in conflicts_detected])
            self.fail(f"CONCURRENT ROUTING CONFLICTS DETECTED: {conflict_details}")
        
        # If failures occurred, indicates fragmentation issues
        if failed_routes:
            failure_details = "; ".join([f"{r[1]['message_id']}: {r[2]}" for r in failed_routes])
            self.fail(f"ROUTING FRAGMENTATION FAILURES: {failure_details}")

    async def _route_message_concurrently(self, message: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Helper to route message through both routers concurrently."""
        result = {
            'message_id': message['message_id'],
            'index': index,
            'core_handled': False,
            'quality_handled': False,
            'core_error': None,
            'quality_error': None,
            'timing': {}
        }
        
        # Try routing through core router
        start_time = time.time()
        try:
            # Simulate message routing through core router
            core_handled = await self._try_core_routing(message)
            result['core_handled'] = core_handled
            result['timing']['core'] = time.time() - start_time
        except Exception as e:
            result['core_error'] = str(e)
            result['timing']['core'] = time.time() - start_time
        
        # Try routing through quality router
        start_time = time.time()
        try:
            # Simulate message routing through quality router
            quality_handled = await self._try_quality_routing(message)
            result['quality_handled'] = quality_handled
            result['timing']['quality'] = time.time() - start_time
        except Exception as e:
            result['quality_error'] = str(e)
            result['timing']['quality'] = time.time() - start_time
        
        return result

    async def _try_core_routing(self, message: Dict[str, Any]) -> bool:
        """Try routing message through core MessageRouter."""
        if not self.core_router:
            return False
        
        # Check if any handler can handle this message
        for handler in self.core_router.handlers:
            try:
                if hasattr(handler, 'supported_types'):
                    if message['type'] in handler.supported_types:
                        # Simulate actual handling (in real scenario would call handler)
                        await asyncio.sleep(0.001)  # Simulate processing time
                        return True
                elif hasattr(handler, 'can_handle'):
                    if handler.can_handle(message):
                        await asyncio.sleep(0.001)  # Simulate processing time
                        return True
            except Exception as e:
                logger.debug(f"Handler {handler.__class__.__name__} failed to check message: {e}")
                continue
        
        return False

    async def _try_quality_routing(self, message: Dict[str, Any]) -> bool:
        """Try routing message through QualityMessageRouter."""
        if not self.quality_router:
            return False
        
        # Check if quality router can handle this message
        try:
            if hasattr(self.quality_router, 'handlers'):
                for handler_name, handler in self.quality_router.handlers.items():
                    try:
                        if hasattr(handler, 'can_handle') and handler.can_handle(message):
                            await asyncio.sleep(0.001)  # Simulate processing time
                            return True
                    except Exception as e:
                        logger.debug(f"Quality handler {handler_name} failed to check message: {e}")
                        continue
        except Exception as e:
            logger.debug(f"Quality router routing failed: {e}")
        
        return False

    async def test_message_routing_race_conditions(self):
        """
        Test for race conditions when multiple routers process messages simultaneously.
        
        Expected Failure: Race conditions cause message handling inconsistencies.
        """
        logger.info("Testing message routing race conditions...")
        
        if not self.core_router or not self.quality_router:
            self.skipTest("Both routers needed for race condition testing")
        
        # Create a high-frequency message stream to trigger race conditions
        message_stream = []
        for i in range(20):
            message_stream.append({
                "type": "START_AGENT",
                "data": {"user_id": f"user_{i}", "query": f"test query {i}"},
                "message_id": f"race_msg_{i}",
                "timestamp": time.time() + (i * 0.001)  # Rapid succession
            })
        
        # Process messages with minimal delay to trigger race conditions
        race_results = []
        tasks = []
        
        for message in message_stream:
            # Create task with very small delay to simulate race conditions
            task = asyncio.create_task(self._process_with_race_condition(message))
            tasks.append(task)
            await asyncio.sleep(0.0001)  # Very small delay to create race condition
        
        # Collect results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze for race condition indicators
        race_conditions = []
        timing_inconsistencies = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                race_conditions.append({
                    'message_id': message_stream[i]['message_id'],
                    'error': str(result),
                    'type': 'exception_race'
                })
            elif isinstance(result, dict):
                # Check for timing inconsistencies that indicate race conditions
                if 'timing' in result:
                    core_time = result['timing'].get('core', 0)
                    quality_time = result['timing'].get('quality', 0)
                    
                    # If processing times vary wildly, might indicate race condition
                    if abs(core_time - quality_time) > 0.05:  # 50ms difference
                        timing_inconsistencies.append({
                            'message_id': result['message_id'],
                            'core_time': core_time,
                            'quality_time': quality_time,
                            'difference': abs(core_time - quality_time)
                        })
                
                # Check for inconsistent handling results
                if result.get('core_handled') != result.get('quality_handled'):
                    race_conditions.append({
                        'message_id': result['message_id'],
                        'core_handled': result.get('core_handled'),
                        'quality_handled': result.get('quality_handled'),
                        'type': 'inconsistent_handling'
                    })
        
        logger.info(f"Race condition analysis:")
        logger.info(f"  Total messages: {len(message_stream)}")
        logger.info(f"  Race conditions detected: {len(race_conditions)}")
        logger.info(f"  Timing inconsistencies: {len(timing_inconsistencies)}")
        
        # Report race conditions if detected
        if race_conditions:
            race_details = "; ".join([f"{r['message_id']}: {r.get('type', 'unknown')}" for r in race_conditions])
            self.fail(f"RACE CONDITIONS DETECTED: {race_details}")
        
        if timing_inconsistencies:
            timing_details = "; ".join([f"{t['message_id']}: {t['difference']:.3f}s" for t in timing_inconsistencies])
            self.fail(f"TIMING INCONSISTENCIES DETECTED: {timing_details}")

    async def _process_with_race_condition(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process message with intentional race condition setup."""
        result = {
            'message_id': message['message_id'],
            'core_handled': False,
            'quality_handled': False,
            'timing': {},
            'race_detected': False
        }
        
        # Use threading to create actual race condition
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both routing attempts simultaneously
            core_future = executor.submit(self._sync_core_routing, message)
            quality_future = executor.submit(self._sync_quality_routing, message)
            
            # Wait for both with timeout
            try:
                core_start = time.time()
                core_result = core_future.result(timeout=1.0)
                core_end = time.time()
                
                quality_start = time.time()
                quality_result = quality_future.result(timeout=1.0)
                quality_end = time.time()
                
                result['core_handled'] = core_result
                result['quality_handled'] = quality_result
                result['timing']['core'] = core_end - core_start
                result['timing']['quality'] = quality_end - quality_start
                
                # Detect if they overlapped (potential race condition)
                if (core_start < quality_end and quality_start < core_end):
                    result['race_detected'] = True
                    
            except Exception as e:
                raise Exception(f"Race condition processing failed: {e}")
        
        return result

    def _sync_core_routing(self, message: Dict[str, Any]) -> bool:
        """Synchronous version of core routing for threading."""
        if not self.core_router:
            return False
        
        # Simulate message processing
        time.sleep(0.001)  # Small processing delay
        
        for handler in self.core_router.handlers:
            try:
                if hasattr(handler, 'supported_types'):
                    if message['type'] in handler.supported_types:
                        return True
            except:
                continue
        return False

    def _sync_quality_routing(self, message: Dict[str, Any]) -> bool:
        """Synchronous version of quality routing for threading."""
        if not self.quality_router:
            return False
        
        # Simulate message processing
        time.sleep(0.001)  # Small processing delay
        
        try:
            if hasattr(self.quality_router, 'handlers'):
                for handler_name, handler in self.quality_router.handlers.items():
                    try:
                        if hasattr(handler, 'can_handle') and handler.can_handle(message):
                            return True
                    except:
                        continue
        except:
            pass
        return False


@pytest.mark.integration
class TestMessageRouterStateConflicts(SSotAsyncTestCase):
    """Test state conflicts between different MessageRouter implementations."""

    async def test_shared_state_contamination(self):
        """
        Test for shared state contamination between router instances.
        
        Expected Failure: Routers share state leading to cross-contamination.
        """
        logger.info("Testing shared state contamination between routers...")
        
        # Create multiple instances of core router
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router1 = MessageRouter()
            router2 = MessageRouter()
        except Exception as e:
            self.skipTest(f"Could not create MessageRouter instances: {e}")
        
        # Test if routers share any state
        initial_stats1 = router1.routing_stats.copy()
        initial_stats2 = router2.routing_stats.copy()
        
        # Modify router1 state
        router1.routing_stats["messages_routed"] = 999
        router1.routing_stats["test_marker"] = "router1_modified"
        
        # Check if router2 was affected
        after_stats2 = router2.routing_stats.copy()
        
        # Compare state
        contamination_detected = False
        contamination_details = []
        
        for key, value in after_stats2.items():
            if key in initial_stats1 and initial_stats1[key] != value:
                if value == 999 or value == "router1_modified":
                    contamination_detected = True
                    contamination_details.append(f"{key}: {value}")
        
        if contamination_detected:
            details = "; ".join(contamination_details)
            self.fail(f"SHARED STATE CONTAMINATION DETECTED: {details}")
        
        # Test handler state sharing
        handler_contamination = []
        
        # Add custom handler to router1
        test_handler = Mock()
        test_handler.supported_types = ["TEST_TYPE"]
        router1.custom_handlers.append(test_handler)
        
        # Check if router2 sees the custom handler
        router2_handler_count = len(router2.custom_handlers)
        if test_handler in router2.custom_handlers:
            handler_contamination.append("Custom handler shared between instances")
        
        # Check if builtin handlers are shared instances
        for i, handler1 in enumerate(router1.builtin_handlers):
            for j, handler2 in enumerate(router2.builtin_handlers):
                if handler1 is handler2 and i == j:  # Same handler instance at same position
                    handler_contamination.append(f"Builtin handler {i} ({handler1.__class__.__name__}) is shared instance")
        
        if handler_contamination:
            details = "; ".join(handler_contamination)
            self.fail(f"HANDLER STATE CONTAMINATION DETECTED: {details}")

    async def test_routing_statistics_isolation(self):
        """
        Test that routing statistics are properly isolated between router instances.
        
        Expected Failure: Statistics contamination between router instances.
        """
        logger.info("Testing routing statistics isolation...")
        
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            # Create multiple router instances
            routers = [MessageRouter() for _ in range(3)]
            
            # Simulate different routing activity for each router
            test_messages = [
                {"type": "START_AGENT", "data": {}, "message_id": "test1"},
                {"type": "user_message", "data": {}, "message_id": "test2"},
                {"type": "agent_started", "data": {}, "message_id": "test3"},
            ]
            
            # Process different numbers of messages with each router
            for i, router in enumerate(routers):
                for j in range(i + 1):  # Router 0: 1 message, Router 1: 2 messages, Router 2: 3 messages
                    message = test_messages[j % len(test_messages)]
                    
                    # Simulate message routing
                    router.routing_stats["messages_routed"] += 1
                    router.routing_stats["message_types"][message["type"]] = router.routing_stats["message_types"].get(message["type"], 0) + 1
            
            # Check for statistics isolation
            isolation_violations = []
            
            expected_counts = [1, 2, 3]  # Expected message counts for each router
            actual_counts = [router.routing_stats["messages_routed"] for router in routers]
            
            if actual_counts != expected_counts:
                isolation_violations.append(f"Message counts: expected {expected_counts}, got {actual_counts}")
            
            # Check if statistics objects are shared
            stats_objects = [id(router.routing_stats) for router in routers]
            if len(set(stats_objects)) != len(routers):
                isolation_violations.append("Statistics objects are shared between router instances")
            
            # Check message type statistics
            for i, router in enumerate(routers):
                for j, other_router in enumerate(routers):
                    if i != j:
                        # Check if statistics leaked between routers
                        for msg_type, count in router.routing_stats["message_types"].items():
                            if msg_type in other_router.routing_stats["message_types"]:
                                other_count = other_router.routing_stats["message_types"][msg_type]
                                # If counts are unexpectedly equal, might indicate sharing
                                if count == other_count and count > 1:
                                    isolation_violations.append(f"Suspicious identical counts for {msg_type}: {count}")
            
            if isolation_violations:
                details = "; ".join(isolation_violations)
                self.fail(f"STATISTICS ISOLATION VIOLATIONS: {details}")
                
        except Exception as e:
            self.fail(f"Statistics isolation test failed: {e}")


if __name__ == '__main__':
    unittest.main()