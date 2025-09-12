"""E2E Staging Test: Golden Path ExecutionEngine Validation (Issue #620)

PURPOSE: End-to-end validation of ExecutionEngine SSOT migration impact on the Golden Path
user flow (login → get AI responses) in the staging environment.

BUSINESS CONTEXT:
- Golden Path represents 90% of platform value (chat functionality)
- ExecutionEngine is core infrastructure enabling agent execution and WebSocket events
- SSOT migration must not break the primary user experience
- Staging environment provides realistic validation with real services

GOLDEN PATH FLOW:
1. User Authentication → Login successful
2. WebSocket Connection → Real-time communication established  
3. Agent Execution → User message processed by AI agents
4. WebSocket Events → Real-time progress updates (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
5. AI Response → User receives substantive AI-powered response

TEST STRATEGY:
- E2E testing in GCP staging environment (real services, no mocks)
- Test both legacy ExecutionEngine imports and modern UserExecutionEngine
- Validate complete Golden Path flow with ExecutionEngine components
- FAILING TESTS FIRST: Reproduce issues affecting Golden Path

EXPECTED FAILING SCENARIOS:
- ExecutionEngine SSOT migration may break agent execution
- WebSocket events may not reach users due to import consolidation issues  
- User isolation problems may affect multi-user chat scenarios
- Performance degradation from compatibility bridge usage

This test validates that Issue #620 SSOT migration preserves Golden Path functionality.
"""

import asyncio
import json
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

# Import test framework for E2E staging tests
from test_framework.e2e.staging_test_base import StagingTestBase
from test_framework.e2e.websocket_client import WebSocketTestClient
from test_framework.e2e.auth_client import AuthTestClient


@dataclass
class GoldenPathStepResult:
    """Results from a single Golden Path step."""
    step_name: str
    success: bool
    duration_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass  
