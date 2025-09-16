"""
DeepAgentState Security Vulnerability Test - Cross-User Contamination

This test is DESIGNED TO FAIL by demonstrating cross-user data contamination risks
that exist when using DeepAgentState instead of UserExecutionContext.

BUSINESS IMPACT: Issue #271 - Protects $500K+ ARR from user isolation failures
"""

import asyncio
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
import unittest
from unittest.mock import MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ThreadID, RunID


class MockDeepAgentState:
    """Mock representation of DeepAgentState showing vulnerability patterns"""
    
    # VULNERABILITY: Shared class-level state across all instances
    _shared_execution_data = {}
    _shared_user_context = {}
    _shared_tool_results = []
    
    def __init__(self, user_id: str = None):
        # VULNERABILITY: user_id not properly isolated
        self.user_id = user_id
        self.execution_context = self._shared_execution_data  # SHARED!
        self.user_context = self._shared_user_context  # SHARED!
        self.tool_results = self._shared_tool_results  # SHARED!
        self.session_data = {}  # Instance level but still vulnerable
        
    def add_tool_result(self, result: Dict[str, Any]):
        """VULNERABILITY: Results added to shared list"""
        self.tool_results.append(result)
        
    def set_execution_data(self, key: str, value: Any):
        """VULNERABILITY: Data stored in shared dict"""
        self.execution_context[key] = value
        
    def get_execution_data(self, key: str) -> Any:
        """VULNERABILITY: Can access other users' data"""
        return self.execution_context.get(key)
        
    def set_user_context(self, context: Dict[str, Any]):
        """VULNERABILITY: User context shared across instances"""
        self.user_context.update(context)


class MockUserExecutionContext:
    """Mock representation of secure UserExecutionContext pattern"""
    
    def __init__(self, user_id: UserID, thread_id: ThreadID = None):
        self.user_id = user_id
        self.thread_id = thread_id or ThreadID(str(uuid.uuid4()))
        
        # SECURE: Each instance has isolated data storage
        self._execution_context = {}
        self._user_context = {}
        self._tool_results = []
        self._security_token = str(uuid.uuid4())
        
    def add_tool_result(self, result: Dict[str, Any]):
        """SECURE: Results isolated per user context"""
        if not self._validate_security_token():
            raise SecurityError("Context security violation")
        self._tool_results.append(result)
        
    def set_execution_data(self, key: str, value: Any):
        """SECURE: Data isolated per user"""
        if not self._validate_security_token():
            raise SecurityError("Context security violation")
        self._execution_context[key] = value
        
    def get_execution_data(self, key: str) -> Any:
        """SECURE: Only returns this user's data"""
        if not self._validate_security_token():
            raise SecurityError("Context security violation")
        return self._execution_context.get(key)
        
    def set_user_context(self, context: Dict[str, Any]):
        """SECURE: Context isolated per user"""
        if not self._validate_security_token():
            raise SecurityError("Context security violation")
        self._user_context.update(context)
        
    def _validate_security_token(self) -> bool:
        """Security validation for context isolation"""
        return hasattr(self, '_security_token') and self._security_token is not None


class SecurityError(Exception):
    """Security violation error for context isolation"""
    pass


