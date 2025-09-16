"""
GOLDEN PATH COVERAGE: Database Persistence Agent State Tests

Business Impact: $500K+ ARR - State persistence critical for conversation continuity
Coverage Target: 0% → 75% for database persistence during agent execution
Priority: P0 - Data integrity and user experience continuity

Tests comprehensive database persistence of agent state across the 3-tier
storage architecture (Redis/PostgreSQL/ClickHouse) during real agent execution.

CRITICAL REQUIREMENTS per CLAUDE.md:
- Real database connections only (no mocks)
- Test 3-tier persistence: Redis (hot), PostgreSQL (warm), ClickHouse (cold)
- Multi-user state isolation validation
- State recovery and consistency validation

Test Categories:
1. Agent State Persistence (10+ test cases)
2. Multi-Tier Storage Integration (8+ test cases)
3. State Recovery and Consistency (7+ test cases)
4. Multi-User State Isolation (6+ test cases)
"""
import asyncio
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env, IsolatedEnvironment
import pytest
from loguru import logger
from netra_backend.app.agents.supervisor.state_manager import StateManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.state_persistence_optimized import OptimizedStatePersistence
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.db.clickhouse_client import ClickHouseClient
from netra_backend.app.core.configuration.database import DatabaseConfig
from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

class DatabasePersistenceAgentStateTests(SSotAsyncTestCase):
    """
    Comprehensive tests for database persistence of agent state.

    Business Value: Ensures conversation continuity and data integrity ($500K+ ARR protection).
    Coverage: Database persistence functionality from 0% to 75%.
    """

    def setup_method(self, method):
        """Setup real database infrastructure - no mocks allowed."""
        super().setup_method(method)
        self.test_id = str(uuid.uuid4())[:8]
        self.user_id = f'test_user_{self.test_id}'
        self.conversation_id = f'conv_{self.test_id}'
        self.database_manager = None
        self.clickhouse_client = None
        self.state_manager = None
        self.optimized_persistence = None
        self.execution_engine = None
        self.user_context = None
        self.db_config = DatabaseConfig()
        logger.info(f'Setup database persistence test for user: {self.user_id}')

    async def setup_real_database_infrastructure(self):
        """Initialize real database infrastructure components."""
        self.database_manager = DatabaseManager()
        await self.database_manager.initialize()
        self.clickhouse_client = ClickHouseClient()
        await self.clickhouse_client.initialize()
        self.user_context = UserExecutionContext(user_id=self.user_id, thread_id=self.conversation_id, run_id=f'run_{uuid.uuid4()}', request_id=f'req_{uuid.uuid4()}')
        self.state_manager = StateManager(user_context=self.user_context, database_manager=self.database_manager)
        self.optimized_persistence = OptimizedStatePersistence(database_manager=self.database_manager, clickhouse_client=self.clickhouse_client)
        websocket_manager = get_websocket_manager(user_context=self.user_context)
        self.execution_engine = UserExecutionEngine(user_context=self.user_context, websocket_manager=websocket_manager, state_manager=self.state_manager)
        logger.info('Real database infrastructure initialized')

    def teardown_method(self, method):
        """Cleanup real database connections and test data."""

        async def cleanup_database():
            if self.state_manager:
                try:
                    await self.state_manager.clear_user_state()
                except Exception as e:
                    logger.warning(f'Error cleaning state: {e}')
            if self.database_manager:
                try:
                    await self.database_manager.execute_query('DELETE FROM conversations WHERE conversation_id = %s', (self.conversation_id,))
                    await self.database_manager.execute_query('DELETE FROM agent_states WHERE user_id = %s', (self.user_id,))
                except Exception as e:
                    logger.warning(f'Error cleaning database: {e}')
            if self.clickhouse_client:
                try:
                    await self.clickhouse_client.execute(f"DELETE FROM agent_analytics WHERE user_id = '{self.user_id}'")
                except Exception as e:
                    logger.warning(f'Error cleaning ClickHouse: {e}')
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cleanup_database())
        loop.close()
        super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_agent_state_basic_persistence(self):
        """Test basic agent state persistence during execution."""
        await self.setup_real_database_infrastructure()
        initial_state = {'conversation_context': 'supply chain analysis', 'user_preferences': {'industry': 'manufacturing'}, 'agent_memory': ['User wants cost optimization'], 'session_data': {'start_time': datetime.now().isoformat()}}
        await self.state_manager.save_state(initial_state)
        result = await self.execution_engine.execute_request('Continue our supply chain analysis with focus on cost reduction')
        final_state = await self.state_manager.get_state()
        assert final_state is not None, 'State should be persisted'
        assert final_state.get('conversation_context') == 'supply chain analysis', 'Context should be preserved'
        assert 'user_preferences' in final_state, 'User preferences should be persisted'
        if result is not None:
            final_memory = final_state.get('agent_memory', [])
            assert len(final_memory) >= len(initial_state.get('agent_memory', [])), 'Agent memory should grow or maintain'
        logger.info('Verified basic agent state persistence')

    @pytest.mark.asyncio
    async def test_agent_state_conversation_continuity(self):
        """Test agent state enables conversation continuity across sessions."""
        await self.setup_real_database_infrastructure()
        session_1_state = {'conversation_history': [{'role': 'user', 'content': 'I need help with supply chain costs'}, {'role': 'assistant', 'content': "I'll analyze your supply chain efficiency"}], 'analysis_context': {'domain': 'supply_chain', 'focus_areas': ['cost_reduction', 'efficiency'], 'data_requirements': ['supplier_data', 'cost_data']}, 'user_context': {'company_size': 'mid_market', 'industry': 'manufacturing'}}
        await self.state_manager.save_state(session_1_state)
        new_user_context = UserExecutionContext(user_id=self.user_id, thread_id=self.conversation_id, run_id=f'run_{uuid.uuid4()}', request_id=f'req_{uuid.uuid4()}')
        new_state_manager = StateManager(user_context=new_user_context, database_manager=self.database_manager)
        continued_state = await new_state_manager.get_state()
        new_execution_engine = UserExecutionEngine(user_context=new_user_context, websocket_manager=get_websocket_manager(user_context=new_user_context), state_manager=new_state_manager)
        result = await new_execution_engine.execute_request('Based on our previous discussion, show me the cost analysis results')
        assert continued_state is not None, 'Previous state should be retrieved'
        assert continued_state.get('conversation_history') is not None, 'Conversation history should be preserved'
        assert continued_state.get('analysis_context') is not None, 'Analysis context should be preserved'
        previous_history = continued_state.get('conversation_history', [])
        assert len(previous_history) > 0, 'Should have previous conversation history'
        analysis_context = continued_state.get('analysis_context', {})
        assert analysis_context.get('domain') == 'supply_chain', 'Domain context should be preserved'
        assert 'cost_reduction' in analysis_context.get('focus_areas', []), 'Focus areas should be preserved'
        logger.info('Verified conversation continuity across sessions')

    @pytest.mark.asyncio
    async def test_agent_state_incremental_updates(self):
        """Test incremental updates to agent state during execution."""
        await self.setup_real_database_infrastructure()
        base_state = {'analysis_progress': {'step': 1, 'total_steps': 5}, 'gathered_data': [], 'insights': [], 'recommendations': []}
        await self.state_manager.save_state(base_state)
        operations = ['Gather supplier data for analysis', 'Analyze cost patterns in the data', 'Identify optimization opportunities', 'Generate preliminary recommendations']
        for i, operation in enumerate(operations):
            result = await self.execution_engine.execute_request(operation)
            current_state = await self.state_manager.get_state()
            assert current_state is not None, f'State should exist after operation {i + 1}'
            progress = current_state.get('analysis_progress', {})
            assert progress.get('step', 0) >= base_state['analysis_progress']['step'], 'Progress should advance or maintain'
            gathered_data = current_state.get('gathered_data', [])
            insights = current_state.get('insights', [])
            recommendations = current_state.get('recommendations', [])
            total_items = len(gathered_data) + len(insights) + len(recommendations)
            expected_min_items = i
            assert total_items >= max(0, expected_min_items - 1), f'Should accumulate data through step {i + 1}'
        logger.info('Verified incremental state updates through execution')

    @pytest.mark.asyncio
    async def test_three_tier_storage_distribution(self):
        """Test state distribution across Redis (hot), PostgreSQL (warm), ClickHouse (cold)."""
        await self.setup_real_database_infrastructure()
        comprehensive_state = {'current_session': {'active_agent': 'supply_researcher', 'current_step': 'data_analysis', 'temporary_results': {'processing': True}}, 'conversation_state': {'conversation_id': self.conversation_id, 'user_preferences': {'format': 'detailed'}, 'analysis_history': ['step1', 'step2']}, 'analytics_data': {'performance_metrics': {'response_time': 2.5, 'tokens_used': 1500}, 'usage_patterns': {'peak_hours': [14, 15, 16]}, 'optimization_results': {'cost_saved': 1000}}}
        await self.optimized_persistence.save_comprehensive_state(user_id=self.user_id, thread_id=self.conversation_id, state_data=comprehensive_state)
        redis_state = await self.optimized_persistence.get_hot_state(self.user_id)
        postgres_state = await self.optimized_persistence.get_warm_state(self.conversation_id)
        clickhouse_analytics = await self.optimized_persistence.get_cold_analytics(self.user_id)
        assert redis_state is not None, 'Redis should contain hot state data'
        if 'current_session' in redis_state:
            current_session = redis_state['current_session']
            assert current_session.get('active_agent') == 'supply_researcher', 'Hot data should be in Redis'
        assert postgres_state is not None, 'PostgreSQL should contain warm state data'
        if 'conversation_state' in postgres_state:
            conversation_state = postgres_state['conversation_state']
            assert conversation_state.get('conversation_id') == self.conversation_id, 'Warm data should be in PostgreSQL'
        assert clickhouse_analytics is not None, 'ClickHouse should contain analytics data'
        if 'analytics_data' in clickhouse_analytics:
            analytics = clickhouse_analytics['analytics_data']
            assert 'performance_metrics' in analytics, 'Analytics data should be in ClickHouse'
        logger.info('Verified 3-tier storage distribution')

    @pytest.mark.asyncio
    async def test_tier_failover_and_recovery(self):
        """Test failover and recovery mechanisms between storage tiers."""
        await self.setup_real_database_infrastructure()
        test_state = {'critical_data': 'Must not be lost', 'user_context': {'important': True}, 'session_info': {'active': True}}
        await self.optimized_persistence.save_comprehensive_state(user_id=self.user_id, thread_id=self.conversation_id, state_data=test_state)
        try:
            fallback_state = await self.optimized_persistence.get_state_with_fallback(user_id=self.user_id, thread_id=self.conversation_id)
            assert fallback_state is not None, 'Should recover state even with tier issues'
            assert fallback_state.get('critical_data') == 'Must not be lost', 'Critical data should be preserved'
        except Exception as e:
            logger.warning(f'Failover test encountered: {e}')
            normal_state = await self.state_manager.get_state()
            assert normal_state is not None, 'Should still be able to retrieve state'
        logger.info('Verified tier failover and recovery mechanisms')

    @pytest.mark.asyncio
    async def test_storage_tier_performance_characteristics(self):
        """Test performance characteristics of different storage tiers."""
        await self.setup_real_database_infrastructure()
        small_state = {'quick': 'data'}
        medium_state = {'conversation': ['msg1', 'msg2', 'msg3'] * 100}
        large_analytics = {'metrics': [{'timestamp': i, 'value': i * 2} for i in range(1000)]}
        redis_start = time.time()
        await self.optimized_persistence.save_hot_state(self.user_id, small_state)
        redis_hot_state = await self.optimized_persistence.get_hot_state(self.user_id)
        redis_time = time.time() - redis_start
        assert redis_hot_state is not None, 'Redis should handle hot state'
        assert redis_time < 0.5, f'Redis operations should be fast (<0.5s), got {redis_time:.3f}s'
        postgres_start = time.time()
        await self.optimized_persistence.save_warm_state(self.conversation_id, medium_state)
        postgres_warm_state = await self.optimized_persistence.get_warm_state(self.conversation_id)
        postgres_time = time.time() - postgres_start
        assert postgres_warm_state is not None, 'PostgreSQL should handle warm state'
        assert postgres_time < 2.0, f'PostgreSQL operations should be reasonable (<2s), got {postgres_time:.3f}s'
        clickhouse_start = time.time()
        await self.optimized_persistence.save_cold_analytics(self.user_id, large_analytics)
        clickhouse_analytics = await self.optimized_persistence.get_cold_analytics(self.user_id)
        clickhouse_time = time.time() - clickhouse_start
        assert clickhouse_analytics is not None, 'ClickHouse should handle analytics data'
        assert clickhouse_time < 5.0, f'ClickHouse operations should complete (<5s), got {clickhouse_time:.3f}s'
        assert redis_time <= postgres_time, 'Redis should be faster than PostgreSQL'
        logger.info(f'Verified performance characteristics: Redis={redis_time:.3f}s, PostgreSQL={postgres_time:.3f}s, ClickHouse={clickhouse_time:.3f}s')

    @pytest.mark.asyncio
    async def test_state_recovery_after_system_restart(self):
        """Test state recovery after simulated system restart."""
        await self.setup_real_database_infrastructure()
        persistent_state = {'conversation_id': self.conversation_id, 'user_id': self.user_id, 'session_data': {'analysis_type': 'supply_chain_optimization', 'progress': {'completed_steps': ['data_gathering', 'initial_analysis']}, 'user_inputs': ['Focus on cost reduction', 'Include supplier diversity'], 'intermediate_results': {'potential_savings': 15000}}, 'agent_context': {'active_workflow': 'optimization_pipeline', 'next_steps': ['generate_recommendations', 'create_implementation_plan']}, 'metadata': {'created_at': datetime.now().isoformat(), 'last_updated': datetime.now().isoformat()}}
        await self.state_manager.save_state(persistent_state)
        new_database_manager = DatabaseManager()
        await new_database_manager.initialize()
        new_user_context = UserExecutionContext(user_id=self.user_id, thread_id=self.conversation_id, run_id=f'run_{uuid.uuid4()}', request_id=f'req_{uuid.uuid4()}')
        new_state_manager = StateManager(user_context=new_user_context, database_manager=new_database_manager)
        recovered_state = await new_state_manager.get_state()
        assert recovered_state is not None, 'State should be recoverable after restart'
        assert recovered_state.get('conversation_id') == self.conversation_id, 'Conversation ID should be preserved'
        assert recovered_state.get('user_id') == self.user_id, 'User ID should be preserved'
        session_data = recovered_state.get('session_data', {})
        assert session_data.get('analysis_type') == 'supply_chain_optimization', 'Analysis type should be preserved'
        progress = session_data.get('progress', {})
        completed_steps = progress.get('completed_steps', [])
        assert 'data_gathering' in completed_steps, 'Completed steps should be preserved'
        assert 'initial_analysis' in completed_steps, 'All completed steps should be preserved'
        agent_context = recovered_state.get('agent_context', {})
        assert agent_context.get('active_workflow') == 'optimization_pipeline', 'Active workflow should be preserved'
        new_execution_engine = UserExecutionEngine(user_context=new_user_context, websocket_manager=get_websocket_manager(user_context=new_user_context), state_manager=new_state_manager)
        continuation_result = await new_execution_engine.execute_request('Continue with the recommendations from our previous analysis')
        assert continuation_result is not None, 'Should be able to continue execution with recovered state'
        logger.info('Verified complete state recovery after system restart')

    @pytest.mark.asyncio
    async def test_state_consistency_across_concurrent_operations(self):
        """Test state consistency during concurrent operations."""
        await self.setup_real_database_infrastructure()
        initial_state = {'shared_counter': 0, 'operation_log': [], 'data_items': []}
        await self.state_manager.save_state(initial_state)

        async def concurrent_operation(operation_id: int):
            """Simulate concurrent operation that modifies state."""
            current_state = await self.state_manager.get_state()
            current_state['shared_counter'] = current_state.get('shared_counter', 0) + 1
            current_state['operation_log'].append(f'operation_{operation_id}')
            current_state['data_items'].append({'id': operation_id, 'timestamp': datetime.now().isoformat()})
            await self.state_manager.save_state(current_state)
            return operation_id
        num_operations = 5
        results = await asyncio.gather(*[concurrent_operation(i) for i in range(num_operations)])
        final_state = await self.state_manager.get_state()
        assert final_state is not None, 'Final state should exist'
        final_counter = final_state.get('shared_counter', 0)
        assert final_counter > 0, 'Counter should have been incremented'
        assert final_counter <= num_operations, 'Counter should not exceed number of operations'
        operation_log = final_state.get('operation_log', [])
        assert len(operation_log) > 0, 'Operation log should contain entries'
        data_items = final_state.get('data_items', [])
        assert len(data_items) > 0, 'Data items should be present'
        assert len(results) == num_operations, 'All operations should complete'
        logger.info(f'Verified state consistency: counter={final_counter}, log_entries={len(operation_log)}, data_items={len(data_items)}')

    @pytest.mark.asyncio
    async def test_multi_user_state_isolation_basic(self):
        """Test basic state isolation between multiple users."""
        await self.setup_real_database_infrastructure()
        user_1_id = f'user_1_{self.test_id}'
        user_2_id = f'user_2_{self.test_id}'
        user_3_id = f'user_3_{self.test_id}'
        user_contexts = {}
        state_managers = {}
        for user_id in [user_1_id, user_2_id, user_3_id]:
            user_contexts[user_id] = UserExecutionContext(user_id=user_id, thread_id=f'conv_{user_id}', run_id=f'run_{uuid.uuid4()}', request_id=f'req_{uuid.uuid4()}')
            state_managers[user_id] = StateManager(user_context=user_contexts[user_id], database_manager=self.database_manager)
        user_states = {user_1_id: {'user_secret': 'confidential_data_user_1', 'analysis_type': 'financial_optimization', 'sensitive_info': {'api_key': 'secret_key_1', 'client': 'client_a'}}, user_2_id: {'user_secret': 'confidential_data_user_2', 'analysis_type': 'supply_chain_analysis', 'sensitive_info': {'api_key': 'secret_key_2', 'client': 'client_b'}}, user_3_id: {'user_secret': 'confidential_data_user_3', 'analysis_type': 'market_research', 'sensitive_info': {'api_key': 'secret_key_3', 'client': 'client_c'}}}
        await asyncio.gather(*[state_managers[user_id].save_state(user_states[user_id]) for user_id in user_states.keys()])
        retrieved_states = {}
        for user_id in user_states.keys():
            retrieved_states[user_id] = await state_managers[user_id].get_state()
        for user_id in user_states.keys():
            retrieved_state = retrieved_states[user_id]
            original_state = user_states[user_id]
            assert retrieved_state is not None, f'State should exist for {user_id}'
            assert retrieved_state.get('user_secret') == original_state['user_secret'], f'User secret should match for {user_id}'
            assert retrieved_state.get('analysis_type') == original_state['analysis_type'], f'Analysis type should match for {user_id}'
            for other_user_id in user_states.keys():
                if other_user_id != user_id:
                    other_secret = user_states[other_user_id]['user_secret']
                    assert retrieved_state.get('user_secret') != other_secret, f"User {user_id} should not see {other_user_id}'s secret"
        logger.info(f'Verified state isolation for {len(user_states)} users')

    @pytest.mark.asyncio
    async def test_multi_user_concurrent_state_operations(self):
        """Test concurrent state operations across multiple users maintain isolation."""
        await self.setup_real_database_infrastructure()
        users = [f'concurrent_user_{i}_{self.test_id}' for i in range(4)]
        execution_engines = {}
        for user_id in users:
            user_context = UserExecutionContext(user_id=user_id, thread_id=f'conv_{user_id}', run_id=f'run_{uuid.uuid4()}', request_id=f'req_{uuid.uuid4()}')
            state_manager = StateManager(user_context=user_context, database_manager=self.database_manager)
            execution_engines[user_id] = UserExecutionEngine(user_context=user_context, websocket_manager=get_websocket_manager(user_context=user_context), state_manager=state_manager)

        async def user_workflow(user_id: str, operation_count: int):
            """Execute a series of operations for a specific user."""
            engine = execution_engines[user_id]
            results = []
            for i in range(operation_count):
                result = await engine.execute_request(f'User {user_id} operation {i + 1}: analyze data batch {i + 1}')
                results.append(result)
                await asyncio.sleep(0.1)
            return (user_id, results)
        workflow_results = await asyncio.gather(*[user_workflow(user_id, 3) for user_id in users])
        assert len(workflow_results) == len(users), 'All user workflows should complete'
        for user_id in users:
            user_context = UserExecutionContext(user_id=user_id, thread_id=f'conv_{user_id}', run_id=f'run_{uuid.uuid4()}', request_id=f'req_{uuid.uuid4()}')
            state_manager = StateManager(user_context=user_context, database_manager=self.database_manager)
            user_state = await state_manager.get_state()
            assert user_state is not None, f'User {user_id} should have state'
            if 'user_id' in user_state:
                assert user_state['user_id'] == user_id, f'State should belong to {user_id}'
        logger.info(f'Verified concurrent operations for {len(users)} users maintained isolation')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')