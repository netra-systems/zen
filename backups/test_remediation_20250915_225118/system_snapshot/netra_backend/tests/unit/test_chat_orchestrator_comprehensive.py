"""
Comprehensive Unit Test Suite for Phase 2: Chat Orchestrator Components

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure 100% reliability of Chat Orchestrator - the CRITICAL $500K+ ARR component
- Value Impact: Chat Orchestrator delivers 90% of our business value through AI-powered interactions
- Strategic Impact: MISSION CRITICAL - Any Chat Orchestrator failure directly impacts revenue

This test suite covers:
1. ChatOrchestrator main orchestration logic (5 tests)
2. IntentClassifier business logic (4 tests)  
3. ExecutionPlanner strategic planning (3 tests)
4. PipelineExecutor workflow execution (4 tests)
5. TraceLogger transparency features (3 tests)
6. ConfidenceManager decision logic (3 tests)
7. QualityEvaluator assessment logic (4 tests)

TOTAL: 26 comprehensive unit tests protecting core business value delivery
"""
import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from typing import Dict, Any, List, Tuple
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RequestID
from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentClassifier, IntentType
from netra_backend.app.agents.chat_orchestrator.execution_planner import ExecutionPlanner
from netra_backend.app.agents.chat_orchestrator.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.chat_orchestrator.trace_logger import TraceLogger
from netra_backend.app.agents.chat_orchestrator.confidence_manager import ConfidenceManager, ConfidenceLevel
from netra_backend.app.agents.chat_orchestrator.quality_evaluator import QualityEvaluator, EvaluationCriteria
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.quality_types import QualityMetrics, QualityLevel

