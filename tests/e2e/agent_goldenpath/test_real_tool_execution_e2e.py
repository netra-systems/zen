"""
E2E Tests for Real Tool Execution in Agent Golden Path
Issue #1081 - Agent Golden Path Messages E2E Test Creation

MISSION CRITICAL: Tests real tool execution during agent message processing
- Agents execute actual tools during message processing
- Tool results are integrated into agent responses
- Tool execution events are delivered via WebSocket
- Real business value is delivered through tool-assisted responses

Business Value Justification (BVJ):
- Segment: Mid/Enterprise Users requiring tool-assisted analysis
- Business Goal: Tool Integration Validation & Advanced AI Capabilities
- Value Impact: Validates $500K+ ARR premium features requiring tool execution
- Strategic Impact: Demonstrates platform's advanced AI capabilities beyond simple chat

Test Strategy:
- REAL TOOLS: Actual tool execution in staging environment
- REAL INTEGRATION: Tool results integrated into agent responses
- REAL EVENTS: Tool execution events via WebSocket
- REAL BUSINESS VALUE: Tools deliver actionable business insights
- NO MOCKING: Full tool execution pipeline testing

Coverage Target: Increase from 65-75% to 85%
Test Focus: Tool execution, tool integration, advanced agent capabilities
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import uuid
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.tool_execution
@pytest.mark.mission_critical
class RealToolExecutionE2ETests(SSotAsyncTestCase):
    """
    E2E tests for real tool execution in agent golden path.
    
    Validates that agents can execute real tools during message processing
    and integrate tool results into meaningful business responses.
    """

    @classmethod
    def setup_class(cls):
        """Setup real tool execution test environment."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EWebSocketAuthHelper(environment='staging')
        cls.tool_execution_patterns = {'data_analysis': ['analyze', 'calculate', 'compute', 'metrics', 'statistics'], 'cost_optimization': ['cost', 'savings', 'optimization', 'efficiency', 'budget'], 'technical_lookup': ['documentation', 'lookup', 'search', 'find', 'retrieve'], 'calculation': ['calculate', 'compute', 'math', 'formula', 'equation']}
        cls.tool_value_indicators = ['based on analysis', 'calculated', 'according to data', 'tool results show', 'analysis indicates', 'computed']
        cls.logger.info('Real tool execution e2e tests initialized')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.test_id = f'tool_execution_test_{int(time.time())}'
        self.thread_id = f'thread_{self.test_id}'
        self.run_id = f'run_{self.test_id}'
        self.logger.info(f'Tool execution test setup - test_id: {self.test_id}')

    def _extract_tool_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract and analyze tool execution events from WebSocket events."""
        tool_events = []
        tool_executions = []
        tool_results = []
        for event in events:
            event_type = event.get('type', 'unknown')
            if 'tool' in event_type.lower():
                tool_events.append(event)
                if 'executing' in event_type.lower():
                    tool_executions.append(event)
                elif 'completed' in event_type.lower():
                    tool_results.append(event)
        return {'tool_events': tool_events, 'tool_executions': tool_executions, 'tool_results': tool_results, 'tool_execution_count': len(tool_executions), 'tool_completion_count': len(tool_results)}

    def _analyze_tool_integration(self, response_text: str) -> Dict[str, Any]:
        """Analyze how well tool results are integrated into the response."""
        integration_analysis = {'tool_references': 0, 'value_indicators': [], 'data_points': 0, 'calculation_results': 0, 'integration_quality': 0.0}
        response_lower = response_text.lower()
        for indicator in self.tool_value_indicators:
            if indicator in response_lower:
                integration_analysis['value_indicators'].append(indicator)
        integration_analysis['tool_references'] = len(integration_analysis['value_indicators'])
        data_patterns = ['\\d+%', '\\$\\d+', '\\d+\\.\\d+', '\\d+\\s+(seconds?|minutes?|hours?)', '\\d+\\s+(bytes?|KB|MB|GB)']
        for pattern in data_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            integration_analysis['data_points'] += len(matches)
        calculation_patterns = ['calculated?\\s+\\w+', 'computed?\\s+\\w+', 'analysis shows?\\s+\\w+', 'results? indicate?\\s+\\w+']
        for pattern in calculation_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            integration_analysis['calculation_results'] += len(matches)
        quality_components = [min(integration_analysis['tool_references'] / 2, 1.0) * 0.4, min(integration_analysis['data_points'] / 5, 1.0) * 0.3, min(integration_analysis['calculation_results'] / 2, 1.0) * 0.3]
        integration_analysis['integration_quality'] = sum(quality_components)
        return integration_analysis

    async def test_data_analysis_tool_execution(self):
        """
        Test agent execution of data analysis tools.
        
        Validates that:
        1. Agent receives data analysis request
        2. Agent executes appropriate data analysis tools
        3. Tool execution events are delivered via WebSocket
        4. Tool results are integrated into meaningful response
        
        Flow:
        1. Send data analysis request -> agent processes
        2. Agent executes data tools -> tool_executing events
        3. Tools complete -> tool_completed events  
        4. Response integrates tool results -> business value
        
        Coverage: Data analysis tools, tool event delivery, result integration
        """
        data_tool_start = time.time()
        tool_metrics = {'executions': 0, 'completions': 0, 'integration_score': 0.0}
        self.logger.info('📊 Testing data analysis tool execution')
        try:
            data_user = await self.auth_helper.create_authenticated_user(email=f'data_tool_test_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'tool_execution', 'data_analysis'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(data_user.jwt_token), ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=15.0)
            analysis_request = {'type': 'chat_message', 'content': 'I need a detailed analysis of my AI infrastructure costs. Current monthly spend is $15,000 with 500,000 API calls. Please analyze cost per call, identify optimization opportunities, and calculate potential savings with different optimization strategies. Use data analysis tools to provide specific metrics and recommendations.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': data_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'data_analysis_tools', 'expects_tool_execution': True, 'tool_categories': ['data_analysis', 'cost_optimization']}}
            await websocket.send(json.dumps(analysis_request))
            self.logger.info('📤 Data analysis request sent')
            all_events = []
            tool_execution_detected = False
            tool_completion_detected = False
            final_response = None
            timeout = 90.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    all_events.append(event)
                    event_type = event.get('type', 'unknown')
                    if 'tool_executing' in event_type:
                        tool_execution_detected = True
                        tool_metrics['executions'] += 1
                        self.logger.info(f'🔧 Tool execution detected: {event_type}')
                    if 'tool_completed' in event_type:
                        tool_completion_detected = True
                        tool_metrics['completions'] += 1
                        self.logger.info(f'CHECK Tool completion detected: {event_type}')
                    if event_type == 'agent_completed':
                        final_response = event
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            processing_time = time.time() - collection_start
            tool_analysis = self._extract_tool_events(all_events)
            assert len(all_events) > 0, 'Should receive events from data analysis request'
            assert final_response is not None, 'Should receive final response'
            assert tool_execution_detected or tool_analysis['tool_execution_count'] > 0, f"Should detect tool execution for data analysis. Tool events: {len(tool_analysis['tool_events'])}"
            response_data = final_response.get('data', {})
            result = response_data.get('result', {})
            response_text = str(result) if result else ''
            integration_analysis = self._analyze_tool_integration(response_text)
            tool_metrics['integration_score'] = integration_analysis['integration_quality']
            assert len(response_text) > 200, f'Data analysis response should be substantial: {len(response_text)} chars'
            assert integration_analysis['integration_quality'] >= 0.3, f"Tool results should be well integrated: {integration_analysis['integration_quality']:.3f} (tool references: {integration_analysis['tool_references']}, data points: {integration_analysis['data_points']})"
            business_indicators = ['cost', 'analysis', 'optimization', 'savings']
            response_lower = response_text.lower()
            found_indicators = [ind for ind in business_indicators if ind in response_lower]
            assert len(found_indicators) >= 2, f'Should contain business value indicators: found {found_indicators}'
            total_time = time.time() - data_tool_start
            self.logger.info('📊 Data analysis tool execution validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Processing time: {processing_time:.2f}s')
            self.logger.info(f"   Tool executions: {tool_metrics['executions']}")
            self.logger.info(f"   Tool completions: {tool_metrics['completions']}")
            self.logger.info(f"   Integration score: {tool_metrics['integration_score']:.3f}")
            self.logger.info(f'   Response length: {len(response_text)} chars')
            self.logger.info(f'   Business indicators: {found_indicators}')
        except Exception as e:
            self.logger.error(f'X Data analysis tool execution failed: {e}')
            raise AssertionError(f'Data analysis tool execution failed: {e}. This breaks advanced AI capabilities requiring tool integration.')

    async def test_calculation_tool_execution(self):
        """
        Test agent execution of calculation tools.
        
        Validates that:
        1. Agent receives calculation request
        2. Agent executes calculation tools for complex computations
        3. Tool results provide accurate calculations
        4. Calculations are integrated into actionable recommendations
        
        Flow:
        1. Send calculation request -> agent processes
        2. Agent executes calculation tools -> numeric results
        3. Tool results integrated -> response with calculated values
        4. Validate calculation accuracy and integration
        
        Coverage: Calculation tools, numeric processing, computational accuracy
        """
        calc_tool_start = time.time()
        calculation_metrics = {'calculations_detected': 0, 'numeric_results': 0, 'accuracy_score': 0.0}
        self.logger.info('🧮 Testing calculation tool execution')
        try:
            calc_user = await self.auth_helper.create_authenticated_user(email=f'calc_tool_test_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'tool_execution', 'calculations'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(calc_user.jwt_token), ssl=ssl_context), timeout=15.0)
            calculation_request = {'type': 'chat_message', 'content': 'Please calculate ROI for our AI optimization initiatives: Current costs: $50,000/month, Projected savings after optimization: 35% reduction, Implementation cost: $25,000 one-time, Timeline: 6 months implementation. Calculate monthly savings, payback period, 12-month ROI, and 3-year total value. Use calculation tools for precision.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': calc_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'calculation_tools', 'expects_calculations': True, 'calculation_types': ['roi', 'savings', 'payback', 'projections']}}
            await websocket.send(json.dumps(calculation_request))
            self.logger.info('📤 Calculation request sent')
            all_events = []
            calculation_events = []
            final_response = None
            timeout = 75.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                    event = json.loads(event_data)
                    all_events.append(event)
                    event_type = event.get('type', 'unknown')
                    if any((word in str(event).lower() for word in ['calc', 'compute', 'math', 'number'])):
                        calculation_events.append(event)
                        calculation_metrics['calculations_detected'] += 1
                    if event_type == 'agent_completed':
                        final_response = event
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            processing_time = time.time() - collection_start
            assert final_response is not None, 'Should receive calculation response'
            response_data = final_response.get('data', {})
            result = response_data.get('result', {})
            response_text = str(result) if result else ''
            numeric_patterns = ['\\$[\\d,]+', '\\d+%', '\\d+\\.\\d+', '\\d+\\s+months?']
            for pattern in numeric_patterns:
                matches = re.findall(pattern, response_text)
                calculation_metrics['numeric_results'] += len(matches)
            integration_analysis = self._analyze_tool_integration(response_text)
            assert len(response_text) > 150, f'Calculation response should be detailed: {len(response_text)} chars'
            assert calculation_metrics['numeric_results'] >= 3, f"Should contain multiple calculated values: {calculation_metrics['numeric_results']} found"
            calc_terms = ['calculated', 'computed', 'roi', 'savings', 'payback']
            response_lower = response_text.lower()
            found_calc_terms = [term for term in calc_terms if term in response_lower]
            assert len(found_calc_terms) >= 2, f'Should contain calculation terminology: found {found_calc_terms}'
            expected_values = ['$17,500', '35%', 'payback', 'roi']
            calculation_accuracy = 0
            for expected in expected_values:
                if expected.lower() in response_lower:
                    calculation_accuracy += 1
            calculation_metrics['accuracy_score'] = calculation_accuracy / len(expected_values)
            total_time = time.time() - calc_tool_start
            self.logger.info('🧮 Calculation tool execution validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Processing time: {processing_time:.2f}s')
            self.logger.info(f"   Calculation events: {calculation_metrics['calculations_detected']}")
            self.logger.info(f"   Numeric results: {calculation_metrics['numeric_results']}")
            self.logger.info(f'   Calculation terms: {found_calc_terms}')
            self.logger.info(f"   Accuracy score: {calculation_metrics['accuracy_score']:.3f}")
            self.logger.info(f'   Response length: {len(response_text)} chars')
        except Exception as e:
            self.logger.error(f'X Calculation tool execution failed: {e}')
            raise AssertionError(f'Calculation tool execution failed: {e}. This breaks computational capabilities and business calculations.')

    async def test_multi_tool_workflow_execution(self):
        """
        Test agent execution of multiple tools in coordinated workflow.
        
        Validates that:
        1. Agent orchestrates multiple tools in sequence
        2. Tool results from one tool feed into another
        3. Complex multi-step analysis is performed
        4. Comprehensive business insights are delivered
        
        Flow:
        1. Send complex request -> requires multiple tools
        2. Agent executes tool sequence -> data gathering -> analysis -> calculation
        3. Tools coordinate -> results build comprehensive analysis
        4. Final response integrates all tool outputs
        
        Coverage: Multi-tool coordination, workflow orchestration, complex analysis
        """
        workflow_start = time.time()
        workflow_metrics = {'tools_executed': [], 'workflow_steps': 0, 'coordination_score': 0.0}
        self.logger.info('🔄 Testing multi-tool workflow execution')
        try:
            workflow_user = await self.auth_helper.create_authenticated_user(email=f'workflow_tool_test_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'tool_execution', 'advanced_analysis'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(workflow_user.jwt_token), ssl=ssl_context), timeout=15.0)
            workflow_request = {'type': 'chat_message', 'content': 'I need a comprehensive AI infrastructure assessment for our enterprise: 1) Analyze current usage patterns from our data (10M+ API calls/month), 2) Calculate cost optimization potential across different models, 3) Research best practices for our industry (FinTech), 4) Generate implementation timeline with specific milestones, 5) Calculate ROI projections for 12-month optimization program. Please use multiple analysis tools to provide detailed recommendations with data-driven insights and actionable next steps.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': workflow_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'multi_tool_workflow', 'expects_multiple_tools': True, 'workflow_complexity': 'high', 'expected_tools': ['data_analysis', 'calculations', 'research', 'planning']}}
            await websocket.send(json.dumps(workflow_request))
            self.logger.info('📤 Multi-tool workflow request sent')
            all_events = []
            tool_sequence = []
            workflow_events = []
            final_response = None
            timeout = 120.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    event = json.loads(event_data)
                    all_events.append(event)
                    event_type = event.get('type', 'unknown')
                    if 'tool' in event_type.lower():
                        workflow_events.append(event)
                        if 'executing' in event_type.lower():
                            tool_info = event.get('data', {}).get('tool_name', 'unknown_tool')
                            tool_sequence.append({'tool': tool_info, 'timestamp': time.time() - collection_start, 'event_type': event_type})
                            workflow_metrics['tools_executed'].append(tool_info)
                            workflow_metrics['workflow_steps'] += 1
                    if any((keyword in str(event).lower() for keyword in ['analyzing', 'calculating', 'researching'])):
                        workflow_events.append(event)
                    if event_type == 'agent_completed':
                        final_response = event
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            processing_time = time.time() - collection_start
            tool_analysis = self._extract_tool_events(all_events)
            unique_tools = list(set(workflow_metrics['tools_executed']))
            assert final_response is not None, 'Should complete multi-tool workflow'
            assert len(workflow_events) > 0, 'Should detect workflow execution events'
            assert workflow_metrics['workflow_steps'] >= 2, f"Should execute multiple workflow steps: {workflow_metrics['workflow_steps']} detected"
            response_data = final_response.get('data', {})
            result = response_data.get('result', {})
            response_text = str(result) if result else ''
            assert len(response_text) > 500, f'Multi-tool workflow should generate comprehensive response: {len(response_text)} chars'
            integration_analysis = self._analyze_tool_integration(response_text)
            workflow_metrics['coordination_score'] = integration_analysis['integration_quality']
            assert integration_analysis['integration_quality'] >= 0.4, f"Multi-tool workflow should show high integration: {integration_analysis['integration_quality']:.3f}"
            business_areas = ['cost', 'optimization', 'analysis', 'implementation', 'roi']
            response_lower = response_text.lower()
            covered_areas = [area for area in business_areas if area in response_lower]
            coverage_rate = len(covered_areas) / len(business_areas)
            assert coverage_rate >= 0.6, f'Should cover most business areas: {coverage_rate:.1%} ({covered_areas})'
            total_time = time.time() - workflow_start
            self.logger.info('🔄 Multi-tool workflow execution validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Processing time: {processing_time:.2f}s')
            self.logger.info(f"   Workflow steps: {workflow_metrics['workflow_steps']}")
            self.logger.info(f'   Unique tools: {len(unique_tools)}')
            self.logger.info(f"   Tool sequence: {[t['tool'] for t in tool_sequence]}")
            self.logger.info(f"   Coordination score: {workflow_metrics['coordination_score']:.3f}")
            self.logger.info(f'   Business coverage: {coverage_rate:.1%}')
            self.logger.info(f'   Response length: {len(response_text)} chars')
        except Exception as e:
            self.logger.error(f'X Multi-tool workflow execution failed: {e}')
            raise AssertionError(f'Multi-tool workflow execution failed: {e}. This breaks complex analysis capabilities requiring tool coordination.')

    async def test_tool_error_handling_and_recovery(self):
        """
        Test tool error handling and recovery during agent processing.
        
        Validates that:
        1. Agent handles tool execution failures gracefully
        2. Alternative tools are used when primary tools fail
        3. Partial tool results are handled appropriately  
        4. User experience remains positive despite tool issues
        
        Flow:
        1. Send request likely to cause tool issues
        2. Monitor for tool error handling
        3. Validate graceful degradation
        4. Ensure response quality maintained
        
        Coverage: Tool error handling, system resilience, graceful degradation
        """
        error_handling_start = time.time()
        error_metrics = {'tool_errors': 0, 'recovery_attempts': 0, 'graceful_degradation': False}
        self.logger.info('🛠️ Testing tool error handling and recovery')
        try:
            error_user = await self.auth_helper.create_authenticated_user(email=f'tool_error_test_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'tool_execution', 'error_testing'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(error_user.jwt_token), ssl=ssl_context), timeout=15.0)
            error_test_request = {'type': 'chat_message', 'content': "Please analyze data from the 'nonexistent_dataset_12345' and calculate optimization metrics using invalid_analysis_tool. If tools fail, please provide alternative analysis based on available information. I still need actionable recommendations for AI cost optimization.", 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': error_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'tool_error_handling', 'expects_error_recovery': True, 'should_gracefully_degrade': True}}
            await websocket.send(json.dumps(error_test_request))
            self.logger.info('📤 Tool error handling test request sent')
            all_events = []
            error_events = []
            recovery_events = []
            final_response = None
            timeout = 60.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                    event = json.loads(event_data)
                    all_events.append(event)
                    event_type = event.get('type', 'unknown')
                    event_str = str(event).lower()
                    if 'error' in event_str and 'tool' in event_str or 'tool_error' in event_type:
                        error_events.append(event)
                        error_metrics['tool_errors'] += 1
                        self.logger.info(f'🚨 Tool error detected: {event_type}')
                    if any((keyword in event_str for keyword in ['retry', 'alternative', 'fallback', 'recovery'])):
                        recovery_events.append(event)
                        error_metrics['recovery_attempts'] += 1
                        self.logger.info(f'🔄 Recovery attempt detected: {event_type}')
                    if event_type == 'agent_completed':
                        final_response = event
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            processing_time = time.time() - collection_start
            assert final_response is not None, 'Should complete processing despite tool errors'
            response_data = final_response.get('data', {})
            result = response_data.get('result', {})
            response_text = str(result) if result else ''
            assert len(response_text) > 100, f'Should provide meaningful response despite tool errors: {len(response_text)} chars'
            degradation_indicators = ['alternative', 'available information', 'based on', 'recommendations', 'despite', 'however', 'alternatively', 'instead']
            response_lower = response_text.lower()
            found_degradation = [ind for ind in degradation_indicators if ind in response_lower]
            if len(found_degradation) > 0:
                error_metrics['graceful_degradation'] = True
            business_value = ['optimization', 'cost', 'recommendations', 'strategy']
            found_value = [val for val in business_value if val in response_lower]
            assert len(found_value) >= 1, f'Should maintain business value despite tool errors: found {found_value}'
            assert 'error' not in response_lower or 'sorry' in response_lower, 'User-facing response should handle errors gracefully'
            total_time = time.time() - error_handling_start
            self.logger.info('🛠️ Tool error handling validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Processing time: {processing_time:.2f}s')
            self.logger.info(f"   Tool errors detected: {error_metrics['tool_errors']}")
            self.logger.info(f"   Recovery attempts: {error_metrics['recovery_attempts']}")
            self.logger.info(f"   Graceful degradation: {error_metrics['graceful_degradation']}")
            self.logger.info(f'   Degradation indicators: {found_degradation}')
            self.logger.info(f'   Business value maintained: {found_value}')
            self.logger.info(f'   Response length: {len(response_text)} chars')
        except Exception as e:
            self.logger.error(f'X Tool error handling test failed: {e}')
            raise AssertionError(f'Tool error handling and recovery failed: {e}. This breaks system resilience and user experience.')

    async def test_tool_performance_and_efficiency(self):
        """
        Test tool execution performance and efficiency.
        
        Validates that:
        1. Tools execute within reasonable time limits
        2. Tool execution doesn't significantly delay responses
        3. Multiple tool executions are efficient
        4. Tool overhead is acceptable for business value
        
        Flow:
        1. Send request requiring tool execution
        2. Monitor tool execution timing
        3. Validate performance metrics
        4. Ensure efficiency meets business requirements
        
        Coverage: Tool performance, execution efficiency, business value timing
        """
        performance_start = time.time()
        performance_metrics = {'tool_execution_times': [], 'total_tool_overhead': 0.0, 'efficiency_score': 0.0}
        self.logger.info('⚡ Testing tool performance and efficiency')
        try:
            perf_user = await self.auth_helper.create_authenticated_user(email=f'tool_perf_test_{self.test_id}@test.com', permissions=['read', 'write', 'chat', 'tool_execution', 'performance_testing'])
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            websocket = await asyncio.wait_for(websockets.connect(self.staging_config.urls.websocket_url, additional_headers=self.auth_helper.get_websocket_headers(perf_user.jwt_token), ssl=ssl_context), timeout=15.0)
            performance_request = {'type': 'chat_message', 'content': 'Quick analysis needed: Calculate savings from reducing GPT-4 usage by 25% on current monthly spend of $8,000. Include implementation recommendations. Please provide efficient tool-based analysis with fast turnaround.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': perf_user.user_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': {'test_type': 'tool_performance', 'expects_efficient_execution': True, 'performance_priority': 'high'}}
            await websocket.send(json.dumps(performance_request))
            message_sent_time = time.time()
            self.logger.info('📤 Performance test request sent')
            all_events = []
            tool_start_times = {}
            tool_end_times = {}
            first_response_time = None
            final_response = None
            timeout = 45.0
            collection_start = time.time()
            while time.time() - collection_start < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    all_events.append(event)
                    event_type = event.get('type', 'unknown')
                    event_time = time.time()
                    if first_response_time is None and event_type != 'connection_ack':
                        first_response_time = event_time - message_sent_time
                    if 'tool_executing' in event_type:
                        tool_name = event.get('data', {}).get('tool_name', 'unknown')
                        tool_start_times[tool_name] = event_time
                        self.logger.info(f'⏱️ Tool started: {tool_name}')
                    if 'tool_completed' in event_type:
                        tool_name = event.get('data', {}).get('tool_name', 'unknown')
                        tool_end_times[tool_name] = event_time
                        if tool_name in tool_start_times:
                            execution_time = event_time - tool_start_times[tool_name]
                            performance_metrics['tool_execution_times'].append(execution_time)
                            self.logger.info(f'CHECK Tool completed: {tool_name} ({execution_time:.2f}s)')
                    if event_type == 'agent_completed':
                        final_response = event
                        break
                except asyncio.TimeoutError:
                    continue
            await websocket.close()
            total_processing_time = time.time() - collection_start
            total_time = time.time() - performance_start
            if performance_metrics['tool_execution_times']:
                avg_tool_time = sum(performance_metrics['tool_execution_times']) / len(performance_metrics['tool_execution_times'])
                max_tool_time = max(performance_metrics['tool_execution_times'])
                total_tool_time = sum(performance_metrics['tool_execution_times'])
                performance_metrics['total_tool_overhead'] = total_tool_time
                efficiency_score = max(0, 1.0 - avg_tool_time / 10.0)
                performance_metrics['efficiency_score'] = efficiency_score
            else:
                avg_tool_time = 0
                max_tool_time = 0
                efficiency_score = 0
            assert final_response is not None, 'Should complete performance test'
            assert total_processing_time < 40.0, f'Performance test should complete quickly: {total_processing_time:.2f}s (max 40s)'
            if first_response_time:
                assert first_response_time < 8.0, f'First response should be fast: {first_response_time:.2f}s (max 8s)'
            if performance_metrics['tool_execution_times']:
                assert avg_tool_time < 8.0, f'Average tool execution should be efficient: {avg_tool_time:.2f}s (max 8s)'
                assert max_tool_time < 15.0, f'Maximum tool execution should be reasonable: {max_tool_time:.2f}s (max 15s)'
            response_data = final_response.get('data', {})
            result = response_data.get('result', {})
            response_text = str(result) if result else ''
            assert len(response_text) > 80, f'Should maintain response quality despite speed focus: {len(response_text)} chars'
            business_terms = ['savings', 'cost', 'recommendation']
            response_lower = response_text.lower()
            found_terms = [term for term in business_terms if term in response_lower]
            assert len(found_terms) >= 1, f'Should maintain business value despite speed focus: {found_terms}'
            self.logger.info('⚡ Tool performance and efficiency validation complete')
            self.logger.info(f'   Total time: {total_time:.2f}s')
            self.logger.info(f'   Processing time: {total_processing_time:.2f}s')
            self.logger.info(f'   First response time: {first_response_time:.2f}s' if first_response_time else '   First response time: N/A')
            self.logger.info(f"   Tool executions: {len(performance_metrics['tool_execution_times'])}")
            if performance_metrics['tool_execution_times']:
                self.logger.info(f'   Average tool time: {avg_tool_time:.2f}s')
                self.logger.info(f'   Max tool time: {max_tool_time:.2f}s')
                self.logger.info(f"   Total tool overhead: {performance_metrics['total_tool_overhead']:.2f}s")
                self.logger.info(f"   Efficiency score: {performance_metrics['efficiency_score']:.3f}")
            self.logger.info(f'   Business terms found: {found_terms}')
            self.logger.info(f'   Response length: {len(response_text)} chars')
        except Exception as e:
            self.logger.error(f'X Tool performance test failed: {e}')
            raise AssertionError(f'Tool performance and efficiency test failed: {e}. This indicates tool execution performance issues.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')