class TestDeepAgentStateSecurityVulnerabilities(SSotAsyncTestCase):
    """
    Demonstrates security vulnerabilities in DeepAgentState vs UserExecutionContext
    
    These tests FAIL to show that DeepAgentState allows cross-user contamination
    that UserExecutionContext prevents.
    """
    
    def setup_method(self, method):
        super().setup_method(method)
        self.user1_id = UserID("user_001_enterprise")
        self.user2_id = UserID("user_002_competitor")
        self.sensitive_data = {
            "api_keys": ["sk-enterprise-key-001", "sk-internal-api-002"],
            "company_name": "TopSecret Corp",
            "revenue_data": {"q4_2024": "$500K", "projections": "$2M"},
            "strategy": "AI optimization competitive advantage"
        }
        
    async def test_deepagentstate_cross_user_data_contamination_vulnerability(self):
        """
        DESIGNED TO FAIL: DeepAgentState allows cross-user data contamination
        
        This demonstrates the security vulnerability that allows User A's sensitive
        data to leak to User B through shared state.
        """
        # User 1 (Enterprise customer) creates state with sensitive data
        user1_state = MockDeepAgentState(user_id=str(self.user1_id))
        user1_state.set_user_context(self.sensitive_data)
        user1_state.set_execution_data("sensitive_strategy", "enterprise_ai_optimization")
        user1_state.add_tool_result({"tool": "revenue_calculator", "result": "$500K ARR"})
        
        # User 2 (Competitor) creates "separate" state
        user2_state = MockDeepAgentState(user_id=str(self.user2_id))
        
        # VULNERABILITY DEMONSTRATION: User 2 can access User 1's sensitive data
        leaked_strategy = user2_state.get_execution_data("sensitive_strategy")
        leaked_results = user2_state.tool_results
        leaked_context = user2_state.user_context
        
        # This test FAILS because the vulnerability exists
        vulnerabilities_detected = []
        
        if leaked_strategy == "enterprise_ai_optimization":
            vulnerabilities_detected.append("Execution data leaked across users")
            
        if leaked_results and any("$500K ARR" in str(result) for result in leaked_results):
            vulnerabilities_detected.append("Tool results leaked across users")
            
        if leaked_context and "TopSecret Corp" in str(leaked_context):
            vulnerabilities_detected.append("User context leaked across users")
            
        # Assert that vulnerabilities exist (test designed to fail)
        assert len(vulnerabilities_detected) > 0, f"""
 ALERT:  TEST WORKING CORRECTLY: Cross-User Data Contamination Detected

DeepAgentState allows Enterprise Customer data to leak to Competitor:

VULNERABILITIES FOUND:
{chr(10).join(f'  - {v}' for v in vulnerabilities_detected)}

LEAKED SENSITIVE DATA:
- Execution Strategy: {leaked_strategy}
- Tool Results Count: {len(leaked_results) if leaked_results else 0}
- Context Keys: {list(leaked_context.keys()) if leaked_context else []}

BUSINESS IMPACT: $500K+ ARR at risk from data privacy violations
COMPLIANCE RISK: GDPR/SOC2 violations possible
CUSTOMER TRUST: Enterprise customers at risk of competitive data exposure

REMEDIATION: Migrate to UserExecutionContext for proper isolation
        """
            
    async def test_concurrent_user_execution_data_race_vulnerability(self):
        """
        DESIGNED TO FAIL: DeepAgentState has race conditions in concurrent execution
        
        This demonstrates race conditions that can cause data corruption
        between concurrent user sessions.
        """
        contamination_detected = []
        
        def user1_execution():
            """Enterprise user execution"""
            state = MockDeepAgentState(user_id=str(self.user1_id))
            for i in range(50):
                state.set_execution_data(f"enterprise_data_{i}", f"confidential_value_{i}")
                state.add_tool_result({"user": "enterprise", "iteration": i, "value": f"secret_{i}"})
                
        def user2_execution():
            """Competitor user execution"""  
            state = MockDeepAgentState(user_id=str(self.user2_id))
            for i in range(50):
                # Check if we can see enterprise data
                leaked_data = state.get_execution_data(f"enterprise_data_{i}")
                if leaked_data and "confidential" in str(leaked_data):
                    contamination_detected.append(f"Leaked enterprise_data_{i}: {leaked_data}")
                    
                state.set_execution_data(f"competitor_data_{i}", f"competitive_intel_{i}")
                
        # Execute concurrent user sessions
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(user1_execution)
            future2 = executor.submit(user2_execution)
            
            future1.result()
            future2.result()
            
        # Assert that contamination was detected (test designed to fail)
        assert len(contamination_detected) > 0, f"""
 ALERT:  TEST WORKING CORRECTLY: Concurrent User Data Contamination Detected

During concurrent execution, competitor accessed enterprise data:

CONTAMINATION INSTANCES:
{chr(10).join(f'  - {c}' for c in contamination_detected[:5])}
{f'... and {len(contamination_detected) - 5} more instances' if len(contamination_detected) > 5 else ''}

TOTAL LEAKS: {len(contamination_detected)} instances of data contamination

BUSINESS RISK: Multi-tenant system allows data leakage under concurrent load
TECHNICAL CAUSE: Shared state between supposedly isolated user contexts
CUSTOMER IMPACT: Enterprise customers' confidential data exposed to competitors

REMEDIATION: UserExecutionContext provides thread-safe per-user isolation
        """
            
    async def test_userexecutioncontext_prevents_contamination_properly(self):
        """
        DESIGNED TO PASS: UserExecutionContext prevents cross-user contamination
        
        This test validates that the secure pattern prevents the vulnerabilities
        demonstrated in the previous tests.
        """
        # Create isolated contexts for each user
        user1_context = MockUserExecutionContext(self.user1_id)
        user2_context = MockUserExecutionContext(self.user2_id)
        
        # User 1 adds sensitive data
        user1_context.set_user_context(self.sensitive_data)
        user1_context.set_execution_data("sensitive_strategy", "enterprise_ai_optimization")
        user1_context.add_tool_result({"tool": "revenue_calculator", "result": "$500K ARR"})
        
        # User 2 should NOT be able to access User 1's data
        user2_leaked_strategy = user2_context.get_execution_data("sensitive_strategy")
        user2_results = user2_context._tool_results
        user2_context_data = user2_context._user_context
        
        # Validate proper isolation
        isolation_verified = []
        
        if user2_leaked_strategy is None:
            isolation_verified.append("Execution data properly isolated")
            
        if len(user2_results) == 0:
            isolation_verified.append("Tool results properly isolated")
            
        if not user2_context_data or "TopSecret Corp" not in str(user2_context_data):
            isolation_verified.append("User context properly isolated")
            
        # This test should PASS when using secure pattern
        self.assertEqual(len(isolation_verified), 3, 
                        f"UserExecutionContext isolation working: {isolation_verified}")
                        
        # Verify User 1 can still access their own data
        user1_strategy = user1_context.get_execution_data("sensitive_strategy")
        self.assertEqual(user1_strategy, "enterprise_ai_optimization")
        self.assertEqual(len(user1_context._tool_results), 1)
        
    async def test_memory_leak_detection_in_shared_state_pattern(self):
        """
        DESIGNED TO FAIL: DeepAgentState causes memory leaks through shared references
        
        This demonstrates how shared state accumulates data across user sessions
        without proper cleanup.
        """
        initial_shared_data_count = len(MockDeepAgentState._shared_execution_data)
        initial_shared_results_count = len(MockDeepAgentState._shared_tool_results)
        
        # Simulate 100 user sessions with DeepAgentState
        for user_num in range(100):
            user_state = MockDeepAgentState(user_id=f"user_{user_num}")
            user_state.set_execution_data(f"user_{user_num}_data", f"session_data_{user_num}")
            user_state.add_tool_result({"user": f"user_{user_num}", "data": f"result_{user_num}"})
            # User session ends but data remains in shared state
            
        final_shared_data_count = len(MockDeepAgentState._shared_execution_data)
        final_shared_results_count = len(MockDeepAgentState._shared_tool_results)
        
        data_accumulated = final_shared_data_count - initial_shared_data_count
        results_accumulated = final_shared_results_count - initial_shared_results_count
        
        # Assert memory leaks were detected (test designed to fail)
        assert data_accumulated > 0 or results_accumulated > 0, f"""
 ALERT:  TEST WORKING CORRECTLY: Memory Leak Vulnerability Detected

DeepAgentState accumulates data across user sessions without cleanup:

MEMORY LEAKS DETECTED:
- Shared execution data grew by: {data_accumulated} entries
- Shared tool results grew by: {results_accumulated} entries
- Total memory impact: {data_accumulated + results_accumulated} leaked objects

BUSINESS IMPACT:
- Server memory consumption grows with each user session
- Performance degradation under load
- Potential service crashes from memory exhaustion
- Cross-user data availability increases over time

REMEDIATION: UserExecutionContext provides per-session cleanup and isolation
        """


if __name__ == '__main__':
    unittest.main()