class ChatOrchestratorTests(BaseIntegrationTest):
    """Test ChatOrchestrator main orchestration logic - MISSION CRITICAL."""

    def setup_method(self):
        """Set up test fixtures for each test."""
        super().setup_method()
        self.mock_db_session = AsyncMock()
        self.mock_llm_manager = AsyncMock()
        self.mock_websocket_manager = AsyncMock()
        self.mock_tool_dispatcher = Mock()
        self.mock_cache_manager = Mock()
        with patch.object(ChatOrchestrator, '_init_helper_modules'):
            self.orchestrator = ChatOrchestrator(db_session=self.mock_db_session, llm_manager=self.mock_llm_manager, websocket_manager=self.mock_websocket_manager, tool_dispatcher=self.mock_tool_dispatcher, cache_manager=self.mock_cache_manager, semantic_cache_enabled=True)
        self.orchestrator.intent_classifier = Mock()
        self.orchestrator.intent_classifier.classify = AsyncMock()
        self.orchestrator.confidence_manager = Mock()
        self.orchestrator.pipeline_executor = Mock()
        self.orchestrator.pipeline_executor.execute = AsyncMock()
        self.orchestrator.trace_logger = Mock()
        self.orchestrator.trace_logger.log = AsyncMock()
        self.orchestrator.trace_logger.get_compressed_trace = Mock(return_value=['trace_line'])
        self.orchestrator.trace_logger.traces = []
        self.orchestrator._should_use_cache = Mock(return_value=False)
        self.orchestrator._try_semantic_cache = AsyncMock(return_value=None)
        self.orchestrator._cache_if_appropriate = AsyncMock()
        self.orchestrator._check_cache = AsyncMock(return_value=None)
        self.orchestrator._execute_pipeline = AsyncMock()
        self.orchestrator._format_final_response = Mock()
        self.orchestrator.registry = Mock()
        self.orchestrator.registry.agents = {}
        self.mock_context = Mock(spec=ExecutionContext)
        self.mock_context.request_id = 'req-12345'
        self.mock_context.state = Mock()
        self.mock_context.state.user_request = 'Optimize my AWS costs'

    @pytest.mark.unit
    async def test_orchestrator_nacis_execution_flow_business_value(self):
        """Test complete NACIS orchestration delivers business value."""
        self.orchestrator.intent_classifier.classify = AsyncMock(return_value=(IntentType.OPTIMIZATION_ADVICE, 0.85))
        pipeline_result = {'intent': 'optimization', 'data': {'recommendations': ['Use reserved instances', 'Right-size EC2'], 'potential_savings': {'monthly_amount': 5000}}, 'steps': [{'agent': 'researcher', 'result': 'success'}]}
        self.orchestrator.pipeline_executor.execute = AsyncMock(return_value=pipeline_result)
        result = await self.orchestrator.execute_core_logic(self.mock_context)
        assert result is not None
        self.orchestrator.intent_classifier.classify.assert_called_once()
        self.orchestrator._execute_pipeline.assert_called_once()

    @pytest.mark.unit
    async def test_orchestrator_cache_hit_efficiency_business_value(self):
        """Test cache hit provides instant business value."""
        cached_data = {'cached_data': 'Previous optimization result'}
        self.orchestrator._check_cache = AsyncMock(return_value=cached_data)
        self.orchestrator._format_cached_response = Mock(return_value={'source': 'cache', 'confidence': 1.0, 'data': cached_data, 'trace': ['cache_hit_trace']})
        self.orchestrator.intent_classifier.classify = AsyncMock(return_value=(IntentType.TCO_ANALYSIS, 0.9))
        result = await self.orchestrator.execute_core_logic(self.mock_context)
        assert result['source'] == 'cache'
        assert result['confidence'] == 1.0
        assert result['data']['cached_data'] == 'Previous optimization result'
        assert 'trace' in result

    @pytest.mark.unit
    async def test_orchestrator_error_recovery_business_continuity(self):
        """Test error recovery maintains business continuity."""
        self.orchestrator.intent_classifier.classify = AsyncMock(side_effect=Exception('LLM service unavailable'))
        result = await self.orchestrator.execute_core_logic(self.mock_context)
        assert 'error' in result
        assert 'LLM service unavailable' in result['error']
        assert 'trace' in result
        self.orchestrator.trace_logger.log.assert_called()

    @pytest.mark.unit
    async def test_orchestrator_confidence_threshold_routing(self):
        """Test confidence-based routing optimizes cost and quality."""
        self.orchestrator.intent_classifier.classify = AsyncMock(return_value=(IntentType.TECHNICAL_QUESTION, 0.4))
        self.orchestrator._should_use_cache = Mock(return_value=False)
        pipeline_result = {'intent': 'technical', 'data': {'answer': 'Basic technical response'}, 'steps': []}
        self.orchestrator.pipeline_executor.execute = AsyncMock(return_value=pipeline_result)
        result = await self.orchestrator.execute_core_logic(self.mock_context)
        assert result is not None
        self.orchestrator.intent_classifier.classify.assert_called_once()
        self.orchestrator._execute_pipeline.assert_called_once()

    @pytest.mark.unit
    async def test_orchestrator_nacis_disabled_fallback(self):
        """Test fallback behavior when NACIS is disabled."""
        with patch.dict('os.environ', {'NACIS_ENABLED': 'false'}), patch.object(ChatOrchestrator, '_init_helper_modules'):
            orchestrator = ChatOrchestrator(db_session=self.mock_db_session, llm_manager=self.mock_llm_manager, websocket_manager=self.mock_websocket_manager, tool_dispatcher=self.mock_tool_dispatcher)
            orchestrator.intent_classifier = Mock()
            orchestrator.intent_classifier.classify = AsyncMock(return_value=(IntentType.GENERAL_INQUIRY, 0.7))
            orchestrator.pipeline_executor = Mock()
            orchestrator.pipeline_executor.execute = AsyncMock(return_value={'data': {'basic_response': 'Standard AI response'}})
            orchestrator.trace_logger = Mock()
            orchestrator.trace_logger.log = AsyncMock()
            orchestrator.trace_logger.get_compressed_trace = Mock(return_value=[])
            result = await orchestrator.execute_core_logic(self.mock_context)
            assert result is not None
            assert orchestrator.nacis_enabled == False

