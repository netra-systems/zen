"""
Test Golden Path WebSocket Protection - Issue #1100

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Core Business Value
- Business Goal: Protect $500K+ ARR WebSocket functionality during SSOT migration
- Value Impact: Ensures chat functionality continues during import pattern updates
- Strategic Impact: Validates business continuity throughout technical debt elimination

This test module protects Golden Path WebSocket functionality during SSOT migration
and validates that business value is preserved throughout the import update process.

CRITICAL: These tests use staging environment and are designed to maintain PASS
status throughout the migration process to ensure business continuity.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from test_framework.base_e2e_test import BaseE2ETest
from tests.e2e.staging.conftest import staging_services_fixture
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class GoldenPathWebSocketProtectionTests(BaseE2ETest):
    """Test Golden Path WebSocket functionality protection during SSOT migration."""
    
    # Golden Path WebSocket events that MUST continue working
    GOLDEN_PATH_EVENTS = [
        "agent_started",
        "agent_thinking",
        "tool_executing", 
        "tool_completed",
        "agent_completed"
    ]
    
    # Business-critical user flow scenarios
    BUSINESS_CRITICAL_SCENARIOS = [
        "user_login_chat_flow",
        "agent_execution_response_flow", 
        "multi_message_conversation_flow",
        "agent_tool_usage_flow"
    ]
    
    @pytest.mark.e2e
    @pytest.mark.staging_required
    async def test_golden_path_websocket_events_during_migration(self, staging_services):
        """
        SHOULD PASS: Golden Path WebSocket events continue working during migration.
        
        This test MUST pass throughout the entire migration process to ensure
        business continuity. If this fails, it indicates business value is at risk.
        """
        logger.info("Testing Golden Path WebSocket events during SSOT migration")
        
        staging_url = staging_services.get("backend_url", "http://localhost:8000")
        websocket_url = staging_url.replace("http", "ws") + "/ws"
        
        # Test user context for staging
        test_user_context = {
            "user_id": "golden_path_test_user",
            "thread_id": f"golden_path_{int(time.time())}",
            "run_id": f"run_{int(time.time())}",
            "request_id": f"golden_path_test_{int(time.time())}"
        }
        
        golden_path_results = {
            'connection_established': False,
            'events_received': [],
            'agent_response_received': False,
            'total_test_time': 0,
            'business_continuity': False
        }
        
        start_time = time.time()
        
        try:
            # Test Golden Path WebSocket connection
            async with self._create_staging_websocket_client(websocket_url) as websocket:
                golden_path_results['connection_established'] = True
                logger.info("Golden Path WebSocket connection established")
                
                # Send agent request (core Golden Path scenario)
                agent_request = {
                    "type": "agent_request",
                    "data": {
                        "message": "Golden Path test: analyze system status",
                        "agent": "triage_agent",
                        "user_context": test_user_context
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **test_user_context
                }
                
                await websocket.send(json.dumps(agent_request))
                logger.info("Golden Path agent request sent")
                
                # Collect events for Golden Path validation
                events_collected = []
                timeout_start = time.time()
                
                while time.time() - timeout_start < 30:  # 30 second timeout
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5)
                        event_data = json.loads(message)
                        events_collected.append(event_data)
                        
                        logger.info(f"Golden Path event received: {event_data.get('type', 'unknown')}")
                        
                        # Check for agent completion
                        if event_data.get('type') == 'agent_completed':
                            golden_path_results['agent_response_received'] = True
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.warning(f"Golden Path event reception error: {e}")
                        break
                
                golden_path_results['events_received'] = events_collected
                
        except Exception as e:
            logger.error(f"Golden Path WebSocket test failed: {e}")
            golden_path_results['error'] = str(e)
        
        end_time = time.time()
        golden_path_results['total_test_time'] = end_time - start_time
        
        # Validate Golden Path business continuity
        required_events_received = []
        for event in golden_path_results['events_received']:
            event_type = event.get('type')
            if event_type in self.GOLDEN_PATH_EVENTS:
                required_events_received.append(event_type)
        
        # Check business continuity criteria
        golden_path_results['business_continuity'] = (
            golden_path_results['connection_established'] and
            golden_path_results['agent_response_received'] and
            len(required_events_received) >= 3  # At least 3 of 5 required events
        )
        
        logger.info(f"Golden Path test results: {golden_path_results}")
        
        # This assertion MUST pass for business continuity
        assert golden_path_results['connection_established'], (
            "Golden Path WebSocket connection MUST be established during migration. "
            "Business continuity is at risk if this fails."
        )
        
        assert golden_path_results['business_continuity'], (
            f"Golden Path business continuity validation failed. "
            f"Connection: {golden_path_results['connection_established']}, "
            f"Agent response: {golden_path_results['agent_response_received']}, "
            f"Events received: {len(required_events_received)}/5 required events. "
            f"This indicates $500K+ ARR functionality may be impacted."
        )
    
    @pytest.mark.e2e
    @pytest.mark.staging_required
    async def test_agent_execution_websocket_integration_ssot(self, staging_services):
        """
        SHOULD FAIL then PASS: Agent execution WebSocket integration via SSOT.
        
        FAIL: With fragmented imports causing agent-WebSocket integration issues
        PASS: After SSOT consolidation ensures reliable agent-WebSocket integration
        """
        logger.info("Testing agent execution WebSocket integration via SSOT")
        
        staging_url = staging_services.get("backend_url", "http://localhost:8000")
        websocket_url = staging_url.replace("http", "ws") + "/ws"
        
        integration_results = {
            'agent_websocket_integration': False,
            'event_delivery_consistency': False,
            'agent_response_quality': False,
            'ssot_compliance_indicators': []
        }
        
        try:
            async with self._create_staging_websocket_client(websocket_url) as websocket:
                # Test agent execution with WebSocket integration
                test_request = {
                    "type": "agent_request",
                    "data": {
                        "message": "SSOT integration test: provide system analysis",
                        "agent": "triage_agent",
                        "integration_test": True
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": "ssot_integration_test",
                    "thread_id": f"ssot_test_{int(time.time())}",
                    "request_id": f"ssot_integration_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_request))
                
                # Collect integration events
                integration_events = []
                agent_response_data = None
                
                timeout_start = time.time()
                while time.time() - timeout_start < 45:  # Extended timeout for agent processing
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        event_data = json.loads(message)
                        integration_events.append(event_data)
                        
                        # Analyze event for SSOT compliance indicators
                        if self._analyze_event_for_ssot_compliance(event_data):
                            integration_results['ssot_compliance_indicators'].append(
                                event_data.get('type', 'unknown')
                            )
                        
                        if event_data.get('type') == 'agent_completed':
                            agent_response_data = event_data.get('data', {})
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.warning(f"Integration event error: {e}")
                        break
                
                # Validate integration quality
                integration_results['agent_websocket_integration'] = len(integration_events) > 0
                
                # Check event delivery consistency
                event_types_received = [e.get('type') for e in integration_events]
                expected_event_sequence = ['agent_started', 'agent_thinking', 'agent_completed']
                sequence_match = all(event_type in event_types_received for event_type in expected_event_sequence)
                integration_results['event_delivery_consistency'] = sequence_match
                
                # Validate agent response quality
                if agent_response_data:
                    integration_results['agent_response_quality'] = (
                        'result' in agent_response_data and
                        len(str(agent_response_data.get('result', ''))) > 10
                    )
                
        except Exception as e:
            logger.error(f"Agent-WebSocket integration test failed: {e}")
            integration_results['error'] = str(e)
        
        logger.info(f"Integration test results: {integration_results}")
        
        # This assertion should FAIL initially with fragmented imports
        # and PASS after SSOT consolidation
        assert integration_results['agent_websocket_integration'], (
            "Agent-WebSocket integration failed. This indicates SSOT fragmentation "
            "is causing integration issues between agent execution and WebSocket delivery."
        )
        
        assert integration_results['event_delivery_consistency'], (
            f"WebSocket event delivery inconsistent. Expected sequence not found. "
            f"Events received: {[e.get('type') for e in integration_events] if 'integration_events' in locals() else 'none'}. "
            f"This suggests SSOT violations in event delivery patterns."
        )
    
    @pytest.mark.e2e
    @pytest.mark.staging_required
    async def test_multi_user_websocket_isolation_post_migration(self, staging_services):
        """
        SHOULD FAIL then PASS: Multi-user WebSocket isolation after SSOT migration.
        
        FAIL: If factory patterns cause user isolation violations
        PASS: After SSOT ensures proper user context isolation
        """
        logger.info("Testing multi-user WebSocket isolation post-SSOT migration")
        
        staging_url = staging_services.get("backend_url", "http://localhost:8000")
        websocket_url = staging_url.replace("http", "ws") + "/ws"
        
        isolation_results = {
            'user1_events': [],
            'user2_events': [],
            'cross_contamination_detected': False,
            'proper_isolation': False,
            'isolation_violations': []
        }
        
        try:
            # Create two concurrent user sessions
            user1_context = {
                "user_id": "isolation_test_user1",
                "thread_id": f"user1_thread_{int(time.time())}",
                "request_id": f"user1_req_{int(time.time())}"
            }
            
            user2_context = {
                "user_id": "isolation_test_user2", 
                "thread_id": f"user2_thread_{int(time.time())}",
                "request_id": f"user2_req_{int(time.time())}"
            }
            
            # Test concurrent WebSocket connections
            async with self._create_staging_websocket_client(websocket_url) as ws1, \
                      self._create_staging_websocket_client(websocket_url) as ws2:
                
                # Send requests from both users simultaneously
                user1_request = {
                    "type": "agent_request",
                    "data": {
                        "message": "User 1 isolation test message",
                        "agent": "triage_agent",
                        "isolation_marker": "USER1_MARKER"
                    },
                    **user1_context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                user2_request = {
                    "type": "agent_request", 
                    "data": {
                        "message": "User 2 isolation test message",
                        "agent": "triage_agent",
                        "isolation_marker": "USER2_MARKER"
                    },
                    **user2_context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Send both requests
                await asyncio.gather(
                    ws1.send(json.dumps(user1_request)),
                    ws2.send(json.dumps(user2_request))
                )
                
                # Collect events from both users
                async def collect_user_events(websocket, user_id, results_key):
                    events = []
                    timeout_start = time.time()
                    
                    while time.time() - timeout_start < 30:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=5)
                            event_data = json.loads(message)
                            events.append(event_data)
                            
                            if event_data.get('type') == 'agent_completed':
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logger.warning(f"Event collection error for {user_id}: {e}")
                            break
                    
                    isolation_results[results_key] = events
                
                # Collect events concurrently
                await asyncio.gather(
                    collect_user_events(ws1, "user1", 'user1_events'),
                    collect_user_events(ws2, "user2", 'user2_events')
                )
                
        except Exception as e:
            logger.error(f"Multi-user isolation test failed: {e}")
            isolation_results['error'] = str(e)
        
        # Analyze isolation
        user1_events = isolation_results['user1_events']
        user2_events = isolation_results['user2_events']
        
        # Check for cross-contamination
        for event in user1_events:
            if event.get('user_id') == 'isolation_test_user2':
                isolation_results['cross_contamination_detected'] = True
                isolation_results['isolation_violations'].append({
                    'type': 'user1_received_user2_event',
                    'event': event
                })
        
        for event in user2_events:
            if event.get('user_id') == 'isolation_test_user1':
                isolation_results['cross_contamination_detected'] = True
                isolation_results['isolation_violations'].append({
                    'type': 'user2_received_user1_event',
                    'event': event
                })
        
        # Check for proper isolation markers
        user1_markers = [e for e in user1_events 
                        if 'USER1_MARKER' in str(e.get('data', {}))]
        user2_markers = [e for e in user2_events 
                        if 'USER2_MARKER' in str(e.get('data', {}))]
        
        isolation_results['proper_isolation'] = (
            len(user1_markers) > 0 and len(user2_markers) > 0 and
            not isolation_results['cross_contamination_detected']
        )
        
        logger.info(f"Multi-user isolation results: {isolation_results}")
        
        # This assertion should FAIL initially if factory patterns cause isolation violations
        assert not isolation_results['cross_contamination_detected'], (
            f"Multi-user WebSocket isolation violations detected: "
            f"{isolation_results['isolation_violations']}. "
            f"SSOT consolidation should prevent user context cross-contamination."
        )
        
        assert isolation_results['proper_isolation'], (
            "Proper multi-user WebSocket isolation not achieved. "
            f"User1 events: {len(user1_events)}, User2 events: {len(user2_events)}. "
            "SSOT implementation must ensure complete user context isolation."
        )
    
    @pytest.mark.e2e
    @pytest.mark.staging_required
    async def test_business_critical_chat_scenarios_preservation(self, staging_services):
        """
        SHOULD PASS: Business-critical chat scenarios continue working.
        
        Validates that core business value scenarios continue functioning
        throughout the SSOT migration process.
        """
        logger.info("Testing business-critical chat scenarios preservation")
        
        staging_url = staging_services.get("backend_url", "http://localhost:8000")
        websocket_url = staging_url.replace("http", "ws") + "/ws"
        
        scenario_results = {}
        
        for scenario in self.BUSINESS_CRITICAL_SCENARIOS:
            scenario_results[scenario] = {
                'completed': False,
                'business_value_delivered': False,
                'execution_time': 0,
                'events_count': 0
            }
            
            try:
                start_time = time.time()
                
                async with self._create_staging_websocket_client(websocket_url) as websocket:
                    scenario_result = await self._execute_business_scenario(
                        websocket, scenario
                    )
                    
                    end_time = time.time()
                    
                    scenario_results[scenario].update({
                        'completed': scenario_result['completed'],
                        'business_value_delivered': scenario_result['business_value_delivered'],
                        'execution_time': end_time - start_time,
                        'events_count': len(scenario_result.get('events', []))
                    })
                    
            except Exception as e:
                logger.error(f"Business scenario {scenario} failed: {e}")
                scenario_results[scenario]['error'] = str(e)
        
        # Validate business continuity
        completed_scenarios = [s for s, r in scenario_results.items() if r['completed']]
        business_value_scenarios = [s for s, r in scenario_results.items() 
                                  if r['business_value_delivered']]
        
        logger.info(f"Business scenario results: {len(completed_scenarios)}/{len(self.BUSINESS_CRITICAL_SCENARIOS)} completed")
        
        # This assertion MUST pass for business continuity
        assert len(completed_scenarios) >= len(self.BUSINESS_CRITICAL_SCENARIOS) * 0.8, (
            f"Insufficient business-critical scenarios completed: "
            f"{len(completed_scenarios)}/{len(self.BUSINESS_CRITICAL_SCENARIOS)}. "
            f"Business continuity is at risk during SSOT migration."
        )
        
        assert len(business_value_scenarios) >= len(self.BUSINESS_CRITICAL_SCENARIOS) * 0.8, (
            f"Insufficient business value delivery: "
            f"{len(business_value_scenarios)}/{len(self.BUSINESS_CRITICAL_SCENARIOS)} scenarios delivered value. "
            f"$500K+ ARR functionality may be impacted."
        )
    
    async def _create_staging_websocket_client(self, websocket_url: str):
        """Create WebSocket client for staging environment."""
        import websockets
        
        try:
            return await websockets.connect(
                websocket_url,
                timeout=10,
                ping_interval=20,
                ping_timeout=10
            )
        except Exception as e:
            logger.error(f"Failed to create staging WebSocket client: {e}")
            raise
    
    def _analyze_event_for_ssot_compliance(self, event_data: Dict[str, Any]) -> bool:
        """
        Analyze event data for SSOT compliance indicators.
        
        Args:
            event_data: WebSocket event data
            
        Returns:
            True if event shows SSOT compliance indicators
        """
        ssot_indicators = [
            'user_context' in str(event_data),
            'unified' in str(event_data).lower(),
            event_data.get('type') in self.GOLDEN_PATH_EVENTS,
            'timestamp' in event_data,
            'user_id' in event_data
        ]
        
        return sum(ssot_indicators) >= 3  # At least 3 SSOT indicators
    
    async def _execute_business_scenario(self, websocket, scenario: str) -> Dict[str, Any]:
        """
        Execute a business-critical scenario.
        
        Args:
            websocket: WebSocket connection
            scenario: Scenario identifier
            
        Returns:
            Scenario execution results
        """
        scenario_request = {
            "type": "agent_request",
            "data": {
                "message": f"Business scenario test: {scenario}",
                "agent": "triage_agent",
                "scenario": scenario
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": f"business_test_{scenario}",
            "thread_id": f"business_thread_{int(time.time())}",
            "request_id": f"business_req_{int(time.time())}"
        }
        
        await websocket.send(json.dumps(scenario_request))
        
        events = []
        business_value_delivered = False
        
        timeout_start = time.time()
        while time.time() - timeout_start < 45:  # 45 second timeout for business scenarios
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                event_data = json.loads(message)
                events.append(event_data)
                
                # Check for business value indicators
                if event_data.get('type') == 'agent_completed':
                    result_data = event_data.get('data', {})
                    business_value_delivered = (
                        'result' in result_data and
                        len(str(result_data.get('result', ''))) > 20 and
                        scenario in str(result_data)
                    )
                    break
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Business scenario event error: {e}")
                break
        
        return {
            'completed': len(events) > 0,
            'business_value_delivered': business_value_delivered,
            'events': events
        }