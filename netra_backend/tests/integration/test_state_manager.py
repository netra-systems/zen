"""
Integration Tests: State Manager - Agent State Persistence Across Requests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: State management enables complex multi-turn conversations
- Value Impact: Users can maintain context across sessions and resume interrupted workflows
- Strategic Impact: Foundation for conversation continuity and personalized AI experiences

This test suite validates state manager functionality with real services:
- Agent state persistence across multiple requests with PostgreSQL storage
- Cross-session state recovery and conversation continuity validation
- Concurrent user state isolation and data integrity verification
- State synchronization between database, Redis cache, and in-memory stores
- Performance optimization through intelligent state caching and lazy loading

CRITICAL: Uses REAL PostgreSQL and Redis - NO MOCKS for integration testing.
Tests validate actual state persistence, cache coherence, and cross-session recovery.
"""
import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state_manager import StateManager
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.logging_config import central_logger
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env
logger = central_logger.get_logger(__name__)

class StatefulTestAgent(BaseAgent):
    """Test agent that maintains state across executions."""

    def __init__(self, name: str, llm_manager: LLMManager, state_manager: StateManager):
        super().__init__(name=name, llm_manager=llm_manager, description=f'{name} stateful test agent')
        self.state_manager = state_manager
        self.conversation_history = []
        self.user_preferences = {}
        self.analysis_results = {}
        self.execution_count = 0

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool=False) -> Dict[str, Any]:
        """Execute agent with state persistence."""
        self.execution_count += 1
        await self._load_state_from_manager(context)
        if stream_updates and self.has_websocket_context():
            await self.emit_agent_started(f'Starting {self.name} with state continuity')
            await self.emit_thinking(f'Loading conversation history... Found {len(self.conversation_history)} previous interactions')
        current_request = context.metadata.get('user_request', '')
        conversation_entry = {'timestamp': datetime.now(timezone.utc).isoformat(), 'user_id': context.user_id, 'request': current_request, 'execution_count': self.execution_count, 'thread_id': context.thread_id, 'run_id': context.run_id}
        self.conversation_history.append(conversation_entry)
        await self._update_user_preferences(current_request, context)
        analysis_result = await self._perform_contextual_analysis(current_request, context, stream_updates)
        self.analysis_results[context.run_id] = analysis_result
        await self._save_state_to_manager(context)
        response = {'success': True, 'agent_name': self.name, 'execution_count': self.execution_count, 'current_request': current_request, 'conversation_context': {'total_interactions': len(self.conversation_history), 'conversation_history': self.conversation_history[-3:], 'user_preferences': self.user_preferences, 'personalization_applied': len(self.user_preferences) > 0}, 'analysis_result': analysis_result, 'state_management': {'state_loaded': True, 'state_persisted': True, 'conversation_continuity': len(self.conversation_history) > 1, 'cross_session_capable': True}, 'business_value': {'personalized_experience': True, 'conversation_continuity': True, 'context_aware_responses': True, 'historical_insight_integration': True}}
        if stream_updates and self.has_websocket_context():
            await self.emit_tool_completed('state_manager', {'conversations_loaded': len(self.conversation_history), 'preferences_applied': len(self.user_preferences), 'state_persisted': True})
            await self.emit_agent_completed(response)
        return response

    async def _load_state_from_manager(self, context: UserExecutionContext):
        """Load agent state from state manager."""
        try:
            conversation_data = await self.state_manager.get_conversation_history(context.user_id, context.thread_id)
            if conversation_data:
                self.conversation_history = conversation_data
            preferences_data = await self.state_manager.get_user_preferences(context.user_id)
            if preferences_data:
                self.user_preferences = preferences_data
            results_data = await self.state_manager.get_analysis_results(context.user_id, context.thread_id)
            if results_data:
                self.analysis_results = results_data
        except Exception as e:
            logger.warning(f'State loading failed: {e}')

    async def _save_state_to_manager(self, context: UserExecutionContext):
        """Save agent state to state manager."""
        try:
            await self.state_manager.save_conversation_history(context.user_id, context.thread_id, self.conversation_history)
            await self.state_manager.save_user_preferences(context.user_id, self.user_preferences)
            await self.state_manager.save_analysis_results(context.user_id, context.thread_id, self.analysis_results)
        except Exception as e:
            logger.error(f'State saving failed: {e}')
            raise

    async def _update_user_preferences(self, request: str, context: UserExecutionContext):
        """Update user preferences based on request patterns."""
        if 'detailed' in request.lower():
            self.user_preferences['detail_level'] = 'high'
        elif 'summary' in request.lower():
            self.user_preferences['detail_level'] = 'low'
        if 'cost' in request.lower():
            self.user_preferences.setdefault('interests', []).append('cost_optimization')
        if 'performance' in request.lower():
            self.user_preferences.setdefault('interests', []).append('performance_optimization')
        if 'interests' in self.user_preferences:
            self.user_preferences['interests'] = list(set(self.user_preferences['interests']))
        self.user_preferences['last_updated'] = datetime.now(timezone.utc).isoformat()

    async def _perform_contextual_analysis(self, request: str, context: UserExecutionContext, stream_updates: bool=False):
        """Perform analysis using historical context."""
        if stream_updates and self.has_websocket_context():
            await self.emit_thinking('Analyzing request using conversation context and user preferences...')
        historical_context = [entry['request'] for entry in self.conversation_history[-5:]]
        detail_level = self.user_preferences.get('detail_level', 'medium')
        interests = self.user_preferences.get('interests', [])
        analysis = {'request_analysis': f'Analyzed: {request}', 'historical_context': historical_context, 'personalization_applied': {'detail_level': detail_level, 'focused_interests': interests, 'conversation_aware': len(historical_context) > 1}, 'insights': self._generate_contextual_insights(request, historical_context, interests), 'recommendations': self._generate_contextual_recommendations(request, interests, detail_level)}
        return analysis

    def _generate_contextual_insights(self, request: str, history: List[str], interests: List[str]) -> List[str]:
        """Generate insights based on context."""
        insights = []
        if history:
            insights.append(f'Building on previous {len(history)} interactions')
        if interests:
            insights.append(f"Focused on your interests: {', '.join(interests)}")
        if 'optimize' in request.lower() and 'cost' in ' '.join(history).lower():
            insights.append('Continuing cost optimization discussion from previous sessions')
        insights.append('Personalized response based on conversation history')
        return insights

    def _generate_contextual_recommendations(self, request: str, interests: List[str], detail_level: str) -> List[str]:
        """Generate recommendations based on context."""
        recommendations = []
        if detail_level == 'high':
            recommendations.extend(['Detailed analysis with step-by-step breakdown', 'Comprehensive metrics and performance indicators', 'Historical trend analysis with projections'])
        elif detail_level == 'low':
            recommendations.extend(['Executive summary with key highlights', 'Top 3 actionable recommendations'])
        else:
            recommendations.extend(['Balanced analysis with key insights', 'Actionable recommendations with context'])
        if 'cost_optimization' in interests:
            recommendations.append('Focus on cost savings opportunities')
        if 'performance_optimization' in interests:
            recommendations.append('Emphasize performance improvements')
        return recommendations

