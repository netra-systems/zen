"Issue #874: WebSocket events routing test for ExecutionEngine SSOT."

This test validates that WebSocket events are properly routed to the correct
users through the consolidated ExecutionEngine pattern. It ensures user-specific
event delivery and prevents cross-user event leakage.

Business Value Justification:
    - Segment: Platform/Internal  
- Business Goal: User Experience & Security
- Value Impact: Ensures real-time chat events reach correct users for $"500K" plus ARR operations
- Strategic Impact: Validates WebSocket integration in SSOT ExecutionEngine consolidation

Key Validation Areas:
    - User-specific WebSocket event routing
- Prevention of cross-user event leakage
- Real-time event delivery through ExecutionEngine
- WebSocket event data integrity
- Concurrent user event handling

EXPECTED BEHAVIOR:
    This test should PASS if WebSocket events are properly routed through UserExecutionEngine.
If it FAILS, it indicates WebSocket integration issues in SSOT consolidation.
""

import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional
import concurrent.futures

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketEventsRoutingTests(SSotBaseTestCase):
    Test WebSocket events routing through UserExecutionEngine."
    Test WebSocket events routing through UserExecutionEngine.""

    
    def setup_method(self, method):
        "Set up test environment for WebSocket routing tests."
        super().setup_method(method)
        
        self.routing_violations = []
        self.event_delivery_issues = []
        self.cross_user_leaks = []
        self.performance_issues = []
        
        # Record test context metrics
        self.record_metric('test_type', 'websocket_events_routing')
        self.record_metric('test_category', 'mission_critical')
        logger.info(Starting WebSocket events routing testing")"
    
    def test_user_specific_event_delivery(self):
        Test that WebSocket events are delivered only to the correct user."
        Test that WebSocket events are delivered only to the correct user."
        logger.info(📡 ROUTING TEST: Validating user-specific event delivery")"
        
        async def test_event_delivery():
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                # Create event tracking for multiple users
                user_events = {}
                
                def create_tracking_websocket_manager(user_id: str):
                    Create WebSocket manager that tracks events for specific user.""
                    user_events[user_id] = []
                    
                    mock_manager = Mock()
                    
                    async def emit_user_event(event_type, event_data, target_user_id=None, **kwargs):
                        event_record = {
                            'event_type': event_type,
                            'event_data': event_data,
                            'target_user_id': target_user_id or user_id,
                            'timestamp': time.time(),
                            'kwargs': kwargs
                        }
                        user_events[user_id].append(event_record)
                        return True
                    
                    mock_manager.emit_user_event = emit_user_event
                    return mock_manager
                
                # Create multiple users
                users = []
                for i in range(3):
                    user_id = UnifiedIdGenerator.generate_base_id(fevent_user_{i}, True, 8)
                    thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, fevent_test_{i})
                    
                    user_context = UserExecutionContext(
                        user_id=user_id,
                        run_id=run_id,
                        thread_id=thread_id,
                        metadata={'test': f'event_delivery_{i}'}
                    
                    # Create WebSocket manager with event tracking
                    websocket_manager = create_tracking_websocket_manager(user_id)
                    
                    # Create engine
                    agent_factory = AgentInstanceFactory()
                    websocket_emitter = UnifiedWebSocketEmitter(
                        manager=websocket_manager,
                        user_id=user_context.user_id,
                        context=user_context
                    )
                    
                    engine = UserExecutionEngine(user_context, agent_factory, websocket_emitter)
                    
                    users.append({
                        'user_id': user_id,
                        'engine': engine,
                        'websocket_emitter': websocket_emitter,
                        'context': user_context
                    }
                
                # Trigger events for each user
                for i, user in enumerate(users):
                    emitter = user['websocket_emitter']
                    user_id = user['user_id']
                    
                    # Send different types of events
                    await emitter.notify_agent_started(fagent_{i)", {"
                        user_specific_data: fdata_for_user_{i},
                        agent_id: fagent_{i}"
                        agent_id: fagent_{i}""

                    }
                    
                    await emitter.notify_agent_thinking(f"agent_{i}, fUser {i} is thinking, i+1)"
                    
                    await emitter.notify_tool_executing(ftool_{i), {
                        tool_name: f"user_tool_{i},"
                        parameters: {"user: i}"
                    }
                    
                    await emitter.notify_tool_completed(ftool_{i), {
                        result: fresult_for_user_{i}","
                        "success: True"
                    }
                    
                    await emitter.notify_agent_completed(fagent_{i), {
                        "final_result: fcompleted_for_user_{i},"
                        user_id: user_id
                    }
                
                # Validate event delivery
                all_users_received_events = True
                cross_user_contamination = False
                
                for i, user in enumerate(users):
                    user_id = user['user_id']
                    events = user_events.get(user_id, [)
                    
                    # Check that user received events
                    if len(events) == 0:
                        all_users_received_events = False
                        self.event_delivery_issues.append(fUser {user_id} received no events)"
                        self.event_delivery_issues.append(fUser {user_id} received no events)""

                        continue
                    
                    # Verify events contain correct user-specific data
                    user_specific_found = False
                    for event in events:
                        event_data = event.get('event_data', {)
                        if isinstance(event_data, dict):
                            # Check for user-specific data
                            if (f"data_for_user_{i} in str(event_data) or"
                                fresult_for_user_{i} in str(event_data) or
                                fcompleted_for_user_{i} in str(event_data)):
                                user_specific_found = True
                            
                            # Check for contamination from other users
                            for j in range(3):
                                if j != i:
                                    if (fdata_for_user_{j}" in str(event_data) or"
                                        fresult_for_user_{j} in str(event_data)):
                                        cross_user_contamination = True
                                        self.cross_user_leaks.append(
                                            fUser {user_id} received data for user {j}: {event_data}
                                        )
                    
                    if not user_specific_found:
                        self.routing_violations.append(f"User {user_id} did not receive user-specific events)"
                    
                    logger.info(fUser {i} ({user_id}: Received {len(events)} events, user-specific: {user_specific_found}")"
                
                # Cleanup
                for user in users:
                    await user['engine'].cleanup()
                
                # Validate overall results
                self.assertTrue(all_users_received_events, All users should receive their events)
                self.assertFalse(cross_user_contamination, No cross-user event contamination should occur")"
                
                logger.info(✅ PASS: User-specific event delivery working correctly)
                return True
                
            except Exception as e:
                self.routing_violations.append(fEvent delivery test failed: {e})"
                self.routing_violations.append(fEvent delivery test failed: {e})"
                logger.error(f"❌ FAIL: User-specific event delivery broken - {e})"
                return False
        
        result = asyncio.run(test_event_delivery())
        self.assertTrue(result, User-specific WebSocket event delivery should work correctly)
    
    def test_concurrent_websocket_events(self):
        Test that WebSocket events work correctly under concurrent load.""
        logger.info(🔄 CONCURRENCY TEST: Validating concurrent WebSocket event handling)
        
        async def concurrent_event_sender(user_index: int, event_count: int = 20):
            "Send events concurrently for a single user."
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                user_id = UnifiedIdGenerator.generate_base_id(fconcurrent_event_user_{user_index}, True, 8)"
                user_id = UnifiedIdGenerator.generate_base_id(fconcurrent_event_user_{user_index}, True, 8)"
                thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, f"concurrent_event_{user_index})"
                
                user_context = UserExecutionContext(
                    user_id=user_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    metadata={'test': f'concurrent_events_{user_index}'}
                
                # Track events for this user
                events_sent = []
                
                mock_websocket_manager = Mock()
                async def track_emit(*args, **kwargs):
                    events_sent.append({
                        'args': args,
                        'kwargs': kwargs,
                        'timestamp': time.time()
                    }
                    return True
                mock_websocket_manager.emit_user_event = track_emit
                
                # Create engine
                agent_factory = AgentInstanceFactory()
                websocket_emitter = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user_context.user_id,
                    context=user_context
                )
                
                engine = UserExecutionEngine(user_context, agent_factory, websocket_emitter)
                
                # Send events rapidly
                event_tasks = []
                for i in range(event_count):
                    # Mix different event types
                    if i % 5 == 0:
                        task = emitter.notify_agent_started(fagent_{i), {event_index: i)
                    elif i % 5 == 1:
                        task = emitter.notify_agent_thinking(fagent_{i}, f"Thinking {i}, i)"
                    elif i % 5 == 2:
                        task = emitter.notify_tool_executing(ftool_{i), {"tool_index: i)"
                    elif i % 5 == 3:
                        task = emitter.notify_tool_completed(ftool_{i), {result_index: i)
                    else:
                        task = emitter.notify_agent_completed(fagent_{i), {"completion_index: i)"
                    
                    event_tasks.append(task)
                    
                    # Small delay to simulate realistic timing
                    if i % 5 == 0:
                        await asyncio.sleep(0.1)
                
                # Wait for all events to complete
                await asyncio.gather(*event_tasks)
                
                # Cleanup
                await engine.cleanup()
                
                return {
                    'user_index': user_index,
                    'user_id': user_id,
                    'events_sent': len(events_sent),
                    'expected_events': event_count,
                    'success': len(events_sent) == event_count
                }
                
            except Exception as e:
                logger.error(fConcurrent event sender failed for user {user_index}: {e}")"
                return {
                    'user_index': user_index,
                    'error': str(e),
                    'success': False
                }
        
        async def test_concurrent_events():
            # Run multiple concurrent event senders
            user_count = 4
            events_per_user = 20
            
            start_time = time.time()
            tasks = [
                concurrent_event_sender(i, events_per_user)
                for i in range(user_count)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful_users = 0
            total_events_sent = 0
            performance_ok = True
            
            for result in results:
                if isinstance(result, dict) and result.get('success', False):
                    successful_users += 1
                    total_events_sent += result['events_sent']
                    logger.info(fUser {result['user_index']}: Sent {result['events_sent']}/{result['expected_events']} events)
                else:
                    self.performance_issues.append(fConcurrent event test failed: {result})"
                    self.performance_issues.append(fConcurrent event test failed: {result})""

            
            total_time = end_time - start_time
            events_per_second = total_events_sent / total_time if total_time > 0 else 0
            
            # Performance validation
            if events_per_second < 100:  # Should handle at least 100 events/sec
                performance_ok = False
                self.performance_issues.append(f"Low event throughput: {events_per_second:."1f"} events/sec)"
            
            # Validate results
            expected_total_events = user_count * events_per_user
            self.assertEqual(successful_users, user_count, fAll {user_count} users should complete successfully)
            self.assertEqual(total_events_sent, expected_total_events, fAll {expected_total_events} events should be sent)
            self.assertTrue(performance_ok, fEvent throughput should be adequate (got {events_per_second:."1f"} events/sec)")"
            
            logger.info(f✅ PASS: Concurrent events handled - {total_events_sent} events in {total_time:."3f"}s ({events_per_second:."1f"} events/sec))""

            return True
        
        result = asyncio.run(test_concurrent_events())
        self.assertTrue(result, Concurrent WebSocket events should be handled correctly)
    
    def test_websocket_event_data_integrity(self):
        "Test that WebSocket event data maintains integrity through ExecutionEngine."
        logger.info(🔒 INTEGRITY TEST: Validating WebSocket event data integrity)"
        logger.info(🔒 INTEGRITY TEST: Validating WebSocket event data integrity)""

        
        async def test_data_integrity():
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                user_id = UnifiedIdGenerator.generate_base_id("integrity_user, True, 8)"
                thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, integrity_test)
                
                user_context = UserExecutionContext(
                    user_id=user_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    metadata={'test': 'data_integrity'}
                
                # Create event capture mechanism
                captured_events = []
                
                mock_websocket_manager = Mock()
                async def capture_event(event_type, event_data, **kwargs):
                    captured_events.append({
                        'event_type': event_type,
                        'event_data': event_data,
                        'kwargs': kwargs,
                        'capture_time': time.time()
                    }
                    return True
                mock_websocket_manager.emit_user_event = capture_event
                
                # Create engine
                agent_factory = AgentInstanceFactory()
                websocket_emitter = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user_context.user_id,
                    context=user_context
                )
                
                engine = UserExecutionEngine(user_context, agent_factory, websocket_emitter)
                
                # Test data integrity with complex data structures
                test_data_sets = [
                    # Simple data
                    {"simple: value, number: 42},"
                    
                    # Complex nested data
                    {
                        nested: {"
                        nested: {"
                            "level1: {"
                                level2: [item1, item2", {level3: True}]"
                            }
                        },
                        array: [1, 2, 3, {nested_in_array: value}]"
                        array: [1, 2, 3, {nested_in_array: value}]""

                    },
                    
                    # Special characters and unicode
                    {
                        "special_chars: !@#$%^&*(),"
                        unicode: 🚀 测试 データ,
                        "quotes: 'Single double quotes'"
                    },
                    
                    # Large data
                    {
                        large_string: x * 1000,
                        large_array: list(range(100)),"
                        large_array: list(range(100)),"
                        user_context": {"
                            user_id: user_id,
                            thread_id": thread_id,"
                            run_id: run_id
                        }
                    }
                ]
                
                # Send events with different data types
                for i, test_data in enumerate(test_data_sets):
                    await websocket_emitter.notify_agent_started(fintegrity_agent_{i}, test_data)"
                    await websocket_emitter.notify_agent_started(fintegrity_agent_{i}, test_data)"
                    await websocket_emitter.notify_tool_executing(f"integrity_tool_{i), {"
                        original_data: test_data,
                        test_index: i"
                        test_index: i""

                    }
                    await websocket_emitter.notify_agent_completed(fintegrity_agent_{i)", {"
                        result: test_data,
                        integrity_check": ftest_{i}_complete"
                    }
                
                # Validate data integrity
                self.assertGreater(len(captured_events), 0, Should have captured events)
                
                data_corruption_found = False
                for i, event in enumerate(captured_events):
                    event_data = event.get('event_data', {)
                    
                    # Check that event data is properly structured
                    if not isinstance(event_data, dict):
                        data_corruption_found = True
                        self.event_delivery_issues.append(fEvent {i}: Data not dictionary - {type(event_data)})
                        continue
                    
                    # Validate specific data integrity based on event content
                    if integrity_check in str(event_data):"
                    if integrity_check in str(event_data):"
                        # This should be a completion event
                        if "result not in event_data:"
                            data_corruption_found = True
                            self.event_delivery_issues.append(fEvent {i}: Missing result in completion event)
                    
                    if "unicode in str(event_data):"
                        # Check unicode preservation
                        if 🚀 not in str(event_data) or 測試 not in str(event_data):
                            data_corruption_found = True
                            self.event_delivery_issues.append(fEvent {i}: Unicode characters corrupted)"
                            self.event_delivery_issues.append(fEvent {i}: Unicode characters corrupted)""

                    
                    # Check user context preservation
                    user_context_found = user_id in str(event_data)
                    if not user_context_found and "user_context in str(event_data):"
                        data_corruption_found = True
                        self.event_delivery_issues.append(fEvent {i}: User context corrupted)
                
                # Cleanup
                await engine.cleanup()
                
                # Validate overall integrity
                self.assertFalse(data_corruption_found, "No data corruption should be found)"
                
                logger.info(f✅ PASS: Data integrity maintained - {len(captured_events)} events validated)
                return True
                
            except Exception as e:
                self.event_delivery_issues.append(fData integrity test failed: {e})
                logger.error(f❌ FAIL: WebSocket event data integrity broken - {e}")"
                return False
        
        result = asyncio.run(test_data_integrity())
        self.assertTrue(result, WebSocket event data integrity should be maintained)
    
    def test_websocket_event_ordering(self):
        "Test that WebSocket events maintain proper ordering through ExecutionEngine."
        logger.info(📊 ORDERING TEST: Validating WebSocket event ordering)
        
        async def test_event_ordering():
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                user_id = UnifiedIdGenerator.generate_base_id(ordering_user", True, 8)"
                thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, ordering_test)
                
                user_context = UserExecutionContext(
                    user_id=user_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    metadata={'test': 'event_ordering'}
                
                # Capture events with timestamps
                ordered_events = []
                
                mock_websocket_manager = Mock()
                async def capture_ordered_event(event_type, event_data, **kwargs):
                    ordered_events.append({
                        'event_type': event_type,
                        'event_data': event_data,
                        'sequence': len(ordered_events),
                        'timestamp': time.time()
                    }
                    return True
                mock_websocket_manager.emit_user_event = capture_ordered_event
                
                # Create engine
                agent_factory = AgentInstanceFactory()
                websocket_emitter = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user_context.user_id,
                    context=user_context
                )
                
                engine = UserExecutionEngine(user_context, agent_factory, websocket_emitter)
                
                # Send events in specific order
                expected_sequence = []
                
                # Start agent
                await websocket_emitter.notify_agent_started(ordering_agent, {"step: 1)"
                expected_sequence.append(agent_started")"
                
                # Agent thinking
                await websocket_emitter.notify_agent_thinking(ordering_agent, Planning execution, 1)
                expected_sequence.append("agent_thinking)"
                
                # Tool execution
                await websocket_emitter.notify_tool_executing(ordering_tool, {step: 2)
                expected_sequence.append(tool_executing)"
                expected_sequence.append(tool_executing)""

                
                # Tool completed
                await websocket_emitter.notify_tool_completed("ordering_tool, {step: 3, result: success)"
                expected_sequence.append("tool_completed)"
                
                # More thinking
                await websocket_emitter.notify_agent_thinking(ordering_agent, Processing results, 2)
                expected_sequence.append(agent_thinking)"
                expected_sequence.append(agent_thinking)""

                
                # Agent completed
                await websocket_emitter.notify_agent_completed("ordering_agent, {step: 4, final: True)"
                expected_sequence.append(agent_completed")"
                
                # Validate event ordering
                self.assertEqual(len(ordered_events), len(expected_sequence), Should have correct number of events)
                
                ordering_violations = []
                for i, (event, expected_type) in enumerate(zip(ordered_events, expected_sequence)):
                    if expected_type not in event['event_type']:
                        ordering_violations.append(fPosition {i}: Expected {expected_type}, got {event['event_type']})"
                        ordering_violations.append(fPosition {i}: Expected {expected_type}, got {event['event_type']})""

                    
                    # Check sequential timestamps (allowing for small timing variations)
                    if i > 0:
                        prev_timestamp = ordered_events[i-1]['timestamp']
                        curr_timestamp = event['timestamp']
                        if curr_timestamp < prev_timestamp:
                            ordering_violations.append(f"Timestamp ordering violation at position {i})"
                
                # Cleanup
                await engine.cleanup()
                
                # Validate ordering
                self.assertEqual(len(ordering_violations), 0, fEvent ordering violations: {ordering_violations})
                
                logger.info(f✅ PASS: Event ordering maintained - {len(ordered_events)} events in correct sequence)
                return True
                
            except Exception as e:
                self.routing_violations.append(fEvent ordering test failed: {e}")"
                logger.error(f❌ FAIL: WebSocket event ordering broken - {e})
                return False
        
        result = asyncio.run(test_event_ordering())
        self.assertTrue(result, WebSocket event ordering should be maintained)
    
    def test_comprehensive_websocket_routing_report(self):
        "Generate comprehensive WebSocket routing test report."
        logger.info(📊 COMPREHENSIVE WEBSOCKET ROUTING REPORT)"
        logger.info(📊 COMPREHENSIVE WEBSOCKET ROUTING REPORT)""

        
        all_issues = (self.routing_violations + self.event_delivery_issues + 
                     self.cross_user_leaks + self.performance_issues)
        
        routing_summary = {
            'total_issues': len(all_issues),
            'routing_violations': len(self.routing_violations),
            'delivery_issues': len(self.event_delivery_issues),
            'cross_user_leaks': len(self.cross_user_leaks),
            'performance_issues': len(self.performance_issues),
            'routing_status': 'PASS' if len(all_issues) == 0 else 'FAIL',
            'security_risk': len(self.cross_user_leaks) > 0,
            'performance_risk': len(self.performance_issues) > 0
        }
        
        logger.info(f"WEBSOCKET ROUTING SUMMARY:)"
        logger.info(f  Total Issues: {routing_summary['total_issues']})
        logger.info(f  Routing Violations: {routing_summary['routing_violations']})
        logger.info(f  Delivery Issues: {routing_summary['delivery_issues']}")"
        logger.info(f  Cross-User Leaks: {routing_summary['cross_user_leaks']})
        logger.info(f  Performance Issues: {routing_summary['performance_issues']})
        logger.info(f"  Overall Status: {routing_summary['routing_status']})"
        
        if all_issues:
            logger.warning(WEBSOCKET ROUTING ISSUES DETECTED:")"
            for i, issue in enumerate(all_issues[:5], 1):
                logger.warning(f  {i}. {issue})
            if len(all_issues) > 5:
                logger.warning(f  ... and {len(all_issues) - 5} more issues)"
                logger.warning(f  ... and {len(all_issues) - 5} more issues)""

        
        # This test should PASS if WebSocket routing works correctly
        self.assertEqual(
            routing_summary['total_issues'], 0,
            f"WebSocket events routing should work correctly."
            fFound {routing_summary['total_issues']} issues: Security Risk: {routing_summary['security_risk']}, 
            fPerformance Risk: {routing_summary['performance_risk']}
        )
        
        logger.info(✅ SUCCESS: WebSocket events routing working correctly through UserExecutionEngine")"


if __name__ == '__main__':
    # Configure logging for direct execution
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    unittest.main()
))))))))))))))))))))))))))
}