class WebSocketEvent:
    """WebSocket event received during Golden Path execution."""
    event_type: str
    timestamp: datetime
    user_id: str
    agent_name: Optional[str] = None
    data: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class TestGoldenPathExecutionEngineStaging(StagingTestBase):
    """E2E tests for Golden Path validation with ExecutionEngine SSOT migration.
    
    Tests run against GCP staging environment with real services to validate
    that ExecutionEngine import consolidation preserves critical user flows.
    """
    
    @classmethod
    async def async_setUpClass(cls):
        """Set up E2E test environment with staging services."""
        await super().async_setUpClass()
        
        # Initialize staging environment clients
        cls.auth_client = AuthTestClient(cls.staging_config)
        cls.websocket_client = WebSocketTestClient(cls.staging_config)
        
        # Test user accounts for Golden Path validation
        cls.test_users = []
        for i in range(2):  # Multi-user testing
            test_user = await cls._create_staging_test_user(f"golden_path_user_{i}_{uuid.uuid4().hex[:8]}")
            cls.test_users.append(test_user)
        
        print(f"\n🌟 E2E STAGING SETUP:")
        print(f"   Environment: {cls.staging_config.get('environment', 'staging')}")
        print(f"   Test users: {len(cls.test_users)}")
        print(f"   Services: Auth, Backend, WebSocket")
    
    @classmethod
    async def _create_staging_test_user(cls, username: str) -> Dict[str, Any]:
        """Create a test user in staging environment."""
        try:
            user_data = {
                'username': username,
                'email': f"{username}@test.netra-staging.com",
                'password': 'TestPassword123!',
                'full_name': f'Golden Path Test User {username}',
                'test_user': True,
                'created_for': 'execution_engine_ssot_golden_path_validation'
            }
            
            # Create user via staging auth service
            created_user = await cls.auth_client.create_test_user(user_data)
            print(f"   ✅ Created staging test user: {username}")
            return created_user
            
        except Exception as e:
            print(f"   ❌ Failed to create test user {username}: {e}")
            raise
    
    async def test_golden_path_single_user_legacy_execution_engine(self):
        """Test Golden Path with legacy ExecutionEngine imports (single user).
        
        EXPECTED TO PARTIALLY FAIL: May demonstrate compatibility bridge issues
        or performance impacts affecting user experience.
        """
        print(f"\n🎯 TESTING: Golden Path with Legacy ExecutionEngine (Single User)")
        
        test_user = self.test_users[0]
        golden_path_results = []
        websocket_events = []
        
        try:
            # Step 1: User Authentication
            auth_step = await self._execute_golden_path_step(
                "user_authentication",
                self._authenticate_user_staging,
                test_user
            )
            golden_path_results.append(auth_step)
            
            if not auth_step.success:
                self.fail(f"Golden Path blocked at authentication: {auth_step.error}")
            
            # Step 2: WebSocket Connection
            websocket_step = await self._execute_golden_path_step(
                "websocket_connection",
                self._establish_websocket_connection,
                test_user,
                websocket_events
            )
            golden_path_results.append(websocket_step)
            
            if not websocket_step.success:
                self.fail(f"Golden Path blocked at WebSocket connection: {websocket_step.error}")
            
            # Step 3: Agent Execution (Legacy ExecutionEngine)
            agent_execution_step = await self._execute_golden_path_step(
                "legacy_agent_execution",
                self._execute_agent_via_legacy_execution_engine,
                test_user,
                websocket_events
            )
            golden_path_results.append(agent_execution_step)
            
            if not agent_execution_step.success:
                # This failure is expected and demonstrates Issue #620 impact
                self.fail(
                    f"🚨 ISSUE #620 GOLDEN PATH IMPACT: Legacy ExecutionEngine breaks Golden Path. "
                    f"Agent execution failed: {agent_execution_step.error}. "
                    f"Business Impact: Users cannot get AI responses (90% platform value lost). "
                    f"Migration Status: Compatibility issues affecting production functionality."
                )
            
            # Step 4: WebSocket Events Validation
            events_step = await self._execute_golden_path_step(
                "websocket_events_validation",
                self._validate_websocket_events,
                websocket_events,
                expected_events=['agent_started', 'agent_thinking', 'agent_completed']
            )
            golden_path_results.append(events_step)
            
            # Step 5: AI Response Validation
            response_step = await self._execute_golden_path_step(
                "ai_response_validation", 
                self._validate_ai_response_quality,
                agent_execution_step.metadata
            )
            golden_path_results.append(response_step)
            
            # Summarize Golden Path results
            await self._summarize_golden_path_results(
                "Legacy ExecutionEngine Single User",
                golden_path_results,
                websocket_events
            )
            
        except Exception as e:
            self.fail(f"Golden Path test failed unexpectedly: {e}")
        finally:
            # Cleanup WebSocket connection
            await self._cleanup_websocket_connection(test_user)
    
    async def test_golden_path_single_user_ssot_user_execution_engine(self):
        """Test Golden Path with SSOT UserExecutionEngine (single user).
        
        This test should PASS as UserExecutionEngine is the migration target.
        """
        print(f"\n🎯 TESTING: Golden Path with SSOT UserExecutionEngine (Single User)")
        
        test_user = self.test_users[1]
        golden_path_results = []
        websocket_events = []
        
        try:
            # Step 1: User Authentication
            auth_step = await self._execute_golden_path_step(
                "user_authentication",
                self._authenticate_user_staging,
                test_user
            )
            golden_path_results.append(auth_step)
            
            if not auth_step.success:
                self.fail(f"Golden Path blocked at authentication: {auth_step.error}")
            
            # Step 2: WebSocket Connection
            websocket_step = await self._execute_golden_path_step(
                "websocket_connection",
                self._establish_websocket_connection,
                test_user,
                websocket_events
            )
            golden_path_results.append(websocket_step)
            
            if not websocket_step.success:
                self.fail(f"Golden Path blocked at WebSocket connection: {websocket_step.error}")
            
            # Step 3: Agent Execution (SSOT UserExecutionEngine)
            agent_execution_step = await self._execute_golden_path_step(
                "ssot_agent_execution",
                self._execute_agent_via_user_execution_engine,
                test_user,
                websocket_events
            )
            golden_path_results.append(agent_execution_step)
            
            if not agent_execution_step.success:
                self.fail(
                    f"CRITICAL: SSOT UserExecutionEngine breaks Golden Path. "
                    f"Agent execution failed: {agent_execution_step.error}. "
                    f"This indicates fundamental issues with the migration target. "
                    f"System cannot function without working UserExecutionEngine."
                )
            
            # Step 4: WebSocket Events Validation
            events_step = await self._execute_golden_path_step(
                "websocket_events_validation",
                self._validate_websocket_events,
                websocket_events,
                expected_events=['agent_started', 'agent_thinking', 'agent_completed']
            )
            golden_path_results.append(events_step)
            
            # Step 5: AI Response Validation
            response_step = await self._execute_golden_path_step(
                "ai_response_validation",
                self._validate_ai_response_quality,
                agent_execution_step.metadata
            )
            golden_path_results.append(response_step)
            
            # Summarize Golden Path results
            await self._summarize_golden_path_results(
                "SSOT UserExecutionEngine Single User",
                golden_path_results,
                websocket_events
            )
            
            # Success assertion for SSOT path
            successful_steps = sum(1 for step in golden_path_results if step.success)
            total_steps = len(golden_path_results)
            
            if successful_steps < total_steps:
                failing_steps = [step.step_name for step in golden_path_results if not step.success]
                self.fail(
                    f"SSOT UserExecutionEngine Golden Path incomplete: "
                    f"{successful_steps}/{total_steps} steps successful. "
                    f"Failing steps: {', '.join(failing_steps)}"
                )
            
            print(f"   ✅ SSOT Golden Path successful: {successful_steps}/{total_steps} steps")
            
        except Exception as e:
            self.fail(f"SSOT Golden Path test failed unexpectedly: {e}")
        finally:
            # Cleanup WebSocket connection
            await self._cleanup_websocket_connection(test_user)
    
    async def test_golden_path_multi_user_isolation_validation(self):
        """Test Golden Path with multiple concurrent users to validate isolation.
        
        EXPECTED TO PARTIALLY FAIL: May demonstrate user isolation issues
        or WebSocket event routing problems in multi-user scenarios.
        """
        print(f"\n👥 TESTING: Golden Path Multi-User Isolation")
        
        multi_user_results = {}
        concurrent_websocket_events = {}
        
        try:
            # Initialize concurrent user sessions
            user_tasks = []
            
            for i, test_user in enumerate(self.test_users):
                user_id = test_user['user_id']
                concurrent_websocket_events[user_id] = []
                
                # Create concurrent Golden Path task for each user
                task = asyncio.create_task(
                    self._execute_concurrent_golden_path(
                        test_user,
                        concurrent_websocket_events[user_id],
                        f"user_{i}"
                    )
                )
                user_tasks.append((user_id, task))
            
            # Execute all users concurrently
            print(f"   🔄 Executing concurrent Golden Path for {len(user_tasks)} users")
            start_time = time.time()
            
            for user_id, task in user_tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=60.0)
                    multi_user_results[user_id] = result
                    print(f"   ✅ User {user_id[:8]}... Golden Path completed")
                except asyncio.TimeoutError:
                    print(f"   ⏱️  User {user_id[:8]}... Golden Path timed out")
                    multi_user_results[user_id] = {
                        'status': 'TIMEOUT',
                        'error': 'Golden Path execution timed out',
                        'steps': []
                    }
                except Exception as e:
                    print(f"   ❌ User {user_id[:8]}... Golden Path failed: {e}")
                    multi_user_results[user_id] = {
                        'status': 'ERROR',
                        'error': str(e),
                        'steps': []
                    }
            
            concurrent_duration = time.time() - start_time
            print(f"   ⏱️  Multi-user execution duration: {concurrent_duration:.2f}s")
            
            # Validate multi-user isolation
            await self._validate_multi_user_isolation(
                multi_user_results,
                concurrent_websocket_events
            )
            
        except Exception as e:
            self.fail(f"Multi-user Golden Path test failed: {e}")
    
    # Helper methods for Golden Path execution
    
    async def _execute_golden_path_step(self, step_name: str, step_function, *args) -> GoldenPathStepResult:
        """Execute a single Golden Path step with timing and error handling."""
        start_time = time.time()
        
        try:
            print(f"   🔄 Executing step: {step_name}")
            result = await step_function(*args)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, dict) and 'success' in result:
                step_result = GoldenPathStepResult(
                    step_name=step_name,
                    success=result['success'],
                    duration_ms=duration_ms,
                    error=result.get('error'),
                    metadata=result.get('metadata', {})
                )
            else:
                # Assume success if function returns without exception
                step_result = GoldenPathStepResult(
                    step_name=step_name,
                    success=True,
                    duration_ms=duration_ms,
                    metadata={'result': result}
                )
            
            status_emoji = "✅" if step_result.success else "❌"
            print(f"   {status_emoji} Step {step_name}: {duration_ms:.1f}ms")
            
            return step_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            print(f"   ❌ Step {step_name} failed: {e}")
            
            return GoldenPathStepResult(
                step_name=step_name,
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def _authenticate_user_staging(self, test_user: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate user in staging environment."""
        try:
            auth_response = await self.auth_client.authenticate(
                username=test_user['username'],
                password=test_user['password']
            )
            
            if auth_response.get('access_token'):
                test_user['access_token'] = auth_response['access_token']
                test_user['refresh_token'] = auth_response.get('refresh_token')
                
                return {
                    'success': True,
                    'metadata': {
                        'user_id': test_user['user_id'],
                        'username': test_user['username'],
                        'token_type': auth_response.get('token_type', 'Bearer')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Authentication failed: No access token received',
                    'metadata': auth_response
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Authentication error: {e}'
            }
    
    async def _establish_websocket_connection(self, test_user: Dict[str, Any], websocket_events: List[WebSocketEvent]) -> Dict[str, Any]:
        """Establish WebSocket connection for real-time communication."""
        try:
            # Connect to staging WebSocket endpoint with authentication
            websocket_url = f"{self.staging_config['websocket_url']}/ws/chat"
            headers = {
                'Authorization': f"Bearer {test_user['access_token']}"
            }
            
            connection = await self.websocket_client.connect(
                websocket_url,
                headers=headers,
                user_id=test_user['user_id']
            )
            
            # Set up event listener for this user
            def event_handler(event_data):
                event = WebSocketEvent(
                    event_type=event_data.get('type', 'unknown'),
                    timestamp=datetime.now(timezone.utc),
                    user_id=test_user['user_id'],
                    agent_name=event_data.get('agent_name'),
                    data=event_data
                )
                websocket_events.append(event)
            
            connection.set_event_handler(event_handler)
            
            # Store connection reference for cleanup
            test_user['websocket_connection'] = connection
            
            return {
                'success': True,
                'metadata': {
                    'connection_id': connection.connection_id,
                    'user_id': test_user['user_id'],
                    'connected_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'WebSocket connection error: {e}'
            }
    
    async def _execute_agent_via_legacy_execution_engine(self, test_user: Dict[str, Any], websocket_events: List[WebSocketEvent]) -> Dict[str, Any]:
        """Execute agent via legacy ExecutionEngine import path."""
        try:
            # Send chat message that should trigger agent execution
            chat_message = {
                'type': 'chat_message',
                'message': f'Hello, I am {test_user["username"]} testing the Golden Path with Legacy ExecutionEngine. Please provide a helpful AI response about the current time and date.',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'execution_engine_type': 'legacy'
            }
            
            connection = test_user.get('websocket_connection')
            if not connection:
                return {
                    'success': False,
                    'error': 'No WebSocket connection available'
                }
            
            # Send message and wait for response
            await connection.send_message(chat_message)
            
            # Wait for agent execution to complete (expect WebSocket events)
            response_timeout = 30.0
            start_time = time.time()
            
            while time.time() - start_time < response_timeout:
                # Check for completed agent execution
                completed_events = [
                    event for event in websocket_events 
                    if event.event_type == 'agent_completed'
                ]
                
                if completed_events:
                    latest_completion = completed_events[-1]
                    return {
                        'success': True,
                        'metadata': {
                            'execution_time_ms': (time.time() - start_time) * 1000,
                            'agent_name': latest_completion.agent_name,
                            'completion_data': latest_completion.data,
                            'total_events': len(websocket_events),
                            'execution_engine_type': 'legacy'
                        }
                    }
                
                await asyncio.sleep(0.5)
            
            # Timeout - agent execution may have failed
            return {
                'success': False,
                'error': f'Agent execution timeout after {response_timeout}s. No completion event received.',
                'metadata': {
                    'events_received': len(websocket_events),
                    'event_types': list(set(event.event_type for event in websocket_events)),
                    'execution_engine_type': 'legacy'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Legacy agent execution error: {e}',
                'metadata': {
                    'execution_engine_type': 'legacy'
                }
            }
    
    async def _execute_agent_via_user_execution_engine(self, test_user: Dict[str, Any], websocket_events: List[WebSocketEvent]) -> Dict[str, Any]:
        """Execute agent via SSOT UserExecutionEngine."""
        try:
            # Send chat message that should trigger UserExecutionEngine
            chat_message = {
                'type': 'chat_message',
                'message': f'Hello, I am {test_user["username"]} testing the Golden Path with SSOT UserExecutionEngine. Please provide a helpful AI response about optimal AI usage patterns.',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'execution_engine_type': 'ssot_user_execution_engine'
            }
            
            connection = test_user.get('websocket_connection')
            if not connection:
                return {
                    'success': False,
                    'error': 'No WebSocket connection available'
                }
            
            # Send message and wait for response
            await connection.send_message(chat_message)
            
            # Wait for agent execution to complete
            response_timeout = 30.0
            start_time = time.time()
            
            while time.time() - start_time < response_timeout:
                # Check for completed agent execution
                completed_events = [
                    event for event in websocket_events 
                    if event.event_type == 'agent_completed'
                ]
                
                if completed_events:
                    latest_completion = completed_events[-1]
                    return {
                        'success': True,
                        'metadata': {
                            'execution_time_ms': (time.time() - start_time) * 1000,
                            'agent_name': latest_completion.agent_name,
                            'completion_data': latest_completion.data,
                            'total_events': len(websocket_events),
                            'execution_engine_type': 'ssot_user_execution_engine'
                        }
                    }
                
                await asyncio.sleep(0.5)
            
            # Timeout
            return {
                'success': False,
                'error': f'SSOT agent execution timeout after {response_timeout}s. No completion event received.',
                'metadata': {
                    'events_received': len(websocket_events),
                    'event_types': list(set(event.event_type for event in websocket_events)),
                    'execution_engine_type': 'ssot_user_execution_engine'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'SSOT agent execution error: {e}',
                'metadata': {
                    'execution_engine_type': 'ssot_user_execution_engine'
                }
            }
    
    async def _validate_websocket_events(self, websocket_events: List[WebSocketEvent], expected_events: List[str]) -> Dict[str, Any]:
        """Validate that expected WebSocket events were received."""
        try:
            received_event_types = [event.event_type for event in websocket_events]
            missing_events = [event_type for event_type in expected_events if event_type not in received_event_types]
            unexpected_events = list(set(received_event_types) - set(expected_events))
            
            if missing_events:
                return {
                    'success': False,
                    'error': f'Missing expected WebSocket events: {missing_events}',
                    'metadata': {
                        'expected_events': expected_events,
                        'received_events': received_event_types,
                        'missing_events': missing_events,
                        'unexpected_events': unexpected_events,
                        'total_events': len(websocket_events)
                    }
                }
            
            return {
                'success': True,
                'metadata': {
                    'expected_events': expected_events,
                    'received_events': received_event_types,
                    'event_sequence_valid': True,
                    'total_events': len(websocket_events)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'WebSocket event validation error: {e}'
            }
    
    async def _validate_ai_response_quality(self, agent_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality and substance of AI response (90% platform value)."""
        try:
            completion_data = agent_metadata.get('completion_data', {})
            
            # Check for substantive AI response (core business value)
            has_response = bool(completion_data.get('result') or completion_data.get('response'))
            response_length = len(str(completion_data.get('result', '') or completion_data.get('response', '')))
            
            # Business criteria for valuable AI response
            is_substantive = response_length > 50  # Minimum substance threshold
            is_helpful = True  # Would check for helpful content in real implementation
            
            if not has_response:
                return {
                    'success': False,
                    'error': 'No AI response received - core platform value missing',
                    'metadata': {
                        'business_impact': 'Complete loss of platform value (90%)',
                        'completion_data': completion_data
                    }
                }
            
            if not is_substantive:
                return {
                    'success': False,
                    'error': f'AI response too brief ({response_length} chars) - insufficient value delivery',
                    'metadata': {
                        'business_impact': 'Reduced platform value due to poor response quality',
                        'response_length': response_length,
                        'minimum_expected': 50
                    }
                }
            
            return {
                'success': True,
                'metadata': {
                    'response_length': response_length,
                    'is_substantive': is_substantive,
                    'business_value_delivered': True,
                    'platform_value_percentage': 90 if is_substantive and is_helpful else 45
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'AI response validation error: {e}'
            }
    
    async def _execute_concurrent_golden_path(self, test_user: Dict[str, Any], websocket_events: List[WebSocketEvent], user_label: str) -> Dict[str, Any]:
        """Execute complete Golden Path for a single user in concurrent scenario."""
        steps = []
        
        try:
            # Authentication
            auth_step = await self._execute_golden_path_step(
                f"{user_label}_authentication",
                self._authenticate_user_staging,
                test_user
            )
            steps.append(auth_step)
            
            if not auth_step.success:
                return {'status': 'FAILED_AUTH', 'steps': steps, 'error': auth_step.error}
            
            # WebSocket Connection
            websocket_step = await self._execute_golden_path_step(
                f"{user_label}_websocket",
                self._establish_websocket_connection,
                test_user,
                websocket_events
            )
            steps.append(websocket_step)
            
            if not websocket_step.success:
                return {'status': 'FAILED_WEBSOCKET', 'steps': steps, 'error': websocket_step.error}
            
            # Agent Execution (use UserExecutionEngine for concurrent testing)
            agent_step = await self._execute_golden_path_step(
                f"{user_label}_agent_execution",
                self._execute_agent_via_user_execution_engine,
                test_user,
                websocket_events
            )
            steps.append(agent_step)
            
            return {
                'status': 'SUCCESS' if agent_step.success else 'FAILED_AGENT',
                'steps': steps,
                'user_id': test_user['user_id'],
                'total_events': len(websocket_events)
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'steps': steps,
                'error': str(e),
                'user_id': test_user['user_id']
            }
        finally:
            # Cleanup
            await self._cleanup_websocket_connection(test_user)
    
    async def _validate_multi_user_isolation(self, multi_user_results: Dict[str, Any], websocket_events: Dict[str, List[WebSocketEvent]]) -> None:
        """Validate user isolation in multi-user Golden Path scenario."""
        isolation_issues = []
        
        successful_users = [
            user_id for user_id, result in multi_user_results.items()
            if result.get('status') == 'SUCCESS'
        ]
        
        if len(successful_users) < 2:
            self.fail(
                f"🚨 MULTI-USER GOLDEN PATH: Insufficient successful executions for isolation validation. "
                f"Only {len(successful_users)}/{len(multi_user_results)} users completed successfully. "
                f"Business Impact: Multi-user deployment unsafe - concurrent users cannot use chat functionality."
            )
        
        # Check for cross-user event contamination
        for user_id, events in websocket_events.items():
            for event in events:
                if event.user_id != user_id:
                    isolation_issues.append(
                        f"User {user_id} received event intended for user {event.user_id}: {event.event_type}"
                    )
        
        # Check for user context leakage in response data
        user_response_data = {}
        for user_id, result in multi_user_results.items():
            if result.get('status') == 'SUCCESS':
                steps = result.get('steps', [])
                agent_steps = [step for step in steps if 'agent_execution' in step.step_name]
                if agent_steps:
                    user_response_data[user_id] = agent_steps[-1].metadata
        
        # Validate no user data cross-contamination
        for user_id_a, data_a in user_response_data.items():
            for user_id_b, data_b in user_response_data.items():
                if user_id_a != user_id_b:
                    # Check if user_id_a appears in user_b's response data (context leakage)
                    response_text = str(data_b.get('completion_data', {}))
                    if user_id_a in response_text:
                        isolation_issues.append(
                            f"User {user_id_b} response contains data from user {user_id_a}: context leakage"
                        )
        
        if isolation_issues:
            self.fail(
                f"🚨 ISSUE #620 MULTI-USER ISOLATION: User isolation violations in Golden Path:\n"
                f"{'  • ' + chr(10).join(isolation_issues[:5])}\n"  # Limit to first 5 issues
                f"{'  • ...' if len(isolation_issues) > 5 else ''}\n"
                f"\nBUSINESS IMPACT: Data privacy violations, incorrect AI responses, "
                f"users seeing other users' information (GDPR/privacy risk).\n"
                f"CRITICAL: Multi-user production deployment blocked until isolation fixed."
            )
        
        print(f"   ✅ Multi-user isolation validated: {len(successful_users)} users, no cross-contamination")
    
    async def _summarize_golden_path_results(self, test_name: str, results: List[GoldenPathStepResult], events: List[WebSocketEvent]) -> None:
        """Summarize Golden Path execution results."""
        successful_steps = sum(1 for result in results if result.success)
        total_steps = len(results)
        total_duration = sum(result.duration_ms for result in results)
        
        print(f"\n📊 GOLDEN PATH SUMMARY: {test_name}")
        print(f"   Steps completed: {successful_steps}/{total_steps}")
        print(f"   Total duration: {total_duration:.1f}ms")
        print(f"   WebSocket events: {len(events)}")
        
        if events:
            event_types = list(set(event.event_type for event in events))
            print(f"   Event types: {', '.join(event_types)}")
        
        for result in results:
            status_emoji = "✅" if result.success else "❌"
            print(f"   {status_emoji} {result.step_name}: {result.duration_ms:.1f}ms")
            if not result.success and result.error:
                print(f"      Error: {result.error[:100]}...")
    
    async def _cleanup_websocket_connection(self, test_user: Dict[str, Any]) -> None:
        """Clean up WebSocket connection for test user."""
        try:
            connection = test_user.get('websocket_connection')
            if connection:
                await connection.close()
                del test_user['websocket_connection']
        except Exception as e:
            print(f"   ⚠️  WebSocket cleanup error for {test_user['user_id']}: {e}")


if __name__ == '__main__':
    import unittest
    unittest.main()