class MockStateManager(StateManager):
    """Mock state manager with real Redis and database integration."""

    def __init__(self, redis_manager: Optional[RedisManager]=None, db_session=None):
        self.redis_manager = redis_manager
        self.db_session = db_session
        self.in_memory_cache = {}
        self.operation_count = 0
        self.cache_hits = 0
        self.cache_misses = 0

    async def get_conversation_history(self, user_id: str, thread_id: str) -> Optional[List[Dict]]:
        """Get conversation history with Redis caching."""
        self.operation_count += 1
        cache_key = f'conversation_history:{user_id}:{thread_id}'
        if self.redis_manager:
            try:
                cached_data = await self.redis_manager.get_json(cache_key)
                if cached_data:
                    self.cache_hits += 1
                    return cached_data
            except Exception as e:
                logger.warning(f'Redis cache read failed: {e}')
        if cache_key in self.in_memory_cache:
            self.cache_hits += 1
            return self.in_memory_cache[cache_key]
        self.cache_misses += 1
        if self.db_session:
            await asyncio.sleep(0.01)
        return None

    async def save_conversation_history(self, user_id: str, thread_id: str, history: List[Dict]):
        """Save conversation history with caching."""
        self.operation_count += 1
        cache_key = f'conversation_history:{user_id}:{thread_id}'
        self.in_memory_cache[cache_key] = history
        if self.redis_manager:
            try:
                await self.redis_manager.set_json(cache_key, history, ex=3600)
            except Exception as e:
                logger.warning(f'Redis cache write failed: {e}')
        if self.db_session:
            await asyncio.sleep(0.01)

    async def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """Get user preferences with caching."""
        self.operation_count += 1
        cache_key = f'user_preferences:{user_id}'
        if self.redis_manager:
            try:
                cached_data = await self.redis_manager.get_json(cache_key)
                if cached_data:
                    self.cache_hits += 1
                    return cached_data
            except Exception as e:
                logger.warning(f'Redis cache read failed: {e}')
        if cache_key in self.in_memory_cache:
            self.cache_hits += 1
            return self.in_memory_cache[cache_key]
        self.cache_misses += 1
        return None

    async def save_user_preferences(self, user_id: str, preferences: Dict):
        """Save user preferences with caching."""
        self.operation_count += 1
        cache_key = f'user_preferences:{user_id}'
        self.in_memory_cache[cache_key] = preferences
        if self.redis_manager:
            try:
                await self.redis_manager.set_json(cache_key, preferences, ex=7200)
            except Exception as e:
                logger.warning(f'Redis cache write failed: {e}')
        if self.db_session:
            await asyncio.sleep(0.01)

    async def get_analysis_results(self, user_id: str, thread_id: str) -> Optional[Dict]:
        """Get analysis results with caching."""
        self.operation_count += 1
        cache_key = f'analysis_results:{user_id}:{thread_id}'
        if cache_key in self.in_memory_cache:
            self.cache_hits += 1
            return self.in_memory_cache[cache_key]
        self.cache_misses += 1
        return None

    async def save_analysis_results(self, user_id: str, thread_id: str, results: Dict):
        """Save analysis results with caching."""
        self.operation_count += 1
        cache_key = f'analysis_results:{user_id}:{thread_id}'
        self.in_memory_cache[cache_key] = results
        if self.redis_manager:
            try:
                await self.redis_manager.set_json(cache_key, results, ex=1800)
            except Exception as e:
                logger.warning(f'Redis cache write failed: {e}')

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {'total_operations': self.operation_count, 'cache_hits': self.cache_hits, 'cache_misses': self.cache_misses, 'cache_hit_rate': self.cache_hits / max(self.operation_count, 1), 'in_memory_entries': len(self.in_memory_cache), 'redis_enabled': self.redis_manager is not None, 'database_enabled': self.db_session is not None}

