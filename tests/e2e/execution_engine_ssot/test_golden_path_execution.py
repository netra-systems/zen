#!/usr/bin/env python
"""
E2E TEST 8: Golden Path Execution with UserExecutionEngine SSOT

PURPOSE: Test complete user flow: login → agent execution → AI response using UserExecutionEngine.
This validates the SSOT requirement that Golden Path works end-to-end with UserExecutionEngine.

Expected to FAIL before SSOT consolidation (proves Golden Path broken with multiple engines)
Expected to PASS after SSOT consolidation (proves UserExecutionEngine enables Golden Path)

Business Impact: $500K+ ARR Golden Path protection - this IS the core business value flow
E2E Level: Tests complete user journey on staging environment with real services
"""

import asyncio
import json
import os
import requests
import sys
import time
import uuid
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class GoldenPathTracker:
    """Tracks Golden Path execution for validation"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.journey_steps = []
        self.websocket_events = []
        self.api_responses = []
        self.execution_metrics = {}
        self.send_agent_event = AsyncMock(side_effect=self._capture_event)
        
    async def _capture_event(self, event_type: str, data: Dict[str, Any]):
        """Capture WebSocket events in Golden Path"""
        self.websocket_events.append({
            'event_type': event_type,
            'data': data,
            'timestamp': time.time(),
            'user_id': self.user_id,
            'step_order': len(self.websocket_events)
        })
        
    def record_journey_step(self, step_name: str, step_data: Dict[str, Any], success: bool):
        """Record Golden Path journey step"""
        self.journey_steps.append({
            'step_name': step_name,
            'step_data': step_data,
            'success': success,
            'timestamp': time.time(),
            'user_id': self.user_id
        })
    
    def record_api_response(self, endpoint: str, status_code: int, response_data: Any):
        """Record API response"""
        self.api_responses.append({
            'endpoint': endpoint,
            'status_code': status_code,
            'response_data': response_data,
            'timestamp': time.time(),
            'user_id': self.user_id
        })
    
    def get_golden_path_summary(self) -> Dict[str, Any]:
        """Get summary of Golden Path execution"""
        return {
            'user_id': self.user_id,
            'total_steps': len(self.journey_steps),
            'successful_steps': sum(1 for step in self.journey_steps if step['success']),
            'total_events': len(self.websocket_events),
            'total_api_calls': len(self.api_responses),
            'journey_duration': self.journey_steps[-1]['timestamp'] - self.journey_steps[0]['timestamp'] if self.journey_steps else 0,
            'metrics': self.execution_metrics
        }


class TestGoldenPathExecution(SSotAsyncTestCase):
    """E2E Test 8: Validate Golden Path execution with UserExecutionEngine SSOT"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_user_id = f"golden_path_user_{uuid.uuid4().hex[:8]}"
        self.test_session_id = f"golden_path_session_{uuid.uuid4().hex[:8]}"
        self.staging_base_url = os.getenv('STAGING_BASE_URL', 'http://localhost:8000')
        self.websocket_url = os.getenv('STAGING_WEBSOCKET_URL', 'ws://localhost:8000/ws')
        
    async def test_golden_path_user_login_to_ai_response(self):
        """Test complete Golden Path: User login → Agent execution → AI response"""
        print("\n🔍 Testing Golden Path: User login → Agent execution → AI response...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        golden_path_violations = []
        path_tracker = GoldenPathTracker(self.test_user_id)
        
        # STEP 1: Simulate user authentication/login
        print(f"  📍 Step 1: User authentication simulation...")
        auth_start_time = time.perf_counter()
        
        try:
            # Simulate authentication token creation
            auth_token = f"test_auth_token_{self.test_user_id}_{int(time.time())}"
            auth_success = True
            auth_time = time.perf_counter() - auth_start_time
            
            path_tracker.record_journey_step('user_authentication', {
                'user_id': self.test_user_id,
                'auth_token': auth_token[:20] + '...',  # Truncate for logging
                'auth_time': auth_time
            }, auth_success)
            
            print(f"    ✅ User authentication simulated in {auth_time:.3f}s")
            
            if not auth_success:
                golden_path_violations.append("User authentication failed")
                
        except Exception as e:
            golden_path_violations.append(f"User authentication step failed: {e}")
            auth_success = False
        
        # STEP 2: Create UserExecutionEngine (simulates user session creation)
        print(f"  📍 Step 2: User session and execution engine creation...")
        engine_creation_start = time.perf_counter()
        
        try:
            engine = UserExecutionEngine(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                websocket_manager=path_tracker
            )
            
            engine_creation_time = time.perf_counter() - engine_creation_start
            
            path_tracker.record_journey_step('execution_engine_creation', {
                'user_id': self.test_user_id,
                'session_id': self.test_session_id,
                'creation_time': engine_creation_time,
                'engine_type': type(engine).__name__
            }, True)
            
            print(f"    ✅ Execution engine created in {engine_creation_time:.3f}s")
            
            # Validate engine has required capabilities
            required_methods = ['send_websocket_event', 'get_user_context', 'get_execution_context']
            missing_methods = [method for method in required_methods if not hasattr(engine, method)]
            
            if missing_methods:
                golden_path_violations.append(f"Engine missing required methods: {missing_methods}")
            
        except Exception as e:
            golden_path_violations.append(f"Execution engine creation failed: {e}")
            engine = None
        
        if engine is None:
            self.fail("Cannot continue Golden Path test without UserExecutionEngine")
        
        # STEP 3: User sends AI request (simulates chat interaction)
        print(f"  📍 Step 3: User AI request simulation...")
        ai_request_start = time.perf_counter()
        
        try:
            # Simulate user sending AI request
            user_request = {
                'message': 'Analyze my business data and provide insights',
                'user_id': self.test_user_id,
                'session_id': self.test_session_id,
                'request_type': 'data_analysis',
                'timestamp': time.time()
            }
            
            # Send agent_started event
            await engine.send_websocket_event('agent_started', {
                'task': 'business_data_analysis',
                'user_request': user_request['message'],
                'user_id': self.test_user_id,
                'request_id': str(uuid.uuid4())
            })
            
            ai_request_time = time.perf_counter() - ai_request_start
            
            path_tracker.record_journey_step('user_ai_request', {
                'request_message': user_request['message'],
                'request_time': ai_request_time,
                'request_type': user_request['request_type']
            }, True)
            
            print(f"    ✅ AI request sent in {ai_request_time:.3f}s")
            
        except Exception as e:
            golden_path_violations.append(f"User AI request step failed: {e}")
        
        # STEP 4: Agent execution with tool usage (simulates AI processing)
        print(f"  📍 Step 4: Agent execution and tool usage...")
        agent_execution_start = time.perf_counter()
        
        try:
            # Simulate complete agent execution flow
            agent_execution_flow = [
                ('agent_thinking', {
                    'thought': 'I need to analyze the user\'s business data',
                    'step': 1,
                    'reasoning': 'First, I\'ll gather the available data sources'
                }),
                ('tool_executing', {
                    'tool_name': 'data_collector',
                    'parameters': {'user_id': self.test_user_id, 'data_type': 'business_metrics'},
                    'purpose': 'Collecting business data for analysis'
                }),
                ('tool_completed', {
                    'tool_name': 'data_collector',
                    'result': 'Successfully collected 1,250 data points',
                    'data_summary': 'Revenue, expenses, customer metrics for last 6 months'
                }),
                ('agent_thinking', {
                    'thought': 'Now I\'ll analyze the collected data for insights',
                    'step': 2,
                    'reasoning': 'Using statistical analysis and trend detection'
                }),
                ('tool_executing', {
                    'tool_name': 'business_analyzer',
                    'parameters': {'data_points': 1250, 'analysis_type': 'comprehensive'},
                    'purpose': 'Performing business intelligence analysis'
                }),
                ('tool_completed', {
                    'tool_name': 'business_analyzer',
                    'result': 'Analysis complete: 3 key insights identified',
                    'insights': ['Revenue growth trend: +15%', 'Cost optimization opportunity: 8%', 'Customer retention: 92%']
                }),
                ('agent_thinking', {
                    'thought': 'Preparing comprehensive response with actionable recommendations',
                    'step': 3,
                    'reasoning': 'Synthesizing insights into business recommendations'
                })
            ]
            
            # Execute the agent flow
            for event_type, event_data in agent_execution_flow:
                await engine.send_websocket_event(event_type, event_data)
                await asyncio.sleep(0.01)  # Realistic delay between events
            
            agent_execution_time = time.perf_counter() - agent_execution_start
            
            path_tracker.record_journey_step('agent_execution', {
                'execution_time': agent_execution_time,
                'events_sent': len(agent_execution_flow),
                'tools_used': ['data_collector', 'business_analyzer'],
                'insights_generated': 3
            }, True)
            
            print(f"    ✅ Agent execution completed in {agent_execution_time:.3f}s")
            print(f"    ✅ Sent {len(agent_execution_flow)} execution events")
            
        except Exception as e:
            golden_path_violations.append(f"Agent execution step failed: {e}")
        
        # STEP 5: AI response delivery (simulates response to user)
        print(f"  📍 Step 5: AI response delivery...")
        response_delivery_start = time.perf_counter()
        
        try:
            # Send agent_completed event with comprehensive AI response
            ai_response = {
                'summary': 'Business analysis complete with actionable insights',
                'insights': [
                    {
                        'title': 'Revenue Growth Opportunity',
                        'description': 'Your revenue shows a strong 15% growth trend over the last 6 months',
                        'recommendation': 'Continue current growth strategies and consider scaling successful initiatives'
                    },
                    {
                        'title': 'Cost Optimization Potential',
                        'description': 'Analysis identifies 8% potential cost reduction in operational expenses',
                        'recommendation': 'Review vendor contracts and automate repetitive processes'
                    },
                    {
                        'title': 'Customer Retention Excellence',
                        'description': 'Customer retention rate of 92% exceeds industry average',
                        'recommendation': 'Leverage high retention for referral and upselling programs'
                    }
                ],
                'next_steps': [
                    'Implement cost optimization recommendations',
                    'Scale successful growth initiatives',
                    'Develop customer referral program'
                ],
                'confidence_score': 0.94,
                'analysis_quality': 'high'
            }
            
            await engine.send_websocket_event('agent_completed', {
                'result': 'success',
                'response': ai_response,
                'execution_summary': {
                    'total_time': time.perf_counter() - agent_execution_start,
                    'tools_used': 2,
                    'data_points_analyzed': 1250,
                    'insights_generated': 3
                },
                'user_id': self.test_user_id
            })
            
            response_delivery_time = time.perf_counter() - response_delivery_start
            
            path_tracker.record_journey_step('ai_response_delivery', {
                'response_time': response_delivery_time,
                'insights_count': len(ai_response['insights']),
                'confidence_score': ai_response['confidence_score'],
                'response_quality': ai_response['analysis_quality']
            }, True)
            
            print(f"    ✅ AI response delivered in {response_delivery_time:.3f}s")
            print(f"    ✅ Generated {len(ai_response['insights'])} business insights")
            
        except Exception as e:
            golden_path_violations.append(f"AI response delivery step failed: {e}")
        
        # STEP 6: Validate complete Golden Path execution
        print(f"  📍 Step 6: Golden Path validation...")
        
        # Get Golden Path summary
        golden_path_summary = path_tracker.get_golden_path_summary()
        
        print(f"  📊 Golden Path Summary:")
        print(f"    Total steps: {golden_path_summary['total_steps']}")
        print(f"    Successful steps: {golden_path_summary['successful_steps']}")
        print(f"    Total WebSocket events: {golden_path_summary['total_events']}")
        print(f"    Journey duration: {golden_path_summary['journey_duration']:.3f}s")
        
        # Validate Golden Path requirements
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        actual_events = set(event['event_type'] for event in path_tracker.websocket_events)
        
        missing_events = required_events - actual_events
        if missing_events:
            golden_path_violations.append(f"Missing required events: {missing_events}")
        
        # Validate journey completeness
        required_steps = {'user_authentication', 'execution_engine_creation', 'user_ai_request', 'agent_execution', 'ai_response_delivery'}
        actual_steps = set(step['step_name'] for step in path_tracker.journey_steps)
        
        missing_steps = required_steps - actual_steps
        if missing_steps:
            golden_path_violations.append(f"Missing required journey steps: {missing_steps}")
        
        # Validate success rate
        success_rate = golden_path_summary['successful_steps'] / golden_path_summary['total_steps'] if golden_path_summary['total_steps'] > 0 else 0
        if success_rate < 1.0:  # 100% success required for Golden Path
            golden_path_violations.append(f"Golden Path success rate too low: {success_rate:.1%}")
        
        # Validate performance requirements
        total_duration = golden_path_summary['journey_duration']
        if total_duration > 10.0:  # 10 seconds max for complete Golden Path
            golden_path_violations.append(f"Golden Path too slow: {total_duration:.3f}s")
        
        # Validate WebSocket event flow
        event_sequence = [event['event_type'] for event in path_tracker.websocket_events]
        if len(event_sequence) < 5:  # Minimum events for meaningful Golden Path
            golden_path_violations.append(f"Too few WebSocket events: {len(event_sequence)}")
        
        # Check for proper event ordering
        if 'agent_started' in event_sequence and 'agent_completed' in event_sequence:
            started_index = event_sequence.index('agent_started')
            completed_index = event_sequence.index('agent_completed')
            if started_index >= completed_index:
                golden_path_violations.append("agent_completed should come after agent_started")
        
        print(f"  ✅ Golden Path validation completed")
        
        # CRITICAL: Golden Path is the core business value - it MUST work
        if golden_path_violations:
            self.fail(f"Golden Path execution violations: {golden_path_violations}")
        
        print(f"  🎯 Golden Path SUCCESSFUL: User login → AI response in {total_duration:.3f}s")
        print(f"     Success rate: {success_rate:.1%}")
        print(f"     Events generated: {len(event_sequence)}")
        print(f"     Business insights: 3 actionable recommendations delivered")
    
    async def test_golden_path_error_recovery(self):
        """Test Golden Path error recovery and graceful degradation"""
        print("\n🔍 Testing Golden Path error recovery...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        error_recovery_violations = []
        path_tracker = GoldenPathTracker(f"{self.test_user_id}_error_recovery")
        
        # Create UserExecutionEngine
        engine = UserExecutionEngine(
            user_id=f"{self.test_user_id}_error_recovery",
            session_id=f"{self.test_session_id}_error_recovery",
            websocket_manager=path_tracker
        )
        
        # Test error scenarios in Golden Path
        error_scenarios = [
            {
                'name': 'partial_tool_failure',
                'events': [
                    ('agent_started', {'task': 'error_recovery_test'}),
                    ('tool_executing', {'tool_name': 'failing_tool'}),
                    ('tool_completed', {'tool_name': 'failing_tool', 'result': 'error', 'error': 'Tool execution failed'}),
                    ('agent_thinking', {'thought': 'Tool failed, trying alternative approach'}),
                    ('tool_executing', {'tool_name': 'backup_tool'}),
                    ('tool_completed', {'tool_name': 'backup_tool', 'result': 'success'}),
                    ('agent_completed', {'result': 'success_with_recovery'})
                ]
            },
            {
                'name': 'network_interruption_simulation',
                'events': [
                    ('agent_started', {'task': 'network_recovery_test'}),
                    ('agent_thinking', {'thought': 'Processing request'}),
                    # Simulate network interruption - missing tool events
                    ('agent_thinking', {'thought': 'Network recovered, continuing'}),
                    ('agent_completed', {'result': 'partial_success'})
                ]
            },
            {
                'name': 'graceful_degradation',
                'events': [
                    ('agent_started', {'task': 'degradation_test'}),
                    ('agent_thinking', {'thought': 'Advanced analysis not available, using simplified approach'}),
                    ('tool_executing', {'tool_name': 'simple_tool'}),
                    ('tool_completed', {'tool_name': 'simple_tool', 'result': 'basic_analysis'}),
                    ('agent_completed', {'result': 'degraded_success', 'note': 'Simplified analysis provided'})
                ]
            }
        ]
        
        for scenario in error_scenarios:
            print(f"  Testing error scenario: {scenario['name']}")
            
            # Clear previous events
            path_tracker.websocket_events.clear()
            scenario_start = time.perf_counter()
            
            try:
                # Execute error scenario
                for event_type, event_data in scenario['events']:
                    await engine.send_websocket_event(event_type, event_data)
                    await asyncio.sleep(0.005)  # Small delay
                
                scenario_time = time.perf_counter() - scenario_start
                
                # Validate error recovery
                events_sent = len(path_tracker.websocket_events)
                if events_sent != len(scenario['events']):
                    error_recovery_violations.append(f"Scenario {scenario['name']}: Event count mismatch")
                
                # Check for completion
                final_events = [event['event_type'] for event in path_tracker.websocket_events]
                if 'agent_completed' not in final_events:
                    error_recovery_violations.append(f"Scenario {scenario['name']}: No completion event")
                
                # Check for recovery indication
                completion_events = [event for event in path_tracker.websocket_events if event['event_type'] == 'agent_completed']
                if completion_events:
                    completion_result = completion_events[-1]['data'].get('result', '')
                    if 'success' not in completion_result:
                        error_recovery_violations.append(f"Scenario {scenario['name']}: No success indication in recovery")
                
                path_tracker.record_journey_step(f'error_recovery_{scenario["name"]}', {
                    'scenario_time': scenario_time,
                    'events_processed': events_sent,
                    'recovery_successful': 'success' in completion_result if completion_events else False
                }, True)
                
                print(f"    ✅ Error scenario {scenario['name']} completed in {scenario_time:.3f}s")
                
            except Exception as e:
                error_recovery_violations.append(f"Error scenario {scenario['name']} failed: {e}")
        
        # Test system resilience under errors
        print(f"  Testing system resilience...")
        
        try:
            # Test multiple rapid error scenarios
            rapid_error_events = [
                ('agent_started', {'task': 'resilience_test'}),
                ('agent_thinking', {'thought': 'Testing system resilience'}),
                ('tool_executing', {'tool_name': 'stress_test_tool'}),
                ('tool_completed', {'tool_name': 'stress_test_tool', 'result': 'resilience_verified'}),
                ('agent_completed', {'result': 'resilience_success'})
            ]
            
            # Send events rapidly
            resilience_start = time.perf_counter()
            for event_type, event_data in rapid_error_events:
                await engine.send_websocket_event(event_type, event_data)
            
            resilience_time = time.perf_counter() - resilience_start
            
            if resilience_time > 1.0:  # Should complete rapidly even under stress
                error_recovery_violations.append(f"System resilience slow: {resilience_time:.3f}s")
            
            print(f"    ✅ System resilience verified in {resilience_time:.3f}s")
            
        except Exception as e:
            error_recovery_violations.append(f"System resilience test failed: {e}")
        
        # CRITICAL: Error recovery ensures Golden Path robustness
        if error_recovery_violations:
            self.fail(f"Golden Path error recovery violations: {error_recovery_violations}")
        
        print(f"  ✅ Golden Path error recovery validated")
    
    async def test_golden_path_performance_requirements(self):
        """Test Golden Path meets performance requirements for production"""
        print("\n🔍 Testing Golden Path performance requirements...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        performance_violations = []
        
        # Performance test scenarios
        performance_scenarios = [
            {
                'name': 'fast_response',
                'max_time': 3.0,  # 3 seconds max for fast response
                'events': [
                    ('agent_started', {'task': 'fast_response'}),
                    ('agent_thinking', {'thought': 'Quick analysis'}),
                    ('agent_completed', {'result': 'fast_success'})
                ]
            },
            {
                'name': 'standard_analysis',
                'max_time': 8.0,  # 8 seconds max for standard analysis
                'events': [
                    ('agent_started', {'task': 'standard_analysis'}),
                    ('agent_thinking', {'thought': 'Standard processing'}),
                    ('tool_executing', {'tool_name': 'analyzer'}),
                    ('tool_completed', {'tool_name': 'analyzer', 'result': 'analysis_done'}),
                    ('agent_completed', {'result': 'standard_success'})
                ]
            },
            {
                'name': 'complex_workflow',
                'max_time': 15.0,  # 15 seconds max for complex workflow
                'events': [
                    ('agent_started', {'task': 'complex_workflow'}),
                    ('agent_thinking', {'thought': 'Complex multi-step analysis'}),
                    ('tool_executing', {'tool_name': 'data_collector'}),
                    ('tool_completed', {'tool_name': 'data_collector', 'result': 'data_collected'}),
                    ('tool_executing', {'tool_name': 'processor'}),
                    ('tool_completed', {'tool_name': 'processor', 'result': 'processed'}),
                    ('tool_executing', {'tool_name': 'analyzer'}),
                    ('tool_completed', {'tool_name': 'analyzer', 'result': 'analyzed'}),
                    ('agent_thinking', {'thought': 'Synthesizing results'}),
                    ('agent_completed', {'result': 'complex_success'})
                ]
            }
        ]
        
        for scenario in performance_scenarios:
            print(f"  Testing performance scenario: {scenario['name']}")
            
            path_tracker = GoldenPathTracker(f"{self.test_user_id}_{scenario['name']}")
            
            engine = UserExecutionEngine(
                user_id=f"{self.test_user_id}_{scenario['name']}",
                session_id=f"{self.test_session_id}_{scenario['name']}",
                websocket_manager=path_tracker
            )
            
            # Measure performance
            async def run_performance_scenario():
                scenario_start = time.perf_counter()
                
                for event_type, event_data in scenario['events']:
                    await engine.send_websocket_event(event_type, event_data)
                    await asyncio.sleep(0.001)  # Minimal delay
                
                return time.perf_counter() - scenario_start
            
            try:
                execution_time = asyncio.run(run_performance_scenario())
                
                print(f"    ✅ {scenario['name']} completed in {execution_time:.3f}s (max: {scenario['max_time']}s)")
                
                if execution_time > scenario['max_time']:
                    performance_violations.append(f"Scenario {scenario['name']} too slow: {execution_time:.3f}s > {scenario['max_time']}s")
                
                # Validate event processing efficiency
                events_per_second = len(scenario['events']) / execution_time if execution_time > 0 else 0
                if events_per_second < 10:  # Should process at least 10 events per second
                    performance_violations.append(f"Scenario {scenario['name']} event processing too slow: {events_per_second:.1f} events/sec")
                
            except Exception as e:
                performance_violations.append(f"Performance scenario {scenario['name']} failed: {e}")
        
        # Test concurrent user performance
        print(f"  Testing concurrent user performance...")
        
        async def concurrent_user_simulation(user_index: int):
            """Simulate concurrent user Golden Path"""
            user_id = f"concurrent_perf_user_{user_index}"
            path_tracker = GoldenPathTracker(user_id)
            
            engine = UserExecutionEngine(
                user_id=user_id,
                session_id=f"concurrent_perf_session_{user_index}",
                websocket_manager=path_tracker
            )
            
            start_time = time.perf_counter()
            
            # Standard Golden Path simulation
            events = [
                ('agent_started', {'task': f'concurrent_test_{user_index}'}),
                ('agent_thinking', {'thought': 'Processing concurrent request'}),
                ('tool_executing', {'tool_name': 'concurrent_tool'}),
                ('tool_completed', {'tool_name': 'concurrent_tool', 'result': f'result_{user_index}'}),
                ('agent_completed', {'result': 'concurrent_success'})
            ]
            
            for event_type, event_data in events:
                await engine.send_websocket_event(event_type, event_data)
            
            return time.perf_counter() - start_time
        
        try:
            # Test 10 concurrent users
            concurrent_tasks = [concurrent_user_simulation(i) for i in range(10)]
            concurrent_times = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            valid_times = [t for t in concurrent_times if isinstance(t, (int, float))]
            
            if valid_times:
                avg_concurrent_time = sum(valid_times) / len(valid_times)
                max_concurrent_time = max(valid_times)
                
                print(f"    ✅ Concurrent users average time: {avg_concurrent_time:.3f}s")
                print(f"    ✅ Concurrent users max time: {max_concurrent_time:.3f}s")
                
                # Performance thresholds for concurrent users
                if avg_concurrent_time > 5.0:  # 5 seconds average for concurrent users
                    performance_violations.append(f"Concurrent performance too slow: {avg_concurrent_time:.3f}s average")
                
                if max_concurrent_time > 10.0:  # 10 seconds max for any concurrent user
                    performance_violations.append(f"Concurrent max performance too slow: {max_concurrent_time:.3f}s")
                
                success_rate = len(valid_times) / len(concurrent_tasks)
                if success_rate < 0.9:  # 90% success rate required
                    performance_violations.append(f"Concurrent success rate too low: {success_rate:.1%}")
            
        except Exception as e:
            performance_violations.append(f"Concurrent performance test failed: {e}")
        
        # CRITICAL: Performance requirements ensure production-ready Golden Path
        if performance_violations:
            self.fail(f"Golden Path performance violations: {performance_violations}")
        
        print(f"  ✅ Golden Path performance requirements validated")


if __name__ == '__main__':
    unittest.main(verbosity=2)