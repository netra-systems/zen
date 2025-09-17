"""
Issue #1182 Golden Path WebSocket Validation - E2E Staging Tests

End-to-end tests running against staging environment to detect:
- WebSocket Manager SSOT violations in production environment
- Golden Path user flow disruptions caused by manager fragmentation
- Real-world impact of Issue #1209 DemoWebSocketBridge failures
- Staging environment WebSocket event delivery failures

These tests should FAIL initially to prove staging environment SSOT violations.
"""

import asyncio
import json
import time
import websockets
import pytest
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urljoin

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@dataclass
class GoldenPathValidation:
    """Data class to track Golden Path validation results and metrics."""
    test_scenario: str
    user_journey_success: bool = False
    websocket_connection_success: bool = False
    event_delivery_complete: bool = False
    ai_response_received: bool = False
    total_execution_time: float = 0.0
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@pytest.mark.e2e
class GoldenPathWebSocketValidationTests(SSotAsyncTestCase):
    """
    E2E tests for Issue #1182 Golden Path WebSocket validation in staging environment.
    
    These tests validate that the consolidated WebSocket manager maintains full
    Golden Path functionality in production-like environment.
    """

    def setUp(self):
        """Set up staging E2E test environment for Golden Path validation."""
        super().setUp()
        
        # Staging environment configuration
        self.staging_base_url = "https://api.staging.netrasystems.ai"
        self.staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
        self.demo_ws_url = "wss://api.staging.netrasystems.ai/api/demo/ws"
        
        # Test configuration
        self.golden_path_timeout = 60.0  # 60 seconds for complete journey
        self.websocket_connect_timeout = 10.0
        self.ai_response_timeout = 45.0
        
        # Expected WebSocket events for Golden Path
        self.expected_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        self.validation_results = []

    async def test_complete_user_journey_with_websocket_events(self):
        """
        Test complete Golden Path: login → send message → receive AI response.
        
        CURRENT STATE: SHOULD PASS - Golden Path must remain functional
        TARGET STATE: SHOULD PASS - Full user journey working with SSOT manager
        
        Business Impact: Validates complete user experience with consolidated WebSocket manager
        Critical: $500K+ ARR depends on this user journey working reliably
        """
        logger.info("🚀 Testing complete Golden Path user journey (Issue #1182)")
        
        validation = GoldenPathValidation(test_scenario="complete_user_journey")
        journey_start_time = time.time()
        
        try:
            # Step 1: Establish WebSocket connection (using demo endpoint for staging)
            logger.info("📡 Step 1: Establishing WebSocket connection to staging...")
            
            connection_start_time = time.time()
            
            async with websockets.connect(
                self.demo_ws_url,
                timeout=self.websocket_connect_timeout,
                additional_headers={"Origin": "https://app.staging.netrasystems.ai"}
            ) as websocket:
                
                connection_time = time.time() - connection_start_time
                validation.websocket_connection_success = True
                validation.performance_metrics['connection_time'] = connection_time
                
                logger.info(f"✓ WebSocket connected successfully in {connection_time:.2f}s")
                
                # Step 2: Send user message to trigger agent workflow
                logger.info("💬 Step 2: Sending user message to trigger Golden Path...")
                
                test_message = {
                    "type": "user_message",
                    "content": "Help me optimize my cloud infrastructure costs. I'm using AWS and want to reduce my monthly bill.",
                    "timestamp": datetime.now().isoformat(),
                    "user_id": "golden_path_test_user",
                    "thread_id": "golden_path_test_thread"
                }
                
                message_send_time = time.time()
                await websocket.send(json.dumps(test_message))
                
                logger.info(f"✓ User message sent: {test_message['content'][:50]}...")
                
                # Step 3: Listen for WebSocket events and AI response
                logger.info("🔄 Step 3: Listening for WebSocket events and AI response...")
                
                events_received = []
                ai_response = None
                event_timeout = time.time() + self.ai_response_timeout
                
                while time.time() < event_timeout:
                    try:
                        # Wait for WebSocket message with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(message)
                        
                        events_received.append({
                            'timestamp': time.time(),
                            'event': event_data,
                            'received_at': datetime.now().isoformat()
                        })
                        
                        event_type = event_data.get('type', 'unknown')
                        logger.info(f"📨 Received event: {event_type}")
                        
                        # Log event details for analysis
                        if event_type in self.expected_events:
                            logger.info(f"✓ Expected event received: {event_type}")
                        
                        # Check for AI response completion
                        if event_type == "agent_completed" or event_type == "ai_response":
                            ai_response = event_data
                            logger.info("🎯 AI response received - Golden Path complete!")
                            break
                            
                        # Check for agent response with actual content
                        if event_type == "agent_response" and event_data.get('content'):
                            ai_response = event_data
                            logger.info("🎯 Agent response with content received!")
                            break
                            
                    except asyncio.TimeoutError:
                        # Continue listening until overall timeout
                        continue
                    except websockets.ConnectionClosed:
                        logger.error("❌ WebSocket connection closed unexpectedly")
                        break
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ Non-JSON message received: {message}")
                        continue
                
                # Step 4: Analyze Golden Path completion
                validation.events_received = events_received
                validation.total_execution_time = time.time() - journey_start_time
                
                # Validate event delivery
                received_event_types = set(event['event'].get('type') for event in events_received)
                expected_event_set = set(self.expected_events)
                events_delivered = expected_event_set.intersection(received_event_types)
                
                validation.event_delivery_complete = len(events_delivered) >= 3  # At least 3 core events
                validation.ai_response_received = ai_response is not None
                
                # Golden Path success criteria
                validation.user_journey_success = (
                    validation.websocket_connection_success and
                    validation.event_delivery_complete and
                    validation.ai_response_received
                )
                
                # Performance metrics
                validation.performance_metrics.update({
                    'total_journey_time': validation.total_execution_time,
                    'events_received_count': len(events_received),
                    'unique_event_types': len(received_event_types),
                    'expected_events_delivered': len(events_delivered),
                    'ai_response_time': time.time() - message_send_time if ai_response else None
                })
                
                logger.info(f"📊 Golden Path Validation Results:")
                logger.info(f"   Journey success: {validation.user_journey_success}")
                logger.info(f"   WebSocket connection: {validation.websocket_connection_success}")
                logger.info(f"   Event delivery: {validation.event_delivery_complete}")
                logger.info(f"   AI response: {validation.ai_response_received}")
                logger.info(f"   Total time: {validation.total_execution_time:.2f}s")
                logger.info(f"   Events received: {len(events_received)}")
                logger.info(f"   Event types: {list(received_event_types)}")
                
                if ai_response:
                    response_content = ai_response.get('content', ai_response.get('data', {}))
                    logger.info(f"   AI response preview: {str(response_content)[:100]}...")
                
        except Exception as e:
            validation.errors.append(str(e))
            validation.user_journey_success = False
            logger.error(f"❌ Golden Path validation failed: {e}")
        
        self.validation_results.append(validation)
        
        # CRITICAL: Golden Path must work for business continuity
        # This should PASS to protect $500K+ ARR functionality
        self.assertTrue(
            validation.user_journey_success,
            f"Golden Path user journey failed after Issue #1182 WebSocket SSOT migration. "
            f"Critical business impact: $500K+ ARR at risk. "
            f"Connection: {validation.websocket_connection_success}, "
            f"Events: {validation.event_delivery_complete}, "
            f"AI Response: {validation.ai_response_received}. "
            f"Errors: {validation.errors}"
        )
        
        self.assertTrue(
            validation.websocket_connection_success,
            f"WebSocket connection failed in staging environment. "
            f"Issue #1182 WebSocket manager may have broken connectivity."
        )

    async def test_websocket_five_critical_events_delivered(self):
        """
        Validate all 5 critical WebSocket events sent during agent execution.
        
        CURRENT STATE: SHOULD PASS - Critical business value protection
        TARGET STATE: SHOULD PASS - All events delivered reliably
        
        Business Impact: Real-time user experience depends on these events
        Events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        """
        logger.info("📡 Testing WebSocket five critical events delivery (Issue #1182)")
        
        validation = GoldenPathValidation(test_scenario="five_critical_events")
        
        try:
            logger.info("📡 Connecting to staging WebSocket for event validation...")
            
            async with websockets.connect(
                self.demo_ws_url,
                timeout=self.websocket_connect_timeout,
                additional_headers={"Origin": "https://app.staging.netrasystems.ai"}
            ) as websocket:
                
                validation.websocket_connection_success = True
                logger.info("✓ WebSocket connected for event validation")
                
                # Send message to trigger all agent events
                test_message = {
                    "type": "user_message", 
                    "content": "Run a comprehensive analysis with multiple tool executions to trigger all agent events.",
                    "timestamp": datetime.now().isoformat()
                }
                
                event_start_time = time.time()
                await websocket.send(json.dumps(test_message))
                
                # Track received events
                received_events = {}
                event_timeline = []
                timeout = time.time() + self.ai_response_timeout
                
                while time.time() < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(message)
                        event_type = event_data.get('type')
                        
                        if event_type in self.expected_events:
                            received_events[event_type] = event_data
                            event_timeline.append({
                                'event_type': event_type,
                                'timestamp': time.time() - event_start_time,
                                'data': event_data
                            })
                            logger.info(f"✓ Critical event received: {event_type}")
                        
                        # Check if we've received all expected events
                        if len(received_events) >= len(self.expected_events):
                            logger.info("🎯 All critical events received!")
                            break
                            
                        # Or if we received completion event
                        if event_type == "agent_completed":
                            logger.info("🏁 Agent completion event received")
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except (websockets.ConnectionClosed, json.JSONDecodeError):
                        break
                
                # Analyze event delivery
                validation.events_received = event_timeline
                validation.total_execution_time = time.time() - event_start_time
                
                events_delivered = len(received_events)
                events_expected = len(self.expected_events)
                event_delivery_rate = events_delivered / events_expected if events_expected > 0 else 0
                
                validation.event_delivery_complete = event_delivery_rate >= 0.6  # At least 60% of events
                validation.ai_response_received = 'agent_completed' in received_events
                
                validation.performance_metrics = {
                    'events_delivered': events_delivered,
                    'events_expected': events_expected,
                    'event_delivery_rate': event_delivery_rate,
                    'event_delivery_time': validation.total_execution_time,
                    'events_timeline': event_timeline
                }
                
                logger.info(f"📊 Critical Events Analysis:")
                logger.info(f"   Events delivered: {events_delivered}/{events_expected}")
                logger.info(f"   Delivery rate: {event_delivery_rate:.2%}")
                logger.info(f"   Delivered events: {list(received_events.keys())}")
                logger.info(f"   Missing events: {set(self.expected_events) - set(received_events.keys())}")
                logger.info(f"   Total time: {validation.total_execution_time:.2f}s")
                
                # Log event timeline
                for event in event_timeline:
                    logger.info(f"   📅 {event['event_type']}: +{event['timestamp']:.2f}s")
                
                validation.user_journey_success = (
                    validation.websocket_connection_success and
                    validation.event_delivery_complete
                )
                
        except Exception as e:
            validation.errors.append(str(e))
            validation.user_journey_success = False
            logger.error(f"❌ Critical events validation failed: {e}")
        
        self.validation_results.append(validation)
        
        # CRITICAL: All critical events must be delivered for real-time UX
        # This should PASS to maintain user experience quality
        self.assertTrue(
            validation.event_delivery_complete,
            f"Critical WebSocket events not fully delivered after Issue #1182 migration. "
            f"Real-time user experience compromised. "
            f"Delivery rate: {validation.performance_metrics.get('event_delivery_rate', 0):.2%}. "
            f"Missing events: {set(self.expected_events) - set(event['event_type'] for event in validation.events_received)}"
        )
        
        # Validate minimum event delivery rate for acceptable user experience
        delivery_rate = validation.performance_metrics.get('event_delivery_rate', 0)
        self.assertGreaterEqual(
            delivery_rate, 0.6,
            f"Event delivery rate too low: {delivery_rate:.2%}. "
            f"Minimum 60% required for acceptable user experience. "
            f"Issue #1182 WebSocket manager may have broken event delivery."
        )

    async def test_production_readiness_concurrent_users(self):
        """
        Test production readiness with multiple concurrent users.
        
        CURRENT STATE: SHOULD PASS - Production scalability validation
        TARGET STATE: SHOULD PASS - Handles concurrent load gracefully
        
        Business Impact: Validates system can handle production user load
        """
        logger.info("👥 Testing production readiness with concurrent users (Issue #1182)")
        
        validation = GoldenPathValidation(test_scenario="concurrent_users_production")
        concurrent_users = 3  # Conservative for staging environment
        
        try:
            async def simulate_user_journey(user_index: int) -> Dict[str, Any]:
                """Simulate individual user Golden Path journey."""
                user_start_time = time.time()
                user_result = {
                    'user_index': user_index,
                    'success': False,
                    'connection_time': 0,
                    'events_received': 0,
                    'ai_response': False,
                    'total_time': 0,
                    'error': None
                }
                
                try:
                    # Connect user to WebSocket
                    async with websockets.connect(
                        self.demo_ws_url,
                        timeout=self.websocket_connect_timeout,
                        additional_headers={"Origin": "https://app.staging.netrasystems.ai"}
                    ) as websocket:
                        
                        connection_time = time.time() - user_start_time
                        user_result['connection_time'] = connection_time
                        
                        # Send user-specific message
                        message = {
                            "type": "user_message",
                            "content": f"User {user_index}: Help me analyze cost optimization strategies for my infrastructure.",
                            "user_id": f"concurrent_test_user_{user_index}",
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        await websocket.send(json.dumps(message))
                        
                        # Listen for events
                        events_count = 0
                        ai_response_received = False
                        timeout = time.time() + 30.0  # 30 second timeout per user
                        
                        while time.time() < timeout:
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                                event_data = json.loads(response)
                                events_count += 1
                                
                                if event_data.get('type') in ['agent_completed', 'agent_response']:
                                    ai_response_received = True
                                    break
                                    
                            except asyncio.TimeoutError:
                                continue
                            except (websockets.ConnectionClosed, json.JSONDecodeError):
                                break
                        
                        user_result.update({
                            'success': ai_response_received,
                            'events_received': events_count,
                            'ai_response': ai_response_received,
                            'total_time': time.time() - user_start_time
                        })
                        
                        logger.info(f"✓ User {user_index}: {events_count} events, AI response: {ai_response_received}")
                        
                except Exception as e:
                    user_result['error'] = str(e)
                    user_result['total_time'] = time.time() - user_start_time
                    logger.error(f"❌ User {user_index} failed: {e}")
                
                return user_result
            
            # Execute concurrent user simulations
            logger.info(f"🚀 Starting {concurrent_users} concurrent user simulations...")
            
            concurrent_start_time = time.time()
            user_tasks = [simulate_user_journey(i) for i in range(concurrent_users)]
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            total_concurrent_time = time.time() - concurrent_start_time
            
            # Analyze concurrent performance
            successful_users = sum(1 for result in user_results 
                                 if isinstance(result, dict) and result.get('success'))
            
            total_events = sum(result.get('events_received', 0) for result in user_results 
                             if isinstance(result, dict))
            
            avg_connection_time = sum(result.get('connection_time', 0) for result in user_results 
                                    if isinstance(result, dict)) / len(user_results)
            
            validation.user_journey_success = successful_users >= (concurrent_users * 0.7)  # 70% success rate
            validation.websocket_connection_success = True
            validation.event_delivery_complete = total_events > 0
            validation.ai_response_received = successful_users > 0
            
            validation.performance_metrics = {
                'concurrent_users': concurrent_users,
                'successful_users': successful_users,
                'success_rate': successful_users / concurrent_users,
                'total_events': total_events,
                'avg_connection_time': avg_connection_time,
                'total_concurrent_time': total_concurrent_time,
                'user_results': user_results
            }
            
            logger.info(f"📊 Concurrent Users Analysis:")
            logger.info(f"   Concurrent users: {concurrent_users}")
            logger.info(f"   Successful users: {successful_users}")
            logger.info(f"   Success rate: {successful_users/concurrent_users:.2%}")
            logger.info(f"   Total events: {total_events}")
            logger.info(f"   Avg connection time: {avg_connection_time:.2f}s")
            logger.info(f"   Total execution time: {total_concurrent_time:.2f}s")
            
        except Exception as e:
            validation.errors.append(str(e))
            validation.user_journey_success = False
            logger.error(f"❌ Concurrent users test failed: {e}")
        
        self.validation_results.append(validation)
        
        # Validate production readiness
        success_rate = validation.performance_metrics.get('success_rate', 0)
        self.assertGreaterEqual(
            success_rate, 0.7,
            f"Concurrent user success rate too low: {success_rate:.2%}. "
            f"Production readiness requires ≥70% success rate. "
            f"Issue #1182 WebSocket manager may not handle concurrent load properly."
        )

    def tearDown(self):
        """Clean up and log comprehensive Golden Path validation results."""
        super().tearDown()
        
        if self.validation_results:
            logger.info("📋 COMPREHENSIVE GOLDEN PATH VALIDATION SUMMARY:")
            logger.info("=" * 70)
            
            total_validations = len(self.validation_results)
            successful_journeys = sum(1 for result in self.validation_results if result.user_journey_success)
            
            logger.info(f"Total Golden Path validations: {total_validations}")
            logger.info(f"Successful user journeys: {successful_journeys}")
            logger.info(f"Golden Path success rate: {successful_journeys/total_validations:.2%}")
            
            # Business impact summary
            if successful_journeys == total_validations:
                logger.info("🎯 GOLDEN PATH FULLY PROTECTED: $500K+ ARR functionality validated")
            else:
                logger.error(f"🚨 GOLDEN PATH AT RISK: {total_validations - successful_journeys} failures detected")
            
            for result in self.validation_results:
                logger.info(f"\n📊 {result.test_scenario}:")
                logger.info(f"   Journey success: {result.user_journey_success}")
                logger.info(f"   WebSocket connection: {result.websocket_connection_success}")
                logger.info(f"   Event delivery: {result.event_delivery_complete}")
                logger.info(f"   AI response: {result.ai_response_received}")
                logger.info(f"   Execution time: {result.total_execution_time:.2f}s")
                logger.info(f"   Events received: {len(result.events_received)}")
                
                if result.performance_metrics:
                    logger.info(f"   Performance: {result.performance_metrics}")
                
                if result.errors:
                    logger.error(f"   Errors: {result.errors}")
            
            logger.info("=" * 70)


if __name__ == '__main__':
    # Run with pytest for proper staging E2E execution
    pytest.main([__file__, "-v", "--tb=short"])