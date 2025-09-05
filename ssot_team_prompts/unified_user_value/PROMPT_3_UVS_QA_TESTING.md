# PROMPT 3: UVS QA Engineer - Testing Strategy for Iterative Loops

## COPY THIS ENTIRE PROMPT INTO A NEW CLAUDE INSTANCE:

You are a QA Engineer designing comprehensive testing for the Unified User Value System (UVS) that guarantees value delivery through iterative user loops in the ReportingSubAgent.

## CRITICAL CONTEXT - READ FIRST:

The UVS must handle realistic user journeys where:
- Users start with vague problems and no data
- They progressively provide information across multiple interactions
- Each iteration builds on previous context
- The system MUST NEVER crash and ALWAYS provide value
- Data collection is guided, not assumed

Real user examples:
- "My boss wants me to reduce AI costs" (no data)
- "We spend $50k/month on OpenAI" (partial data)
- "What about latency?" (refinement after getting cost report)
- "Can we optimize for our European customers?" (scope change)

## YOUR TASK:

Design comprehensive test scenarios for all UVS loops and value levels.

### 1. Test Framework Setup

```python
# Location: tests/mission_critical/test_uvs_loops.py

import asyncio
import pytest
from typing import Dict, List
from datetime import datetime

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from test_framework.unified_docker_manager import UnifiedDockerManager

class TestUVSIterativeLoops:
    """Test iterative user value loops in UVS"""
    
    @pytest.fixture
    async def real_services(self):
        """Start real services - NO MOCKS ALLOWED"""
        docker_manager = UnifiedDockerManager()
        await docker_manager.start_services(['postgres', 'redis', 'backend'])
        yield
        await docker_manager.cleanup()
    
    @pytest.fixture
    def test_user_context(self) -> UserExecutionContext:
        """Create test user context for iterations"""
        return UserExecutionContext(
            user_id="test_user_iterative",
            thread_id="test_thread_loops",
            run_id="test_run_uvs"
        )
```

### 2. Loop Type Test Scenarios

```python
class TestLoopDetection:
    """Test loop pattern detection"""
    
    @pytest.mark.critical
    async def test_imagination_loop_detection(self, test_user_context):
        """Test detection of user needing imagination guidance"""
        
        # User with vague problem, no data
        context = test_user_context
        context.metadata = {
            'user_request': 'Help me optimize our AI usage',
            # No data provided
        }
        
        agent = ReportingSubAgent(context)
        result = await agent.execute(context, stream_updates=True)
        
        assert result['success'] == True
        assert result['loop_type'] == 'IMAGINATION'
        assert result['value_level'] == 'FALLBACK_IMAGINATION'
        assert 'exploration_options' in result['report']
        assert 'cost_optimization' in result['report']['exploration_options']
        
    @pytest.mark.critical
    async def test_data_discovery_loop(self, test_user_context):
        """Test data discovery loop with partial data"""
        
        context = test_user_context
        context.metadata = {
            'user_request': 'Reduce our OpenAI costs',
            'data_result': {
                'monthly_spend': 50000,
                # Missing: token counts, model distribution, etc.
            }
        }
        
        agent = ReportingSubAgent(context)
        result = await agent.execute(context, stream_updates=True)
        
        assert result['loop_type'] == 'DATA_DISCOVERY'
        assert result['value_level'] == 'MINIMAL'
        assert 'data_requests' in result['next_steps']
        assert 'token_usage' in result['next_steps']['data_requests']
        
    @pytest.mark.critical
    async def test_refinement_loop(self, test_user_context):
        """Test refinement loop after initial report"""
        
        context = test_user_context
        context.metadata = {
            'user_request': 'What about latency optimization?',
            'previous_report_id': 'report_123',
            'data_result': {
                'monthly_spend': 50000,
                'token_usage': {...},
                # Has cost data, asking about latency
            }
        }
        
        agent = ReportingSubAgent(context)
        result = await agent.execute(context, stream_updates=True)
        
        assert result['loop_type'] == 'REFINEMENT'
        assert 'latency' in result['next_steps']['data_requests']
        assert result['report']['maintains_context'] == True
```

### 3. Progressive Value Level Tests

