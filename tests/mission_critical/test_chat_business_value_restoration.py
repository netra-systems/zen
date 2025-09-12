"""
Mission Critical Tests for Chat Business Value Restoration

This module validates that the core chat functionality is restored after
ToolRegistry duplicate registration fixes. These tests focus on actual
business value delivery rather than technical metrics.

CRITICAL REQUIREMENTS:
- Tests MUST validate complete chat functionality end-to-end
- Tests MUST use real authentication (JWT/OAuth) per CLAUDE.md
- Tests MUST detect if business value (chat interactions) is broken
- Tests MUST validate all 5 WebSocket agent events are delivered

Business Value Focus:
- Users can successfully chat with AI agents
- WebSocket events provide real-time interaction feedback
- Multiple users can chat simultaneously without conflicts
- System remains stable across multiple chat sessions

See: /Users/anthony/Documents/GitHub/netra-apex/audit/staging/auto-solve-loop/toolregistry-duplicate-registration-20250109.md
"""

import asyncio
import json
import logging
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any

import websockets
from websockets.exceptions import ConnectionClosedError

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.base_test_case import SSotBaseTestCase
from tests.e2e.staging_config import StagingTestConfig

logger = logging.getLogger(__name__)


class WebSocketEventCapture:
    """Helper to capture and analyze WebSocket events during chat sessions."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_types: Set[str] = set()
        self.agent_events: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.start_time = time.time()
        
    def capture_event(self, event_data: Dict[str, Any]):
        """Capture a WebSocket event."""
        event = {
            'timestamp': time.time() - self.start_time,
            'type': event_data.get('type', 'unknown'),
            'data': event_data,
            'received_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.events.append(event)
        self.event_types.add(event['type'])
        
        # Track agent-specific events
        if event['type'] in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
            self.agent_events.append(event)
        
        # Track errors
        if event['type'] == 'error':
            error_msg = event_data.get('message', 'Unknown error')
            self.errors.append(error_msg)
            if "already registered" in error_msg or "modelmetaclass" in error_msg:
                logger.error(f" ALERT:  Registry error captured: {error_msg}")
    
    def has_complete_agent_flow(self) -> bool:
        """Check if all 5 critical agent events were received."""
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        return required_events.issubset(self.event_types)
    
    def has_registry_errors(self) -> bool:
        """Check if any registry-related errors were captured."""
        return any(
            "already registered" in error or "modelmetaclass" in error 
            for error in self.errors
        )
    
    def get_business_value_score(self) -> float:
        """Calculate business value score based on captured events (0.0 to 1.0)."""
        score = 0.0
        
        # Base score for successful connection
        if len(self.events) > 0:
            score += 0.2
        
        # Score for agent events
        agent_event_score = len(self.event_types.intersection({
            'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'
        })) / 5.0 * 0.5
        score += agent_event_score
        
        # Score for complete flow
        if self.has_complete_agent_flow():
            score += 0.2
        
        # Penalty for errors
        if self.has_registry_errors():
            score -= 0.5
        
        # Score for response content
        if any(event.get('data', {}).get('result') for event in self.events):
            score += 0.1
            
        return max(0.0, min(1.0, score))
    
    def get_analysis_report(self) -> Dict[str, Any]:
        """Get comprehensive business value analysis."""
        return {
            'total_events': len(self.events),
            'event_types': list(self.event_types),
            'agent_events_count': len(self.agent_events),
            'complete_agent_flow': self.has_complete_agent_flow(),
            'registry_errors': self.has_registry_errors(),
            'error_count': len(self.errors),
            'business_value_score': self.get_business_value_score(),
            'session_duration': time.time() - self.start_time,
            'errors': self.errors
        }


@pytest.mark.mission_critical
@pytest.mark.e2e
@pytest.mark.authenticated
class TestChatBusinessValueRestoration(SSotBaseTestCase):
    """
    Mission critical tests for chat business value restoration.
    
    These tests validate that the ToolRegistry fixes restore actual business value
    by enabling users to successfully chat with AI agents.
    
    CRITICAL: Tests are designed to FAIL if business value is broken.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up class-level fixtures."""
        # Initialize class attributes first
        cls.staging_config = StagingTestConfig()
        cls.ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Track test execution for business value analysis
        cls.test_executions: Dict[str, Dict[str, Any]] = {}
    
    def setup_method(self, method):
        """Set up method-level fixtures."""
        super().setup_method(method)
        self.test_start_time = time.time()
        self.event_capture = WebSocketEventCapture()
        
        logger.info(f"[U+1F680] Starting mission critical chat test: {method.__name__}")
    
    def teardown_method(self, method):
        """Analyze business value and cleanup."""
        super().teardown_method(method)
        
        # Calculate execution time
        execution_time = time.time() - self.test_start_time
        
        # CRITICAL: Validate test actually connected to real services
        if execution_time < 1.0:
            pytest.fail(f" ALERT:  CRITICAL: Mission critical test {method.__name__} executed in {execution_time:.3f}s. "
                      f"This indicates the test did not connect to real services or was mocked.")
        
        # Analyze business value
        analysis = self.event_capture.get_analysis_report()
        business_value_score = analysis['business_value_score']
        
        # Store execution data for reporting
        self.test_executions[method.__name__] = {
            'execution_time': execution_time,
            'business_value_score': business_value_score,
            'analysis': analysis
        }
        
        logger.info(f" CHART:  Mission critical test results for {method.__name__}:")
        logger.info(f"   [U+23F1][U+FE0F] Execution time: {execution_time:.3f}s")
        logger.info(f"   [U+1F4B0] Business value score: {business_value_score:.2f}/1.0")
        logger.info(f"   [U+1F4C8] Analysis: {analysis}")
    
    async def test_complete_chat_flow_after_toolregistry_fix(self):
        """
        FAILING TEST: End-to-end chat functionality validation.
        
        This is the ULTIMATE business value test.
        
        Current State (MUST FAIL):
        - Users cannot send messages to agents
        - WebSocket connections fail or timeout
        - No agent responses received
        - Business value = $0
        
        After Fix (MUST PASS):
        - Users can successfully chat with agents
        - All WebSocket events delivered
        - Agent responses contain valuable insights
        - Business value restored
        """
        logger.info(" TARGET:  ULTIMATE TEST: Complete chat flow business value validation")
        
        try:
            # Step 1: Authenticate with staging (real business user)
            logger.info("[U+1F510] Getting real user authentication...")
            token = await self.ws_auth_helper.get_staging_token_async()
            user_id = self._extract_user_id_from_token(token)
            
            # Step 2: Connect to chat system
            logger.info("[U+1F50C] Connecting to chat system...")
            websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
            logger.info(" PASS:  Chat connection established")
            
            # Step 3: Send meaningful business query
            business_query = {
                "type": "agent_request",
                "agent": "data_agent",
                "message": "Help me analyze my customer acquisition costs and suggest optimization strategies",
                "user_id": user_id,
                "session_id": f"chat_test_{int(time.time())}"
            }
            
            logger.info("[U+1F4AC] Sending business query to AI agent...")
            await websocket.send(json.dumps(business_query))
            
            # Step 4: Capture complete chat interaction
            chat_complete = False
            timeout_time = time.time() + 30.0  # 30 second timeout
            
            while time.time() < timeout_time and not chat_complete:
                try:
                    # Wait for WebSocket events
                    event_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event_data = json.loads(event_raw)
                    
                    # Capture event for business value analysis
                    self.event_capture.capture_event(event_data)
                    
                    event_type = event_data.get('type', 'unknown')
                    logger.info(f"[U+1F4E5] Received event: {event_type}")
                    
                    # Check for registry errors that break business value
                    if event_type == 'error':
                        error_msg = event_data.get('message', '')
                        if "modelmetaclass already registered" in error_msg:
                            pytest.fail(f"REPRODUCED STAGING BUG: Registry error breaks chat - {error_msg}")
                        elif "already registered" in error_msg:
                            pytest.fail(f"Registry duplicate error breaks chat functionality: {error_msg}")
                    
                    # Complete when agent finishes
                    if event_type == 'agent_completed':
                        chat_complete = True
                        logger.info(" PASS:  Agent completed response - chat interaction successful")
                        break
                        
                except asyncio.TimeoutError:
                    # Check if we have partial events (indicates progress)
                    if len(self.event_capture.events) > 0:
                        logger.info(f"[U+23F1][U+FE0F] Timeout waiting for more events (have {len(self.event_capture.events)} so far)")
                        continue
                    else:
                        logger.error("[U+23F0] No events received - chat system may be completely broken")
                        break
            
            await websocket.close()
            
            # Step 5: Analyze business value delivery
            analysis = self.event_capture.get_analysis_report()
            logger.info(f" CHART:  Chat business value analysis: {analysis}")
            
            # CRITICAL BUSINESS VALUE VALIDATIONS:
            
            # 1. Must have received events (basic connectivity)
            if analysis['total_events'] == 0:
                pytest.fail("BUSINESS VALUE BROKEN: No WebSocket events received - chat completely non-functional")
            
            # 2. Must have agent events (AI interaction working)
            if analysis['agent_events_count'] == 0:
                pytest.fail("BUSINESS VALUE BROKEN: No agent events - AI system not responding")
            
            # 3. Must have complete agent flow (full business interaction)
            if not analysis['complete_agent_flow']:
                missing_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'} - set(analysis['event_types'])
                pytest.fail(f"BUSINESS VALUE INCOMPLETE: Missing critical agent events: {missing_events}")
            
            # 4. Must not have registry errors (core issue resolved)
            if analysis['registry_errors']:
                pytest.fail(f"REPRODUCED: Registry errors break chat business value: {analysis['errors']}")
            
            # 5. Must achieve minimum business value score
            business_score = analysis['business_value_score']
            if business_score < 0.7:  # 70% threshold for business value
                pytest.fail(f"BUSINESS VALUE INSUFFICIENT: Score {business_score:.2f}/1.0 - chat not delivering value")
            
            # Step 6: Validate response quality
            final_events = [e for e in self.event_capture.events if e['type'] == 'agent_completed']
            if final_events:
                final_response = final_events[-1]['data'].get('result', '')
                if len(final_response.strip()) < 50:
                    pytest.fail(f"BUSINESS VALUE BROKEN: Agent response too short ({len(final_response)} chars) - not providing value")
                
                # Check for meaningful business content
                business_indicators = [
                    'cost', 'optimize', 'strategy', 'recommend', 'analysis', 
                    'improve', 'increase', 'reduce', 'data', 'customer'
                ]
                
                if not any(indicator in final_response.lower() for indicator in business_indicators):
                    logger.warning(" WARNING: [U+FE0F] Response may not contain substantial business value")
            
            logger.info(f" CELEBRATION:  BUSINESS VALUE RESTORED: Chat functionality working with score {business_score:.2f}/1.0")
            
        except ConnectionClosedError as e:
            logger.error(f" FAIL:  Chat connection failed: {e}")
            if hasattr(e, 'reason') and e.reason and "already registered" in str(e.reason):
                pytest.fail(f"REPRODUCED: Registry error caused connection failure - {e.reason}")
            pytest.fail(f"Chat connection broken - business value at risk: {e}")
            
        except Exception as e:
            logger.error(f" FAIL:  Chat system failure: {e}")
            if "modelmetaclass already registered" in str(e):
                pytest.fail(f"REPRODUCED STAGING BUG: {e}")
            raise
    
    async def test_websocket_agent_events_with_fixed_registry(self):
        """
        FAILING TEST: WebSocket agent events not delivered due to registry blocking.
        
        Validates delivery of all 5 mission-critical events for substantive chat value:
        1. agent_started - User sees agent began processing
        2. agent_thinking - Real-time reasoning visibility
        3. tool_executing - Tool usage transparency
        4. tool_completed - Tool results display
        5. agent_completed - Final response ready
        """
        logger.info(" TARGET:  Testing all 5 WebSocket agent events delivery")
        
        # Connect with authentication
        token = await self.ws_auth_helper.get_staging_token_async()
        websocket = await self.ws_auth_helper.connect_authenticated_websocket()
        
        # Send agent request that should trigger all events
        agent_request = {
            "type": "agent_request",
            "agent": "optimization_agent",
            "message": "Analyze performance metrics and provide recommendations",
            "user_id": self._extract_user_id_from_token(token),
            "request_events": True  # Explicitly request event delivery
        }
        
        await websocket.send(json.dumps(agent_request))
        
        # Capture events with timeout
        event_timeout = time.time() + 25.0
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        
        while time.time() < event_timeout and not self.event_capture.has_complete_agent_flow():
            try:
                event_raw = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                event_data = json.loads(event_raw)
                self.event_capture.capture_event(event_data)
                
                event_type = event_data.get('type')
                if event_type in required_events:
                    logger.info(f" PASS:  Received required event: {event_type}")
                
                # Stop early if we have all events
                if self.event_capture.has_complete_agent_flow():
                    break
                    
            except asyncio.TimeoutError:
                continue
        
        await websocket.close()
        
        # Analyze event delivery
        analysis = self.event_capture.get_analysis_report()
        received_events = set(analysis['event_types'])
        
        # CRITICAL VALIDATIONS:
        
        # 1. Check for registry errors blocking events
        if analysis['registry_errors']:
            pytest.fail(f"REPRODUCED: Registry errors block WebSocket events: {analysis['errors']}")
        
        # 2. Validate all 5 critical events received
        missing_events = required_events - received_events
        if missing_events:
            logger.error(f" FAIL:  BUSINESS VALUE BROKEN: Missing WebSocket events: {missing_events}")
            logger.error(f"   Received events: {list(received_events)}")
            pytest.fail(f"CRITICAL WebSocket events missing - chat experience broken: {missing_events}")
        
        # 3. Validate event sequence makes sense
        event_sequence = [e['type'] for e in self.event_capture.agent_events]
        if event_sequence[0] != 'agent_started':
            pytest.fail("Agent events out of sequence - should start with 'agent_started'")
        
        if 'agent_completed' not in event_sequence[-2:]:  # Should be last or second-to-last
            logger.warning(" WARNING: [U+FE0F] agent_completed not at end of sequence - may indicate issues")
        
        logger.info(f" PASS:  All 5 critical WebSocket events delivered successfully")
        logger.info(f"[U+1F4C8] Event sequence: {event_sequence}")
    
    async def test_concurrent_users_chat_without_registry_conflicts(self):
        """
        FAILING TEST: Multi-user business value validation.
        
        Current State: Multiple users connecting simultaneously cause registry conflicts
        After Fix: Each user gets isolated registry, no cross-user conflicts
        """
        logger.info(" TARGET:  Testing concurrent users chat without registry conflicts")
        
        # Create 3 concurrent chat sessions
        num_concurrent_users = 3
        chat_sessions = []
        
        async def concurrent_chat_session(user_index: int):
            """Execute a complete chat session for one user."""
            session_start = time.time()
            session_events = WebSocketEventCapture()
            
            try:
                # Get auth for this user
                user_email = f"concurrent_chat_user_{user_index}_{int(time.time())}@staging.test"
                auth_helper = E2EWebSocketAuthHelper(environment="staging")
                token = await auth_helper.get_staging_token_async(email=user_email)
                
                # Connect and chat
                websocket = await auth_helper.connect_authenticated_websocket()
                
                # Send business query
                chat_message = {
                    "type": "agent_request",
                    "agent": "analysis_agent",
                    "message": f"User {user_index}: Analyze market trends for tech startups",
                    "user_id": f"concurrent_user_{user_index}"
                }
                
                await websocket.send(json.dumps(chat_message))
                
                # Wait for response
                response_timeout = time.time() + 15.0
                while time.time() < response_timeout:
                    try:
                        event_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event_data = json.loads(event_raw)
                        session_events.capture_event(event_data)
                        
                        if event_data.get('type') == 'agent_completed':
                            break
                        
                    except asyncio.TimeoutError:
                        continue
                
                await websocket.close()
                
                # Analyze this session
                session_analysis = session_events.get_analysis_report()
                session_time = time.time() - session_start
                
                return {
                    'user_index': user_index,
                    'success': True,
                    'session_time': session_time,
                    'business_value_score': session_analysis['business_value_score'],
                    'registry_errors': session_analysis['registry_errors'],
                    'event_count': session_analysis['total_events'],
                    'complete_flow': session_analysis['complete_agent_flow'],
                    'errors': session_analysis['errors']
                }
                
            except Exception as e:
                return {
                    'user_index': user_index,
                    'success': False,
                    'error': str(e),
                    'session_time': time.time() - session_start,
                    'registry_conflict': "already registered" in str(e) or "modelmetaclass" in str(e)
                }
        
        # Execute concurrent chat sessions
        logger.info(f" LIGHTNING:  Starting {num_concurrent_users} concurrent chat sessions...")
        concurrent_start = time.time()
        
        tasks = [concurrent_chat_session(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        concurrent_time = time.time() - concurrent_start
        logger.info(f"[U+23F1][U+FE0F] Concurrent chat sessions completed in {concurrent_time:.3f}s")
        
        # Analyze concurrent results
        successful_sessions = 0
        registry_conflicts = 0
        total_business_value = 0.0
        all_errors = []
        
        for result in results:
            if isinstance(result, Exception):
                all_errors.append(f"Exception: {result}")
                if "already registered" in str(result) or "modelmetaclass" in str(result):
                    registry_conflicts += 1
            elif isinstance(result, dict):
                if result['success']:
                    successful_sessions += 1
                    total_business_value += result['business_value_score']
                    
                    # Check for registry errors in successful sessions
                    if result.get('registry_errors'):
                        all_errors.extend(result['errors'])
                        registry_conflicts += 1
                else:
                    all_errors.append(f"User {result['user_index']}: {result['error']}")
                    if result.get('registry_conflict'):
                        registry_conflicts += 1
        
        # Report results
        logger.info(f" CHART:  Concurrent chat analysis:")
        logger.info(f"    PASS:  Successful sessions: {successful_sessions}/{num_concurrent_users}")
        logger.info(f"    FAIL:  Registry conflicts: {registry_conflicts}")
        logger.info(f"   [U+1F4B0] Average business value: {total_business_value/max(1, successful_sessions):.2f}")
        logger.info(f"    ALERT:  Total errors: {len(all_errors)}")
        
        # CRITICAL BUSINESS VALUE VALIDATIONS:
        
        # 1. No registry conflicts should occur
        if registry_conflicts > 0:
            conflict_errors = [err for err in all_errors if "already registered" in err or "modelmetaclass" in err]
            pytest.fail(f"REPRODUCED: Registry conflicts break multi-user chat: {conflict_errors}")
        
        # 2. Most users should succeed (business availability)
        success_rate = successful_sessions / num_concurrent_users
        if success_rate < 0.8:  # 80% success rate minimum
            pytest.fail(f"BUSINESS VALUE BROKEN: Only {success_rate:.1%} of users could chat successfully")
        
        # 3. Average business value should be acceptable
        avg_business_value = total_business_value / max(1, successful_sessions)
        if successful_sessions > 0 and avg_business_value < 0.6:
            pytest.fail(f"MULTI-USER BUSINESS VALUE LOW: Average score {avg_business_value:.2f}/1.0")
        
        # 4. All errors should be analyzed
        if all_errors:
            logger.warning(f" WARNING: [U+FE0F] Concurrent session errors detected: {all_errors}")
            # Fail if errors indicate system problems
            system_errors = [err for err in all_errors if any(
                indicator in err.lower() for indicator in ['timeout', 'connection', 'server', 'registry']
            )]
            if len(system_errors) > num_concurrent_users * 0.3:  # More than 30% system errors
                pytest.fail(f"SYSTEM RELIABILITY ISSUES: {system_errors}")
        
        logger.info(f" CELEBRATION:  MULTI-USER BUSINESS VALUE CONFIRMED: {successful_sessions} users chatting successfully")
    
    async def test_no_performance_regression_after_registry_fixes(self):
        """
        Test that registry fixes don't introduce performance regressions.
        
        Business impact: Chat system should remain fast and responsive.
        """
        logger.info(" TARGET:  Testing no performance regression after registry fixes")
        
        performance_metrics = []
        
        # Run multiple chat sessions to measure performance
        for session in range(3):
            session_start = time.time()
            
            # Standard chat interaction
            token = await self.ws_auth_helper.get_staging_token_async()
            websocket = await self.ws_auth_helper.connect_authenticated_websocket()
            
            connect_time = time.time() - session_start
            
            # Send simple query
            query_start = time.time()
            await websocket.send(json.dumps({
                "type": "agent_request",
                "agent": "quick_agent", 
                "message": "Quick performance test",
                "user_id": self._extract_user_id_from_token(token)
            }))
            
            # Wait for first response
            try:
                await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_time = time.time() - query_start
            except asyncio.TimeoutError:
                response_time = 10.0  # Timeout
            
            await websocket.close()
            
            total_time = time.time() - session_start
            
            performance_metrics.append({
                'session': session,
                'connect_time': connect_time,
                'response_time': response_time, 
                'total_time': total_time
            })
        
        # Analyze performance
        avg_connect = sum(m['connect_time'] for m in performance_metrics) / len(performance_metrics)
        avg_response = sum(m['response_time'] for m in performance_metrics) / len(performance_metrics)
        avg_total = sum(m['total_time'] for m in performance_metrics) / len(performance_metrics)
        
        logger.info(f" CHART:  Performance metrics:")
        logger.info(f"    LIGHTNING:  Average connect time: {avg_connect:.3f}s")
        logger.info(f"   [U+1F4AC] Average response time: {avg_response:.3f}s")
        logger.info(f"   [U+23F1][U+FE0F] Average total time: {avg_total:.3f}s")
        
        # Performance thresholds
        if avg_connect > 5.0:
            pytest.fail(f"PERFORMANCE REGRESSION: Connection time too slow ({avg_connect:.3f}s)")
        
        if avg_response > 15.0:
            pytest.fail(f"PERFORMANCE REGRESSION: Response time too slow ({avg_response:.3f}s)")
        
        if any(m['response_time'] >= 10.0 for m in performance_metrics):
            timeout_count = sum(1 for m in performance_metrics if m['response_time'] >= 10.0)
            pytest.fail(f"PERFORMANCE ISSUES: {timeout_count} sessions timed out")
        
        logger.info(" PASS:  No performance regression - chat system remains responsive")
    
    def _extract_user_id_from_token(self, token: str) -> str:
        """Extract user ID from JWT token."""
        try:
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded.get("sub", "mission-critical-user")
        except Exception:
            return "mission-critical-user"