class IntentClassifierTests(BaseIntegrationTest):
    """Test IntentClassifier business logic - Revenue-critical routing decisions."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.mock_llm_manager = AsyncMock()
        self.classifier = IntentClassifier(self.mock_llm_manager)
        self.mock_context = Mock(spec=ExecutionContext)
        self.mock_context.state = Mock()

    @pytest.mark.unit
    async def test_intent_classification_tco_analysis_accuracy(self):
        """Test TCO analysis intent classification for enterprise value."""
        self.mock_context.state.user_request = 'Calculate total cost of ownership for AWS migration'
        self.mock_llm_manager.ask_llm.return_value = json.dumps({'intent': 'tco_analysis', 'confidence': 0.92})
        intent, confidence = await self.classifier.classify(self.mock_context)
        assert intent == IntentType.TCO_ANALYSIS
        assert confidence == 0.92
        assert confidence > ConfidenceLevel.HIGH.value

    @pytest.mark.unit
    async def test_intent_classification_pricing_inquiry_routing(self):
        """Test pricing inquiry routing for sales enablement."""
        self.mock_context.state.user_request = 'What are your pricing plans?'
        self.mock_llm_manager.ask_llm.return_value = json.dumps({'intent': 'pricing', 'confidence': 0.88})
        intent, confidence = await self.classifier.classify(self.mock_context)
        assert intent == IntentType.PRICING_INQUIRY
        assert confidence == 0.88

    @pytest.mark.unit
    async def test_intent_classification_parse_error_recovery(self):
        """Test JSON parse error recovery maintains service."""
        self.mock_context.state.user_request = 'Help with optimization'
        self.mock_llm_manager.ask_llm.return_value = 'Invalid JSON response'
        intent, confidence = await self.classifier.classify(self.mock_context)
        assert intent == IntentType.GENERAL_INQUIRY
        assert confidence == 0.5

    @pytest.mark.unit
    async def test_intent_classification_empty_request_handling(self):
        """Test empty request handling prevents errors."""
        self.mock_context.state.user_request = ''
        self.mock_llm_manager.ask_llm.return_value = json.dumps({'intent': 'general', 'confidence': 0.3})
        intent, confidence = await self.classifier.classify(self.mock_context)
        assert intent == IntentType.GENERAL_INQUIRY
        assert confidence == 0.3

class ExecutionPlannerTests(BaseIntegrationTest):
    """Test ExecutionPlanner strategic planning logic - Workflow optimization."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.planner = ExecutionPlanner()
        self.mock_context = Mock(spec=ExecutionContext)

    @pytest.mark.unit
    async def test_execution_plan_tco_analysis_complexity(self):
        """Test TCO analysis gets comprehensive execution plan."""
        plan = await self.planner.generate_plan(self.mock_context, IntentType.TCO_ANALYSIS, confidence=0.75)
        assert len(plan) >= 3
        research_step = next((s for s in plan if s['agent'] == 'researcher'), None)
        assert research_step is not None
        assert research_step['params']['require_citations'] == True
        domain_step = next((s for s in plan if s['agent'] == 'domain_expert'), None)
        assert domain_step is not None
        assert domain_step['params']['domain'] == 'finance'
        analysis_step = next((s for s in plan if s['agent'] == 'analyst'), None)
        assert analysis_step is not None
        assert analysis_step['params']['analysis_type'] == 'tco_analysis'

    @pytest.mark.unit
    async def test_execution_plan_high_confidence_optimization(self):
        """Test high confidence reduces execution steps for efficiency."""
        plan = await self.planner.generate_plan(self.mock_context, IntentType.GENERAL_INQUIRY, confidence=0.95)
        validation_step = next((s for s in plan if s['agent'] == 'validator'), None)
        assert validation_step is not None
        research_steps = [s for s in plan if s['agent'] == 'researcher']
        assert len(research_steps) == 0

    @pytest.mark.unit
    async def test_execution_plan_volatile_intent_research_required(self):
        """Test volatile intents always require fresh research."""
        plan = await self.planner.generate_plan(self.mock_context, IntentType.PRICING_INQUIRY, confidence=0.9)
        research_step = next((s for s in plan if s['agent'] == 'researcher'), None)
        assert research_step is not None
        assert research_step['params']['require_citations'] == True