```python
class TestProgressiveValue:
    """Test value delivery at each level"""
    
    @pytest.mark.critical
    async def test_full_value_delivery(self, test_user_context):
        """Test FULL value with complete data"""
        
        context = test_user_context
        context.metadata = {
            'user_request': 'Optimize our AI costs',
            'triage_result': {'category': 'cost_optimization'},
            'data_result': complete_test_data(),
            'optimizations_result': optimization_recommendations(),
            'action_plan_result': implementation_plan()
        }
        
        agent = ReportingSubAgent(context)
        result = await agent.execute(context, stream_updates=True)
        
        assert result['value_level'] == 'FULL'
        assert result['data_completeness'] >= 0.9
        assert 'implementation_plan' in result['report']
        assert result['report']['confidence_score'] >= 0.85
        
    @pytest.mark.critical
    async def test_degradation_chain(self, test_user_context):
        """Test graceful degradation through value levels"""
        
        data_levels = [
            ({}, 'FALLBACK_IMAGINATION'),
            ({'triage_result': {...}}, 'MINIMAL'),
            ({'triage_result': {...}, 'data_result': {...}}, 'BASIC'),
            ({'triage_result': {...}, 'data_result': {...}, 
              'optimizations_result': {...}}, 'STANDARD'),
            ({'triage_result': {...}, 'data_result': {...},
              'optimizations_result': {...}, 'action_plan_result': {...}}, 'FULL')
        ]
        
        for data, expected_level in data_levels:
            context = test_user_context
            context.metadata = data
            
            agent = ReportingSubAgent(context)
            result = await agent.execute(context, stream_updates=True)
            
            assert result['success'] == True  # Never fails
            assert result['value_level'] == expected_level
            assert 'report' in result  # Always has output
```

### 4. Multi-Iteration Journey Tests

```python
class TestUserJourneys:
    """Test complete user journeys through multiple iterations"""
    
    @pytest.mark.critical
    async def test_zero_to_optimization_journey(self, test_user_context):
        """Test complete journey from no data to full optimization"""
        
        agent = ReportingSubAgent(test_user_context)
        journey_results = []
        
        # Iteration 1: User starts with vague problem
        context = test_user_context
        context.metadata = {
            'user_request': 'Boss says reduce AI costs',
            'iteration': 1
        }
        
        result1 = await agent.execute(context, stream_updates=True)
        journey_results.append(result1)
        
        assert result1['loop_type'] == 'IMAGINATION'
        assert 'data_collection_guide' in result1['report']
        
        # Iteration 2: User provides some data
        context.metadata = {
            'user_request': 'Here is our OpenAI usage',
            'iteration': 2,
            'data_result': {
                'monthly_spend': 50000,
                'api_calls': 1000000
            }
        }
        
        result2 = await agent.execute(context, stream_updates=True)
        journey_results.append(result2)
        
        assert result2['loop_type'] == 'DATA_DISCOVERY'
        assert result2['value_level'] in ['MINIMAL', 'BASIC']
        assert 'initial_insights' in result2['report']
        
        # Iteration 3: User provides requested data
        context.metadata.update({
            'user_request': 'Added token usage data',
            'iteration': 3,
            'data_result': {
                'monthly_spend': 50000,
                'api_calls': 1000000,
                'token_usage': {...},
                'model_distribution': {...}
            }
        })
        
        result3 = await agent.execute(context, stream_updates=True)
        journey_results.append(result3)
        
        assert result3['value_level'] in ['STANDARD', 'FULL']
        assert 'optimization_plan' in result3['report']
        
        # Iteration 4: User asks refinement question
        context.metadata['user_request'] = 'What about latency impact?'
        context.metadata['iteration'] = 4
        
        result4 = await agent.execute(context, stream_updates=True)
        journey_results.append(result4)
        
        assert result4['loop_type'] == 'REFINEMENT'
        assert result4['report']['includes_latency_analysis'] == True
        
        # Verify journey continuity
        assert all(r['success'] for r in journey_results)
        assert journey_results[-1]['journey_progress'] > 0.8
```

### 5. Data Helper Integration Tests

