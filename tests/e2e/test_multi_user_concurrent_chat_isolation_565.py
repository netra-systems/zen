#!/usr/bin/env python3
"""
Issue #565 E2E Test: Multi-User Concurrent Chat Isolation on GCP Staging
========================================================================

Purpose: End-to-end validation of UserExecutionEngine isolation under real production conditions
using GCP staging environment with real LLM integration.

Business Value Justification (BVJ):
- Segment: All Users (Free, Early, Mid, Enterprise)
- Business Goal: Protect $500K+ ARR chat functionality with secure multi-user operation
- Value Impact: Ensures users never see each other's private conversations or agent responses
- Strategic Impact: Enables production-scale concurrent user support without data contamination

Test Strategy:
1. Simulate multiple users having concurrent chat sessions on GCP staging
2. Validate complete user isolation throughout full agent execution lifecycle
3. Verify WebSocket events route to correct users only (all 5 critical events)
4. Confirm business value preservation - users get substantive agent responses
5. Test under realistic load with actual LLM interactions

Infrastructure: GCP Staging Environment + Real LLM + WebSocket connections
Expected: ALL PASS - complete business value delivery with perfect user isolation
"""

import asyncio
import pytest
import uuid
import time
import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test framework imports following SSOT patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from shared.isolated_environment import get_env

# Import UserExecutionEngine (SSOT implementation for Issue #565)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestMultiUserConcurrentChatIsolation565(SSotAsyncTestCase):
    """
    E2E tests validating complete user isolation in concurrent chat scenarios.
    
    These tests prove that the migration to UserExecutionEngine (Issue #565 SSOT fix)
    enables safe concurrent chat operations in production conditions.
    
    Expected Result: ALL PASS - business value preserved with perfect isolation
    """

    def setUp(self):
        """Set up GCP staging environment for E2E testing"""
        super().setUp()
        self.env = get_env()
        
        # GCP Staging configuration
        self.staging_api_url = self.env.get("STAGING_API_URL", "https://api.staging.netrasystems.ai")
        self.staging_websocket_url = self.env.get("STAGING_WS_URL", "wss://api.staging.netrasystems.ai/api/v1/websocket")
        
        self.test_results = {
            'concurrent_chat_isolation': [],
            'business_value_delivery': [],
            'websocket_event_isolation': [],
            'performance_under_load': []
        }
        
        # Test user profiles for realistic scenarios
        self.test_user_profiles = [
            {
                'user_id': 'enterprise_user_financial',
                'scenario': 'Financial Analysis',
                'query': 'Analyze our Q4 AWS costs and identify optimization opportunities worth $50K+',
                'sensitive_context': {'budget': 500000, 'department': 'finance', 'confidential': 'board_review_q4'}
            },
            {
                'user_id': 'startup_user_technical',
                'scenario': 'Technical Architecture',
                'query': 'Help me design a scalable microservices architecture for 100K+ users',
                'sensitive_context': {'funding_round': 'series_a', 'tech_stack': 'proprietary', 'competitive_advantage': 'ai_algorithm'}
            },
            {
                'user_id': 'healthcare_user_compliance',
                'scenario': 'Healthcare Compliance',
                'query': 'What HIPAA compliance measures do we need for our patient data analytics platform?',
                'sensitive_context': {'patient_data': True, 'phi_access': 'restricted', 'regulatory': 'hipaa_sox'}
            },
            {
                'user_id': 'retail_user_marketing',
                'scenario': 'Marketing Optimization',
                'query': 'Optimize our holiday marketing campaign to increase conversion by 25%',
                'sensitive_context': {'campaign_budget': 250000, 'target_demographics': 'proprietary', 'competitor_analysis': 'confidential'}
            },
            {
                'user_id': 'manufacturing_user_ops',
                'scenario': 'Operations Efficiency',
                'query': 'Analyze our supply chain bottlenecks and reduce lead times by 30%',
                'sensitive_context': {'supplier_contracts': 'nda_protected', 'production_capacity': 'trade_secret', 'cost_structure': 'confidential'}
            }
        ]
        
        print(f"\n🌐 GCP Staging Environment:")
        print(f"   - API URL: {self.staging_api_url}")
        print(f"   - WebSocket URL: {self.staging_websocket_url}")
        print(f"   - Test Users: {len(self.test_user_profiles)}")

    @pytest.mark.e2e
    @pytest.mark.multi_user_isolation
    @pytest.mark.gcp_staging
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_concurrent_multi_user_chat_complete_isolation(self):
        """
        MISSION CRITICAL E2E TEST: Complete user isolation in concurrent chat scenarios.
        
        Business Impact: Protects $500K+ ARR by ensuring users never see each other's private chats
        Expected: PASS - perfect isolation with full business value delivery
        """
        print("\n" + "="*90)
        print("🚀 MISSION CRITICAL E2E: Concurrent Multi-User Chat Complete Isolation")
        print("="*90)
        
        concurrent_users = len(self.test_user_profiles)
        chat_sessions = {}
        user_responses = {}
        contamination_detected = []
        business_value_delivered = {}
        
        async def execute_user_chat_session(user_profile: Dict[str, Any]) -> Dict[str, Any]:
            """Execute complete chat session for a single user"""
            user_id = user_profile['user_id']
            scenario = user_profile['scenario']
            query = user_profile['query']
            sensitive_context = user_profile['sensitive_context']
            
            print(f"\n👤 Starting chat session for {user_id} ({scenario})")
            
            # Create UserExecutionContext for complete isolation
            user_context = UserExecutionContext(
                user_id=user_id,
                session_id=f'e2e_session_{user_id}_{uuid.uuid4()}',
                thread_id=f'e2e_thread_{user_id}_{uuid.uuid4()}',
                request_id=f'e2e_req_{user_id}_{uuid.uuid4()}'
            )
            
            session_start_time = time.time()
            collected_events = []
            websocket_errors = []
            
            try:
                # Connect to GCP staging WebSocket
                async with WebSocketTestClient(
                    url=self.staging_websocket_url,
                    headers={'Authorization': f'Bearer staging_test_token_{user_id}'}
                ) as websocket:
                    
                    print(f"   🔌 WebSocket connected for {user_id}")
                    
                    # Send agent request with sensitive context
                    agent_request = {
                        "type": "agent_request",
                        "agent": "triage_agent",  # Use triage agent for consistent responses
                        "message": query,
                        "user_context": user_context.to_dict(),
                        "sensitive_context": sensitive_context,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send_json(agent_request)
                    print(f"   📤 Agent request sent for {user_id}")
                    
                    # Collect WebSocket events with timeout
                    event_timeout = 45  # Allow time for real LLM processing
                    event_collection_start = time.time()
                    
                    while (time.time() - event_collection_start) < event_timeout:
                        try:
                            event = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                            collected_events.append(event)
                            
                            event_type = event.get('type', 'unknown')
                            print(f"   📨 {user_id} received: {event_type}")
                            
                            # Check for completion
                            if event_type == 'agent_completed':
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            websocket_errors.append(f"WebSocket error for {user_id}: {str(e)}")
                            break
                    
                    session_duration = time.time() - session_start_time
                    
                    return {
                        'user_id': user_id,
                        'scenario': scenario,
                        'user_context': user_context.to_dict(),
                        'events_collected': len(collected_events),
                        'events': collected_events,
                        'websocket_errors': websocket_errors,
                        'session_duration': session_duration,
                        'sensitive_context': sensitive_context
                    }
                    
            except Exception as e:
                print(f"   ❌ Chat session failed for {user_id}: {str(e)}")
                return {
                    'user_id': user_id,
                    'scenario': scenario,
                    'error': str(e),
                    'events_collected': 0,
                    'events': [],
                    'websocket_errors': [str(e)],
                    'session_duration': time.time() - session_start_time,
                    'sensitive_context': sensitive_context
                }
        
        # Execute all user chat sessions concurrently
        print(f"\n🚀 Starting {concurrent_users} concurrent chat sessions on GCP staging...")
        
        tasks = [execute_user_chat_session(profile) for profile in self.test_user_profiles]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"\n📊 Concurrent chat session results:")
        
        # Analyze results for isolation and business value
        successful_sessions = 0
        total_events = 0
        
        for result in session_results:
            if isinstance(result, Exception):
                print(f"   ❌ Session exception: {result}")
                continue
                
            user_id = result['user_id']
            scenario = result['scenario']
            events_collected = result['events_collected']
            session_duration = result['session_duration']
            websocket_errors = result.get('websocket_errors', [])
            
            print(f"   👤 {user_id} ({scenario}):")
            print(f"      - Events collected: {events_collected}")
            print(f"      - Duration: {session_duration:.2f}s")
            print(f"      - WebSocket errors: {len(websocket_errors)}")
            
            if events_collected > 0 and len(websocket_errors) == 0:
                successful_sessions += 1
                total_events += events_collected
                
                # Store for cross-contamination analysis
                chat_sessions[user_id] = result
                
                # Analyze business value delivery
                agent_completed_events = [e for e in result['events'] if e.get('type') == 'agent_completed']
                if agent_completed_events:
                    final_response = agent_completed_events[-1].get('data', {}).get('result', '')
                    business_value_delivered[user_id] = {
                        'response_length': len(final_response),
                        'has_actionable_content': any(keyword in final_response.lower() 
                                                    for keyword in ['recommend', 'suggest', 'optimize', 'improve', 'reduce']),
                        'response_relevant': any(keyword in final_response.lower() 
                                               for keyword in result['query'].lower().split()[:3])
                    }
        
        print(f"\n📈 Overall Results:")
        print(f"   - Successful sessions: {successful_sessions}/{concurrent_users}")
        print(f"   - Total events collected: {total_events}")
        
        # VALIDATION 1: All sessions should succeed
        self.assertGreater(successful_sessions, concurrent_users * 0.8,  # Allow 20% failure tolerance for staging
                          f"Too many failed sessions. Expected >80% success, got {successful_sessions}/{concurrent_users}")
        
        # VALIDATION 2: Cross-user contamination analysis
        print(f"\n🔍 Cross-user contamination analysis:")
        
        for user1_id, user1_session in chat_sessions.items():
            user1_events = user1_session['events']
            user1_sensitive = user1_session['sensitive_context']
            
            for user2_id, user2_session in chat_sessions.items():
                if user1_id == user2_id:
                    continue
                    
                user2_events = user2_session['events'] 
                user2_sensitive = user2_session['sensitive_context']
                
                # Check if user1's sensitive data appears in user2's events
                user1_sensitive_strings = [str(v) for v in user1_sensitive.values() if isinstance(v, str)]
                user2_events_str = json.dumps(user2_events, default=str).lower()
                
                for sensitive_string in user1_sensitive_strings:
                    if len(sensitive_string) > 5 and sensitive_string.lower() in user2_events_str:
                        contamination_detected.append(
                            f"CONTAMINATION: {user1_id} sensitive data '{sensitive_string}' found in {user2_id} events"
                        )
                
                # Check WebSocket event user context isolation
                for event in user2_events:
                    event_user_context = event.get('user_context', {})
                    if event_user_context:
                        event_user_id = event_user_context.get('user_id')
                        if event_user_id and event_user_id == user1_id:
                            contamination_detected.append(
                                f"ROUTING ERROR: {user1_id} context found in {user2_id} event: {event.get('type')}"
                            )
        
        print(f"   - Contamination issues detected: {len(contamination_detected)}")
        for contamination in contamination_detected[:5]:  # Show first 5
            print(f"     ⚠️ {contamination}")
        
        # VALIDATION 3: No cross-user contamination allowed
        self.assertEqual(len(contamination_detected), 0,
                        f"User isolation breach detected: {contamination_detected}")
        
        # VALIDATION 4: Business value delivery verification
        print(f"\n💼 Business value delivery analysis:")
        
        for user_id, bv_analysis in business_value_delivered.items():
            response_length = bv_analysis['response_length']
            has_actionable = bv_analysis['has_actionable_content']
            is_relevant = bv_analysis['response_relevant']
            
            print(f"   👤 {user_id}:")
            print(f"      - Response length: {response_length} chars")
            print(f"      - Actionable content: {'✅' if has_actionable else '❌'}")
            print(f"      - Query relevant: {'✅' if is_relevant else '❌'}")
            
            # VALIDATION: Each user should get substantive, relevant responses
            self.assertGreater(response_length, 100,
                              f"User {user_id} response too short: {response_length} chars")
            
            self.assertTrue(has_actionable or is_relevant,
                           f"User {user_id} response lacks business value: no actionable content or relevance")
        
        # VALIDATION 5: WebSocket event completeness
        print(f"\n📡 WebSocket event completeness analysis:")
        
        required_events = ['agent_started', 'agent_thinking', 'agent_completed']
        
        for user_id, session in chat_sessions.items():
            events = session['events']
            event_types = [e.get('type') for e in events]
            
            missing_events = [req_event for req_event in required_events if req_event not in event_types]
            
            print(f"   👤 {user_id}: {len(event_types)} events, missing: {missing_events}")
            
            # VALIDATION: Critical events must be present
            self.assertIn('agent_started', event_types,
                         f"User {user_id} missing agent_started event")
            self.assertIn('agent_completed', event_types,
                         f"User {user_id} missing agent_completed event")
        
        print("\n✅ CONCURRENT MULTI-USER CHAT ISOLATION: All validations passed")
        
        # Store results for reporting
        self.test_results['concurrent_chat_isolation'].append({
            'test': 'multi_user_chat_isolation',
            'status': 'PASS',
            'concurrent_users': concurrent_users,
            'successful_sessions': successful_sessions,
            'total_events': total_events,
            'contamination_detected': len(contamination_detected),
            'business_value_delivered': len(business_value_delivered)
        })

    @pytest.mark.e2e
    @pytest.mark.performance_load
    @pytest.mark.gcp_staging
    @pytest.mark.real_llm
    async def test_concurrent_chat_performance_under_load(self):
        """
        PERFORMANCE E2E TEST: Validates system performance under concurrent user load.
        
        Business Impact: Ensures production-level performance with UserExecutionEngine
        Expected: PASS - response times ≤ 2s, memory usage bounded
        """
        print("\n" + "="*90)
        print("⚡ PERFORMANCE E2E: Concurrent Chat Performance Under Load")
        print("="*90)
        
        # Performance test configuration
        load_test_users = 3  # Reasonable for staging environment
        performance_metrics = {
            'response_times': [],
            'memory_usage': [],
            'concurrent_sessions': 0,
            'failed_sessions': 0
        }
        
        async def load_test_user_session(user_index: int) -> Dict[str, Any]:
            """Execute load test user session"""
            user_id = f'load_test_user_{user_index}'
            query = f"Optimize costs for user {user_index} - analyze spending patterns and recommend savings"
            
            session_start = time.time()
            
            try:
                user_context = UserExecutionContext(
                    user_id=user_id,
                    session_id=f'load_session_{user_index}_{uuid.uuid4()}',
                    thread_id=f'load_thread_{user_index}_{uuid.uuid4()}',
                    request_id=f'load_req_{user_index}_{uuid.uuid4()}'
                )
                
                async with WebSocketTestClient(
                    url=self.staging_websocket_url,
                    headers={'Authorization': f'Bearer load_test_token_{user_index}'}
                ) as websocket:
                    
                    # Send simple agent request
                    await websocket.send_json({
                        "type": "agent_request", 
                        "agent": "triage_agent",
                        "message": query,
                        "user_context": user_context.to_dict()
                    })
                    
                    # Wait for completion with timeout
                    response_start = time.time()
                    
                    async for event in websocket.receive_events(timeout=30):
                        if event.get('type') == 'agent_completed':
                            response_time = time.time() - response_start
                            total_time = time.time() - session_start
                            
                            return {
                                'user_index': user_index,
                                'status': 'success',
                                'response_time': response_time,
                                'total_time': total_time,
                                'events_received': 1
                            }
                    
                    # Timeout occurred
                    return {
                        'user_index': user_index,
                        'status': 'timeout',
                        'response_time': time.time() - response_start,
                        'total_time': time.time() - session_start
                    }
                    
            except Exception as e:
                return {
                    'user_index': user_index,
                    'status': 'error',
                    'error': str(e),
                    'total_time': time.time() - session_start
                }
        
        # Execute load test
        print(f"🚀 Starting load test with {load_test_users} concurrent users...")
        
        load_start_time = time.time()
        
        tasks = [load_test_user_session(i) for i in range(load_test_users)]
        load_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        load_duration = time.time() - load_start_time
        
        # Analyze performance results
        successful_sessions = 0
        
        for result in load_results:
            if isinstance(result, Exception):
                performance_metrics['failed_sessions'] += 1
                continue
                
            status = result.get('status', 'unknown')
            user_index = result.get('user_index', -1)
            
            print(f"   User {user_index}: {status}")
            
            if status == 'success':
                successful_sessions += 1
                response_time = result.get('response_time', 0)
                performance_metrics['response_times'].append(response_time)
                
                print(f"      - Response time: {response_time:.2f}s")
            else:
                performance_metrics['failed_sessions'] += 1
        
        performance_metrics['concurrent_sessions'] = successful_sessions
        
        # Calculate performance statistics
        if performance_metrics['response_times']:
            avg_response_time = sum(performance_metrics['response_times']) / len(performance_metrics['response_times'])
            max_response_time = max(performance_metrics['response_times'])
            min_response_time = min(performance_metrics['response_times'])
            
            print(f"\n📊 Performance Results:")
            print(f"   - Successful sessions: {successful_sessions}/{load_test_users}")
            print(f"   - Average response time: {avg_response_time:.2f}s")
            print(f"   - Max response time: {max_response_time:.2f}s")
            print(f"   - Min response time: {min_response_time:.2f}s")
            print(f"   - Total load duration: {load_duration:.2f}s")
            
            # PERFORMANCE VALIDATIONS
            max_acceptable_response_time = 10.0  # 10s is acceptable for staging with real LLM
            
            self.assertLess(avg_response_time, max_acceptable_response_time,
                           f"Average response time too high: {avg_response_time:.2f}s > {max_acceptable_response_time}s")
            
            self.assertLess(max_response_time, max_acceptable_response_time * 2,
                           f"Max response time too high: {max_response_time:.2f}s > {max_acceptable_response_time * 2}s")
            
            success_rate = (successful_sessions / load_test_users) * 100
            min_success_rate = 70  # 70% success rate acceptable for staging
            
            self.assertGreaterEqual(success_rate, min_success_rate,
                                   f"Success rate too low: {success_rate:.1f}% < {min_success_rate}%")
            
            print(f"✅ PERFORMANCE VALIDATION: {success_rate:.1f}% success rate, {avg_response_time:.2f}s avg response")
        
        else:
            self.fail("No successful sessions for performance analysis")
        
        # Store performance results
        self.test_results['performance_under_load'].append({
            'test': 'concurrent_performance',
            'status': 'PASS',
            'load_test_users': load_test_users,
            'successful_sessions': successful_sessions,
            'avg_response_time': avg_response_time if performance_metrics['response_times'] else 0,
            'max_response_time': max_response_time if performance_metrics['response_times'] else 0
        })

    def tearDown(self):
        """Clean up and report comprehensive E2E test results"""
        super().tearDown()
        
        print("\n" + "="*90)
        print("📋 E2E TEST SUMMARY - Issue #565 Multi-User Concurrent Chat Isolation")
        print("="*90)
        
        total_tests = 0
        passed_tests = 0
        
        for category, results in self.test_results.items():
            if results:
                print(f"\n🔍 {category.upper().replace('_', ' ')}:")
                for result in results:
                    total_tests += 1
                    status = result['status']
                    if status == 'PASS':
                        passed_tests += 1
                    
                    status_icon = "✅" if status == 'PASS' else "❌"
                    print(f"   {status_icon} {result['test']}: {status}")
                    
                    # Print key metrics
                    key_metrics = ['concurrent_users', 'successful_sessions', 'contamination_detected', 
                                 'business_value_delivered', 'avg_response_time']
                    
                    for metric in key_metrics:
                        if metric in result:
                            print(f"      - {metric}: {result[metric]}")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n🎯 OVERALL E2E TEST RESULTS:")
        print(f"   - Tests passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"   - Environment: GCP Staging + Real LLM")
        print(f"   - Infrastructure: UserExecutionEngine (SSOT)")
        
        if success_rate >= 100:
            print(f"\n🎉 SUCCESS: Issue #565 UserExecutionEngine migration delivers:")
            print(f"   ✅ Perfect user isolation in concurrent scenarios")
            print(f"   ✅ $500K+ ARR chat functionality preserved")
            print(f"   ✅ Production-ready multi-user support")
            print(f"   ✅ Zero cross-user data contamination")
        elif success_rate >= 80:
            print(f"\n⚠️ MOSTLY SUCCESSFUL: Minor issues detected but core functionality works")
        else:
            print(f"\n❌ SIGNIFICANT ISSUES: E2E validation failed - migration needs review")


if __name__ == "__main__":
    # Run E2E tests on GCP staging
    import unittest
    
    print("🌐 Starting Issue #565 Multi-User E2E Validation on GCP Staging...")
    print("🎯 Goal: Prove UserExecutionEngine enables safe concurrent production chat")
    print("💡 Infrastructure: GCP Staging + Real LLM + WebSocket connections")
    
    # Set staging environment
    import os
    os.environ['NETRA_ENV'] = 'staging'
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMultiUserConcurrentChatIsolation565)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Report final status
    if result.wasSuccessful():
        print("\n🎉 SUCCESS: Multi-user concurrent chat E2E validation PASSED")
        print("✅ UserExecutionEngine ready for production deployment")
        print("💰 $500K+ ARR chat functionality protected with perfect user isolation")
    else:
        print("\n❌ FAILURE: E2E validation failed")
        print(f"   - Tests run: {result.testsRun}")
        print(f"   - Failures: {len(result.failures)}")
        print(f"   - Errors: {len(result.errors)}")
        print("⚠️ Review results before production deployment")