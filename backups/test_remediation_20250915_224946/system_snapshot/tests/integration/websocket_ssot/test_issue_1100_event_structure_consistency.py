"""
Test Event Structure Consistency - Issue #1100

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure
- Business Goal: Fix current event structure validation failures (3/42 tests)
- Value Impact: Ensures reliable WebSocket event delivery for $500K+ ARR chat functionality
- Strategic Impact: Prevents event delivery inconsistencies affecting user experience

This test module validates WebSocket event structure consistency across different
WebSocket manager implementations and fixes current mission critical test failures.

CRITICAL: These tests use real services and are designed to FAIL initially with
current event structure inconsistencies and PASS after SSOT consolidation.
"""

import pytest
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture, real_redis_fixture
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class WebSocketEventStructureConsistencyTests(BaseIntegrationTest):
    """Test WebSocket event structure consistency with real services."""
    
    # Required WebSocket events for Golden Path functionality
    REQUIRED_WEBSOCKET_EVENTS = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]
    
    # Expected event structure fields
    REQUIRED_EVENT_FIELDS = [
        "type",
        "data",
        "timestamp",
        "user_id",
        "thread_id"
    ]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_structure_consistency(self, real_services_fixture):
        """
        SHOULD FAIL: Validate consistent WebSocket event structure across implementations.
        
        This test addresses the current 3/42 mission critical test failures by
        validating event structure consistency between different WebSocket managers.
        """
        logger.info("Validating WebSocket event structure consistency with real services")
        
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        event_structures = []
        inconsistencies = []
        
        try:
            # Test canonical SSOT WebSocket manager event structure
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            # Create test user context
            test_user_id = ensure_user_id("event_test_user")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="event_test_thread",
                run_id="event_test_run",
                request_id="event_structure_test"
            )
            
            # Create canonical WebSocket manager
            canonical_manager = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            # Test each required event type
            for event_type in self.REQUIRED_WEBSOCKET_EVENTS:
                test_event = {
                    "type": event_type,
                    "data": {"message": f"Test {event_type} event"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": str(test_user_id),
                    "thread_id": "event_test_thread"
                }
                
                # Validate event can be processed
                try:
                    # This should work without errors for consistent structure
                    processed_event = await self._process_event_with_manager(
                        canonical_manager, test_event
                    )
                    
                    event_structures.append({
                        'manager_type': 'canonical_ssot',
                        'event_type': event_type,
                        'structure': processed_event,
                        'fields': list(processed_event.keys()) if processed_event else [],
                        'success': processed_event is not None
                    })
                    
                except Exception as e:
                    logger.error(f"Canonical manager failed to process {event_type}: {e}")
                    event_structures.append({
                        'manager_type': 'canonical_ssot',
                        'event_type': event_type, 
                        'structure': None,
                        'fields': [],
                        'success': False,
                        'error': str(e)
                    })
            
        except ImportError as e:
            logger.error(f"Cannot import canonical WebSocket manager: {e}")
            pytest.fail("Canonical WebSocketManager must be available for event testing")
        
        try:
            # Test deprecated factory WebSocket manager event structure (if available)
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            
            # Create deprecated factory manager
            factory_manager = await create_websocket_manager(user_context=test_context)
            
            # Test event structure from factory manager
            for event_type in self.REQUIRED_WEBSOCKET_EVENTS:
                test_event = {
                    "type": event_type,
                    "data": {"message": f"Factory test {event_type} event"}, 
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": str(test_user_id),
                    "thread_id": "event_test_thread"
                }
                
                try:
                    processed_event = await self._process_event_with_manager(
                        factory_manager, test_event
                    )
                    
                    event_structures.append({
                        'manager_type': 'deprecated_factory',
                        'event_type': event_type,
                        'structure': processed_event,
                        'fields': list(processed_event.keys()) if processed_event else [],
                        'success': processed_event is not None
                    })
                    
                except Exception as e:
                    logger.error(f"Factory manager failed to process {event_type}: {e}")
                    event_structures.append({
                        'manager_type': 'deprecated_factory',
                        'event_type': event_type,
                        'structure': None,
                        'fields': [],
                        'success': False,
                        'error': str(e)
                    })
            
        except ImportError:
            logger.info("Deprecated factory manager not available (good for SSOT)")
        
        # Analyze event structure consistency
        canonical_events = [e for e in event_structures if e['manager_type'] == 'canonical_ssot']
        factory_events = [e for e in event_structures if e['manager_type'] == 'deprecated_factory']
        
        # Check for structure inconsistencies between managers
        for event_type in self.REQUIRED_WEBSOCKET_EVENTS:
            canonical_event = next((e for e in canonical_events if e['event_type'] == event_type), None)
            factory_event = next((e for e in factory_events if e['event_type'] == event_type), None)
            
            if canonical_event and factory_event:
                if canonical_event['fields'] != factory_event['fields']:
                    inconsistencies.append({
                        'event_type': event_type,
                        'issue': 'field_mismatch',
                        'canonical_fields': canonical_event['fields'],
                        'factory_fields': factory_event['fields']
                    })
        
        # Check for missing required fields
        for event_struct in event_structures:
            missing_fields = [field for field in self.REQUIRED_EVENT_FIELDS 
                             if field not in event_struct['fields']]
            if missing_fields:
                inconsistencies.append({
                    'manager_type': event_struct['manager_type'],
                    'event_type': event_struct['event_type'],
                    'issue': 'missing_required_fields',
                    'missing_fields': missing_fields
                })
        
        logger.info(f"Analyzed {len(event_structures)} event structures")
        logger.info(f"Found {len(inconsistencies)} inconsistencies")
        
        # This assertion should FAIL initially with current event structure inconsistencies
        assert len(inconsistencies) == 0, (
            f"Found {len(inconsistencies)} WebSocket event structure inconsistencies:\n" +
            "\n".join([f"  {inc}" for inc in inconsistencies])
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_all_required_websocket_events_supported(self, real_services_fixture):
        """
        SHOULD FAIL: Validate all required WebSocket events are supported consistently.
        
        Addresses mission critical test failures by ensuring all 5 required events
        are supported with consistent structure across WebSocket implementations.
        """
        logger.info("Validating all required WebSocket events are supported")
        
        supported_events = {}
        event_support_issues = []
        
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            test_user_id = ensure_user_id("event_support_test")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="event_support_thread",
                run_id="event_support_run", 
                request_id="event_support_test"
            )
            
            manager = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            # Test support for each required event
            for event_type in self.REQUIRED_WEBSOCKET_EVENTS:
                try:
                    # Create test event
                    test_event = {
                        "type": event_type,
                        "data": {
                            "message": f"Support test for {event_type}",
                            "test_id": f"support_test_{event_type}"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": str(test_user_id),
                        "thread_id": "event_support_thread"
                    }
                    
                    # Test if manager can handle this event type
                    result = await self._test_event_support(manager, test_event)
                    
                    supported_events[event_type] = {
                        'supported': result['supported'],
                        'error': result.get('error'),
                        'processing_time': result.get('processing_time', 0)
                    }
                    
                    if not result['supported']:
                        event_support_issues.append({
                            'event_type': event_type,
                            'issue': 'not_supported',
                            'error': result.get('error', 'Unknown error')
                        })
                        
                except Exception as e:
                    supported_events[event_type] = {
                        'supported': False,
                        'error': str(e),
                        'processing_time': None
                    }
                    event_support_issues.append({
                        'event_type': event_type,
                        'issue': 'exception_during_test',
                        'error': str(e)
                    })
            
        except ImportError as e:
            pytest.fail(f"Cannot import WebSocketManager for event support testing: {e}")
        
        # Analyze event support
        unsupported_events = [event for event, support in supported_events.items() 
                             if not support['supported']]
        
        logger.info(f"Event support results: {len(supported_events)} tested")
        logger.info(f"Unsupported events: {unsupported_events}")
        
        # This assertion should FAIL initially if required events are not supported
        assert len(unsupported_events) == 0, (
            f"Required WebSocket events not supported: {unsupported_events}. "
            f"All {self.REQUIRED_WEBSOCKET_EVENTS} must be supported for Golden Path functionality. "
            f"Issues: {event_support_issues}"
        )
        
        # Validate reasonable processing times
        slow_events = []
        for event_type, support_info in supported_events.items():
            if support_info['processing_time'] and support_info['processing_time'] > 1.0:
                slow_events.append({
                    'event_type': event_type,
                    'processing_time': support_info['processing_time']
                })
        
        if slow_events:
            logger.warning(f"Slow event processing detected: {slow_events}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_delivery_consistency(self, real_services_fixture):
        """
        SHOULD FAIL: Validate consistent WebSocket event delivery behavior.
        
        Tests that events are delivered consistently regardless of which
        WebSocket manager implementation is used.
        """
        logger.info("Validating WebSocket event delivery consistency")
        
        redis = real_services_fixture["redis"]
        delivery_results = []
        
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            test_user_id = ensure_user_id("delivery_test_user")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="delivery_test_thread",
                run_id="delivery_test_run",
                request_id="delivery_consistency_test"
            )
            
            manager = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            # Test delivery of each event type multiple times
            for event_type in self.REQUIRED_WEBSOCKET_EVENTS:
                delivery_attempts = []
                
                for attempt in range(3):  # Test 3 deliveries per event type
                    test_event = {
                        "type": event_type,
                        "data": {
                            "message": f"Delivery test {attempt} for {event_type}",
                            "attempt": attempt,
                            "test_timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": str(test_user_id),
                        "thread_id": "delivery_test_thread",
                        "delivery_test_id": f"{event_type}_attempt_{attempt}"
                    }
                    
                    try:
                        start_time = asyncio.get_event_loop().time()
                        
                        # Attempt event delivery
                        delivery_result = await self._test_event_delivery(
                            manager, test_event, redis
                        )
                        
                        end_time = asyncio.get_event_loop().time()
                        delivery_time = end_time - start_time
                        
                        delivery_attempts.append({
                            'attempt': attempt,
                            'success': delivery_result['success'],
                            'delivery_time': delivery_time,
                            'error': delivery_result.get('error')
                        })
                        
                    except Exception as e:
                        delivery_attempts.append({
                            'attempt': attempt,
                            'success': False,
                            'delivery_time': None,
                            'error': str(e)
                        })
                
                delivery_results.append({
                    'event_type': event_type,
                    'attempts': delivery_attempts,
                    'success_rate': len([a for a in delivery_attempts if a['success']]) / len(delivery_attempts),
                    'avg_delivery_time': sum([a['delivery_time'] for a in delivery_attempts 
                                            if a['delivery_time'] is not None]) / len(delivery_attempts)
                })
            
        except ImportError as e:
            pytest.fail(f"Cannot import WebSocketManager for delivery testing: {e}")
        
        # Analyze delivery consistency
        delivery_issues = []
        
        for result in delivery_results:
            # Check success rate (should be 100%)
            if result['success_rate'] < 1.0:
                delivery_issues.append({
                    'event_type': result['event_type'],
                    'issue': 'delivery_failures',
                    'success_rate': result['success_rate'],
                    'failed_attempts': [a for a in result['attempts'] if not a['success']]
                })
            
            # Check delivery time consistency (should be reasonable and consistent)
            delivery_times = [a['delivery_time'] for a in result['attempts'] 
                            if a['delivery_time'] is not None]
            if delivery_times:
                max_time = max(delivery_times)
                min_time = min(delivery_times)
                if max_time - min_time > 0.5:  # More than 500ms variance
                    delivery_issues.append({
                        'event_type': result['event_type'],
                        'issue': 'inconsistent_delivery_times',
                        'min_time': min_time,
                        'max_time': max_time,
                        'variance': max_time - min_time
                    })
        
        logger.info(f"Delivery consistency results: {len(delivery_results)} event types tested")
        logger.info(f"Found {len(delivery_issues)} delivery issues")
        
        # This assertion should FAIL initially with current delivery inconsistencies
        assert len(delivery_issues) == 0, (
            f"Found {len(delivery_issues)} WebSocket event delivery inconsistencies:\n" +
            "\n".join([f"  {issue}" for issue in delivery_issues])
        )
    
    async def _process_event_with_manager(self, manager, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process an event with the given WebSocket manager.
        
        Args:
            manager: WebSocket manager instance
            event: Event data to process
            
        Returns:
            Processed event data or None if processing failed
        """
        try:
            if hasattr(manager, 'send_event'):
                # Use send_event method if available
                await manager.send_event(event['type'], event['data'])
                return event
            elif hasattr(manager, '_format_event'):
                # Use internal format method if available
                formatted_event = manager._format_event(event['type'], event['data'])
                return formatted_event
            else:
                logger.warning(f"Manager {type(manager).__name__} has no known event processing method")
                return None
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            return None
    
    async def _test_event_support(self, manager, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test if a WebSocket manager supports a specific event type.
        
        Args:
            manager: WebSocket manager instance
            event: Event to test support for
            
        Returns:
            Support test results
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            result = await self._process_event_with_manager(manager, event)
            end_time = asyncio.get_event_loop().time()
            
            return {
                'supported': result is not None,
                'processing_time': end_time - start_time
            }
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            return {
                'supported': False,
                'error': str(e),
                'processing_time': end_time - start_time
            }
    
    async def _test_event_delivery(self, manager, event: Dict[str, Any], redis) -> Dict[str, Any]:
        """
        Test event delivery through WebSocket manager.
        
        Args:
            manager: WebSocket manager instance
            event: Event to deliver
            redis: Redis client for tracking delivery
            
        Returns:
            Delivery test results
        """
        try:
            # Store delivery attempt in Redis for tracking
            delivery_key = f"delivery_test:{event.get('delivery_test_id', 'unknown')}"
            await redis.set(delivery_key, json.dumps(event), ex=60)  # Expire in 60 seconds
            
            # Attempt delivery
            result = await self._process_event_with_manager(manager, event)
            
            # Mark as delivered in Redis
            if result:
                delivery_result_key = f"delivery_result:{event.get('delivery_test_id', 'unknown')}"
                await redis.set(delivery_result_key, json.dumps(result), ex=60)
            
            return {
                'success': result is not None,
                'delivered_event': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }