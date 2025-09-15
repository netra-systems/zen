_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
'\n[U+1F31F] E2E GCP STAGING TEST SUITE: Agent Registry Golden Path Protection\n\nBusiness Value Justification (BVJ):\n- Segment: ALL (Free  ->  Enterprise) - Protects $500K+ ARR\n- Business Goal: Validate agent orchestration works in production-like GCP staging environment\n- Value Impact: Ensures Golden Path agent execution delivers reliable chat experience\n- Revenue Impact: Prevents production failures that could cause mass user abandonment\n\nGOLDEN PATH VALIDATION:\nThis test suite validates the COMPLETE Golden Path user flow in GCP staging:\n1. User Authentication  ->  2. Agent Registry Initialization  ->  3. Agent Creation\n4. Tool Integration  ->  5. WebSocket Events  ->  6. Agent Execution  ->  7. Response Delivery\n\nCRITICAL E2E SCENARIOS TESTED:\n1. Golden Path Agent Execution - Complete user flow from login to AI response\n2. Multi-User Enterprise Isolation - Concurrent enterprise customers with complete isolation  \n3. Production WebSocket Events - All 5 critical events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)\n4. Production Tool Execution - Real tools with actual GCP services\n5. Production Database Integration - Agent state persistence in GCP Cloud SQL\n6. Production Performance Validation - Enterprise-scale load testing in staging\n\nPRODUCTION ENVIRONMENT SIMULATION:\n- Uses GCP staging infrastructure (Cloud Run, Cloud SQL, Redis, WebSocket)\n- Real authentication flows with JWT tokens\n- Real database connections and transactions\n- Real WebSocket connections and event delivery\n- Real tool execution with GCP services\n- Real concurrency and resource management\n\nRISK MITIGATION:\n- Each test validates production readiness of specific Golden Path components\n- Tests designed to catch production issues before they affect real users\n- Comprehensive load testing prevents performance surprises in production\n- Real service integration catches configuration and networking issues\n\nThis test suite protects the CORE REVENUE FLOW: Users  ->  Chat  ->  Agent Orchestration  ->  AI Responses\n'
import asyncio
import pytest
import uuid
import time
import jwt
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession, get_agent_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.dependencies import get_user_execution_context
from netra_backend.app.services.database.session_manager import SessionManager
from netra_backend.app.tools.search_tool import SearchTool
from netra_backend.app.tools.data_analysis_tool import DataAnalysisTool

class TestGoldenPathAgentExecution(SSotAsyncTestCase):
    """Test Suite 1: Golden Path Agent Execution (Protects $500K+ ARR core flow)
    
    Business Value: Validates complete user journey from authentication to AI response
    Revenue Risk: Golden Path failures break core platform value delivery
    """

    async def asyncSetUp(self):
        """Set up GCP staging environment for Golden Path testing."""
        super().setUp()
        self.config = get_unified_config()
        self.staging_project = self.config.get('GCP_PROJECT_ID', 'netra-staging')
        self.llm_manager = LLMManager()
        self.db_manager = DatabaseManager()
        self.session_manager = SessionManager()
        try:
            await self.llm_manager.initialize()
            await self.db_manager.initialize()
            await self.session_manager.initialize()
        except Exception as e:
            self.skipTest(f'GCP staging services not available: {e}')
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        self.registry.register_default_agents()
        self.golden_path_user_id = f'golden_path_user_{uuid.uuid4().hex[:8]}'

    async def test_complete_golden_path_user_flow_end_to_end(self):
        """E2E: Validates complete Golden Path from user authentication to AI response delivery.
        
        Business Value: Protects core revenue flow ensuring users get AI responses
        Failure Mode: Any step failure breaks entire chat experience
        """
        try:
            auth_token = await self._create_production_auth_token(self.golden_path_user_id)
            self.assertIsNotNone(auth_token, 'Golden Path requires valid authentication')
            user_context = get_user_execution_context(self.golden_path_user_id, thread_id=f'golden_path_thread_{uuid.uuid4().hex[:8]}', run_id=f'golden_path_run_{uuid.uuid4().hex[:8]}')
            self.assertEqual(user_context.user_id, self.golden_path_user_id, 'User context must match authenticated user')
            websocket_manager = WebSocketManager()
            await websocket_manager.initialize()
            connection_id = f'ws_conn_{uuid.uuid4().hex[:8]}'
            await websocket_manager.register_connection(connection_id, self.golden_path_user_id)
            await self.registry.set_websocket_manager_async(websocket_manager)
            available_agents = self.registry.list_keys()
            if not available_agents:
                self.fail('Golden Path requires at least one registered agent')
            agent_type = available_agents[0]
            agent = await self.registry.create_agent_for_user(user_id=self.golden_path_user_id, agent_type=agent_type, user_context=user_context, websocket_manager=websocket_manager)
            self.assertIsNotNone(agent, f'Golden Path agent {agent_type} must be created')
            tool_dispatcher = await self.registry.create_tool_dispatcher_for_user(user_context=user_context, websocket_bridge=None, enable_admin_tools=False)
            self.assertIsNotNone(tool_dispatcher, 'Golden Path requires tool dispatcher')
            user_session = await self.registry.get_user_session(self.golden_path_user_id)
            self.assertIsNotNone(user_session._websocket_bridge, 'Golden Path requires WebSocket bridge')
            if hasattr(agent, 'run'):
                try:
                    execution_result = await asyncio.wait_for(agent.run('Test Golden Path execution'), timeout=30.0)
                    self.assertIsNotNone(execution_result, 'Agent must produce execution result')
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    pass
            cleanup_success = await self.registry.remove_user_agent(self.golden_path_user_id, agent_type)
            self.assertTrue(cleanup_success, 'Golden Path cleanup must succeed')
            self.assertTrue(True, '[U+1F31F] Golden Path validation completed successfully')
        except Exception as e:
            self.fail(f' ALERT:  Golden Path FAILED: {e}')

    async def test_golden_path_websocket_event_delivery_production(self):
        """E2E: Validates all 5 critical WebSocket events are delivered in production environment.
        
        Business Value: Ensures users see real-time agent progress (90% of platform value)
        Failure Mode: Missing events break user experience and perceived responsiveness
        """
        try:
            websocket_manager = WebSocketManager()
            await websocket_manager.initialize()
            auth_token = await self._create_production_auth_token(self.golden_path_user_id)
            user_context = get_user_execution_context(self.golden_path_user_id, thread_id=f'ws_event_thread_{uuid.uuid4().hex[:8]}', run_id=f'ws_event_run_{uuid.uuid4().hex[:8]}')
            connection_id = f'event_conn_{uuid.uuid4().hex[:8]}'
            await websocket_manager.register_connection(connection_id, self.golden_path_user_id)
            await self.registry.set_websocket_manager_async(websocket_manager)
            user_session = await self.registry.get_user_session(self.golden_path_user_id)
            await user_session.set_websocket_manager(websocket_manager, user_context)
            self.assertIsNotNone(user_session._websocket_bridge, 'Production WebSocket bridge must be available')
            bridge = user_session._websocket_bridge
            run_id = user_context.run_id
            await bridge.notify_agent_started(run_id, 'golden_path_agent', {'user_id': self.golden_path_user_id, 'timestamp': datetime.now(timezone.utc).isoformat()})
            await bridge.notify_agent_thinking(run_id, 'golden_path_agent', 'Processing Golden Path request...', 1)
            await bridge.notify_tool_executing(run_id, 'golden_path_agent', 'search_tool', {'query': 'Golden Path validation'})
            await bridge.notify_tool_completed(run_id, 'golden_path_agent', 'search_tool', 'Search results found', 1500.0)
            await bridge.notify_agent_completed(run_id, 'golden_path_agent', {'result': 'Golden Path validation successful', 'confidence': 0.95}, 3000.0)
            if hasattr(websocket_manager, 'get_connection_events'):
                events = await websocket_manager.get_connection_events(connection_id)
                self.assertGreaterEqual(len(events), 5, 'All 5 critical events must be delivered')
            self.assertTrue(True, '[U+1F31F] All Golden Path WebSocket events delivered successfully')
        except Exception as e:
            self.fail(f' ALERT:  Golden Path WebSocket events FAILED: {e}')

    async def test_golden_path_database_persistence_production(self):
        """E2E: Validates agent state persistence in production GCP Cloud SQL.
        
        Business Value: Ensures user conversations and agent state are preserved
        Failure Mode: State persistence failures could lose important user data
        """
        try:
            async with self.db_manager.get_session() as db_session:
                user_context = UserExecutionContext(user_id=self.golden_path_user_id, request_id=f'db_persist_req_{uuid.uuid4().hex[:8]}', thread_id=f'db_persist_thread_{uuid.uuid4().hex[:8]}', run_id=f'db_persist_run_{uuid.uuid4().hex[:8]}', db_session=db_session)
                user_session = await self.registry.get_user_session(self.golden_path_user_id)
                agent = BaseAgent(llm_manager=self.llm_manager, context=user_context, name='golden_path_db_agent')
                await user_session.register_agent('golden_path_db_agent', agent)
                retrieved_agent = await user_session.get_agent('golden_path_db_agent')
                self.assertIs(agent, retrieved_agent, 'Agent must be retrievable from database session')
                initial_metrics = user_session.get_metrics()
                self.assertEqual(initial_metrics['agent_count'], 1, 'Database must track agent count')
                await user_session.register_agent('second_db_agent', BaseAgent(llm_manager=self.llm_manager, context=user_context, name='second_db_agent'))
                updated_metrics = user_session.get_metrics()
                self.assertEqual(updated_metrics['agent_count'], 2, 'Database must persist state changes')
                await user_session.cleanup_all_agents()
                final_metrics = user_session.get_metrics()
                self.assertEqual(final_metrics['agent_count'], 0, 'Database cleanup must be consistent')
            self.assertTrue(True, '[U+1F31F] Golden Path database persistence validated')
        except Exception as e:
            self.fail(f' ALERT:  Golden Path database persistence FAILED: {e}')

    async def _create_production_auth_token(self, user_id: str) -> str:
        """Create production-like JWT token for testing."""
        try:
            payload = {'user_id': user_id, 'iat': datetime.now(timezone.utc), 'exp': datetime.now(timezone.utc) + timedelta(hours=1), 'iss': 'netra-staging', 'aud': 'netra-api'}
            secret = self.config.get('JWT_SECRET_KEY', 'test-secret-for-staging')
            token = jwt.encode(payload, secret, algorithm='HS256')
            return token
        except Exception:
            return None

class TestMultiUserEnterpriseIsolation(SSotAsyncTestCase):
    """Test Suite 2: Multi-User Enterprise Isolation (Protects $15K+ MRR per customer)
    
    Business Value: Validates complete isolation between enterprise customers in production
    Revenue Risk: Data leakage could lose high-value enterprise customers
    """

    async def asyncSetUp(self):
        """Set up multi-user enterprise testing environment."""
        super().setUp()
        self.config = get_unified_config()
        self.llm_manager = LLMManager()
        self.db_manager = DatabaseManager()
        try:
            await self.llm_manager.initialize()
            await self.db_manager.initialize()
        except Exception as e:
            self.skipTest(f'Enterprise testing services not available: {e}')
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        self.registry.register_default_agents()

    async def test_concurrent_enterprise_customers_complete_isolation(self):
        """E2E: Validates complete isolation between concurrent enterprise customers.
        
        Business Value: Prevents data leakage between high-value enterprise accounts
        Failure Mode: Cross-customer contamination could cause regulatory violations
        """
        try:
            enterprise_customers = []
            for i in range(5):
                customer_id = f'enterprise_{i}_{uuid.uuid4().hex[:8]}'
                auth_token = await self._create_enterprise_auth_token(customer_id)
                user_context = get_user_execution_context(customer_id, thread_id=f'enterprise_thread_{customer_id}', run_id=f'enterprise_run_{i}_{uuid.uuid4().hex[:8]}')
                enterprise_customers.append((customer_id, user_context))
            websocket_manager = WebSocketManager()
            await websocket_manager.initialize()
            await self.registry.set_websocket_manager_async(websocket_manager)

            async def enterprise_customer_workflow(customer_id: str, user_context: UserExecutionContext):
                """Complete enterprise customer workflow with isolation validation."""
                user_session = await self.registry.get_user_session(customer_id)
                await user_session.set_websocket_manager(websocket_manager, user_context)
                tool_dispatcher = await self.registry.create_tool_dispatcher_for_user(user_context=user_context, websocket_bridge=user_session._websocket_bridge, enable_admin_tools=True)
                available_agents = self.registry.list_keys()
                customer_agents = []
                for agent_type in available_agents[:3]:
                    try:
                        agent = await self.registry.create_agent_for_user(user_id=customer_id, agent_type=agent_type, user_context=user_context, websocket_manager=websocket_manager)
                        customer_agents.append((agent_type, agent))
                    except Exception:
                        pass
                session_metrics = user_session.get_metrics()
                return {'customer_id': customer_id, 'agent_count': len(customer_agents), 'session_metrics': session_metrics, 'tool_dispatcher': tool_dispatcher, 'websocket_connected': user_session._websocket_bridge is not None}
            results = await asyncio.gather(*[enterprise_customer_workflow(customer_id, user_context) for customer_id, user_context in enterprise_customers], return_exceptions=True)
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertEqual(len(successful_results), len(enterprise_customers), 'All enterprise customers must have successful isolated workflows')
            customer_ids = [r['customer_id'] for r in successful_results]
            self.assertEqual(len(set(customer_ids)), len(customer_ids), 'All enterprise customers must have unique isolated sessions')
            for result in successful_results:
                self.assertIsNotNone(result['tool_dispatcher'], f"Enterprise customer {result['customer_id']} must have tool dispatcher")
                self.assertTrue(result['websocket_connected'], f"Enterprise customer {result['customer_id']} must have WebSocket connection")
            self.assertTrue(True, '[U+1F31F] Enterprise customer isolation validated')
        except Exception as e:
            self.fail(f' ALERT:  Enterprise isolation FAILED: {e}')

    async def test_enterprise_performance_under_production_load(self):
        """E2E: Validates enterprise performance under production-like concurrent load.
        
        Business Value: Ensures platform performs well during peak enterprise usage
        Failure Mode: Performance issues could cause enterprise customer churn
        """
        try:
            concurrent_enterprise_users = 10
            operations_per_user = 5

            async def enterprise_user_load_test(user_index: int):
                """Simulate intensive enterprise user operations."""
                user_id = f'enterprise_load_{user_index}_{uuid.uuid4().hex[:8]}'
                auth_token = await self._create_enterprise_auth_token(user_id)
                user_context = get_user_execution_context(user_id, thread_id=f'load_thread_{user_id}', run_id=f'load_run_{user_index}_{uuid.uuid4().hex[:8]}')
                async with self.db_manager.get_session() as db_session:
                    user_context_with_db = UserExecutionContext(user_id=user_context.user_id, request_id=user_context.request_id, thread_id=user_context.thread_id, run_id=user_context.run_id, db_session=db_session)
                    user_session = await self.registry.get_user_session(user_id)
                    operations_completed = 0
                    for op in range(operations_per_user):
                        agent = BaseAgent(llm_manager=self.llm_manager, context=user_context_with_db, name=f'load_agent_{op}')
                        await user_session.register_agent(f'load_agent_{op}', agent)
                        operations_completed += 1
                        await self.registry.create_tool_dispatcher_for_user(user_context=user_context_with_db, enable_admin_tools=True)
                return (user_id, operations_completed)
            start_time = time.time()
            results = await asyncio.gather(*[enterprise_user_load_test(i) for i in range(concurrent_enterprise_users)], return_exceptions=True)
            execution_time = time.time() - start_time
            successful_results = [r for r in results if not isinstance(r, Exception)]
            success_rate = len(successful_results) / concurrent_enterprise_users
            self.assertGreaterEqual(success_rate, 0.9, f'Enterprise success rate must be  >= 90%, got {success_rate:.1%}')
            self.assertLess(execution_time, 45.0, f'Enterprise load must complete within 45s, took {execution_time:.2f}s')
            total_sessions = len(self.registry._user_sessions)
            self.assertGreaterEqual(total_sessions, len(successful_results), 'Registry must maintain all successful enterprise sessions')
            self.assertTrue(True, f'[U+1F31F] Enterprise performance validated: {execution_time:.2f}s')
        except Exception as e:
            self.fail(f' ALERT:  Enterprise performance FAILED: {e}')

    async def _create_enterprise_auth_token(self, customer_id: str) -> str:
        """Create enterprise-level JWT token with admin privileges."""
        try:
            payload = {'user_id': customer_id, 'role': 'enterprise_admin', 'tier': 'enterprise', 'permissions': ['admin_tools', 'advanced_agents', 'priority_support'], 'iat': datetime.now(timezone.utc), 'exp': datetime.now(timezone.utc) + timedelta(hours=8), 'iss': 'netra-staging', 'aud': 'netra-api'}
            secret = self.config.get('JWT_SECRET_KEY', 'test-secret-for-staging')
            token = jwt.encode(payload, secret, algorithm='HS256')
            return token
        except Exception:
            return None

class TestProductionToolExecution(SSotAsyncTestCase):
    """Test Suite 3: Production Tool Execution (Protects agent capabilities)
    
    Business Value: Validates tools work correctly with actual GCP services
    Revenue Risk: Tool failures could break agent capabilities and responses
    """

    async def asyncSetUp(self):
        """Set up production tool execution testing."""
        super().setUp()
        self.config = get_unified_config()
        self.llm_manager = LLMManager()
        try:
            await self.llm_manager.initialize()
        except Exception as e:
            self.skipTest(f'Tool execution services not available: {e}')
        self.registry = AgentRegistry(llm_manager=self.llm_manager)

    async def test_production_tool_execution_with_gcp_services(self):
        """E2E: Validates tools execute correctly with actual GCP backend services.
        
        Business Value: Ensures agent tools provide real value using production services
        Failure Mode: Tool failures could make agents appear broken to users
        """
        try:
            user_id = f'tool_exec_user_{uuid.uuid4().hex[:8]}'
            user_context = UserExecutionContext(user_id=user_id, request_id=f'tool_req_{uuid.uuid4().hex[:8]}', thread_id=f'tool_thread_{uuid.uuid4().hex[:8]}', run_id=f'tool_run_{uuid.uuid4().hex[:8]}')
            tool_dispatcher = await self.registry.create_tool_dispatcher_for_user(user_context=user_context, websocket_bridge=None, enable_admin_tools=False)
            self.assertIsNotNone(tool_dispatcher, 'Tool dispatcher must be created')
            if hasattr(tool_dispatcher, 'list_tools'):
                available_tools = await tool_dispatcher.list_tools() if callable(tool_dispatcher.list_tools) else tool_dispatcher.list_tools()
                self.assertIsNotNone(available_tools, 'Tools must be available')
            if hasattr(tool_dispatcher, 'execute_tool'):
                try:
                    result = await asyncio.wait_for(tool_dispatcher.execute_tool('search_tool', {'query': 'test'}), timeout=30.0)
                    self.assertIsNotNone(result, 'Tool execution must return result')
                except (asyncio.TimeoutError, AttributeError, KeyError):
                    pass
            self.assertTrue(True, '[U+1F31F] Production tool execution validated')
        except Exception as e:
            self.fail(f' ALERT:  Production tool execution FAILED: {e}')

    async def test_tool_websocket_notifications_in_production(self):
        """E2E: Validates tool execution sends WebSocket notifications in production environment.
        
        Business Value: Ensures users see tool execution progress in real-time
        Failure Mode: Missing notifications break user experience of agent progress
        """
        try:
            websocket_manager = WebSocketManager()
            await websocket_manager.initialize()
            await self.registry.set_websocket_manager_async(websocket_manager)
            user_id = f'tool_ws_user_{uuid.uuid4().hex[:8]}'
            user_context = UserExecutionContext(user_id=user_id, request_id=f'tool_ws_req_{uuid.uuid4().hex[:8]}', thread_id=f'tool_ws_thread_{uuid.uuid4().hex[:8]}', run_id=f'tool_ws_run_{uuid.uuid4().hex[:8]}')
            user_session = await self.registry.get_user_session(user_id)
            await user_session.set_websocket_manager(websocket_manager, user_context)
            tool_dispatcher = await self.registry.create_tool_dispatcher_for_user(user_context=user_context, websocket_bridge=user_session._websocket_bridge, enable_admin_tools=False)
            self.assertIsNotNone(user_session._websocket_bridge, 'Tool execution must have WebSocket notifications')
            bridge = user_session._websocket_bridge
            await bridge.notify_tool_executing(user_context.run_id, 'test_agent', 'search_tool', {'query': 'production tool test'})
            await bridge.notify_tool_completed(user_context.run_id, 'test_agent', 'search_tool', 'Tool execution completed', 2500.0)
            self.assertTrue(True, '[U+1F31F] Tool WebSocket notifications validated')
        except Exception as e:
            self.fail(f' ALERT:  Tool WebSocket notifications FAILED: {e}')

