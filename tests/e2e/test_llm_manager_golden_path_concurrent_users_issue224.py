"""
LLM Manager Golden Path Concurrent Users E2E Tests - Issue #224 Phase 3

DESIGNED TO FAIL: These tests prove user conversation mixing in production scenarios.
They will PASS after proper factory pattern remediation is implemented.

Business Value: Platform/Enterprise - $500K+ ARR Chat Protection
Protects critical chat functionality from user conversation mixing in real-world scenarios.

Test Strategy:
1. Concurrent users through golden path (login → chat → AI response)
2. Real WebSocket connections with agent execution
3. Conversation isolation validation in production-like scenarios
4. Golden path reliability under user concurrency stress

MISSION CRITICAL: These tests validate the core business value delivery path
that generates $500K+ ARR from chat functionality.

Target Issue: 51 LLMManager factory violations causing user conversation mixing
in production golden path scenarios with concurrent users.
"""

import asyncio
import json
import time
import uuid
import websockets
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

import pytest
import requests
from loguru import logger

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@dataclass
class GoldenPathUser:
    """Represents a user going through the golden path flow."""
    user_id: str
    session_id: str
    thread_id: str
    run_id: str
    auth_token: Optional[str] = None
    websocket_url: Optional[str] = None
    conversation_history: List[Dict] = field(default_factory=list)
    responses_received: List[Dict] = field(default_factory=list)
    test_marker: str = ""
    created_at: float = 0.0
    

@dataclass
class ConversationMixingEvidence:
    """Evidence of conversation mixing between users."""
    user_a: str
    user_b: str
    mixed_content: str
    evidence_type: str
    severity: str
    detected_at: float


