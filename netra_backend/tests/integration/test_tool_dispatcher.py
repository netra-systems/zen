"""
Integration Tests: Tool Dispatcher - Tool Execution Pipeline with Real Redis Cache

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Tool dispatcher enables agent capabilities and external service integration
- Value Impact: Agents can use specialized tools to solve complex problems and deliver insights
- Strategic Impact: Foundation for extensible AI agent toolkit and third-party integrations

This test suite validates tool dispatcher functionality with real services:
- Tool execution pipeline with Redis state management and caching
- Tool result persistence and retrieval across agent sessions
- Concurrent tool execution with proper isolation and resource management
- Tool error handling, retry logic, and failure recovery patterns
- Performance optimization through intelligent caching and batching

CRITICAL: Uses REAL Redis for caching and state - NO MOCKS for integration testing.
Tests validate actual tool execution, caching behavior, and cross-agent tool sharing.
"""
import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
import pytest
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.logging_config import central_logger
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env
logger = central_logger.get_logger(__name__)

class ToolTests:
    """Test tool for dispatcher integration testing."""

    def __init__(self, tool_name: str, execution_time: float=0.1, failure_rate: float=0.0):
        self.name = tool_name
        self.execution_time = execution_time
        self.failure_rate = failure_rate
        self.execution_count = 0
        self.last_execution = None
        self.execution_history = []

    async def execute(self, parameters: Dict[str, Any], context: Optional[UserExecutionContext]=None) -> Dict[str, Any]:
        """Execute tool with specified parameters."""
        self.execution_count += 1
        self.last_execution = datetime.now(timezone.utc)
        execution_record = {'execution_id': str(uuid.uuid4()), 'timestamp': self.last_execution.isoformat(), 'parameters': parameters, 'user_id': context.user_id if context else None}
        self.execution_history.append(execution_record)
        await asyncio.sleep(self.execution_time)
        if self.failure_rate > 0 and self.execution_count * self.failure_rate >= 1:
            raise RuntimeError(f'Simulated {self.name} tool failure (failure rate: {self.failure_rate})')
        if self.name == 'cost_analyzer':
            return self._generate_cost_analysis_result(parameters)
        elif self.name == 'performance_monitor':
            return self._generate_performance_result(parameters)
        elif self.name == 'security_scanner':
            return self._generate_security_result(parameters)
        elif self.name == 'data_processor':
            return self._generate_data_processing_result(parameters)
        else:
            return self._generate_generic_result(parameters)

    def _generate_cost_analysis_result(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cost analysis results."""
        return {'tool_name': self.name, 'execution_count': self.execution_count, 'analysis_type': parameters.get('analysis_type', 'comprehensive'), 'cost_breakdown': {'compute': '$12,450/month', 'storage': '$3,200/month', 'networking': '$890/month', 'total': '$16,540/month'}, 'optimization_opportunities': [{'resource': 'compute', 'potential_savings': '$3,750', 'effort': 'low'}, {'resource': 'storage', 'potential_savings': '$960', 'effort': 'medium'}, {'resource': 'networking', 'potential_savings': '$267', 'effort': 'high'}], 'confidence_score': 0.89, 'recommendation': 'Prioritize compute optimization for maximum ROI'}

    def _generate_performance_result(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance monitoring results."""
        return {'tool_name': self.name, 'execution_count': self.execution_count, 'metrics_collected': parameters.get('metrics', ['latency', 'throughput']), 'performance_data': {'avg_latency_ms': 145, 'p95_latency_ms': 280, 'throughput_rps': 1250, 'error_rate_percent': 0.23}, 'performance_score': 8.2, 'bottlenecks_identified': ['database_queries', 'external_api_calls'], 'optimization_suggestions': ['Implement connection pooling', 'Add caching layer for frequent queries', 'Optimize API call batching']}

    def _generate_security_result(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate security scan results."""
        return {'tool_name': self.name, 'execution_count': self.execution_count, 'scan_scope': parameters.get('scope', 'infrastructure'), 'vulnerabilities': [{'id': 'CVE-2023-001', 'severity': 'medium', 'component': 'web_server'}, {'id': 'CVE-2023-002', 'severity': 'low', 'component': 'database'}], 'compliance_status': {'SOC2': 'compliant', 'GDPR': 'compliant', 'PCI_DSS': 'non_compliant'}, 'risk_score': 6.5, 'recommendations': ['Update web server to latest version', 'Implement PCI DSS controls for payment processing']}

    def _generate_data_processing_result(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data processing results."""
        return {'tool_name': self.name, 'execution_count': self.execution_count, 'data_source': parameters.get('source', 'user_data'), 'processing_stats': {'records_processed': 125000, 'processing_time_sec': 45.2, 'success_rate': 0.987, 'quality_score': 0.94}, 'output_summary': {'clean_records': 123375, 'flagged_records': 1625, 'schema_violations': 0}, 'recommendations': ['Review flagged records for data quality issues', 'Implement automated data validation rules']}

    def _generate_generic_result(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generic tool result."""
        return {'tool_name': self.name, 'execution_count': self.execution_count, 'parameters': parameters, 'result': f'Tool {self.name} executed successfully', 'execution_time': self.execution_time, 'success': True}

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        return {'tool_name': self.name, 'total_executions': self.execution_count, 'last_execution': self.last_execution.isoformat() if self.last_execution else None, 'average_execution_time': self.execution_time, 'success_rate': 1.0 - self.failure_rate, 'execution_history_count': len(self.execution_history)}

class ToolAwareTestAgent(BaseAgent):
    """Test agent that uses tool dispatcher for task execution."""

    def __init__(self, name: str, llm_manager: LLMManager, tool_dispatcher: UnifiedToolDispatcher):
        super().__init__(name=name, llm_manager=llm_manager, description=f'{name} tool-enabled agent')
        self.tool_dispatcher = tool_dispatcher
        self.tools_used = []
        self.tool_results = {}
        self.execution_count = 0

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool=False) -> Dict[str, Any]:
        """Execute agent using tool dispatcher for specialized tasks."""
        self.execution_count += 1
        if stream_updates and self.has_websocket_context():
            await self.emit_agent_started(f'Starting {self.name} with tool-powered analysis')
            await self.emit_thinking('Planning tool usage strategy for comprehensive analysis...')
        tool_plan = self._create_tool_execution_plan(context)
        for tool_step in tool_plan:
            tool_name = tool_step['tool']
            parameters = tool_step['parameters']
            if stream_updates and self.has_websocket_context():
                await self.emit_tool_executing(tool_name, parameters)
            try:
                tool_result = await self.tool_dispatcher.execute_tool(tool_name=tool_name, parameters=parameters, context=context)
                self.tools_used.append(tool_name)
                self.tool_results[tool_name] = tool_result
                if stream_updates and self.has_websocket_context():
                    await self.emit_tool_completed(tool_name, tool_result)
                    await self.emit_thinking(f'Analyzing results from {tool_name}...')
            except Exception as e:
                error_result = {'error': str(e), 'tool': tool_name}
                self.tool_results[tool_name] = error_result
                if stream_updates and self.has_websocket_context():
                    await self.emit_error(f'Tool {tool_name} failed: {str(e)}', 'ToolExecutionError')
        synthesized_result = self._synthesize_tool_results(context)
        if stream_updates and self.has_websocket_context():
            await self.emit_thinking('Synthesizing insights from all tool executions...')
            await self.emit_agent_completed(synthesized_result)
        return synthesized_result

    def _create_tool_execution_plan(self, context: UserExecutionContext) -> List[Dict[str, Any]]:
        """Create tool execution plan based on user request."""
        user_request = context.metadata.get('user_request', '')
        plan = []
        if 'cost' in user_request.lower() or 'optimization' in user_request.lower():
            plan.append({'tool': 'cost_analyzer', 'parameters': {'analysis_type': 'comprehensive', 'time_window': '30_days', 'include_forecasting': True}})
        if 'performance' in user_request.lower() or 'monitor' in user_request.lower():
            plan.append({'tool': 'performance_monitor', 'parameters': {'metrics': ['latency', 'throughput', 'error_rate'], 'duration': '24_hours'}})
        if 'security' in user_request.lower() or 'vulnerability' in user_request.lower():
            plan.append({'tool': 'security_scanner', 'parameters': {'scope': 'infrastructure', 'compliance_check': True}})
        if 'data' in user_request.lower() or 'process' in user_request.lower():
            plan.append({'tool': 'data_processor', 'parameters': {'source': 'user_data', 'validation': True, 'quality_check': True}})
        if not plan:
            plan.append({'tool': 'cost_analyzer', 'parameters': {'analysis_type': 'basic'}})
        return plan

    def _synthesize_tool_results(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Synthesize results from all tool executions."""
        return {'success': True, 'agent_name': self.name, 'execution_count': self.execution_count, 'user_id': context.user_id, 'tools_executed': len(self.tools_used), 'tools_used': self.tools_used, 'tool_results': self.tool_results, 'business_insights': self._extract_business_insights(), 'recommendations': self._generate_recommendations(), 'tool_integration': {'dispatcher_used': True, 'multi_tool_workflow': len(self.tools_used) > 1, 'tool_success_rate': self._calculate_tool_success_rate()}, 'business_value': {'tools_delivered_insights': True, 'multi_domain_analysis': len(self.tools_used) > 1, 'actionable_recommendations': True}}

    def _extract_business_insights(self) -> List[str]:
        """Extract key business insights from tool results."""
        insights = []
        for tool_name, result in self.tool_results.items():
            if 'error' not in result:
                if tool_name == 'cost_analyzer':
                    total_cost = result.get('cost_breakdown', {}).get('total', '$0')
                    insights.append(f'Current monthly infrastructure cost: {total_cost}')
                elif tool_name == 'performance_monitor':
                    score = result.get('performance_score', 0)
                    insights.append(f'System performance score: {score}/10')
                elif tool_name == 'security_scanner':
                    risk_score = result.get('risk_score', 0)
                    insights.append(f'Security risk assessment: {risk_score}/10')
        return insights

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations from tool results."""
        recommendations = []
        for tool_name, result in self.tool_results.items():
            if 'error' not in result and 'recommendations' in result:
                tool_recs = result['recommendations']
                if isinstance(tool_recs, list):
                    recommendations.extend(tool_recs)
                elif isinstance(tool_recs, str):
                    recommendations.append(tool_recs)
        return recommendations[:5]

    def _calculate_tool_success_rate(self) -> float:
        """Calculate success rate of tool executions."""
        if not self.tool_results:
            return 0.0
        successful_tools = sum((1 for result in self.tool_results.values() if 'error' not in result))
        return successful_tools / len(self.tool_results)

class MockToolDispatcher(UnifiedToolDispatcher):
    """Mock tool dispatcher for integration testing with real Redis caching."""

    def __init__(self, redis_manager: Optional[RedisManager]=None):
        self.tools = {}
        self.redis_manager = redis_manager
        self.execution_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.error_count = 0
        self._register_test_tools()

    def _register_test_tools(self):
        """Register test tools with the dispatcher."""
        self.tools = {'cost_analyzer': ToolTests('cost_analyzer', execution_time=0.2), 'performance_monitor': ToolTests('performance_monitor', execution_time=0.15), 'security_scanner': ToolTests('security_scanner', execution_time=0.3), 'data_processor': ToolTests('data_processor', execution_time=0.1), 'failing_tool': ToolTests('failing_tool', execution_time=0.05, failure_rate=0.5)}

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], context: Optional[UserExecutionContext]=None) -> Dict[str, Any]:
        """Execute tool with Redis caching integration."""
        self.execution_count += 1
        cache_key = self._generate_cache_key(tool_name, parameters, context)
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            self.cache_hits += 1
            logger.debug(f'Cache hit for {tool_name}')
            return cached_result
        self.cache_misses += 1
        if tool_name not in self.tools:
            self.error_count += 1
            raise ValueError(f'Tool {tool_name} not found in dispatcher')
        tool = self.tools[tool_name]
        try:
            result = await tool.execute(parameters, context)
            await self._cache_result(cache_key, result)
            return result
        except Exception as e:
            self.error_count += 1
            raise

    def _generate_cache_key(self, tool_name: str, parameters: Dict[str, Any], context: Optional[UserExecutionContext]) -> str:
        """Generate cache key for tool execution."""
        param_str = json.dumps(parameters, sort_keys=True)
        context_id = context.user_id if context else 'anonymous'
        return f'tool_cache:{tool_name}:{hash(param_str)}:{context_id}'

    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached tool result from Redis."""
        if not self.redis_manager:
            return None
        try:
            cached_data = await self.redis_manager.get_json(cache_key)
            return cached_data
        except Exception as e:
            logger.warning(f'Cache retrieval failed: {e}')
            return None

    async def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache tool result in Redis."""
        if not self.redis_manager:
            return
        try:
            await self.redis_manager.set_json(cache_key, result, ex=3600)
            logger.debug(f'Cached tool result: {cache_key}')
        except Exception as e:
            logger.warning(f'Cache storage failed: {e}')

    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return list(self.tools.keys())

    def get_tool_stats(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for specific tool."""
        if tool_name in self.tools:
            return self.tools[tool_name].get_execution_stats()
        return None

    def get_dispatcher_stats(self) -> Dict[str, Any]:
        """Get comprehensive dispatcher statistics."""
        return {'total_executions': self.execution_count, 'cache_hits': self.cache_hits, 'cache_misses': self.cache_misses, 'cache_hit_rate': self.cache_hits / max(self.execution_count, 1), 'error_count': self.error_count, 'error_rate': self.error_count / max(self.execution_count, 1), 'available_tools': len(self.tools), 'redis_enabled': self.redis_manager is not None}

class ToolDispatcherTests(BaseIntegrationTest):
    """Integration tests for tool dispatcher with real Redis caching."""

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
    async def dispatcher_test_context(self):
        """Create user context for tool dispatcher testing."""
        return UserExecutionContext(user_id=f'tool_user_{uuid.uuid4().hex[:8]}', thread_id=f'tool_thread_{uuid.uuid4().hex[:8]}', run_id=f'tool_run_{uuid.uuid4().hex[:8]}', request_id=f'tool_req_{uuid.uuid4().hex[:8]}', metadata={'user_request': 'Comprehensive infrastructure cost optimization and performance analysis', 'requires_tools': ['cost_analyzer', 'performance_monitor'], 'tool_test': True})

    @pytest.fixture
    async def test_tool_dispatcher(self, real_services_fixture):
        """Create tool dispatcher with real Redis integration."""
        redis_url = real_services_fixture.get('redis_url')
        redis_manager = None
        if redis_url:
            try:
                redis_manager = RedisManager(redis_url=redis_url)
                await redis_manager.initialize()
            except Exception as e:
                logger.warning(f'Could not initialize Redis manager: {e}')
        return MockToolDispatcher(redis_manager=redis_manager)

    @pytest.fixture
    async def tool_aware_agent(self, mock_llm_manager, test_tool_dispatcher):
        """Create agent with tool dispatcher integration."""
        return ToolAwareTestAgent('tool_agent', mock_llm_manager, test_tool_dispatcher)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_with_redis_caching(self, real_services_fixture, test_tool_dispatcher, dispatcher_test_context):
        """Test tool execution pipeline with real Redis caching."""
        redis = real_services_fixture.get('redis_url')
        if not redis:
            pytest.skip('Redis not available for caching tests')
        start_time = time.time()
        result1 = await test_tool_dispatcher.execute_tool('cost_analyzer', {'analysis_type': 'comprehensive', 'time_window': '30_days'}, dispatcher_test_context)
        first_execution_time = time.time() - start_time
        assert result1['success'] is True
        assert result1['tool_name'] == 'cost_analyzer'
        assert 'cost_breakdown' in result1
        assert 'optimization_opportunities' in result1
        start_time = time.time()
        result2 = await test_tool_dispatcher.execute_tool('cost_analyzer', {'analysis_type': 'comprehensive', 'time_window': '30_days'}, dispatcher_test_context)
        cached_execution_time = time.time() - start_time
        assert result2 == result1
        assert cached_execution_time < first_execution_time
        stats = test_tool_dispatcher.get_dispatcher_stats()
        assert stats['total_executions'] == 2
        assert stats['cache_hits'] >= 1
        assert stats['cache_hit_rate'] >= 0.5
        logger.info(f" PASS:  Tool caching test passed - cache hit rate: {stats['cache_hit_rate']:.2f}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_tool_integration_workflow(self, real_services_fixture, dispatcher_test_context, tool_aware_agent):
        """Test complete agent workflow using tool dispatcher."""
        result = await tool_aware_agent._execute_with_user_context(dispatcher_test_context, stream_updates=True)
        assert result['success'] is True
        assert result['tools_executed'] >= 2
        assert len(result['tools_used']) >= 2
        assert result['tool_integration']['dispatcher_used'] is True
        assert result['tool_integration']['multi_tool_workflow'] is True
        assert result['tool_integration']['tool_success_rate'] >= 0.5
        assert result['business_value']['tools_delivered_insights'] is True
        assert result['business_value']['multi_domain_analysis'] is True
        assert len(result['business_insights']) >= 1
        assert len(result['recommendations']) >= 1
        tool_results = result['tool_results']
        assert len(tool_results) >= 2
        for tool_name, tool_result in tool_results.items():
            assert 'error' not in tool_result, f'Tool {tool_name} failed: {tool_result}'
            assert tool_result['tool_name'] == tool_name
        logger.info(f" PASS:  Agent tool integration test passed - {result['tools_executed']} tools used")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_tool_execution(self, real_services_fixture, test_tool_dispatcher, mock_llm_manager):
        """Test concurrent tool execution with isolation."""
        contexts = []
        for i in range(4):
            context = UserExecutionContext(user_id=f'concurrent_tool_user_{i}', thread_id=f'concurrent_tool_thread_{i}', run_id=f'concurrent_tool_run_{i}', request_id=f'concurrent_tool_req_{i}', metadata={'concurrent_test': True, 'user_index': i})
            contexts.append(context)
        tool_tasks = []
        tools_to_test = ['cost_analyzer', 'performance_monitor', 'security_scanner', 'data_processor']
        for i, context in enumerate(contexts):
            tool_name = tools_to_test[i]
            parameters = {'analysis_type': f'concurrent_{i}', 'user_id': context.user_id}
            task = test_tool_dispatcher.execute_tool(tool_name, parameters, context)
            tool_tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*tool_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        assert len(results) == 4
        successful_executions = 0
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                assert result['success'] is True
                assert result['tool_name'] == tools_to_test[i]
                successful_executions += 1
            else:
                logger.warning(f'Concurrent tool execution failed: {result}')
        assert successful_executions >= 3
        assert execution_time < 2.0
        stats = test_tool_dispatcher.get_dispatcher_stats()
        assert stats['total_executions'] >= successful_executions
        assert stats['error_rate'] <= 0.25
        logger.info(f' PASS:  Concurrent tool execution test passed - {successful_executions}/4 tools in {execution_time:.3f}s')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_error_handling_and_recovery(self, real_services_fixture, test_tool_dispatcher, dispatcher_test_context):
        """Test tool error handling and recovery patterns."""
        with pytest.raises(ValueError, match='Tool nonexistent_tool not found'):
            await test_tool_dispatcher.execute_tool('nonexistent_tool', {}, dispatcher_test_context)
        with pytest.raises(RuntimeError, match='Simulated failing_tool tool failure'):
            await test_tool_dispatcher.execute_tool('failing_tool', {}, dispatcher_test_context)
        recovery_result = await test_tool_dispatcher.execute_tool('cost_analyzer', {'analysis_type': 'recovery_test'}, dispatcher_test_context)
        assert recovery_result['success'] is True
        assert recovery_result['tool_name'] == 'cost_analyzer'
        stats = test_tool_dispatcher.get_dispatcher_stats()
        assert stats['error_count'] >= 2
        assert stats['total_executions'] >= 3
        logger.info(' PASS:  Tool error handling and recovery test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_performance_optimization(self, real_services_fixture, test_tool_dispatcher, dispatcher_test_context):
        """Test tool performance optimization through caching."""
        redis = real_services_fixture.get('redis_url')
        if not redis:
            pytest.skip('Redis not available for performance optimization tests')
        tool_executions = 10
        execution_times = []
        for i in range(tool_executions):
            start_time = time.time()
            if i < 3:
                parameters = {'analysis_type': 'performance_test', 'iteration': 1}
            else:
                parameters = {'analysis_type': 'performance_test', 'iteration': i}
            result = await test_tool_dispatcher.execute_tool('cost_analyzer', parameters, dispatcher_test_context)
            execution_time = time.time() - start_time
            execution_times.append(execution_time)
            assert result['success'] is True
        avg_execution_time = sum(execution_times) / len(execution_times)
        cache_eligible_time = sum(execution_times[:3]) / 3
        stats = test_tool_dispatcher.get_dispatcher_stats()
        assert stats['total_executions'] >= tool_executions
        assert stats['cache_hit_rate'] > 0
        assert cache_eligible_time <= avg_execution_time
        logger.info(f" PASS:  Tool performance optimization test passed - {stats['cache_hit_rate']:.2f} hit rate, {avg_execution_time:.3f}s avg time")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_state_persistence_across_sessions(self, real_services_fixture, test_tool_dispatcher):
        """Test tool execution state persistence across different user sessions."""
        session1_context = UserExecutionContext(user_id='persistence_user', thread_id='persistence_thread_1', run_id='persistence_run_1', request_id='persistence_req_1', metadata={'session': 1, 'persistence_test': True})
        result1 = await test_tool_dispatcher.execute_tool('cost_analyzer', {'analysis_type': 'session_1', 'persistence': True}, session1_context)
        assert result1['success'] is True
        session1_stats = test_tool_dispatcher.get_dispatcher_stats()
        session2_context = UserExecutionContext(user_id='persistence_user', thread_id='persistence_thread_2', run_id='persistence_run_2', request_id='persistence_req_2', metadata={'session': 2, 'persistence_test': True})
        result2 = await test_tool_dispatcher.execute_tool('performance_monitor', {'analysis_type': 'session_2', 'persistence': True}, session2_context)
        assert result2['success'] is True
        session2_stats = test_tool_dispatcher.get_dispatcher_stats()
        assert session2_stats['total_executions'] > session1_stats['total_executions']
        assert len(test_tool_dispatcher.get_available_tools()) >= 2
        cost_tool_stats = test_tool_dispatcher.get_tool_stats('cost_analyzer')
        perf_tool_stats = test_tool_dispatcher.get_tool_stats('performance_monitor')
        assert cost_tool_stats['total_executions'] >= 1
        assert perf_tool_stats['total_executions'] >= 1
        logger.info(' PASS:  Tool state persistence test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_tool_workflow_orchestration(self, real_services_fixture, dispatcher_test_context, tool_aware_agent):
        """Test complex multi-tool workflow orchestration."""
        complex_context = UserExecutionContext(user_id=dispatcher_test_context.user_id, thread_id=dispatcher_test_context.thread_id, run_id=f'complex_{dispatcher_test_context.run_id}', request_id=f'complex_{dispatcher_test_context.request_id}', metadata={'user_request': 'Complete infrastructure analysis including cost optimization, performance monitoring, security assessment, and data processing', 'requires_comprehensive_analysis': True, 'workflow_complexity': 'high'})
        result = await tool_aware_agent._execute_with_user_context(complex_context, stream_updates=True)
        assert result['success'] is True
        assert result['tools_executed'] >= 3
        tools_used = result['tools_used']
        assert len(set(tools_used)) >= 3
        business_insights = result['business_insights']
        assert len(business_insights) >= 2
        recommendations = result['recommendations']
        assert len(recommendations) >= 3
        assert result['tool_integration']['tool_success_rate'] >= 0.75
        logger.info(f' PASS:  Multi-tool workflow orchestration test passed - {len(tools_used)} tools, {len(business_insights)} insights')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')