class PipelineExecutorTests(BaseIntegrationTest):
    """Test PipelineExecutor workflow execution - Business process reliability."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.mock_orchestrator = Mock()
        self.mock_orchestrator.agent_registry = Mock()
        self.mock_orchestrator.execution_engine = AsyncMock()
        self.mock_orchestrator.trace_logger = AsyncMock()
        self.executor = PipelineExecutor(self.mock_orchestrator)
        self.mock_context = Mock(spec=ExecutionContext)

    @pytest.mark.unit
    async def test_pipeline_execution_successful_flow(self):
        """Test successful pipeline execution delivers results."""
        plan = [{'agent': 'researcher', 'action': 'deep_research', 'params': {'intent': 'optimization'}}, {'agent': 'validator', 'action': 'validate_response', 'params': {'check_accuracy': True}}]
        self.mock_orchestrator.agent_registry.agents = {'researcher', 'validator'}
        self.mock_orchestrator.agent_registry.get_agent.return_value = Mock()
        self.mock_orchestrator.execution_engine.execute_agent.side_effect = [{'research_data': 'AWS cost optimization insights'}, {'validation_status': 'passed', 'confidence': 0.9}]
        result = await self.executor.execute(self.mock_context, plan, IntentType.OPTIMIZATION_ADVICE)
        assert result['intent'] == 'optimization'
        assert result['status'] == 'processing'
        assert len(result['steps']) == 2
        assert result['steps'][0]['agent'] == 'researcher'
        assert result['steps'][1]['agent'] == 'validator'

    @pytest.mark.unit
    async def test_pipeline_execution_agent_not_available_fallback(self):
        """Test unavailable agent fallback maintains workflow."""
        plan = [{'agent': 'unavailable_agent', 'action': 'specialized_task', 'params': {}}]
        self.mock_orchestrator.agent_registry.agents = {'other_agent'}
        result = await self.executor.execute(self.mock_context, plan, IntentType.GENERAL_INQUIRY)
        assert len(result['steps']) == 1
        step_result = result['steps'][0]['result']
        assert step_result['status'] == 'pending'
        assert step_result['agent'] == 'unavailable_agent'
        assert 'implementation pending' in step_result['message']

    @pytest.mark.unit
    async def test_pipeline_execution_context_data_accumulation(self):
        """Test context data accumulation across pipeline steps."""
        plan = [{'agent': 'data_collector', 'action': 'collect', 'params': {}}, {'agent': 'analyzer', 'action': 'analyze', 'params': {}}]
        self.mock_orchestrator.agent_registry.agents = {'data_collector', 'analyzer'}
        self.mock_orchestrator.agent_registry.get_agent.return_value = Mock()
        self.mock_orchestrator.execution_engine.execute_agent.side_effect = [{'collected_metrics': ['cpu_usage', 'memory_usage']}, {'analysis_result': 'Optimization recommended'}]
        self.mock_context.state = Mock()
        result = await self.executor.execute(self.mock_context, plan, IntentType.OPTIMIZATION_ADVICE)
        assert len(result['steps']) == 2
        assert self.mock_context.state.accumulated_data is not None

    @pytest.mark.unit
    async def test_pipeline_execution_trace_logging_transparency(self):
        """Test trace logging provides execution transparency."""
        plan = [{'agent': 'researcher', 'action': 'research', 'params': {'topic': 'cloud costs'}}]
        self.mock_orchestrator.agent_registry.agents = {'researcher'}
        await self.executor.execute(self.mock_context, plan, IntentType.MARKET_RESEARCH)
        self.mock_orchestrator.trace_logger.log.assert_called()
        call_args = self.mock_orchestrator.trace_logger.log.call_args_list
        assert any(('Executing researcher.research' in str(call) for call in call_args))

class TraceLoggerTests(BaseIntegrationTest):
    """Test TraceLogger transparency features - User trust and debugging."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.mock_websocket_manager = AsyncMock()
        self.trace_logger = TraceLogger(self.mock_websocket_manager)

    @pytest.mark.unit
    async def test_trace_logging_websocket_transparency(self):
        """Test trace logging provides real-time transparency."""
        await self.trace_logger.log('Starting optimization analysis', {'intent': 'optimization'})
        self.mock_websocket_manager.send_agent_update.assert_called_once()
        call_args = self.mock_websocket_manager.send_agent_update.call_args
        assert call_args[1]['agent_name'] == 'ChatOrchestrator'
        assert call_args[1]['status'] == 'trace'
        assert 'Starting optimization analysis' in call_args[1]['data']['action']

    @pytest.mark.unit
    async def test_trace_logging_size_limit_memory_management(self):
        """Test trace size limit prevents memory leaks."""
        for i in range(25):
            await self.trace_logger.log(f'Action {i}', {'step': i})
        assert len(self.trace_logger.traces) == 20
        actions = [trace['action'] for trace in self.trace_logger.traces]
        assert 'Action 0' not in actions
        assert 'Action 24' in actions

    @pytest.mark.unit
    def test_trace_compression_ui_display(self):
        """Test compressed trace format for UI display."""
        self.trace_logger.traces = [{'timestamp': '2024-01-01T12:00:00.000000Z', 'action': 'Intent classification started'}, {'timestamp': '2024-01-01T12:00:01.500000Z', 'action': 'Research phase initiated'}, {'timestamp': '2024-01-01T12:00:03.200000Z', 'action': 'Analysis completed'}]
        compressed = self.trace_logger.get_compressed_trace(limit=2)
        assert len(compressed) == 2
        assert 'Research phase initiated' in compressed[0]
        assert 'Analysis completed' in compressed[1]