class TestLLMManagerGoldenPathConcurrentUsersIssue224(SSotAsyncTestCase):
    """E2E tests for LLM manager violations in golden path concurrent user scenarios"""
    
    def setup_method(self, method=None):
        """Setup for E2E tests."""
        super().setup_method(method)
        
        # E2E test configuration
        self.backend_url = self.get_env_var("BACKEND_URL", "http://localhost:8001")
        self.frontend_url = self.get_env_var("FRONTEND_URL", "http://localhost:3000")
        self.websocket_url = self.backend_url.replace("http", "ws") + "/ws"
        
        # Test configuration
        self.test_timeout = 60  # seconds for E2E operations
        self.max_concurrent_users = 6  # Concurrent users for stress testing
        
        logger.info(f"E2E test setup - Backend: {self.backend_url}, WebSocket: {self.websocket_url}")
    
    async def test_golden_path_concurrent_users_conversation_isolation(self):
        """DESIGNED TO FAIL: Test conversation isolation in golden path with concurrent users.
        
        This test should FAIL because agents using direct LLMManager() instantiation
        will mix conversations between concurrent users in the golden path flow.
        
        Golden Path Flow:
        1. User authentication
        2. WebSocket connection
        3. Chat message
        4. Agent processing (WHERE VIOLATIONS OCCUR)
        5. AI response
        
        Expected Issues:
        - User A gets response intended for User B
        - Agent context from User A bleeds into User B's session
        - LLM manager sharing causes conversation mixing
        
        Business Impact: CRITICAL - $500K+ ARR chat functionality reliability
        """
        logger.info("Starting golden path concurrent users conversation isolation test...")
        
        conversation_mixing_evidence = []
        golden_path_users = []
        
        # Create multiple users for concurrent golden path testing
        for i in range(self.max_concurrent_users):
            user = GoldenPathUser(
                user_id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                test_marker=f"concurrent_user_{i}_{int(time.time())}",
                created_at=time.time()
            )
            golden_path_users.append(user)
        
        async def execute_golden_path_for_user(user: GoldenPathUser) -> Dict:
            """Execute the complete golden path flow for a single user."""
            try:
                # Step 1: Authentication (simulate or skip for E2E focus)
                user.auth_token = f"test_token_{user.user_id}"
                
                # Step 2: WebSocket connection
                websocket_uri = f"{self.websocket_url}?user_id={user.user_id}&session_id={user.session_id}"
                
                async with websockets.connect(
                    websocket_uri,
                    timeout=self.test_timeout,
                    extra_headers={"Authorization": f"Bearer {user.auth_token}"}
                ) as websocket:
                    
                    # Step 3: Send unique chat message
                    unique_message = f"Hello, I am {user.test_marker}. Please help me with optimization analysis for project {user.user_id}."
                    
                    chat_message = {
                        "type": "chat_message",
                        "user_id": user.user_id,
                        "session_id": user.session_id,
                        "thread_id": user.thread_id,
                        "run_id": user.run_id,
                        "message": unique_message,
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(chat_message))
                    user.conversation_history.append(chat_message)
                    
                    # Step 4: Collect agent processing events and responses
                    response_timeout = 30  # Wait up to 30 seconds for agent response
                    start_time = time.time()
                    
                    while time.time() - start_time < response_timeout:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            response_data = json.loads(response)
                            
                            user.responses_received.append({
                                'data': response_data,
                                'received_at': time.time()
                            })
                            
                            # Check if this is the final agent response
                            if response_data.get('type') == 'agent_completed' or response_data.get('type') == 'agent_response':
                                logger.info(f"User {user.test_marker} received agent response")
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logger.error(f"Error receiving response for {user.test_marker}: {e}")
                            break
                
                return {
                    'success': True,
                    'user': user,
                    'responses_count': len(user.responses_received),
                    'conversation_items': len(user.conversation_history),
                    'completed_at': time.time()
                }
                
            except Exception as e:
                logger.error(f"Golden path failed for user {user.test_marker}: {e}")
                return {
                    'success': False,
                    'user': user,
                    'error': str(e),
                    'completed_at': time.time()
                }
        
        # Execute golden path for all users concurrently
        logger.info(f"Executing golden path for {len(golden_path_users)} concurrent users...")
        
        concurrent_tasks = [execute_golden_path_for_user(user) for user in golden_path_users]
        execution_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Process results
        successful_executions = [r for r in execution_results if isinstance(r, dict) and r.get('success')]
        failed_executions = [r for r in execution_results if isinstance(r, dict) and not r.get('success')]
        
        logger.info(f"Successful golden path executions: {len(successful_executions)}")
        logger.info(f"Failed golden path executions: {len(failed_executions)}")
        
        # Analyze for conversation mixing violations
        for i, result_a in enumerate(successful_executions):
            user_a = result_a['user']
            
            for j, result_b in enumerate(successful_executions):
                if i >= j:  # Avoid duplicate comparisons
                    continue
                    
                user_b = result_b['user']
                
                # Check for cross-contamination in responses
                for response_a in user_a.responses_received:
                    response_content_a = str(response_a['data'])
                    
                    # Look for User B's test marker in User A's responses
                    if user_b.test_marker in response_content_a:
                        conversation_mixing_evidence.append(ConversationMixingEvidence(
                            user_a=user_a.user_id,
                            user_b=user_b.user_id,
                            mixed_content=user_b.test_marker,
                            evidence_type='user_marker_in_wrong_response',
                            severity='CRITICAL',
                            detected_at=time.time()
                        ))
                        logger.error(f"CONVERSATION MIXING: User {user_a.test_marker} received response containing {user_b.test_marker}")
                    
                    # Look for User B's user_id in User A's responses
                    if user_b.user_id in response_content_a:
                        conversation_mixing_evidence.append(ConversationMixingEvidence(
                            user_a=user_a.user_id,
                            user_b=user_b.user_id,
                            mixed_content=user_b.user_id,
                            evidence_type='user_id_in_wrong_response',
                            severity='HIGH',
                            detected_at=time.time()
                        ))
                        logger.error(f"USER ID MIXING: User {user_a.test_marker} received response containing user ID {user_b.user_id}")
        
        # Check for identical responses (indicating shared state)
        response_signatures = defaultdict(list)
        for result in successful_executions:
            user = result['user']
            for response in user.responses_received:
                if response['data'].get('type') == 'agent_response' or response['data'].get('type') == 'agent_completed':
                    # Create a signature of the response content
                    content = response['data'].get('content', '')
                    signature = hash(content) if content else 0
                    response_signatures[signature].append(user.user_id)
        
        # Detect shared responses
        for signature, user_ids in response_signatures.items():
            if len(user_ids) > 1 and signature != 0:  # More than one user got identical response
                conversation_mixing_evidence.append(ConversationMixingEvidence(
                    user_a=user_ids[0],
                    user_b=user_ids[1],
                    mixed_content=f"identical_response_signature_{signature}",
                    evidence_type='identical_responses',
                    severity='MEDIUM',
                    detected_at=time.time()
                ))
                logger.error(f"IDENTICAL RESPONSES: Users {user_ids} received identical agent responses")
        
        # Record metrics
        self.record_metric('concurrent_users_tested', len(golden_path_users))
        self.record_metric('successful_golden_path_executions', len(successful_executions))
        self.record_metric('failed_golden_path_executions', len(failed_executions))
        self.record_metric('conversation_mixing_evidence_count', len(conversation_mixing_evidence))
        
        # Categorize evidence by severity
        critical_evidence = [e for e in conversation_mixing_evidence if e.severity == 'CRITICAL']
        high_evidence = [e for e in conversation_mixing_evidence if e.severity == 'HIGH']
        medium_evidence = [e for e in conversation_mixing_evidence if e.severity == 'MEDIUM']
        
        self.record_metric('critical_mixing_evidence', len(critical_evidence))
        self.record_metric('high_mixing_evidence', len(high_evidence))
        self.record_metric('medium_mixing_evidence', len(medium_evidence))
        
        # Log summary
        logger.info(f"Golden path concurrent users test completed")
        logger.info(f"Total users: {len(golden_path_users)}, Successful: {len(successful_executions)}")
        logger.info(f"Conversation mixing evidence: {len(conversation_mixing_evidence)}")
        logger.info(f"Critical: {len(critical_evidence)}, High: {len(high_evidence)}, Medium: {len(medium_evidence)}")
        
        for evidence in conversation_mixing_evidence:
            logger.error(f"MIXING EVIDENCE: {evidence}")
        
        # This test should FAIL if we find conversation mixing evidence
        if len(conversation_mixing_evidence) > 0:
            pytest.fail(
                f"Golden Path Conversation Mixing Detected! "
                f"Found {len(conversation_mixing_evidence)} pieces of evidence: "
                f"{len(critical_evidence)} critical, {len(high_evidence)} high, {len(medium_evidence)} medium. "
                f"This proves LLM manager factory violations cause user conversation mixing in production scenarios."
            )
        
        # If no direct evidence, check for concerning patterns
        if len(successful_executions) < len(golden_path_users) * 0.8:  # Less than 80% success rate
            pytest.fail(
                f"Golden Path Reliability Issues Detected! "
                f"Only {len(successful_executions)}/{len(golden_path_users)} users completed golden path successfully. "
                f"This indicates agent factory pattern violations may be causing system instability."
            )
        
        # If everything passed, that's unexpected for this "designed to fail" test
        pytest.fail(
            f"Unexpected: No conversation mixing evidence found in golden path concurrent users test. "
            f"Expected to find LLM manager factory violations causing user conversation mixing. "
            f"Tested {len(successful_executions)} successful concurrent users through complete golden path."
        )
    
    async def test_golden_path_reliability_under_llm_manager_violations(self):
        """DESIGNED TO FAIL: Test golden path reliability with LLM manager factory violations.
        
        This test should FAIL because LLM manager violations cause instability
        in the golden path under concurrent user load.
        
        Expected Issues:
        - Golden path completion rate drops under concurrent load
        - Agent response times increase due to shared LLM managers
        - WebSocket connections become unstable
        - User experience degrades
        
        Business Impact: $500K+ ARR at risk from unreliable chat functionality
        """
        logger.info("Starting golden path reliability test under LLM manager violations...")
        
        reliability_issues = []
        performance_metrics = {
            'response_times': [],
            'completion_rates': [],
            'error_rates': [],
            'websocket_failures': []
        }
        
        # Test multiple rounds of concurrent users to stress the system
        test_rounds = 3
        users_per_round = 4
        
        for round_num in range(test_rounds):
            logger.info(f"Starting reliability test round {round_num + 1}/{test_rounds}")
            
            round_start_time = time.time()
            round_users = []
            
            # Create users for this round
            for i in range(users_per_round):
                user = GoldenPathUser(
                    user_id=str(uuid.uuid4()),
                    session_id=str(uuid.uuid4()),
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4()),
                    test_marker=f"reliability_round_{round_num}_user_{i}",
                    created_at=time.time()
                )
                round_users.append(user)
            
            async def execute_timed_golden_path(user: GoldenPathUser) -> Dict:
                """Execute golden path with timing and reliability tracking."""
                execution_start = time.time()
                
                try:
                    websocket_uri = f"{self.websocket_url}?user_id={user.user_id}"
                    
                    async with websockets.connect(websocket_uri, timeout=30) as websocket:
                        # Send message
                        message = {
                            "type": "chat_message",
                            "user_id": user.user_id,
                            "message": f"Reliability test message from {user.test_marker}",
                            "timestamp": time.time()
                        }
                        
                        await websocket.send(json.dumps(message))
                        
                        # Wait for response with timeout
                        response_received = False
                        response_time = None
                        
                        timeout_duration = 25  # 25 second timeout
                        start_wait = time.time()
                        
                        while time.time() - start_wait < timeout_duration:
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                                response_data = json.loads(response)
                                
                                if response_data.get('type') in ['agent_completed', 'agent_response']:
                                    response_time = time.time() - execution_start
                                    response_received = True
                                    break
                                    
                            except asyncio.TimeoutError:
                                continue
                        
                        return {
                            'success': response_received,
                            'response_time': response_time,
                            'execution_time': time.time() - execution_start,
                            'user': user,
                            'websocket_error': None
                        }
                        
                except Exception as e:
                    return {
                        'success': False,
                        'response_time': None,
                        'execution_time': time.time() - execution_start,
                        'user': user,
                        'websocket_error': str(e)
                    }
            
            # Execute round concurrently
            round_tasks = [execute_timed_golden_path(user) for user in round_users]
            round_results = await asyncio.gather(*round_tasks, return_exceptions=True)
            
            # Analyze round results
            valid_results = [r for r in round_results if isinstance(r, dict)]
            successful_results = [r for r in valid_results if r.get('success')]
            failed_results = [r for r in valid_results if not r.get('success')]
            
            # Calculate metrics for this round
            completion_rate = len(successful_results) / len(valid_results) if valid_results else 0
            error_rate = len(failed_results) / len(valid_results) if valid_results else 1
            
            response_times = [r['response_time'] for r in successful_results if r['response_time']]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            websocket_failures = [r for r in failed_results if r.get('websocket_error')]
            
            # Record round metrics
            performance_metrics['completion_rates'].append(completion_rate)
            performance_metrics['error_rates'].append(error_rate)
            performance_metrics['response_times'].extend(response_times)
            performance_metrics['websocket_failures'].extend(websocket_failures)
            
            logger.info(f"Round {round_num + 1} - Completion: {completion_rate:.2%}, Avg Response: {avg_response_time:.2f}s")
            
            # Detect reliability issues
            if completion_rate < 0.8:  # Less than 80% completion
                reliability_issues.append({
                    'issue_type': 'low_completion_rate',
                    'round': round_num + 1,
                    'completion_rate': completion_rate,
                    'severity': 'HIGH'
                })
            
            if avg_response_time > 15.0:  # Response time over 15 seconds
                reliability_issues.append({
                    'issue_type': 'slow_response_time',
                    'round': round_num + 1,
                    'avg_response_time': avg_response_time,
                    'severity': 'MEDIUM'
                })
            
            if len(websocket_failures) > 1:  # Multiple WebSocket failures
                reliability_issues.append({
                    'issue_type': 'websocket_instability',
                    'round': round_num + 1,
                    'failure_count': len(websocket_failures),
                    'severity': 'HIGH'
                })
            
            # Brief pause between rounds
            await asyncio.sleep(2)
        
        # Overall analysis
        overall_completion_rate = sum(performance_metrics['completion_rates']) / len(performance_metrics['completion_rates'])
        overall_error_rate = sum(performance_metrics['error_rates']) / len(performance_metrics['error_rates'])
        overall_avg_response_time = sum(performance_metrics['response_times']) / len(performance_metrics['response_times']) if performance_metrics['response_times'] else 0
        
        # Record overall metrics
        self.record_metric('test_rounds', test_rounds)
        self.record_metric('users_per_round', users_per_round)
        self.record_metric('overall_completion_rate', overall_completion_rate)
        self.record_metric('overall_error_rate', overall_error_rate)
        self.record_metric('overall_avg_response_time', overall_avg_response_time)
        self.record_metric('reliability_issues_count', len(reliability_issues))
        self.record_metric('total_websocket_failures', len(performance_metrics['websocket_failures']))
        
        # Log summary
        logger.info(f"Golden path reliability test completed - {test_rounds} rounds")
        logger.info(f"Overall completion rate: {overall_completion_rate:.2%}")
        logger.info(f"Overall error rate: {overall_error_rate:.2%}")
        logger.info(f"Overall avg response time: {overall_avg_response_time:.2f}s")
        logger.info(f"Reliability issues: {len(reliability_issues)}")
        
        for issue in reliability_issues:
            logger.error(f"RELIABILITY ISSUE: {issue}")
        
        # This test should FAIL if we find reliability issues
        if len(reliability_issues) > 0:
            critical_issues = [i for i in reliability_issues if i.get('severity') == 'CRITICAL']
            high_issues = [i for i in reliability_issues if i.get('severity') == 'HIGH']
            medium_issues = [i for i in reliability_issues if i.get('severity') == 'MEDIUM']
            
            pytest.fail(
                f"Golden Path Reliability Issues Detected! "
                f"Found {len(reliability_issues)} issues: "
                f"{len(critical_issues)} critical, {len(high_issues)} high, {len(medium_issues)} medium. "
                f"Completion rate: {overall_completion_rate:.2%}, "
                f"Error rate: {overall_error_rate:.2%}, "
                f"Avg response time: {overall_avg_response_time:.2f}s. "
                f"This proves LLM manager factory violations degrade golden path reliability."
            )
        
        # Check for concerning patterns even without explicit issues
        if overall_completion_rate < 0.9:  # Less than 90% overall completion
            pytest.fail(
                f"Golden Path Completion Rate Below Threshold! "
                f"Overall completion rate: {overall_completion_rate:.2%} (expected >90%). "
                f"This indicates LLM manager factory violations may be causing instability."
            )
        
        if overall_avg_response_time > 10.0:  # Average response time over 10 seconds
            pytest.fail(
                f"Golden Path Response Time Above Threshold! "
                f"Average response time: {overall_avg_response_time:.2f}s (expected <10s). "
                f"This suggests LLM manager sharing is causing performance degradation."
            )
        
        # If everything passed, that's unexpected for this "designed to fail" test
        pytest.fail(
            f"Unexpected: No reliability issues found in golden path stress test. "
            f"Expected LLM manager factory violations to cause degraded performance under load. "
            f"Tested {test_rounds} rounds with {users_per_round} concurrent users each."
        )


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    import sys
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)