```python
class TestDataHelperIntegration:
    """Test automatic data helper triggering"""
    
    @pytest.mark.critical
    async def test_automatic_data_helper_trigger(self, test_user_context):
        """Test data helper triggers on insufficient data"""
        
        context = test_user_context
        context.metadata = {
            'user_request': 'Optimize our AI',
            'data_result': {'monthly_spend': 50000}  # Insufficient
        }
        
        agent = ReportingSubAgent(context)
        result = await agent.execute(context, stream_updates=True)
        
        assert result['success'] == True
        assert 'data_helper_triggered' in result
        assert result['data_helper_triggered'] == True
        
        # Verify data request quality
        data_request = result['next_steps']['data_requests']
        assert 'token_usage' in data_request
        assert 'collection_instructions' in data_request
        assert 'example_formats' in data_request
        
    @pytest.mark.critical
    async def test_contextual_data_requests(self, test_user_context):
        """Test data requests are contextual to user's journey"""
        
        # First-time user gets educational request
        context_new = test_user_context
        context_new.metadata = {'user_request': 'Help', 'iteration': 1}
        
        agent = ReportingSubAgent(context_new)
        result_new = await agent.execute(context_new, stream_updates=True)
        
        assert 'educational' in result_new['next_steps']['tone']
        assert len(result_new['next_steps']['data_requests']) <= 3  # Don't overwhelm
        
        # Experienced user gets direct request
        context_exp = test_user_context
        context_exp.metadata = {
            'user_request': 'Need latency data', 
            'iteration': 5,
            'has_previous_reports': True
        }
        
        result_exp = await agent.execute(context_exp, stream_updates=True)
        
        assert 'direct' in result_exp['next_steps']['tone']
        assert 'technical_details' in result_exp['next_steps']
```

### 6. Context Preservation Tests

```python
class TestContextPreservation:
    """Test context maintained across iterations"""
    
    @pytest.mark.critical
    async def test_context_across_iterations(self, test_user_context):
        """Test context preserved between user interactions"""
        
        agent = ReportingSubAgent(test_user_context)
        
        # First iteration
        context = test_user_context
        context.metadata = {
            'user_request': 'Reduce costs for GPT-4',
            'data_result': {'model': 'gpt-4', 'monthly_cost': 30000}
        }
        
        result1 = await agent.execute(context, stream_updates=True)
        
        # Second iteration - should remember GPT-4 focus
        context.metadata = {
            'user_request': 'What about caching?',
            'iteration': 2
        }
        
        result2 = await agent.execute(context, stream_updates=True)
        
        assert 'gpt-4' in result2['report']['context_maintained']
        assert result2['report']['focuses_on_caching'] == True
        assert result2['report']['relates_to_previous'] == True
        
    @pytest.mark.critical
    async def test_checkpoint_recovery(self, test_user_context):
        """Test recovery from checkpoints in loops"""
        
        agent = ReportingSubAgent(test_user_context)
        
        # Simulate partial completion
        checkpoint_data = {
            'loop_id': 'loop_123',
            'iteration': 2,
            'data_collected': {'cost': 50000},
            'insights_generated': ['High API usage'],
            'next_expected_action': 'collect_token_data'
        }
        
        await agent.checkpoint_manager.save_loop_checkpoint(checkpoint_data)
        
        # Simulate crash and recovery
        new_agent = ReportingSubAgent(test_user_context)
        resumed = await new_agent.checkpoint_manager.resume_from_checkpoint(
            test_user_context.user_id
        )
        
        assert resumed is not None
        assert resumed.loop_id == 'loop_123'
        assert resumed.iteration == 2
```

### 7. Error Recovery Tests

```python
class TestErrorRecovery:
    """Test system never crashes, always delivers value"""
    
    @pytest.mark.critical
    async def test_never_crashes_on_bad_data(self, test_user_context):
        """Test resilience to malformed data"""
        
        bad_data_scenarios = [
            {'data_result': None},
            {'data_result': 'not_a_dict'},
            {'data_result': {'circular': ...}},  # Circular reference
            {'action_plan_result': float('inf')},  # Infinity
            {'triage_result': {'nested': {'very': {'deep': {...}}}}},
        ]
        
        for bad_data in bad_data_scenarios:
            context = test_user_context
            context.metadata = bad_data
            
            agent = ReportingSubAgent(context)
            result = await agent.execute(context, stream_updates=True)
            
            assert result['success'] == True  # Never fails
            assert 'report' in result  # Always has output
            assert result['value_level'] in ['FALLBACK_IMAGINATION', 'MINIMAL']
    
    @pytest.mark.critical
    async def test_timeout_recovery(self, test_user_context):
        """Test recovery from timeouts"""
        
        context = test_user_context
        context.metadata = {
            'user_request': 'Optimize everything',
            'force_timeout': True  # Simulate timeout
        }
        
        agent = ReportingSubAgent(context)
        
        # Should recover and provide value
        result = await agent.execute(context, stream_updates=True)
        
        assert result['success'] == True
        assert 'partial_results' in result['report']
        assert result['next_steps']['retry_available'] == True
```