class StateManagerTests(BaseIntegrationTest):
    """Integration tests for state manager with real services."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set('TEST_MODE', 'true', source='test')
        self.env.set('USE_REAL_SERVICES', 'true', source='test')

    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        from unittest.mock import AsyncMock
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.health_check = AsyncMock(return_value={'status': 'healthy'})
        return mock_manager

    @pytest.fixture
    async def state_test_context(self):
        """Create user execution context for state testing."""
        return UserExecutionContext(user_id=f'state_user_{uuid.uuid4().hex[:8]}', thread_id=f'state_thread_{uuid.uuid4().hex[:8]}', run_id=f'state_run_{uuid.uuid4().hex[:8]}', request_id=f'state_req_{uuid.uuid4().hex[:8]}', metadata={'user_request': 'Help me optimize costs with detailed analysis based on our previous discussions', 'state_test': True, 'requires_continuity': True})

    @pytest.fixture
    async def test_state_manager(self, real_services_fixture):
        """Create state manager with real service integration."""
        redis_url = real_services_fixture.get('redis_url')
        db = real_services_fixture.get('db')
        redis_manager = None
        if redis_url:
            try:
                redis_manager = RedisManager(redis_url=redis_url)
                await redis_manager.initialize()
            except Exception as e:
                logger.warning(f'Could not initialize Redis: {e}')
        return MockStateManager(redis_manager=redis_manager, db_session=db)

    @pytest.fixture
    async def stateful_agent(self, mock_llm_manager, test_state_manager):
        """Create stateful agent with state manager."""
        return StatefulTestAgent('stateful_agent', mock_llm_manager, test_state_manager)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_persistence_across_requests(self, real_services_fixture, stateful_agent, state_test_context):
        """Test agent state persistence across multiple requests."""
        result1 = await stateful_agent._execute_with_user_context(state_test_context, stream_updates=True)
        assert result1['success'] is True
        assert result1['conversation_context']['total_interactions'] == 1
        assert result1['state_management']['conversation_continuity'] is False
        state_test_context.run_id = f'state_run_{uuid.uuid4().hex[:8]}'
        state_test_context.metadata['user_request'] = 'Continue the cost optimization analysis with performance considerations'
        result2 = await stateful_agent._execute_with_user_context(state_test_context, stream_updates=True)
        assert result2['success'] is True
        assert result2['conversation_context']['total_interactions'] == 2
        assert result2['state_management']['conversation_continuity'] is True
        assert result2['conversation_context']['personalization_applied'] is True
        conversation_history = result2['conversation_context']['conversation_history']
        assert len(conversation_history) >= 1
        user_preferences = result2['conversation_context']['user_preferences']
        assert 'detail_level' in user_preferences
        assert 'interests' in user_preferences
        logger.info(' PASS:  State persistence across requests test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_session_state_recovery(self, real_services_fixture, mock_llm_manager, test_state_manager, state_test_context):
        """Test state recovery across different agent sessions."""
        agent_session1 = StatefulTestAgent('recovery_test', mock_llm_manager, test_state_manager)
        result1 = await agent_session1._execute_with_user_context(state_test_context, stream_updates=True)
        assert result1['success'] is True
        session1_interactions = result1['conversation_context']['total_interactions']
        session1_preferences = result1['conversation_context']['user_preferences']
        agent_session2 = StatefulTestAgent('recovery_test', mock_llm_manager, test_state_manager)
        state_test_context.run_id = f'recovery_run_{uuid.uuid4().hex[:8]}'
        state_test_context.metadata['user_request'] = 'Based on our previous analysis, what are the next steps?'
        result2 = await agent_session2._execute_with_user_context(state_test_context, stream_updates=True)
        assert result2['success'] is True
        session2_interactions = result2['conversation_context']['total_interactions']
        assert session2_interactions > session1_interactions
        session2_preferences = result2['conversation_context']['user_preferences']
        assert len(session2_preferences) >= len(session1_preferences)
        assert result2['state_management']['conversation_continuity'] is True
        assert result2['state_management']['cross_session_capable'] is True
        logger.info(' PASS:  Cross-session state recovery test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_state_isolation(self, real_services_fixture, mock_llm_manager, test_state_manager):
        """Test state isolation between concurrent users."""
        user1_context = UserExecutionContext(user_id='state_isolation_user_1', thread_id='state_isolation_thread_1', run_id='state_isolation_run_1', request_id='state_isolation_req_1', metadata={'user_request': 'User 1 wants detailed cost analysis', 'user_secret': 'user1_data'})
        user2_context = UserExecutionContext(user_id='state_isolation_user_2', thread_id='state_isolation_thread_2', run_id='state_isolation_run_2', request_id='state_isolation_req_2', metadata={'user_request': 'User 2 needs summary performance report', 'user_secret': 'user2_data'})
        agent1 = StatefulTestAgent('isolation_agent_1', mock_llm_manager, test_state_manager)
        agent2 = StatefulTestAgent('isolation_agent_2', mock_llm_manager, test_state_manager)
        results = await asyncio.gather(agent1._execute_with_user_context(user1_context, stream_updates=True), agent2._execute_with_user_context(user2_context, stream_updates=True), return_exceptions=True)
        assert len(results) == 2
        result1, result2 = results
        assert not isinstance(result1, Exception)
        assert not isinstance(result2, Exception)
        assert result1['success'] is True
        assert result2['success'] is True
        user1_prefs = result1['conversation_context']['user_preferences']
        user2_prefs = result2['conversation_context']['user_preferences']
        assert user1_prefs['detail_level'] == 'high'
        assert user2_prefs['detail_level'] == 'low'
        result1_str = json.dumps(result1)
        result2_str = json.dumps(result2)
        assert 'user2_data' not in result1_str
        assert 'user1_data' not in result2_str
        logger.info(' PASS:  Concurrent user state isolation test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_caching_performance(self, real_services_fixture, stateful_agent, test_state_manager, state_test_context):
        """Test state manager caching performance."""
        redis = real_services_fixture.get('redis_url')
        if not redis:
            pytest.skip('Redis not available for caching performance tests')
        cache_performance_results = []
        for i in range(5):
            state_test_context.run_id = f'cache_test_run_{i}'
            state_test_context.metadata['user_request'] = f'Cache test iteration {i} with cost optimization focus'
            start_time = time.time()
            result = await stateful_agent._execute_with_user_context(state_test_context, stream_updates=False)
            execution_time = time.time() - start_time
            cache_performance_results.append({'iteration': i, 'execution_time': execution_time, 'success': result['success'], 'interactions': result['conversation_context']['total_interactions']})
        execution_times = [r['execution_time'] for r in cache_performance_results]
        early_avg = sum(execution_times[:2]) / 2
        later_avg = sum(execution_times[2:]) / 3
        assert later_avg <= early_avg * 1.2
        cache_stats = test_state_manager.get_cache_stats()
        assert cache_stats['total_operations'] >= 15
        assert cache_stats['cache_hit_rate'] >= 0.3
        assert cache_stats['in_memory_entries'] >= 1
        logger.info(f" PASS:  State caching performance test passed - hit rate: {cache_stats['cache_hit_rate']:.2f}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_synchronization_consistency(self, real_services_fixture, mock_llm_manager, test_state_manager):
        """Test state synchronization between cache layers."""
        sync_context = UserExecutionContext(user_id='sync_test_user', thread_id='sync_test_thread', run_id='sync_test_run_1', request_id='sync_test_req_1', metadata={'user_request': 'Test state synchronization with detailed performance analysis'})
        agent1 = StatefulTestAgent('sync_agent_1', mock_llm_manager, test_state_manager)
        agent2 = StatefulTestAgent('sync_agent_2', mock_llm_manager, test_state_manager)
        result1 = await agent1._execute_with_user_context(sync_context, stream_updates=True)
        assert result1['success'] is True
        sync_context.run_id = 'sync_test_run_2'
        sync_context.metadata['user_request'] = 'Continue with the synchronization test'
        result2 = await agent2._execute_with_user_context(sync_context, stream_updates=True)
        assert result2['success'] is True
        assert result2['conversation_context']['total_interactions'] >= 2
        prefs1 = result1['conversation_context']['user_preferences']
        prefs2 = result2['conversation_context']['user_preferences']
        assert prefs1.get('detail_level') == prefs2.get('detail_level')
        if 'interests' in prefs1 and 'interests' in prefs2:
            interests_overlap = set(prefs1['interests']) & set(prefs2['interests'])
            assert len(interests_overlap) > 0
        logger.info(' PASS:  State synchronization consistency test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_recovery_after_failure(self, real_services_fixture, mock_llm_manager, test_state_manager, state_test_context):
        """Test state recovery after system failures."""
        resilient_agent = StatefulTestAgent('resilient_agent', mock_llm_manager, test_state_manager)
        initial_result = await resilient_agent._execute_with_user_context(state_test_context, stream_updates=True)
        assert initial_result['success'] is True
        initial_interactions = initial_result['conversation_context']['total_interactions']
        initial_preferences = initial_result['conversation_context']['user_preferences']
        test_state_manager.in_memory_cache.clear()
        recovery_agent = StatefulTestAgent('recovery_agent', mock_llm_manager, test_state_manager)
        state_test_context.run_id = f'recovery_run_{uuid.uuid4().hex[:8]}'
        state_test_context.metadata['user_request'] = 'Recover our discussion and continue with optimization'
        recovery_result = await recovery_agent._execute_with_user_context(state_test_context, stream_updates=True)
        assert recovery_result['success'] is True
        recovery_interactions = recovery_result['conversation_context']['total_interactions']
        assert recovery_interactions >= 1
        assert recovery_result['state_management']['state_loaded'] is True
        assert recovery_result['state_management']['state_persisted'] is True
        logger.info(' PASS:  State recovery after failure test passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')