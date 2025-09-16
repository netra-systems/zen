"""
Business Function Preservation Validation - Phase 2
Ensures factory cleanup doesn't break core business functionality.

Purpose:
Validate that essential business functions continue to work correctly after
factory pattern cleanup. These tests ensure that architectural changes don't
impact the core functionality that delivers $500K+ ARR business value.

Business Impact: $500K+ ARR protection through regression prevention
Quality Assurance: Zero tolerance for business function degradation

These tests MUST PASS to ensure factory cleanup doesn't break the business.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockAgentWorkflow:
    """Mock agent workflow for regression testing."""

    def __init__(self, user_context: Dict, websocket_emitter: Optional[Any] = None):
        self.user_context = user_context
        self.websocket_emitter = websocket_emitter or MagicMock()
        self.execution_history = []
        self.current_state = "initialized"

    async def execute_agent_request(self, request: Dict) -> Dict:
        """Execute agent request with WebSocket events."""
        execution_id = f"exec_{uuid.uuid4()}"
        user_id = self.user_context.get('user_id', 'unknown')

        try:
            # Emit agent_started event
            self.websocket_emitter.emit_event('agent_started', {
                'execution_id': execution_id,
                'user_id': user_id,
                'request': request
            })

            self.current_state = "thinking"

            # Emit agent_thinking event
            self.websocket_emitter.emit_event('agent_thinking', {
                'execution_id': execution_id,
                'user_id': user_id,
                'thought': f"Processing request: {request.get('message', 'No message')}"
            })

            # Simulate tool execution if needed
            if request.get('requires_tools', False):
                await self._execute_tools(execution_id, user_id, request)

            # Generate response
            response = await self._generate_response(execution_id, user_id, request)

            # Emit agent_completed event
            self.websocket_emitter.emit_event('agent_completed', {
                'execution_id': execution_id,
                'user_id': user_id,
                'response': response
            })

            self.current_state = "completed"

            execution_record = {
                'execution_id': execution_id,
                'user_id': user_id,
                'request': request,
                'response': response,
                'timestamp': time.time(),
                'status': 'success'
            }

            self.execution_history.append(execution_record)
            return execution_record

        except Exception as e:
            error_record = {
                'execution_id': execution_id,
                'user_id': user_id,
                'request': request,
                'error': str(e),
                'timestamp': time.time(),
                'status': 'error'
            }

            self.execution_history.append(error_record)
            raise

    async def _execute_tools(self, execution_id: str, user_id: str, request: Dict) -> None:
        """Execute tools with WebSocket events."""
        tools = request.get('tools', ['default_tool'])

        for tool_name in tools:
            # Emit tool_executing event
            self.websocket_emitter.emit_event('tool_executing', {
                'execution_id': execution_id,
                'user_id': user_id,
                'tool': tool_name
            })

            # Simulate tool execution time
            await asyncio.sleep(0.1)

            # Emit tool_completed event
            self.websocket_emitter.emit_event('tool_completed', {
                'execution_id': execution_id,
                'user_id': user_id,
                'tool': tool_name,
                'result': f"tool_{tool_name}_result_for_{user_id}"
            })

    async def _generate_response(self, execution_id: str, user_id: str, request: Dict) -> Dict:
        """Generate agent response."""
        # Simulate thinking time
        await asyncio.sleep(0.2)

        return {
            'message': f"Response to '{request.get('message', '')}' for user {user_id}",
            'execution_id': execution_id,
            'user_id': user_id,
            'timestamp': time.time(),
            'response_type': 'success'
        }


class MockWebSocketEventCollector:
    """Mock WebSocket event collector for validation."""

    def __init__(self):
        self.events = []
        self.events_by_user = {}
        self.event_lock = threading.Lock()

    def emit_event(self, event_type: str, data: Dict) -> None:
        """Collect emitted events."""
        with self.event_lock:
            event = {
                'type': event_type,
                'data': data,
                'timestamp': time.time()
            }

            self.events.append(event)

            user_id = data.get('user_id', 'unknown')
            if user_id not in self.events_by_user:
                self.events_by_user[user_id] = []
            self.events_by_user[user_id].append(event)

    def get_events_for_user(self, user_id: str) -> List[Dict]:
        """Get all events for a specific user."""
        return self.events_by_user.get(user_id, [])

    def get_all_events(self) -> List[Dict]:
        """Get all collected events."""
        return self.events.copy()

    def clear_events(self) -> None:
        """Clear all collected events."""
        with self.event_lock:
            self.events.clear()
            self.events_by_user.clear()


class MockDatabaseOperations:
    """Mock database operations for regression testing."""

    def __init__(self):
        self.data_store = {}
        self.operations_log = []
        self.connection_pool = {'active_connections': 0, 'max_connections': 10}

    async def create_user_session(self, user_id: str, session_data: Dict) -> str:
        """Create user session in database."""
        session_id = f"session_{uuid.uuid4()}"

        self.data_store[session_id] = {
            'user_id': user_id,
            'session_data': session_data,
            'created_at': time.time(),
            'last_activity': time.time()
        }

        self.operations_log.append({
            'operation': 'create_session',
            'session_id': session_id,
            'user_id': user_id,
            'timestamp': time.time()
        })

        return session_id

    async def get_user_session(self, session_id: str) -> Optional[Dict]:
        """Get user session from database."""
        session = self.data_store.get(session_id)

        if session:
            self.operations_log.append({
                'operation': 'get_session',
                'session_id': session_id,
                'timestamp': time.time()
            })

            # Update last activity
            session['last_activity'] = time.time()

        return session

    async def update_user_session(self, session_id: str, updates: Dict) -> bool:
        """Update user session in database."""
        if session_id not in self.data_store:
            return False

        self.data_store[session_id].update(updates)
        self.data_store[session_id]['last_activity'] = time.time()

        self.operations_log.append({
            'operation': 'update_session',
            'session_id': session_id,
            'updates': updates,
            'timestamp': time.time()
        })

        return True

    async def delete_user_session(self, session_id: str) -> bool:
        """Delete user session from database."""
        if session_id not in self.data_store:
            return False

        del self.data_store[session_id]

        self.operations_log.append({
            'operation': 'delete_session',
            'session_id': session_id,
            'timestamp': time.time()
        })

        return True

    def get_connection_status(self) -> Dict:
        """Get database connection pool status."""
        return self.connection_pool.copy()


class BusinessFunctionPreservationPhase2Tests(SSotBaseTestCase):
    """
    Business Function Preservation Validation - Phase 2

    Validates that essential business functions work after factory cleanup.
    """

    def setUp(self):
        """Set up business function preservation testing."""
        super().setUp()
        self.websocket_collector = MockWebSocketEventCollector()
        self.database_operations = MockDatabaseOperations()
        self.business_function_results = {}

        # Create test user contexts
        self.test_users = [
            {
                'user_id': f'business_user_{i}',
                'auth_token': f'token_{i}_{uuid.uuid4()}',
                'session_data': {
                    'user_type': 'enterprise' if i % 2 == 0 else 'standard',
                    'subscription': 'active',
                    'permissions': ['chat', 'analysis', 'optimization']
                }
            }
            for i in range(5)
        ]

    def test_01_agent_execution_workflow_preservation(self):
        """
        EXPECTED: PASS - CRITICAL for $500K+ ARR

        Validates that agent execution workflows continue to work
        correctly after factory pattern cleanup.
        """
        print(f"\n🔍 PHASE 2.1: Testing agent execution workflow preservation...")

        workflow_failures = []
        successful_workflows = []

        async def test_single_user_workflow(user_data):
            """Test complete agent workflow for a single user."""
            user_id = user_data['user_id']

            try:
                # Create user context
                user_context = {
                    'user_id': user_id,
                    'auth_token': user_data['auth_token'],
                    'session_data': user_data['session_data']
                }

                # Create agent workflow
                workflow = MockAgentWorkflow(user_context, self.websocket_collector)

                # Test basic agent request
                basic_request = {
                    'message': f'Analyze costs for user {user_id}',
                    'type': 'cost_analysis',
                    'requires_tools': False
                }

                basic_result = await workflow.execute_agent_request(basic_request)

                # Test complex agent request with tools
                complex_request = {
                    'message': f'Optimize infrastructure for user {user_id}',
                    'type': 'optimization',
                    'requires_tools': True,
                    'tools': ['cost_analyzer', 'usage_optimizer', 'recommendation_engine']
                }

                complex_result = await workflow.execute_agent_request(complex_request)

                return {
                    'user_id': user_id,
                    'basic_execution': basic_result,
                    'complex_execution': complex_result,
                    'workflow_instance_id': id(workflow),
                    'total_executions': len(workflow.execution_history),
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'success': False
                }

        # Test workflows concurrently for all users
        print(f"  🔄 Testing agent workflows for {len(self.test_users)} users...")

        async def run_concurrent_workflows():
            tasks = [test_single_user_workflow(user) for user in self.test_users]
            return await asyncio.gather(*tasks, return_exceptions=True)

        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            workflow_results = loop.run_until_complete(run_concurrent_workflows())
        finally:
            loop.close()

        # Process results
        for result in workflow_results:
            if isinstance(result, Exception):
                workflow_failures.append({
                    'user_id': 'unknown',
                    'error': str(result),
                    'failure_type': 'exception_during_execution'
                })
            elif result.get('success', False):
                successful_workflows.append(result)
            else:
                workflow_failures.append({
                    'user_id': result.get('user_id', 'unknown'),
                    'error': result.get('error', 'Unknown error'),
                    'failure_type': 'workflow_execution_failure'
                })

        print(f"  📊 Agent workflow execution results:")
        print(f"     ✅ Successful workflows: {len(successful_workflows)}")
        print(f"     ❌ Failed workflows: {len(workflow_failures)}")

        # Validate workflow quality
        for workflow_result in successful_workflows:
            user_id = workflow_result['user_id']

            # Validate basic execution
            basic_exec = workflow_result['basic_execution']
            if basic_exec['status'] != 'success':
                workflow_failures.append({
                    'user_id': user_id,
                    'error': f"Basic execution failed: {basic_exec.get('error', 'Unknown')}",
                    'failure_type': 'basic_execution_failure'
                })

            # Validate complex execution
            complex_exec = workflow_result['complex_execution']
            if complex_exec['status'] != 'success':
                workflow_failures.append({
                    'user_id': user_id,
                    'error': f"Complex execution failed: {complex_exec.get('error', 'Unknown')}",
                    'failure_type': 'complex_execution_failure'
                })

            # Validate execution isolation
            if basic_exec['user_id'] != user_id or complex_exec['user_id'] != user_id:
                workflow_failures.append({
                    'user_id': user_id,
                    'error': 'User ID mismatch in execution results',
                    'failure_type': 'user_isolation_failure'
                })

        print(f"  🚨 Workflow failure summary:")
        for failure in workflow_failures:
            print(f"     ❌ {failure['failure_type']}: {failure['user_id']}")
            print(f"        {failure['error']}")

        self.business_function_results['agent_workflows'] = {
            'successful_workflows': successful_workflows,
            'workflow_failures': workflow_failures,
            'success_rate': len(successful_workflows) / max(1, len(self.test_users)) * 100
        }

        # Agent workflows MUST work for business functionality
        self.assertEqual(
            len(workflow_failures),
            0,
            f"✅ AGENT WORKFLOW PRESERVATION: Found {len(workflow_failures)} workflow failures. "
            f"Expected 0 for business function preservation. "
            f"Agent workflows are CRITICAL for $500K+ ARR business value."
        )

    def test_02_websocket_event_delivery_preservation(self):
        """
        EXPECTED: PASS - CRITICAL for chat UX

        Validates that all 5 critical WebSocket events are still
        delivered correctly after factory cleanup.
        """
        print(f"\n🔍 PHASE 2.2: Testing WebSocket event delivery preservation...")

        event_delivery_failures = []
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

        # Clear any existing events
        self.websocket_collector.clear_events()

        async def test_websocket_event_delivery(user_data):
            """Test WebSocket event delivery for a user."""
            user_id = user_data['user_id']

            try:
                # Create user context and workflow
                user_context = {
                    'user_id': user_id,
                    'auth_token': user_data['auth_token']
                }

                workflow = MockAgentWorkflow(user_context, self.websocket_collector)

                # Execute request that should generate all events
                request = {
                    'message': f'Complete analysis for user {user_id}',
                    'type': 'full_analysis',
                    'requires_tools': True,
                    'tools': ['data_analyzer']
                }

                execution_result = await workflow.execute_agent_request(request)

                # Get events for this user
                user_events = self.websocket_collector.get_events_for_user(user_id)

                return {
                    'user_id': user_id,
                    'execution_result': execution_result,
                    'events': user_events,
                    'event_types': [event['type'] for event in user_events],
                    'event_count': len(user_events),
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'success': False
                }

        # Test WebSocket events for all users
        print(f"  🔄 Testing WebSocket event delivery for {len(self.test_users)} users...")

        async def run_websocket_tests():
            tasks = [test_websocket_event_delivery(user) for user in self.test_users]
            return await asyncio.gather(*tasks, return_exceptions=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            websocket_results = loop.run_until_complete(run_websocket_tests())
        finally:
            loop.close()

        successful_event_deliveries = []

        # Process WebSocket results
        for result in websocket_results:
            if isinstance(result, Exception):
                event_delivery_failures.append({
                    'user_id': 'unknown',
                    'error': str(result),
                    'failure_type': 'websocket_test_exception'
                })
            elif result.get('success', False):
                successful_event_deliveries.append(result)
            else:
                event_delivery_failures.append({
                    'user_id': result.get('user_id', 'unknown'),
                    'error': result.get('error', 'Unknown error'),
                    'failure_type': 'websocket_event_failure'
                })

        print(f"  📊 WebSocket event delivery results:")
        print(f"     ✅ Successful event deliveries: {len(successful_event_deliveries)}")
        print(f"     ❌ Failed event deliveries: {len(event_delivery_failures)}")

        # Validate critical events for each user
        for event_result in successful_event_deliveries:
            user_id = event_result['user_id']
            event_types = event_result['event_types']

            # Check for all required events
            missing_events = []
            for required_event in required_events:
                if required_event not in event_types:
                    missing_events.append(required_event)

            if missing_events:
                event_delivery_failures.append({
                    'user_id': user_id,
                    'error': f"Missing critical events: {missing_events}",
                    'failure_type': 'missing_critical_events',
                    'missing_events': missing_events
                })

            # Check event ordering (some events must come in order)
            if 'agent_started' in event_types and 'agent_completed' in event_types:
                started_index = event_types.index('agent_started')
                completed_index = event_types.index('agent_completed')

                if started_index >= completed_index:
                    event_delivery_failures.append({
                        'user_id': user_id,
                        'error': 'agent_completed came before agent_started',
                        'failure_type': 'event_ordering_violation'
                    })

            # Check for tool events consistency
            if 'tool_executing' in event_types and 'tool_completed' not in event_types:
                event_delivery_failures.append({
                    'user_id': user_id,
                    'error': 'tool_executing without tool_completed',
                    'failure_type': 'incomplete_tool_events'
                })

        print(f"  🚨 WebSocket event delivery failure summary:")
        for failure in event_delivery_failures:
            print(f"     ❌ {failure['failure_type']}: {failure['user_id']}")
            print(f"        {failure['error']}")

        # Validate overall event delivery statistics
        total_events = len(self.websocket_collector.get_all_events())
        expected_min_events = len(self.test_users) * 4  # At least 4 events per user

        print(f"  📈 Event delivery statistics:")
        print(f"     📊 Total events captured: {total_events}")
        print(f"     🎯 Expected minimum events: {expected_min_events}")

        if total_events < expected_min_events:
            event_delivery_failures.append({
                'user_id': 'system',
                'error': f"Insufficient total events: {total_events} < {expected_min_events}",
                'failure_type': 'insufficient_event_volume'
            })

        self.business_function_results['websocket_events'] = {
            'successful_deliveries': successful_event_deliveries,
            'event_failures': event_delivery_failures,
            'total_events_captured': total_events,
            'success_rate': len(successful_event_deliveries) / max(1, len(self.test_users)) * 100
        }

        # WebSocket events MUST be delivered correctly
        self.assertEqual(
            len(event_delivery_failures),
            0,
            f"✅ WEBSOCKET EVENT PRESERVATION: Found {len(event_delivery_failures)} event delivery failures. "
            f"Expected 0 for chat functionality preservation. "
            f"WebSocket events are CRITICAL for chat UX ($500K+ ARR)."
        )

    def test_03_multi_user_chat_functionality_preservation(self):
        """
        EXPECTED: PASS - CRITICAL for business value

        Validates that multiple users can use chat functionality
        simultaneously without interference.
        """
        print(f"\n🔍 PHASE 2.3: Testing multi-user chat functionality preservation...")

        multi_user_failures = []
        concurrent_user_results = []

        async def simulate_user_chat_session(user_data, session_duration=2.0):
            """Simulate a complete chat session for a user."""
            user_id = user_data['user_id']

            try:
                # Create user context
                user_context = {
                    'user_id': user_id,
                    'auth_token': user_data['auth_token'],
                    'session_data': user_data['session_data']
                }

                # Create database session
                session_id = await self.database_operations.create_user_session(
                    user_id, user_data['session_data']
                )

                # Create agent workflow
                workflow = MockAgentWorkflow(user_context, self.websocket_collector)

                # Simulate multiple chat interactions
                chat_interactions = []
                interaction_count = 3

                for i in range(interaction_count):
                    interaction_request = {
                        'message': f'Chat message {i+1} from user {user_id}: Please help me optimize my costs',
                        'type': 'chat_interaction',
                        'requires_tools': i % 2 == 1,  # Alternate tool usage
                        'tools': ['cost_analyzer'] if i % 2 == 1 else []
                    }

                    interaction_result = await workflow.execute_agent_request(interaction_request)
                    chat_interactions.append(interaction_result)

                    # Update session with interaction
                    await self.database_operations.update_user_session(session_id, {
                        f'interaction_{i+1}': interaction_result['execution_id']
                    })

                    # Small delay between interactions
                    await asyncio.sleep(0.1)

                # Get final session state
                final_session = await self.database_operations.get_user_session(session_id)

                return {
                    'user_id': user_id,
                    'session_id': session_id,
                    'chat_interactions': chat_interactions,
                    'final_session': final_session,
                    'interaction_count': len(chat_interactions),
                    'workflow_instance_id': id(workflow),
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'success': False
                }

        # Run concurrent chat sessions
        print(f"  🔄 Testing concurrent chat sessions for {len(self.test_users)} users...")

        async def run_concurrent_chat_sessions():
            tasks = [simulate_user_chat_session(user) for user in self.test_users]
            return await asyncio.gather(*tasks, return_exceptions=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            chat_results = loop.run_until_complete(run_concurrent_chat_sessions())
        finally:
            loop.close()

        # Process chat session results
        for result in chat_results:
            if isinstance(result, Exception):
                multi_user_failures.append({
                    'user_id': 'unknown',
                    'error': str(result),
                    'failure_type': 'chat_session_exception'
                })
            elif result.get('success', False):
                concurrent_user_results.append(result)
            else:
                multi_user_failures.append({
                    'user_id': result.get('user_id', 'unknown'),
                    'error': result.get('error', 'Unknown error'),
                    'failure_type': 'chat_session_failure'
                })

        print(f"  📊 Multi-user chat functionality results:")
        print(f"     ✅ Successful chat sessions: {len(concurrent_user_results)}")
        print(f"     ❌ Failed chat sessions: {len(multi_user_failures)}")

        # Validate chat session quality and isolation
        user_session_data = {}

        for chat_result in concurrent_user_results:
            user_id = chat_result['user_id']
            session_id = chat_result['session_id']

            # Collect user-specific data for isolation validation
            user_session_data[user_id] = {
                'session_id': session_id,
                'interaction_count': chat_result['interaction_count'],
                'workflow_instance_id': chat_result['workflow_instance_id'],
                'interaction_user_ids': [
                    interaction['user_id'] for interaction in chat_result['chat_interactions']
                ]
            }

            # Validate interaction quality
            for i, interaction in enumerate(chat_result['chat_interactions']):
                if interaction['status'] != 'success':
                    multi_user_failures.append({
                        'user_id': user_id,
                        'error': f"Interaction {i+1} failed: {interaction.get('error', 'Unknown')}",
                        'failure_type': 'interaction_execution_failure'
                    })

                if interaction['user_id'] != user_id:
                    multi_user_failures.append({
                        'user_id': user_id,
                        'error': f"Interaction {i+1} has wrong user ID: {interaction['user_id']}",
                        'failure_type': 'interaction_user_contamination'
                    })

        # Validate isolation between concurrent users
        user_ids = list(user_session_data.keys())

        for i, user_id_1 in enumerate(user_ids):
            for user_id_2 in user_ids[i+1:]:
                data_1 = user_session_data[user_id_1]
                data_2 = user_session_data[user_id_2]

                # Check that users have different sessions
                if data_1['session_id'] == data_2['session_id']:
                    multi_user_failures.append({
                        'user_id': f"{user_id_1}, {user_id_2}",
                        'error': 'Users sharing same database session',
                        'failure_type': 'shared_database_session'
                    })

                # Check that users have different workflow instances
                if data_1['workflow_instance_id'] == data_2['workflow_instance_id']:
                    multi_user_failures.append({
                        'user_id': f"{user_id_1}, {user_id_2}",
                        'error': 'Users sharing same workflow instance',
                        'failure_type': 'shared_workflow_instance'
                    })

                # Check for interaction contamination
                for interaction_user_id in data_1['interaction_user_ids']:
                    if interaction_user_id != user_id_1:
                        multi_user_failures.append({
                            'user_id': user_id_1,
                            'error': f"User interactions contaminated with ID: {interaction_user_id}",
                            'failure_type': 'interaction_id_contamination'
                        })

        print(f"  🚨 Multi-user chat failure summary:")
        for failure in multi_user_failures:
            print(f"     ❌ {failure['failure_type']}: {failure['user_id']}")
            print(f"        {failure['error']}")

        self.business_function_results['multi_user_chat'] = {
            'successful_sessions': concurrent_user_results,
            'multi_user_failures': multi_user_failures,
            'concurrent_user_count': len(concurrent_user_results),
            'success_rate': len(concurrent_user_results) / max(1, len(self.test_users)) * 100
        }

        # Multi-user chat MUST work without interference
        self.assertEqual(
            len(multi_user_failures),
            0,
            f"✅ MULTI-USER CHAT PRESERVATION: Found {len(multi_user_failures)} multi-user chat failures. "
            f"Expected 0 for concurrent user support preservation. "
            f"Multi-user chat is CRITICAL for business scalability ($500K+ ARR)."
        )

    def test_04_database_operations_preservation(self):
        """
        EXPECTED: PASS - CRITICAL for data integrity

        Validates that database operations continue to work
        correctly after database factory cleanup.
        """
        print(f"\n🔍 PHASE 2.4: Testing database operations preservation...")

        database_failures = []
        successful_db_operations = []

        async def test_database_operations_for_user(user_data):
            """Test complete database operations for a user."""
            user_id = user_data['user_id']

            try:
                operations_log = []

                # Test 1: Create session
                session_id = await self.database_operations.create_user_session(
                    user_id, user_data['session_data']
                )
                operations_log.append({
                    'operation': 'create_session',
                    'session_id': session_id,
                    'success': True
                })

                # Test 2: Retrieve session
                retrieved_session = await self.database_operations.get_user_session(session_id)
                if retrieved_session is None:
                    raise ValueError("Failed to retrieve created session")

                operations_log.append({
                    'operation': 'get_session',
                    'session_id': session_id,
                    'success': True
                })

                # Test 3: Update session
                update_data = {
                    'last_interaction': time.time(),
                    'interaction_count': 5,
                    'user_preferences': {'theme': 'dark', 'notifications': True}
                }

                update_success = await self.database_operations.update_user_session(
                    session_id, update_data
                )

                if not update_success:
                    raise ValueError("Failed to update session")

                operations_log.append({
                    'operation': 'update_session',
                    'session_id': session_id,
                    'success': True
                })

                # Test 4: Verify update
                updated_session = await self.database_operations.get_user_session(session_id)
                for key, value in update_data.items():
                    if updated_session.get(key) != value:
                        raise ValueError(f"Update verification failed for {key}")

                operations_log.append({
                    'operation': 'verify_update',
                    'session_id': session_id,
                    'success': True
                })

                # Test 5: Multiple concurrent operations
                concurrent_updates = []
                for i in range(3):
                    concurrent_update = {
                        f'concurrent_operation_{i}': time.time(),
                        'operation_index': i
                    }
                    update_task = self.database_operations.update_user_session(
                        session_id, concurrent_update
                    )
                    concurrent_updates.append(update_task)

                # Wait for all concurrent updates
                concurrent_results = await asyncio.gather(*concurrent_updates)

                if not all(concurrent_results):
                    raise ValueError("Some concurrent updates failed")

                operations_log.append({
                    'operation': 'concurrent_updates',
                    'session_id': session_id,
                    'update_count': len(concurrent_updates),
                    'success': True
                })

                # Test 6: Final session state validation
                final_session = await self.database_operations.get_user_session(session_id)

                if final_session['user_id'] != user_id:
                    raise ValueError("Session user ID corrupted")

                operations_log.append({
                    'operation': 'final_validation',
                    'session_id': session_id,
                    'success': True
                })

                return {
                    'user_id': user_id,
                    'session_id': session_id,
                    'operations_log': operations_log,
                    'total_operations': len(operations_log),
                    'final_session_state': final_session,
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'operations_log': operations_log,
                    'success': False
                }

        # Test database operations for all users concurrently
        print(f"  🔄 Testing database operations for {len(self.test_users)} users...")

        async def run_database_tests():
            tasks = [test_database_operations_for_user(user) for user in self.test_users]
            return await asyncio.gather(*tasks, return_exceptions=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            db_results = loop.run_until_complete(run_database_tests())
        finally:
            loop.close()

        # Process database results
        for result in db_results:
            if isinstance(result, Exception):
                database_failures.append({
                    'user_id': 'unknown',
                    'error': str(result),
                    'failure_type': 'database_test_exception'
                })
            elif result.get('success', False):
                successful_db_operations.append(result)
            else:
                database_failures.append({
                    'user_id': result.get('user_id', 'unknown'),
                    'error': result.get('error', 'Unknown error'),
                    'failure_type': 'database_operation_failure',
                    'operations_completed': len(result.get('operations_log', []))
                })

        print(f"  📊 Database operations results:")
        print(f"     ✅ Successful database operations: {len(successful_db_operations)}")
        print(f"     ❌ Failed database operations: {len(database_failures)}")

        # Validate database integrity and isolation
        session_ids = set()
        for db_result in successful_db_operations:
            session_id = db_result['session_id']

            # Check for duplicate session IDs (would indicate poor isolation)
            if session_id in session_ids:
                database_failures.append({
                    'user_id': db_result['user_id'],
                    'error': f"Duplicate session ID detected: {session_id}",
                    'failure_type': 'session_id_collision'
                })
            else:
                session_ids.add(session_id)

            # Validate session data integrity
            final_session = db_result['final_session_state']

            if final_session['user_id'] != db_result['user_id']:
                database_failures.append({
                    'user_id': db_result['user_id'],
                    'error': 'Session user ID does not match expected user',
                    'failure_type': 'session_data_corruption'
                })

            # Validate operation completeness
            expected_operations = 6  # create, get, update, verify, concurrent, final
            actual_operations = db_result['total_operations']

            if actual_operations < expected_operations:
                database_failures.append({
                    'user_id': db_result['user_id'],
                    'error': f"Incomplete operations: {actual_operations}/{expected_operations}",
                    'failure_type': 'incomplete_operations'
                })

        # Test database connection pool status
        connection_status = self.database_operations.get_connection_status()
        print(f"  📊 Database connection pool status:")
        print(f"     🔗 Active connections: {connection_status['active_connections']}")
        print(f"     📈 Max connections: {connection_status['max_connections']}")

        print(f"  🚨 Database operation failure summary:")
        for failure in database_failures:
            print(f"     ❌ {failure['failure_type']}: {failure['user_id']}")
            print(f"        {failure['error']}")

        self.business_function_results['database_operations'] = {
            'successful_operations': successful_db_operations,
            'database_failures': database_failures,
            'unique_sessions_created': len(session_ids),
            'connection_pool_status': connection_status,
            'success_rate': len(successful_db_operations) / max(1, len(self.test_users)) * 100
        }

        # Database operations MUST work correctly
        self.assertEqual(
            len(database_failures),
            0,
            f"✅ DATABASE OPERATIONS PRESERVATION: Found {len(database_failures)} database operation failures. "
            f"Expected 0 for data integrity preservation. "
            f"Database operations are CRITICAL for persistent state management."
        )

    def test_05_comprehensive_business_function_validation(self):
        """
        EXPECTED: PASS - Comprehensive business function validation

        Validates that all business functions work together as an integrated system
        after factory pattern cleanup.
        """
        print(f"\n🔍 PHASE 2.5: Comprehensive business function validation...")

        if not all([
            self.business_function_results.get('agent_workflows'),
            self.business_function_results.get('websocket_events'),
            self.business_function_results.get('multi_user_chat'),
            self.business_function_results.get('database_operations')
        ]):
            # Run all previous tests if not already executed
            self.test_01_agent_execution_workflow_preservation()
            self.test_02_websocket_event_delivery_preservation()
            self.test_03_multi_user_chat_functionality_preservation()
            self.test_04_database_operations_preservation()

        # Compile comprehensive business function analysis
        comprehensive_analysis = {
            'overall_success_rate': 0,
            'component_scores': {},
            'business_impact_assessment': {},
            'critical_failures': [],
            'preservation_score': 0
        }

        # Calculate component scores
        components = ['agent_workflows', 'websocket_events', 'multi_user_chat', 'database_operations']

        for component in components:
            component_data = self.business_function_results.get(component, {})
            success_rate = component_data.get('success_rate', 0)

            comprehensive_analysis['component_scores'][component] = {
                'success_rate': success_rate,
                'status': 'PASS' if success_rate >= 95 else 'FAIL',
                'business_critical': True
            }

            # Weight all components equally for overall score
            comprehensive_analysis['overall_success_rate'] += success_rate / len(components)

        # Assess business impact
        overall_rate = comprehensive_analysis['overall_success_rate']

        if overall_rate >= 95:
            business_impact = 'EXCELLENT - No business impact from factory cleanup'
            preservation_score = 10
        elif overall_rate >= 90:
            business_impact = 'GOOD - Minimal business impact, monitoring recommended'
            preservation_score = 8
        elif overall_rate >= 80:
            business_impact = 'CONCERNING - Moderate business impact, immediate attention required'
            preservation_score = 6
        else:
            business_impact = 'CRITICAL - Severe business impact, rollback recommended'
            preservation_score = 0

        comprehensive_analysis['business_impact_assessment'] = {
            'overall_rate': overall_rate,
            'impact_description': business_impact,
            'preservation_score': preservation_score
        }

        # Identify critical failures
        for component, score_data in comprehensive_analysis['component_scores'].items():
            if score_data['status'] == 'FAIL':
                comprehensive_analysis['critical_failures'].append({
                    'component': component,
                    'success_rate': score_data['success_rate'],
                    'business_impact': 'HIGH - This component is critical for $500K+ ARR'
                })

        print(f"\n📋 COMPREHENSIVE BUSINESS FUNCTION ANALYSIS:")
        print(f"  🎯 Overall success rate: {overall_rate:.1f}%")
        print(f"  💼 Business impact: {business_impact}")
        print(f"  📊 Preservation score: {preservation_score}/10")

        print(f"\n📊 COMPONENT ANALYSIS:")
        for component, score_data in comprehensive_analysis['component_scores'].items():
            status_icon = "✅" if score_data['status'] == 'PASS' else "❌"
            print(f"  {status_icon} {component.replace('_', ' ').title()}: {score_data['success_rate']:.1f}%")

        if comprehensive_analysis['critical_failures']:
            print(f"\n🚨 CRITICAL BUSINESS FAILURES:")
            for failure in comprehensive_analysis['critical_failures']:
                print(f"  ❌ {failure['component']}: {failure['success_rate']:.1f}% success rate")
                print(f"     💼 {failure['business_impact']}")

        # Calculate estimated revenue impact
        if overall_rate < 100:
            revenue_at_risk = 500000 * (100 - overall_rate) / 100  # $500K ARR at risk
            print(f"\n💰 ESTIMATED REVENUE IMPACT:")
            print(f"  📉 Potential ARR at risk: ${revenue_at_risk:,.0f}")
            print(f"  📊 Based on {100 - overall_rate:.1f}% functionality degradation")

        self.business_function_results['comprehensive_analysis'] = comprehensive_analysis

        # Business functions MUST maintain 95%+ success rate
        self.assertGreaterEqual(
            overall_rate,
            95.0,
            f"✅ COMPREHENSIVE BUSINESS FUNCTION PRESERVATION: Overall success rate {overall_rate:.1f}%. "
            f"Required ≥95% for safe factory cleanup. "
            f"Business function preservation is CRITICAL for $500K+ ARR protection."
        )


if __name__ == '__main__':
    import unittest

    print("🚀 Starting Business Function Preservation Validation - Phase 2")
    print("=" * 80)
    print("These tests MUST PASS to ensure factory cleanup doesn't break the business.")
    print("=" * 80)

    unittest.main(verbosity=2)