### 8. Performance Tests

```python
class TestUVSPerformance:
    """Test performance across iterations"""
    
    @pytest.mark.performance
    async def test_iteration_performance(self, test_user_context):
        """Test performance doesn't degrade over iterations"""
        
        agent = ReportingSubAgent(test_user_context)
        iteration_times = []
        
        for i in range(10):
            context = test_user_context
            context.metadata = {
                'user_request': f'Iteration {i}',
                'iteration': i,
                'data_result': {'size': i * 1000}  # Growing data
            }
            
            start = time.time()
            result = await agent.execute(context, stream_updates=True)
            iteration_times.append(time.time() - start)
            
            assert result['success'] == True
        
        # Performance should not degrade significantly
        avg_first_5 = sum(iteration_times[:5]) / 5
        avg_last_5 = sum(iteration_times[5:]) / 5
        
        assert avg_last_5 < avg_first_5 * 1.5  # Max 50% degradation
        assert max(iteration_times) < 5.0  # No iteration over 5 seconds
```

### 9. WebSocket Event Tests

```python
class TestWebSocketEvents:
    """Test WebSocket events through loops"""
    
    @pytest.mark.critical
    async def test_events_during_loops(self, test_user_context):
        """Test all required events sent during iterations"""
        
        events_captured = []
        
        async with websocket_listener(capture_to=events_captured):
            agent = ReportingSubAgent(test_user_context)
            
            # Execute multiple iterations
            for i in range(3):
                context = test_user_context
                context.metadata = {
                    'user_request': f'Request {i}',
                    'iteration': i
                }
                
                await agent.execute(context, stream_updates=True)
        
        # Verify events for each iteration
        for i in range(3):
            iteration_events = [e for e in events_captured if f'iteration_{i}' in str(e)]
            
            assert has_event(iteration_events, 'agent_started')
            assert has_event(iteration_events, 'agent_thinking')
            assert has_event(iteration_events, 'tool_executing')
            assert has_event(iteration_events, 'agent_completed')
```

### 10. End-to-End User Scenarios

```python
class TestRealUserScenarios:
    """Test real user scenarios from requirements"""
    
    @pytest.mark.e2e
    async def test_boss_wants_cost_reduction(self, test_user_context):
        """Test: Boss tells user to reduce AI costs"""
        
        agent = ReportingSubAgent(test_user_context)
        
        # User's first attempt - confused
        result1 = await agent.execute(test_user_context, {
            'user_request': 'My boss wants me to reduce AI costs but I dont know where to start'
        })
        
        assert result1['loop_type'] == 'IMAGINATION'
        assert 'start_here' in result1['report']
        assert 'quick_wins' in result1['report']
        
        # User follows guidance
        result2 = await agent.execute(test_user_context, {
            'user_request': 'I got our OpenAI invoice',
            'data_result': {'invoice_total': 50000}
        })
        
        assert result2['value_level'] == 'MINIMAL'
        assert 'need_more_details' in result2['report']
        
        # User provides more data
        result3 = await agent.execute(test_user_context, {
            'user_request': 'Here is the API usage breakdown',
            'data_result': complete_api_usage_data()
        })
        
        assert result3['value_level'] in ['STANDARD', 'FULL']
        assert 'savings_potential' in result3['report']
        assert result3['report']['savings_potential'] >= 0.2  # 20% minimum
```

## DELIVERABLES:

Create test specifications including:

1. **Test Matrix** - All loop types × value levels
2. **Journey Test Scenarios** - Multi-iteration flows
3. **Failure Injection Tests** - Resilience validation
4. **Performance Benchmarks** - Iteration performance
5. **Integration Test Suite** - DataHelper, Triage, etc.
6. **User Scenario Tests** - Real-world examples
7. **Regression Test Suite** - Backward compatibility

## VALIDATION CHECKLIST:

- [ ] All loop types tested
- [ ] All value levels tested
- [ ] Multi-iteration journeys verified
- [ ] Context preservation validated
- [ ] Data helper integration tested
- [ ] Zero crash guarantee proven
- [ ] Performance targets met
- [ ] Real services used (NO MOCKS)
- [ ] WebSocket events validated
- [ ] User scenarios covered

Remember: Tests must validate that the system helps users through their ENTIRE optimization journey, not just single interactions. Every test must use REAL SERVICES - no mocks allowed.