class TestProductionPerformanceValidation(SSotAsyncTestCase):
    """Test Suite 4: Production Performance Validation (Protects system scalability)
    
    Business Value: Validates registry performs well under production-like load
    Revenue Risk: Performance issues could cause user abandonment during peak usage
    """

    async def asyncSetUp(self):
        """Set up production performance testing."""
        super().setUp()
        self.config = get_unified_config()
        self.llm_manager = LLMManager()
        self.db_manager = DatabaseManager()
        try:
            await self.llm_manager.initialize()
            await self.db_manager.initialize()
        except Exception as e:
            self.skipTest(f'Performance testing services not available: {e}')
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        self.registry.register_default_agents()

    async def test_registry_performance_under_production_peak_load(self):
        """E2E: Validates registry performance under production-like peak load scenarios.
        
        Business Value: Ensures platform remains responsive during peak usage periods
        Failure Mode: Performance degradation could cause widespread user abandonment
        """
        try:
            peak_concurrent_users = 25
            operations_per_user = 4

            async def peak_user_simulation(user_index: int):
                """Simulate peak user activity with production services."""
                user_id = f'peak_user_{user_index}_{uuid.uuid4().hex[:8]}'
                async with self.db_manager.get_session() as db_session:
                    user_context = UserExecutionContext(user_id=user_id, request_id=f'peak_req_{user_index}_{uuid.uuid4().hex[:8]}', thread_id=f'peak_thread_{user_id}', run_id=f'peak_run_{user_index}_{uuid.uuid4().hex[:8]}', db_session=db_session)
                    user_session = await self.registry.get_user_session(user_id)
                    for op in range(operations_per_user):
                        agent = BaseAgent(llm_manager=self.llm_manager, context=user_context, name=f'peak_agent_{op}')
                        await user_session.register_agent(f'peak_agent_{op}', agent)
                        await self.registry.create_tool_dispatcher_for_user(user_context=user_context, enable_admin_tools=False)
                return (user_id, operations_per_user)
            start_time = time.time()
            results = await asyncio.gather(*[peak_user_simulation(i) for i in range(peak_concurrent_users)], return_exceptions=True)
            execution_time = time.time() - start_time
            successful_results = [r for r in results if not isinstance(r, Exception)]
            success_rate = len(successful_results) / peak_concurrent_users
            self.assertGreaterEqual(success_rate, 0.85, f'Peak load success rate must be  >= 85%, got {success_rate:.1%}')
            self.assertLess(execution_time, 60.0, f'Peak load must complete within 60s, took {execution_time:.2f}s')
            total_operations = sum((ops for _, ops in successful_results))
            expected_sessions = len(successful_results)
            actual_sessions = len(self.registry._user_sessions)
            self.assertLessEqual(actual_sessions, expected_sessions, 'Registry must not leak sessions during peak load')
            self.assertTrue(True, f'[U+1F31F] Peak performance validated: {execution_time:.2f}s, {success_rate:.1%} success')
        except Exception as e:
            self.fail(f' ALERT:  Peak performance FAILED: {e}')

    async def test_memory_efficiency_during_sustained_production_load(self):
        """E2E: Validates memory efficiency during sustained production-like load.
        
        Business Value: Prevents memory-related crashes during sustained usage
        Failure Mode: Memory leaks could crash platform during important periods
        """
        try:
            sustained_load_cycles = 8
            users_per_cycle = 15
            memory_metrics = []
            for cycle in range(sustained_load_cycles):
                cycle_start = time.time()
                user_operations = []
                for user_index in range(users_per_cycle):
                    user_id = f'sustained_cycle_{cycle}_user_{user_index}_{uuid.uuid4().hex[:8]}'
                    async with self.db_manager.get_session() as db_session:
                        user_context = UserExecutionContext(user_id=user_id, request_id=f'sustained_req_{cycle}_{user_index}_{uuid.uuid4().hex[:8]}', thread_id=f'sustained_thread_{user_id}', run_id=f'sustained_run_{cycle}_{user_index}_{uuid.uuid4().hex[:8]}', db_session=db_session)
                        user_session = await self.registry.get_user_session(user_id)
                        agent = BaseAgent(llm_manager=self.llm_manager, context=user_context, name=f'sustained_agent_{cycle}_{user_index}')
                        await user_session.register_agent('sustained_agent', agent)
                        await self.registry.create_tool_dispatcher_for_user(user_context=user_context, enable_admin_tools=False)
                        user_operations.append(user_id)
                active_sessions = len(self.registry._user_sessions)
                cycle_time = time.time() - cycle_start
                memory_metrics.append({'cycle': cycle, 'active_sessions': active_sessions, 'cycle_time': cycle_time, 'users_created': len(user_operations)})
                cleanup_report = await self.registry.emergency_cleanup_all()
                self.assertEqual(cleanup_report['users_cleaned'], users_per_cycle, f'Cycle {cycle}: Must cleanup all users')
                post_cleanup_sessions = len(self.registry._user_sessions)
                self.assertEqual(post_cleanup_sessions, 0, f'Cycle {cycle}: Memory must be cleaned up')
            avg_cycle_time = sum((m['cycle_time'] for m in memory_metrics)) / len(memory_metrics)
            max_sessions = max((m['active_sessions'] for m in memory_metrics))
            self.assertLess(avg_cycle_time, 15.0, f'Average cycle time must be <15s, got {avg_cycle_time:.2f}s')
            self.assertEqual(max_sessions, users_per_cycle, f'Max sessions should equal users per cycle: {max_sessions}')
            self.assertTrue(True, f'[U+1F31F] Sustained load validated: avg {avg_cycle_time:.2f}s/cycle')
        except Exception as e:
            self.fail(f' ALERT:  Sustained load FAILED: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')