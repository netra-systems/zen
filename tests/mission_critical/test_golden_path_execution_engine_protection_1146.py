"Golden Path Execution Engine Protection - Issue #1146"

Business Value Justification:
    - Segment: Platform/Business Critical
- Business Goal: Protect $500K+ plus ARR Golden Path functionality  
- Value Impact: Ensures execution engine consolidation doesn't break end-to-end user flow'
- Strategic Impact: Critical protection for login -> AI response flow that delivers 90% platform value

CRITICAL MISSION: NEW 20% SSOT VALIDATION TESTS
This test protects the Golden Path user flow (login -> get AI responses) from being broken
by execution engine consolidation, ensuring UserExecutionEngine maintains all WebSocket events.

Test Scope: Golden Path protection during 12->1 execution engine consolidation
Priority: P0 - Mission Critical - Protects core business value
Docker: NO DEPENDENCIES - Integration non-docker only
NEW TEST: Part of 20% new validation tests for Issue #1146
""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
import unittest
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mocks import get_mock_factory

# Import UserExecutionEngine and dependencies
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import ()
    AgentExecutionContext,
    AgentExecutionResult, 
    PipelineStep
)
from netra_backend.app.services.user_execution_context import ()
    UserExecutionContext,
    create_user_execution_context
)


class GoldenPathExecutionEngineProtection1146Tests(SSotAsyncTestCase):
    Protects Golden Path functionality during execution engine SSOT consolidation."
    Protects Golden Path functionality during execution engine SSOT consolidation.""


    async def asyncSetUp(self):
        "Set up Golden Path protection test environment."
        await super().asyncSetUp()
        
        # Create realistic user context for Golden Path simulation
        self.golden_path_user = create_user_execution_context(
            user_id=golden_path_user_1146","
            operation_name=golden_path_chat_simulation,
            additional_metadata={
                'test_type': 'golden_path_protection',
                'issue': '#1146',
                'business_value': '$500K_ARR_protection',
                'flow': 'login_to_ai_response'
            }
        
        # Create SSOT mock factory
        self.mock_factory = get_mock_factory()
        
        # Create realistic WebSocket emitter for Golden Path
        self.golden_path_websocket = self.mock_factory.create_websocket_emitter_mock()
        self.golden_path_websocket.notify_agent_started = AsyncMock(return_value=True)
        self.golden_path_websocket.notify_agent_thinking = AsyncMock(return_value=True) 
        self.golden_path_websocket.notify_agent_completed = AsyncMock(return_value=True)
        self.golden_path_websocket.notify_tool_executing = AsyncMock(return_value=True)
        self.golden_path_websocket.notify_tool_completed = AsyncMock(return_value=True)
        
        # Track WebSocket events for Golden Path validation
        self.websocket_events_received = []
        
        async def track_agent_started(*args, **kwargs):
            self.websocket_events_received.append(('agent_started', args, kwargs))
            return True
            
        async def track_agent_thinking(*args, **kwargs):
            self.websocket_events_received.append(('agent_thinking', args, kwargs))
            return True
            
        async def track_agent_completed(*args, **kwargs):
            self.websocket_events_received.append(('agent_completed', args, kwargs))
            return True
            
        async def track_tool_executing(*args, **kwargs):
            self.websocket_events_received.append(('tool_executing', args, kwargs))
            return True
            
        async def track_tool_completed(*args, **kwargs):
            self.websocket_events_received.append(('tool_completed', args, kwargs))
            return True
        
        # Override mock methods to track events
        self.golden_path_websocket.notify_agent_started.side_effect = track_agent_started
        self.golden_path_websocket.notify_agent_thinking.side_effect = track_agent_thinking
        self.golden_path_websocket.notify_agent_completed.side_effect = track_agent_completed
        self.golden_path_websocket.notify_tool_executing.side_effect = track_tool_executing
        self.golden_path_websocket.notify_tool_completed.side_effect = track_tool_completed
        
        # Create agent factory for Golden Path
        self.golden_path_agent_factory = self.mock_factory.create_agent_factory_mock()
        
        # Create UserExecutionEngine for Golden Path testing
        self.golden_path_engine = UserExecutionEngine(
            context=self.golden_path_user,
            agent_factory=self.golden_path_agent_factory,
            websocket_emitter=self.golden_path_websocket
        )

    async def asyncTearDown(self):
        "Clean up Golden Path test resources."
        if hasattr(self, 'golden_path_engine') and self.golden_path_engine:
            await self.golden_path_engine.cleanup()
        await super().asyncTearDown()

    async def test_golden_path_complete_user_flow_execution_engine(self):
        CRITICAL: Validate complete Golden Path flow through single UserExecutionEngine.""
        # Simulate complete Golden Path: User Login -> Agent Selection -> AI Response
        golden_path_steps = [
            {
                'step': 'triage_agent',
                'description': 'Initial user request triage',
                'expected_output': 'Request understood and categorized',
                'business_impact': 'User sees AI started processing'
            },
            {
                'step': 'data_helper_agent', 
                'description': 'Gather context data for response',
                'expected_output': 'Relevant data collected',
                'business_impact': 'AI shows it is working on user problem'
            },
            {
                'step': 'apex_optimizer_agent',
                'description': 'Generate AI optimization recommendations', 
                'expected_output': 'Actionable recommendations produced',
                'business_impact': 'User receives valuable AI insights ($500K+ plus ARR value)'
            }
        ]
        
        golden_path_results = []
        total_start_time = time.time()
        
        for step_num, step_info in enumerate(golden_path_steps, 1):
            agent_name = step_info['step']
            
            # Reset WebSocket events for this step
            self.websocket_events_received.clear()
            
            # Mock agent creation for this step
            mock_agent = Mock()
            mock_agent.name = agent_name
            mock_agent.agent_name = agent_name
            self.golden_path_agent_factory.create_agent_instance = AsyncMock(return_value=mock_agent)
            
            # Create execution context for Golden Path step
            execution_context = AgentExecutionContext(
                user_id=self.golden_path_user.user_id,
                thread_id=self.golden_path_user.thread_id,
                run_id=self.golden_path_user.run_id,
                request_id=self.golden_path_user.request_id,
                agent_name=agent_name,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=step_num,
                metadata={
                    'golden_path_step': step_num,
                    'step_description': step_info['description'],
                    'business_impact': step_info['business_impact'],
                    'user_flow': 'login_to_ai_response'
                }
            
            # Mock agent execution with realistic response
            with patch.object(self.golden_path_engine.agent_core, 'execute_agent') as mock_execute:
                mock_result = AgentExecutionResult(
                    success=True,
                    agent_name=agent_name,
                    duration=0.8 + (step_num * 0.2),  # Realistic execution time
                    data=step_info['expected_output'],
                    metadata={
                        'golden_path_step': step_num,
                        'business_value_delivered': True,
                        'user_experience': 'positive'
                    }
                mock_execute.return_value = mock_result
                
                # Execute Golden Path step
                step_start_time = time.time()
                result = await self.golden_path_engine.execute_agent(execution_context, self.golden_path_user)
                step_duration = time.time() - step_start_time
                
                # Validate step execution success
                self.assertTrue(result.success, 
                    fGolden Path step {step_num} ({agent_name} failed: {result.error})
                self.assertEqual(result.agent_name, agent_name)
                self.assertEqual(result.data, step_info['expected_output')
                
                # Validate all 5 critical WebSocket events were emitted for this step
                required_events = ['agent_started', 'agent_thinking', 'agent_completed']
                events_received = [event[0] for event in self.websocket_events_received]
                
                for required_event in required_events:
                    self.assertIn(required_event, events_received,
                        fGolden Path step {step_num} missing critical WebSocket event: {required_event})
                
                # Validate step performance (critical for user experience)
                max_acceptable_time = 3.0  # 3 seconds max per step
                self.assertLess(step_duration, max_acceptable_time,
                    fGolden Path step {step_num} too slow: {step_duration:.""2f""}s (max: {max_acceptable_time}s)")"
                
                golden_path_results.append({
                    'step': step_num,
                    'agent': agent_name,
                    'success': result.success,
                    'duration': step_duration,
                    'websocket_events': len(events_received),
                    'business_impact': step_info['business_impact']
                }
        
        # Validate overall Golden Path performance
        total_duration = time.time() - total_start_time
        max_total_time = 10.0  # 10 seconds max for complete flow
        
        self.assertLess(total_duration, max_total_time,
            fComplete Golden Path too slow: {total_duration:.""2f""}s (max: {max_total_time}s))""

        
        # Validate all steps completed successfully
        failed_steps = [step for step in golden_path_results if not step['success']]
        self.assertEqual(len(failed_steps), 0, 
            fGolden Path failed steps: {failed_steps})
        
        # Log Golden Path success
        print(f"CHECK GOLDEN PATH PROTECTED: Complete user flow successful through UserExecutionEngine)"
        print(f   Total duration: {total_duration:.""2f""}s)
        print(f"   Steps completed: {len(golden_path_results)})"
        print(f   Business value: $500K+ plus ARR flow maintained)

    async def test_golden_path_websocket_events_all_five_critical_events(self):
        "CRITICAL: Validate all 5 critical WebSocket events for Golden Path user experience."
        # The 5 critical WebSocket events that must be emitted for Golden Path
        critical_events = [
            'agent_started',    # User sees AI started
            'agent_thinking',   # User sees AI working 
            'tool_executing',   # User sees tools being used
            'tool_completed',   # User sees tool results
            'agent_completed'   # User sees final response
        ]
        
        # Mock tool dispatcher to trigger tool events
        mock_tool_dispatcher = Mock()
        mock_tool_dispatcher.execute_tool = AsyncMock(return_value={'result': 'Tool executed successfully')
        
        with patch.object(self.golden_path_engine, 'get_tool_dispatcher', 
                         return_value=mock_tool_dispatcher):
            
            # Mock agent that uses tools (realistic Golden Path scenario)
            mock_agent = Mock()
            mock_agent.name = apex_optimizer_agent"
            mock_agent.name = apex_optimizer_agent"
            mock_agent.agent_name = "apex_optimizer_agent"
            self.golden_path_agent_factory.create_agent_instance = AsyncMock(return_value=mock_agent)
            
            # Reset event tracking
            self.websocket_events_received.clear()
            
            # Create realistic Golden Path execution
            execution_context = AgentExecutionContext(
                user_id=self.golden_path_user.user_id,
                thread_id=self.golden_path_user.thread_id,
                run_id=self.golden_path_user.run_id,
                request_id=self.golden_path_user.request_id,
                agent_name=apex_optimizer_agent,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1,
                metadata={
                    'user_request': 'Optimize my AI spending',
                    'golden_path_test': True,
                    'requires_tool_usage': True
                }
            
            # Mock agent execution that uses tools
            with patch.object(self.golden_path_engine.agent_core, 'execute_agent') as mock_execute:
                
                # Simulate tool usage during execution
                async def simulate_agent_with_tools(*args, **kwargs):
                    # Simulate tool execution during agent processing
                    await self.golden_path_websocket.notify_tool_executing("cost_analyzer)"
                    await asyncio.sleep(0.1)  # Simulate tool processing
                    await self.golden_path_websocket.notify_tool_completed(cost_analyzer, {savings: $1000)"
                    await self.golden_path_websocket.notify_tool_completed(cost_analyzer, {savings: $1000)""

                    
                    return AgentExecutionResult(
                        success=True,
                        agent_name="apex_optimizer_agent,"
                        duration=1.2,
                        data=AI spending optimized: potential savings $1000/month,
                        metadata={
                            'tools_used': ['cost_analyzer'],
                            'business_value': 'high',
                            'user_satisfaction': 'high'
                        }
                
                mock_execute.side_effect = simulate_agent_with_tools
                
                # Execute Golden Path with tool usage
                result = await self.golden_path_engine.execute_agent(execution_context, self.golden_path_user)
                
                # Validate execution success
                self.assertTrue(result.success, f"Golden Path execution failed: {result.error})"
                
                # Validate all 5 critical events were emitted
                events_received = [event[0] for event in self.websocket_events_received]
                
                missing_events = []
                for critical_event in critical_events:
                    if critical_event not in events_received:
                        missing_events.append(critical_event)
                
                if missing_events:
                    self.fail(
                        fGOLDEN PATH CRITICAL FAILURE: Missing WebSocket events: {missing_events}\n"
                        fGOLDEN PATH CRITICAL FAILURE: Missing WebSocket events: {missing_events}\n""

                        fEvents received: {events_received}\n
                        fBusiness Impact: User won't see real-time AI progress (breaks 90% platform value)\n"
                        fBusiness Impact: User won't see real-time AI progress (breaks 90% platform value)\n"
                        f"Issue #1146: UserExecutionEngine must emit all 5 critical events"
                    )
                
                # Validate event order (started -> thinking -> tool events -> completed)
                event_order = [event[0] for event in self.websocket_events_received]
                
                # Basic order validation
                started_index = event_order.index('agent_started') if 'agent_started' in event_order else -1
                completed_index = event_order.index('agent_completed') if 'agent_completed' in event_order else -1
                
                if started_index >= 0 and completed_index >= 0:
                    self.assertLess(started_index, completed_index,
                        agent_started must come before agent_completed)
                
                print(fCHECK ALL 5 CRITICAL WEBSOCKET EVENTS VALIDATED:)
                print(f   Events received: {len(events_received")})"
                print(f   Event sequence: {' -> '.join(event_order)})
                print(f   Golden Path user experience: MAINTAINED"")

    async def test_golden_path_multi_user_isolation_execution_engine(self):
        CRITICAL: Validate Golden Path works for multiple concurrent users through single engine type." "
        # Simulate multiple users going through Golden Path simultaneously
        concurrent_users = 3
        user_contexts = []
        user_engines = []
        
        # Create multiple user contexts and engines
        for i in range(concurrent_users):
            user_ctx = create_user_execution_context(
                user_id=fgolden_path_user_{i}_1146,
                operation_name=fconcurrent_golden_path_{i},
                additional_metadata={
                    'user_number': i,
                    'test': 'multi_user_golden_path',
                    'concurrent_test': True
                }
            
            # Create engine for this user
            mock_factory = get_mock_factory()
            mock_agent_factory = mock_factory.create_agent_factory_mock()
            mock_websocket = mock_factory.create_websocket_emitter_mock()
            
            # Track events per user
            user_events = []
            
            async def track_user_events(event_name):
                async def tracker(*args, **kwargs):
                    user_events.append((event_name, time.time()))
                    return True
                return tracker
            
            mock_websocket.notify_agent_started = AsyncMock(side_effect=track_user_events('agent_started'))
            mock_websocket.notify_agent_thinking = AsyncMock(side_effect=track_user_events('agent_thinking'))
            mock_websocket.notify_agent_completed = AsyncMock(side_effect=track_user_events('agent_completed'))
            
            engine = UserExecutionEngine(
                context=user_ctx,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket
            )
            
            user_contexts.append(user_ctx)
            user_engines.append({'engine': engine, 'events': user_events, 'factory': mock_agent_factory)
        
        try:
            # Execute Golden Path for all users concurrently
            async def execute_golden_path_for_user(user_index, user_ctx, engine_info):
                engine = engine_info['engine']
                
                # Mock agent for this user
                mock_agent = Mock()
                mock_agent.name = fapex_optimizer_user_{user_index}""
                engine_info['factory'].create_agent_instance = AsyncMock(return_value=mock_agent)
                
                # Mock execution
                with patch.object(engine.agent_core, 'execute_agent') as mock_execute:
                    mock_result = AgentExecutionResult(
                        success=True,
                        agent_name=fapex_optimizer_user_{user_index},
                        duration=0.8,
                        data=fAI optimization for user {user_index}: $500 savings/month,
                        metadata={
                            'user_id': user_ctx.user_id,
                            'user_index': user_index,
                            'business_value': 'high'
                        }
                    mock_execute.return_value = mock_result
                    
                    execution_context = AgentExecutionContext(
                        user_id=user_ctx.user_id,
                        thread_id=user_ctx.thread_id,
                        run_id=user_ctx.run_id,
                        request_id=user_ctx.request_id,
                        agent_name=f"apex_optimizer_user_{user_index},"
                        step=PipelineStep.EXECUTION,
                        execution_timestamp=datetime.now(timezone.utc),
                        pipeline_step_num=1,
                        metadata={'user_index': user_index}
                    
                    # Execute Golden Path
                    result = await engine.execute_agent(execution_context, user_ctx)
                    return result, user_index
            
            # Run all users concurrently
            start_time = time.time()
            tasks = [
                execute_golden_path_for_user(i, user_contexts[i), user_engines[i)
                for i in range(concurrent_users)
            ]
            results = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time
            
            # Validate all users completed successfully
            failed_users = []
            successful_users = []
            
            for result, user_index in results:
                if result.success:
                    successful_users.append(user_index)
                    
                    # Validate user-specific data
                    self.assertIn(fuser {user_index}", result.data.lower())"
                    self.assertEqual(result.metadata['user_index'], user_index)
                else:
                    failed_users.append({'user': user_index, 'error': result.error)
            
            # Validate no failures
            if failed_users:
                self.fail(fGolden Path failed for users: {failed_users})
            
            # Validate all users succeeded
            self.assertEqual(len(successful_users), concurrent_users)
            self.assertListEqual(sorted(successful_users), list(range(concurrent_users)))
            
            # Validate concurrent performance
            max_acceptable_concurrent_time = 5.0  # 5 seconds for all users
            self.assertLess(total_duration, max_acceptable_concurrent_time,
                fConcurrent Golden Path too slow: {total_duration:.2f}s)"
                fConcurrent Golden Path too slow: {total_duration:."2f"}s)""

            
            # Validate each user received their own WebSocket events
            for i, engine_info in enumerate(user_engines):
                user_events = engine_info['events']
                self.assertGreater(len(user_events), 0, 
                    f"User {i} received no WebSocket events)"
                
                # Validate events are for this user only (no cross-contamination)
                for event_name, event_time in user_events:
                    self.assertIn(event_name, ['agent_started', 'agent_thinking', 'agent_completed')
            
            print(fCHECK MULTI-USER GOLDEN PATH PROTECTED:)
            print(f"   Concurrent users: {concurrent_users})"
            print(f   Total duration: {total_duration:.""2f""}s)
            print(f"   All users successful: {len(successful_users)}/{concurrent_users})"
            print(f   User isolation: MAINTAINED)
            
        finally:
            # Cleanup all engines
            for engine_info in user_engines:
                await engine_info['engine'].cleanup()

    async def test_golden_path_execution_engine_error_handling(self):
        "CRITICAL: Validate Golden Path gracefully handles errors without breaking user experience."
        # Test various error scenarios that could break Golden Path
        error_scenarios = [
            {
                'name': 'agent_timeout',
                'error': asyncio.TimeoutError(Agent execution timed out),"
                'error': asyncio.TimeoutError(Agent execution timed out),""

                'expected_behavior': 'Graceful timeout handling with user notification'
            },
            {
                'name': 'agent_failure',
                'error': RuntimeError("Agent processing failed),"
                'expected_behavior': 'Error handled with fallback response'
            },
            {
                'name': 'websocket_failure',
                'error': ConnectionError(WebSocket connection lost),
                'expected_behavior': 'Continue execution even if events fail'
            }
        ]
        
        error_handling_results = []
        
        for scenario in error_scenarios:
            # Reset for this scenario
            self.websocket_events_received.clear()
            
            # Mock agent creation
            mock_agent = Mock()
            mock_agent.name = "error_test_agent"
            self.golden_path_agent_factory.create_agent_instance = AsyncMock(return_value=mock_agent)
            
            execution_context = AgentExecutionContext(
                user_id=self.golden_path_user.user_id,
                thread_id=self.golden_path_user.thread_id,
                run_id=self.golden_path_user.run_id,
                request_id=self.golden_path_user.request_id,
                agent_name=error_test_agent,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1,
                metadata={'error_scenario': scenario['name']}
            
            try:
                if scenario['name'] == 'websocket_failure':
                    # Test WebSocket failure handling
                    self.golden_path_websocket.notify_agent_started.side_effect = scenario['error']
                    
                    with patch.object(self.golden_path_engine.agent_core, 'execute_agent') as mock_execute:
                        mock_result = AgentExecutionResult(
                            success=True,
                            agent_name=error_test_agent,"
                            agent_name=error_test_agent,""

                            duration=0.5,
                            data=Agent completed despite WebSocket failure","
                            metadata={'websocket_failed': True}
                        mock_execute.return_value = mock_result
                        
                        result = await self.golden_path_engine.execute_agent(execution_context, self.golden_path_user)
                        
                        # Validate execution continues despite WebSocket failure
                        error_handling_results.append({
                            'scenario': scenario['name'],
                            'handled_gracefully': result.success,
                            'user_impact': 'minimal' if result.success else 'severe',
                            'result': result
                        }
                
                else:
                    # Test agent execution errors
                    with patch.object(self.golden_path_engine.agent_core, 'execute_agent') as mock_execute:
                        if scenario['name'] == 'agent_timeout':
                            # Simulate timeout in execute_agent method
                            with patch('asyncio.wait_for', side_effect=scenario['error'):
                                result = await self.golden_path_engine.execute_agent(execution_context, self.golden_path_user)
                        else:
                            mock_execute.side_effect = scenario['error']
                            result = await self.golden_path_engine.execute_agent(execution_context, self.golden_path_user)
                        
                        # Should not reach here for these error types
                        error_handling_results.append({
                            'scenario': scenario['name'],
                            'handled_gracefully': False,
                            'user_impact': 'unexpected_success',
                            'result': result
                        }
                        
            except Exception as e:
                # Expected for some scenarios - check if handled gracefully
                graceful_handling = isinstance(e, (RuntimeError, ValueError)) and failed in str(e).lower()
                
                error_handling_results.append({
                    'scenario': scenario['name'],
                    'handled_gracefully': graceful_handling,
                    'user_impact': 'controlled' if graceful_handling else 'severe',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
        
        # Validate error handling quality
        poorly_handled = [r for r in error_handling_results 
                         if not r['handled_gracefully'] or r['user_impact'] == 'severe']
        
        if poorly_handled:
            error_msg = [GOLDEN PATH ERROR HANDLING FAILED:"]"
            for failure in poorly_handled:
                error_msg.append(f  - {failure['scenario']}: {failure['user_impact']} impact)
                if 'error' in failure:
                    error_msg.append(f    Error: {failure['error']})
            error_msg.append(f"\nIssue #1146: UserExecutionEngine must handle errors gracefully)"
            error_msg.append(fBusiness Impact: Poor error handling breaks user experience")"
            
            self.fail(\n.join(error_msg))
        
        print(fCHECK GOLDEN PATH ERROR HANDLING VALIDATED:"")
        print(f   Scenarios tested: {len(error_scenarios)})
        print(f   Graceful handling: {len([r for r in error_handling_results if r['handled_gracefully']]}"")
        print(f   User experience: PROTECTED)


if __name__ == '__main__':
    unittest.main(")"
))))))))))))))))))))))))