class ConfidenceManagerTests(BaseIntegrationTest):
    """Test ConfidenceManager decision logic - Smart routing and caching."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.confidence_manager = ConfidenceManager()

    @pytest.mark.unit
    def test_confidence_thresholds_enterprise_accuracy(self):
        """Test confidence thresholds ensure enterprise-grade accuracy."""
        tco_threshold = self.confidence_manager.get_threshold(IntentType.TCO_ANALYSIS)
        assert tco_threshold == ConfidenceLevel.HIGH.value
        benchmark_threshold = self.confidence_manager.get_threshold(IntentType.BENCHMARKING)
        assert benchmark_threshold == ConfidenceLevel.HIGH.value
        optimization_threshold = self.confidence_manager.get_threshold(IntentType.OPTIMIZATION_ADVICE)
        assert optimization_threshold == ConfidenceLevel.HIGH.value
        general_threshold = self.confidence_manager.get_threshold(IntentType.GENERAL_INQUIRY)
        assert general_threshold == ConfidenceLevel.LOW.value

    @pytest.mark.unit
    def test_cache_ttl_business_volatility_alignment(self):
        """Test cache TTL aligns with business data volatility."""
        pricing_ttl = self.confidence_manager.get_cache_ttl(IntentType.PRICING_INQUIRY)
        assert pricing_ttl == 900
        market_ttl = self.confidence_manager.get_cache_ttl(IntentType.MARKET_RESEARCH)
        assert market_ttl == 7200
        technical_ttl = self.confidence_manager.get_cache_ttl(IntentType.TECHNICAL_QUESTION)
        assert technical_ttl == 3600

    @pytest.mark.unit
    def test_escalation_decision_cost_optimization(self):
        """Test escalation decisions optimize cost vs quality."""
        should_escalate_high = self.confidence_manager.should_escalate(confidence=0.9, intent=IntentType.TCO_ANALYSIS)
        assert should_escalate_high == False
        should_escalate_low = self.confidence_manager.should_escalate(confidence=0.7, intent=IntentType.TCO_ANALYSIS)
        assert should_escalate_low == True
        should_escalate_general = self.confidence_manager.should_escalate(confidence=0.6, intent=IntentType.GENERAL_INQUIRY)
        assert should_escalate_general == False

class QualityEvaluatorTests(BaseIntegrationTest):
    """Test QualityEvaluator assessment logic - Quality assurance for business value."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.mock_llm_manager = AsyncMock()
        self.evaluator = QualityEvaluator(self.mock_llm_manager)

    @pytest.mark.unit
    async def test_quality_evaluation_business_value_assessment(self):
        """Test quality evaluation identifies business value in responses."""
        business_response = '\n        Based on your AWS usage patterns, I recommend:\n        1. Switch to Reserved Instances for predictable workloads (30% savings)\n        2. Use Spot Instances for batch processing (up to 90% savings)  \n        3. Right-size EC2 instances based on metrics (15% savings)\n        \n        Expected monthly savings: $3,500 from current $10,000 spend.\n        '
        self.mock_llm_manager.generate_response.return_value = json.dumps({'specificity_score': 0.9, 'actionability_score': 0.95, 'quantification_score': 0.9, 'novelty_score': 0.8, 'issues': [], 'reasoning': 'Specific recommendations with quantified savings'})
        criteria = EvaluationCriteria(content_type='optimization', check_actionability=True, require_specificity=True)
        metrics = await self.evaluator.evaluate_response(business_response, 'How can I reduce AWS costs?', criteria)
        assert metrics.overall_score > 0.8
        assert metrics.actionability_score > 0.9
        assert metrics.specificity_score > 0.8

    @pytest.mark.unit
    async def test_quality_evaluation_generic_response_penalty(self):
        """Test quality evaluation penalizes generic responses."""
        generic_response = '\n        It depends on your specific situation. You should generally consider \n        best practices and industry standards. This might help, but it could\n        vary depending on various factors.\n        '
        criteria = EvaluationCriteria(check_actionability=True)
        metrics = await self.evaluator.evaluate_response(generic_response, 'How can I optimize my infrastructure?', criteria)
        assert metrics.generic_phrase_count >= 4
        assert metrics.actionability_score <= 0.3
        assert metrics.overall_score < 0.5

    @pytest.mark.unit
    async def test_quality_evaluation_hallucination_risk_detection(self):
        """Test hallucination risk detection protects user trust."""
        risky_response = '\n        According to our analysis, Amazon Web Services definitely costs exactly\n        $0.045 per hour for all EC2 instances as of 2024-01-15. This is \n        absolutely guaranteed and will never change.\n        '
        criteria = EvaluationCriteria(check_hallucination=True)
        metrics = await self.evaluator.evaluate_response(risky_response, 'What are AWS pricing rates?', criteria)
        assert metrics.hallucination_risk >= 0.3
        assert metrics.overall_score < 0.7

    @pytest.mark.unit
    async def test_quality_evaluation_error_recovery_stability(self):
        """Test quality evaluation handles errors gracefully."""
        self.mock_llm_manager.generate_response.side_effect = Exception('LLM unavailable')
        metrics = await self.evaluator.evaluate_response('Some response text', 'Some query', EvaluationCriteria())
        assert 0.4 <= metrics.overall_score <= 0.6
        assert isinstance(metrics, QualityMetrics)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')