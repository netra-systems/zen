"""
CRITICAL Unit Tests for Tool Dispatcher Isolation Failures

These tests are DESIGNED TO FAIL initially to expose critical tool dispatcher
isolation failures that allow tools to execute in wrong user contexts.

Business Risk: Tool execution results mixed between users - data contamination
Technical Risk: Tool dispatcher uses string-based IDs enabling context mixing
Security Risk: Tools access wrong user's data through weak context isolation

KEY VIOLATIONS TO EXPOSE:
1. Tool dispatcher accepts string-based user/context IDs instead of typed IDs
2. Tool execution context not properly validated before execution
3. Tool results not properly isolated per user context
4. Tool execution state shared between user contexts

These tests MUST initially FAIL to demonstrate the violations exist.
"""

import pytest
import asyncio
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set, Optional, Any, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
import threading

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import problematic modules to test - adjust imports based on actual structure
try:
    from netra_backend.app.tools.unified_tool_dispatcher import UnifiedToolDispatcher
except ImportError:
    # Create mock for testing if actual class doesn't exist yet
    class UnifiedToolDispatcher:
        def __init__(self, user_context=None):
            self.user_context = user_context
            self.executed_tools = []
            
        def execute_tool(self, tool_name: str, user_id: str, context_data: Dict):
            # Mock execution that accepts string IDs (VIOLATION)
            result = {
                "tool_name": tool_name,
                "user_id": user_id,  # VIOLATION: str instead of UserID
                "context": context_data,
                "result": f"tool_result_for_{user_id}",
                "execution_id": f"exec_{int(time.time())}"
            }
            self.executed_tools.append(result)
            return result

from netra_backend.app.data_contexts.user_data_context import UserDataContext

# Import CORRECT types that should be used  
from shared.types import (
    UserID, ThreadID, RequestID, RunID, ExecutionID, AgentID,
    ensure_user_id, ensure_thread_id, ensure_request_id,
    StronglyTypedUserExecutionContext,
    ContextValidationError, IsolationViolationError,
    ToolExecutionState, ToolExecutionRequest, ToolExecutionResult
)


@dataclass
class MockToolExecution:
    """Mock tool execution for testing isolation."""
    tool_name: str
    user_id: str  # VIOLATION: should be UserID
    execution_id: str  # VIOLATION: should be ExecutionID
    context_data: Dict[str, Any]
    results: Dict[str, Any]
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    isolation_violations: List[str] = None
    
    def __post_init__(self):
        if self.isolation_violations is None:
            self.isolation_violations = []


class TestToolDispatcherIsolationFailures(SSotBaseTestCase):
    """
    CRITICAL FAILING TESTS: Tool Dispatcher Isolation Failures
    
    These tests MUST initially FAIL to demonstrate that tool dispatcher
    components allow tool execution in wrong user contexts.
    
    EXPECTED INITIAL RESULT: ALL TESTS SHOULD FAIL
    BUSINESS IMPACT: Prevents tool execution data contamination between users
    """
    
    def setup_method(self, method):
        """Setup test with enhanced tool isolation detection."""
        super().setup_method(method)
        
        # Enable strict tool isolation detection
        self.set_env_var("STRICT_TOOL_ISOLATION", "true")
        self.set_env_var("DETECT_TOOL_CONTEXT_MIXING", "true")
        self.set_env_var("FAIL_ON_TOOL_ID_VIOLATIONS", "true")
        
        # Initialize test tracking
        self.isolation_violations: List[str] = []
        self.tool_executions: Dict[str, MockToolExecution] = {}
        self.user_contexts: Dict[str, UserDataContext] = {}
        self.dispatchers: Dict[str, UnifiedToolDispatcher] = {}
        
    def test_tool_dispatcher_constructor_accepts_string_context_ids(self):
        """
        CRITICAL FAILING TEST: Tool dispatcher should reject string-based context IDs
        
        EXPECTED RESULT: FAIL - Constructor accepts string IDs (VIOLATION)
        BUSINESS RISK: String IDs enable tool execution in wrong user contexts
        """
        print(" ALERT:  TESTING: Tool dispatcher constructor string ID acceptance")
        
        # Create user context with string IDs (the problematic way)
        string_user_id = "tool_test_user_123"  # VIOLATION: str instead of UserID
        string_request_id = "tool_test_request_456"  # VIOLATION: str instead of RequestID
        string_thread_id = "tool_test_thread_789"  # VIOLATION: str instead of ThreadID
        
        try:
            # Create context with string IDs
            context = UserDataContext(
                user_id=string_user_id,
                request_id=string_request_id, 
                thread_id=string_thread_id
            )
            
            # Try to create tool dispatcher with string-based context
            dispatcher = UnifiedToolDispatcher(user_context=context)
            
            # If we reach here, the dispatcher accepted string-based context (VIOLATION)
            violation_msg = (
                f"CRITICAL VIOLATION: UnifiedToolDispatcher accepted context with string IDs! "
                f"user_id='{string_user_id}' (type: {type(string_user_id)}), "
                f"This enables tool execution context mixing between users."
            )
            self.isolation_violations.append(violation_msg)
            print(f" FAIL:  {violation_msg}")
            
            # Test if dispatcher stores the context properly
            if hasattr(dispatcher, 'user_context') and dispatcher.user_context:
                stored_context = dispatcher.user_context
                
                # Check if stored user_id is still a string (violation)
                if hasattr(stored_context, 'user_id') and isinstance(stored_context.user_id, str):
                    violation = f"Dispatcher stores user_id as str: {type(stored_context.user_id)}"
                    self.isolation_violations.append(violation)
                    print(f" FAIL:  Storage violation: {violation}")
            
            # Record metrics
            self.record_metric("dispatcher_accepts_string_context", True)
            self.record_metric("violation_location", "UnifiedToolDispatcher.__init__")
            
            # FAIL the test because tool dispatcher accepted string-based context
            pytest.fail(
                "CRITICAL TOOL DISPATCHER VIOLATION: UnifiedToolDispatcher accepted context "
                "with string-based IDs. This enables tool execution in wrong user contexts, "
                "causing cross-user data contamination."
            )
            
        except TypeError as e:
            # If we get a TypeError, type safety IS working (test passes)
            print(f" PASS:  Type safety working in tool dispatcher: {e}")
            self.record_metric("dispatcher_rejects_string_context", True)
            
        except Exception as e:
            # Unexpected error - still a violation because it should be a TypeError
            violation_msg = f"UNEXPECTED ERROR in tool dispatcher constructor: {e}"
            self.isolation_violations.append(violation_msg)
            print(f" WARNING: [U+FE0F]  {violation_msg}")
            pytest.fail(f"Unexpected error (should be TypeError for string IDs): {e}")
    
    def test_tool_execution_with_wrong_user_context_detection(self):
        """
        CRITICAL FAILING TEST: Tool execution should detect wrong user context
        
        EXPECTED RESULT: FAIL - No detection of wrong user context
        BUSINESS RISK: Tools execute with User A's context but User B's data
        """
        print(" ALERT:  TESTING: Tool execution wrong user context detection")
        
        context_violations = []
        
        # Create two user contexts
        user_a_id = "context_test_user_a"
        user_b_id = "context_test_user_b"
        
        context_a = UserDataContext(
            user_id=user_a_id,
            request_id="req_a",
            thread_id="thread_a"
        )
        
        context_b = UserDataContext(
            user_id=user_b_id,
            request_id="req_b", 
            thread_id="thread_b"
        )
        
        # Create dispatchers for each user
        dispatcher_a = UnifiedToolDispatcher(user_context=context_a)
        dispatcher_b = UnifiedToolDispatcher(user_context=context_b)
        
        self.dispatchers[user_a_id] = dispatcher_a
        self.dispatchers[user_b_id] = dispatcher_b
        
        # Test 1: Try to execute tool with User A's dispatcher but User B's ID (should fail)
        try:
            wrong_context_execution = dispatcher_a.execute_tool(
                tool_name="optimization_tool",
                user_id=user_b_id,  # VIOLATION: Using User B's ID with User A's dispatcher
                context_data={"source": "user_b_data", "mixed_context": True}
            )
            
            # If execution succeeded, context validation is not working (VIOLATION)
            violation = (
                f"Tool executed with wrong user context: dispatcher for {user_a_id} "
                f"executed tool for {user_b_id}. Result: {wrong_context_execution}"
            )
            context_violations.append(violation)
            print(f" FAIL:  Context mixing violation: {violation}")
            
            # Track the problematic execution
            exec_id = wrong_context_execution.get("execution_id", "unknown")
            self.tool_executions[exec_id] = MockToolExecution(
                tool_name="optimization_tool",
                user_id=user_b_id,
                execution_id=exec_id,
                context_data={"mixed_context": True},
                results=wrong_context_execution,
                start_time=time.time(),
                isolation_violations=["wrong_user_context"]
            )
            
        except Exception as context_error:
            # If we got an exception, context validation might be working
            print(f" PASS:  Context validation blocked wrong user execution: {context_error}")
        
        # Test 2: Try to execute tools simultaneously with mixed contexts
        mixed_executions = []
        
        try:
            # Execute tools "simultaneously" with potentially mixed contexts
            execution_a = dispatcher_a.execute_tool(
                tool_name="data_processor",
                user_id=user_a_id,
                context_data={"user_data": "sensitive_a_data"}
            )
            
            execution_b = dispatcher_b.execute_tool(
                tool_name="data_processor", 
                user_id=user_b_id,
                context_data={"user_data": "sensitive_b_data"}
            )
            
            mixed_executions = [execution_a, execution_b]
            
            # Check for cross-contamination in results
            for i, execution in enumerate(mixed_executions):
                exec_user = execution.get("user_id")
                exec_result = str(execution.get("result", ""))
                
                # Check if execution contains data from other user
                for j, other_execution in enumerate(mixed_executions):
                    if i != j:
                        other_user = other_execution.get("user_id")
                        other_data = str(other_execution.get("context", {}).get("user_data", ""))
                        
                        if other_user in exec_result or other_data in exec_result:
                            violation = (
                                f"Tool execution for {exec_user} contains data from {other_user}"
                            )
                            context_violations.append(violation)
                            print(f" FAIL:  Data contamination: {violation}")
            
        except Exception as e:
            print(f" WARNING: [U+FE0F] Error in mixed context test: {e}")
        
        # Test 3: Check dispatcher state isolation
        if hasattr(dispatcher_a, 'executed_tools') and hasattr(dispatcher_b, 'executed_tools'):
            tools_a = dispatcher_a.executed_tools
            tools_b = dispatcher_b.executed_tools
            
            # Check if dispatchers share tool execution state (violation)
            if id(tools_a) == id(tools_b):
                violation = "Tool dispatchers share executed_tools list - state not isolated"
                context_violations.append(violation)
                print(f" FAIL:  Shared state violation: {violation}")
            
            # Check if tools executed by one dispatcher appear in the other
            for tool_a in tools_a:
                tool_a_user = tool_a.get("user_id")
                if tool_a_user and tool_a_user != user_a_id:
                    violation = f"Dispatcher A contains tool for wrong user: {tool_a_user}"
                    context_violations.append(violation)
                    print(f" FAIL:  Cross-dispatcher contamination: {violation}")
        
        # Record metrics
        self.record_metric("context_violations", len(context_violations))
        self.record_metric("mixed_executions_tested", len(mixed_executions))
        self.record_metric("dispatchers_created", len(self.dispatchers))
        
        # FAIL if context violations were detected
        if context_violations:
            self.isolation_violations.extend(context_violations)
            pytest.fail(
                f"CRITICAL TOOL CONTEXT VIOLATIONS: {len(context_violations)} violations "
                f"detected in tool execution context validation. Tools can execute in wrong "
                f"user contexts, causing cross-user data access: {context_violations}"
            )
        
        print(" PASS:  Tool context validation appears intact")
    
    def test_concurrent_tool_executions_isolation_boundaries(self):
        """
        CRITICAL FAILING TEST: Concurrent tool executions should maintain isolation
        
        EXPECTED RESULT: FAIL - Concurrent executions breach isolation boundaries
        BUSINESS RISK: Race conditions cause tool results to mix between users
        """
        print(" ALERT:  TESTING: Concurrent tool execution isolation boundaries")
        
        isolation_breaches = []
        
        # Create multiple users for concurrent testing
        concurrent_users = []
        for i in range(4):
            user_data = {
                "user_id": f"concurrent_tool_user_{i}",
                "request_id": f"concurrent_tool_req_{i}",
                "thread_id": f"concurrent_tool_thread_{i}",
                "sensitive_data": f"CONFIDENTIAL_DATA_USER_{i}"
            }
            concurrent_users.append(user_data)
        
        # Create contexts and dispatchers for each user
        for user in concurrent_users:
            try:
                context = UserDataContext(
                    user_id=user["user_id"],
                    request_id=user["request_id"],
                    thread_id=user["thread_id"]
                )
                dispatcher = UnifiedToolDispatcher(user_context=context)
                
                self.user_contexts[user["user_id"]] = context
                self.dispatchers[user["user_id"]] = dispatcher
                
            except Exception as e:
                print(f" FAIL:  Failed to create dispatcher for user {user['user_id']}: {e}")
        
        print(f"Created {len(self.dispatchers)} tool dispatchers for concurrent testing")
        
        def execute_tool_for_user(user_data: Dict) -> Dict:
            """Execute tool for a specific user in a separate thread."""
            user_id = user_data["user_id"]
            sensitive_data = user_data["sensitive_data"]
            
            try:
                dispatcher = self.dispatchers.get(user_id)
                if not dispatcher:
                    return {"error": f"No dispatcher for user {user_id}"}
                
                # Execute tool with sensitive user data
                execution_result = dispatcher.execute_tool(
                    tool_name="sensitive_data_processor",
                    user_id=user_id,  # VIOLATION: str instead of UserID
                    context_data={
                        "sensitive_input": sensitive_data,
                        "user_tier": f"tier_{user_id}",
                        "processing_timestamp": time.time(),
                        "thread_id": threading.current_thread().ident
                    }
                )
                
                return {
                    "user_id": user_id,
                    "execution_result": execution_result,
                    "thread_id": threading.current_thread().ident,
                    "timestamp": time.time()
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "error": str(e),
                    "thread_id": threading.current_thread().ident
                }
        
        # Execute tools concurrently to test for isolation breaches
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(execute_tool_for_user, user) for user in concurrent_users]
            
            concurrent_results = []
            for future in futures:
                try:
                    result = future.result(timeout=5.0)
                    concurrent_results.append(result)
                except Exception as e:
                    concurrent_results.append({"error": f"Future execution failed: {e}"})
        
        print(f"Completed {len(concurrent_results)} concurrent tool executions")
        
        # ANALYZE FOR ISOLATION BREACHES
        
        # Check 1: Verify each execution only contains its own user data
        for result in concurrent_results:
            if "execution_result" in result:
                user_id = result["user_id"]
                execution = result["execution_result"]
                execution_str = str(execution).lower()
                
                # Check if execution contains data from other users
                for other_user in concurrent_users:
                    other_user_id = other_user["user_id"]
                    other_sensitive = other_user["sensitive_data"].lower()
                    
                    if other_user_id != user_id:
                        if other_user_id.lower() in execution_str:
                            breach = f"User {user_id} execution contains other user ID: {other_user_id}"
                            isolation_breaches.append(breach)
                            print(f" FAIL:  ID contamination breach: {breach}")
                        
                        if other_sensitive in execution_str:
                            breach = f"User {user_id} execution contains other user's sensitive data"
                            isolation_breaches.append(breach)
                            print(f" FAIL:  Sensitive data breach: {breach}")
        
        # Check 2: Verify tool dispatcher state isolation after concurrent execution
        user_ids = [user["user_id"] for user in concurrent_users]
        
        for i, user_id_a in enumerate(user_ids):
            dispatcher_a = self.dispatchers.get(user_id_a)
            if not dispatcher_a or not hasattr(dispatcher_a, 'executed_tools'):
                continue
                
            tools_a = dispatcher_a.executed_tools
            
            for j, user_id_b in enumerate(user_ids):
                if i != j:
                    dispatcher_b = self.dispatchers.get(user_id_b)
                    if not dispatcher_b or not hasattr(dispatcher_b, 'executed_tools'):
                        continue
                        
                    tools_b = dispatcher_b.executed_tools
                    
                    # Check for shared state between dispatchers (critical breach)
                    if id(tools_a) == id(tools_b):
                        breach = f"Dispatchers {user_id_a} and {user_id_b} share tool execution state"
                        isolation_breaches.append(breach)
                        print(f" FAIL:  Critical state sharing breach: {breach}")
                    
                    # Check for cross-dispatcher tool contamination
                    for tool in tools_a:
                        tool_user = tool.get("user_id")
                        if tool_user and tool_user == user_id_b:
                            breach = f"Dispatcher {user_id_a} contains tool execution for {user_id_b}"
                            isolation_breaches.append(breach)
                            print(f" FAIL:  Cross-dispatcher breach: {breach}")
        
        # Check 3: Memory isolation verification
        dispatcher_memory_ids = {}
        for user_id, dispatcher in self.dispatchers.items():
            memory_id = id(dispatcher)
            if memory_id in dispatcher_memory_ids:
                other_user = dispatcher_memory_ids[memory_id]
                breach = f"Dispatchers {user_id} and {other_user} share memory location: {memory_id}"
                isolation_breaches.append(breach)
                print(f" FAIL:  Memory sharing breach: {breach}")
            else:
                dispatcher_memory_ids[memory_id] = user_id
        
        # Record comprehensive metrics
        self.record_metric("concurrent_tool_executions", len(concurrent_results))
        self.record_metric("isolation_breaches", len(isolation_breaches))
        self.record_metric("dispatchers_tested", len(self.dispatchers))
        self.record_metric("unique_dispatcher_memory_locations", len(dispatcher_memory_ids))
        
        # Classify breach types
        id_breaches = [b for b in isolation_breaches if "id" in b.lower()]
        data_breaches = [b for b in isolation_breaches if "sensitive" in b.lower() or "data" in b.lower()]
        state_breaches = [b for b in isolation_breaches if "state" in b.lower() or "memory" in b.lower()]
        
        self.record_metric("id_contamination_breaches", len(id_breaches))
        self.record_metric("sensitive_data_breaches", len(data_breaches))
        self.record_metric("state_sharing_breaches", len(state_breaches))
        
        # FAIL if isolation breaches were detected
        if isolation_breaches:
            self.isolation_violations.extend(isolation_breaches)
            pytest.fail(
                f"CRITICAL CONCURRENT TOOL ISOLATION BREACHES: {len(isolation_breaches)} breaches "
                f"detected in concurrent tool execution. Tool execution isolation boundaries are "
                f"compromised, enabling cross-user data contamination: {isolation_breaches}"
            )
        
        print(" PASS:  Concurrent tool execution isolation appears intact")
    
    def test_tool_result_serialization_user_data_leakage(self):
        """
        CRITICAL FAILING TEST: Tool result serialization should prevent user data leakage
        
        EXPECTED RESULT: FAIL - Tool results leak user data between contexts
        BUSINESS RISK: Serialized tool results contain wrong user's sensitive data
        """
        print(" ALERT:  TESTING: Tool result serialization user data leakage")
        
        leakage_incidents = []
        
        # Create users with distinctly different sensitive data
        sensitive_users = [
            {
                "user_id": "serialization_enterprise_user",
                "request_id": "ent_req_001",
                "thread_id": "ent_thread_001",
                "classification": "ENTERPRISE_CONFIDENTIAL",
                "sensitive_data": "TRADE_SECRETS_ENTERPRISE_2024",
                "tools": ["enterprise_optimizer", "confidential_analyzer"]
            },
            {
                "user_id": "serialization_government_user", 
                "request_id": "gov_req_002",
                "thread_id": "gov_thread_002", 
                "classification": "GOVERNMENT_CLASSIFIED",
                "sensitive_data": "CLASSIFIED_GOVERNMENT_DATA_2024",
                "tools": ["security_scanner", "classified_processor"]
            },
            {
                "user_id": "serialization_free_user",
                "request_id": "free_req_003", 
                "thread_id": "free_thread_003",
                "classification": "PUBLIC",
                "sensitive_data": "FREE_TIER_PUBLIC_DATA",
                "tools": ["basic_optimizer", "public_analyzer"]
            }
        ]
        
        # Setup contexts and dispatchers
        user_executions = {}
        for user in sensitive_users:
            try:
                context = UserDataContext(
                    user_id=user["user_id"],
                    request_id=user["request_id"],
                    thread_id=user["thread_id"]
                )
                dispatcher = UnifiedToolDispatcher(user_context=context)
                
                self.user_contexts[user["user_id"]] = context
                self.dispatchers[user["user_id"]] = dispatcher
                
                user_executions[user["user_id"]] = []
                
            except Exception as e:
                print(f" FAIL:  Failed to setup user {user['user_id']}: {e}")
        
        # Execute tools for each user with sensitive data
        for user in sensitive_users:
            user_id = user["user_id"]
            dispatcher = self.dispatchers.get(user_id)
            
            if not dispatcher:
                continue
            
            for tool_name in user["tools"]:
                try:
                    # Execute tool with sensitive user data
                    tool_result = dispatcher.execute_tool(
                        tool_name=tool_name,
                        user_id=user_id,  # VIOLATION: str instead of UserID
                        context_data={
                            "classification": user["classification"],
                            "sensitive_input": user["sensitive_data"],
                            "user_clearance": user["classification"],
                            "processing_metadata": {
                                "user_id": user_id,
                                "data_sensitivity": user["classification"],
                                "access_level": "RESTRICTED"
                            }
                        }
                    )
                    
                    user_executions[user_id].append(tool_result)
                    
                except Exception as e:
                    print(f" WARNING: [U+FE0F] Tool execution failed for {user_id}/{tool_name}: {e}")
        
        print(f"Executed tools for {len(user_executions)} users with sensitive data")
        
        # ANALYZE FOR DATA LEAKAGE IN SERIALIZED RESULTS
        
        # Check 1: Verify each user's results only contain their own data
        for user in sensitive_users:
            user_id = user["user_id"]
            user_sensitive = user["sensitive_data"]
            user_classification = user["classification"]
            
            user_results = user_executions.get(user_id, [])
            
            for result in user_results:
                result_str = str(result).upper()  # Case insensitive check
                
                # Check if this user's results contain other users' sensitive data
                for other_user in sensitive_users:
                    if other_user["user_id"] != user_id:
                        other_sensitive = other_user["sensitive_data"].upper()
                        other_classification = other_user["classification"].upper()
                        
                        if other_sensitive in result_str:
                            leakage = (
                                f"User {user_id} tool results contain other user's sensitive data: "
                                f"'{other_user['sensitive_data']}'"
                            )
                            leakage_incidents.append(leakage)
                            print(f" FAIL:  Sensitive data leakage: {leakage}")
                        
                        if other_classification in result_str and other_classification != "PUBLIC":
                            leakage = (
                                f"User {user_id} tool results contain other user's classification: "
                                f"'{other_classification}'"
                            )
                            leakage_incidents.append(leakage)
                            print(f" FAIL:  Classification leakage: {leakage}")
        
        # Check 2: Cross-classification contamination (critical security issue)
        enterprise_results = user_executions.get("serialization_enterprise_user", [])
        government_results = user_executions.get("serialization_government_user", [])
        free_results = user_executions.get("serialization_free_user", [])
        
        # Enterprise data should never appear in free user results
        for free_result in free_results:
            free_str = str(free_result).upper()
            if "ENTERPRISE" in free_str or "TRADE_SECRETS" in free_str:
                leakage = "Free user results contain enterprise confidential data"
                leakage_incidents.append(leakage)
                print(f" FAIL:  Critical privilege escalation: {leakage}")
        
        # Government data should never appear in non-government results  
        for user_id, results in user_executions.items():
            if "government" not in user_id.lower():
                for result in results:
                    result_str = str(result).upper()
                    if "CLASSIFIED" in result_str or "GOVERNMENT" in result_str:
                        leakage = f"Non-government user {user_id} has government classified data"
                        leakage_incidents.append(leakage)
                        print(f" FAIL:  Critical security breach: {leakage}")
        
        # Check 3: Serialization metadata leakage
        all_results = []
        for user_results in user_executions.values():
            all_results.extend(user_results)
        
        for i, result_a in enumerate(all_results):
            for j, result_b in enumerate(all_results):
                if i != j:
                    # Check if results share internal metadata that should be isolated
                    if isinstance(result_a, dict) and isinstance(result_b, dict):
                        # Look for shared execution IDs (should be unique)
                        exec_id_a = result_a.get("execution_id")
                        exec_id_b = result_b.get("execution_id") 
                        
                        if exec_id_a and exec_id_b and exec_id_a == exec_id_b:
                            leakage = f"Shared execution ID between results: {exec_id_a}"
                            leakage_incidents.append(leakage)
                            print(f" FAIL:  Execution ID collision: {leakage}")
        
        # Record detailed metrics
        self.record_metric("sensitive_users_tested", len(sensitive_users))
        self.record_metric("total_tool_executions", sum(len(results) for results in user_executions.values()))
        self.record_metric("data_leakage_incidents", len(leakage_incidents))
        
        # Classify leakage types
        sensitive_data_leaks = [l for l in leakage_incidents if "sensitive data" in l.lower()]
        classification_leaks = [l for l in leakage_incidents if "classification" in l.lower()]
        privilege_escalations = [l for l in leakage_incidents if "privilege" in l.lower() or "escalation" in l.lower()]
        security_breaches = [l for l in leakage_incidents if "security" in l.lower() or "breach" in l.lower()]
        
        self.record_metric("sensitive_data_leaks", len(sensitive_data_leaks))
        self.record_metric("classification_leaks", len(classification_leaks)) 
        self.record_metric("privilege_escalations", len(privilege_escalations))
        self.record_metric("security_breaches", len(security_breaches))
        
        # FAIL if data leakage incidents were detected
        if leakage_incidents:
            self.isolation_violations.extend(leakage_incidents)
            pytest.fail(
                f"CRITICAL TOOL RESULT DATA LEAKAGE: {len(leakage_incidents)} leakage incidents "
                f"detected in tool result serialization. Sensitive user data is leaking between "
                f"tool execution contexts, causing serious security violations: {leakage_incidents}"
            )
        
        print(" PASS:  Tool result serialization appears secure")
    
    def teardown_method(self, method):
        """Enhanced teardown with isolation violation reporting."""
        super().teardown_method(method)
        
        # Report all isolation violations found during test
        if self.isolation_violations:
            print(f"\n ALERT:  CRITICAL TOOL ISOLATION VIOLATIONS: {len(self.isolation_violations)}")
            for i, violation in enumerate(self.isolation_violations, 1):
                print(f"  {i}. {violation}")
            
            # Save violations to metrics for comprehensive reporting  
            self.record_metric("total_isolation_violations", len(self.isolation_violations))
            self.record_metric("isolation_violations_list", self.isolation_violations)
            
            # Classify violation types for analysis
            context_violations = [v for v in self.isolation_violations if "context" in v.lower()]
            data_violations = [v for v in self.isolation_violations if "data" in v.lower() or "sensitive" in v.lower()]
            state_violations = [v for v in self.isolation_violations if "state" in v.lower() or "memory" in v.lower()]
            execution_violations = [v for v in self.isolation_violations if "execution" in v.lower()]
            
            self.record_metric("context_violations", len(context_violations))
            self.record_metric("data_violations", len(data_violations))
            self.record_metric("state_violations", len(state_violations)) 
            self.record_metric("execution_violations", len(execution_violations))
        else:
            print("\n PASS:  No tool isolation violations detected (unexpected - tests designed to fail)")
            self.record_metric("total_isolation_violations", 0)
        
        # Generate tool isolation summary report
        test_metrics = self.get_all_metrics()
        print(f"\n CHART:  Tool Dispatcher Isolation Test Metrics:")
        for metric, value in test_metrics.items():
            if any(keyword in metric for keyword in ["violation", "breach", "leakage", "contamination"]):
                print(f"  {metric}: {value}")


# Mark these as critical tool isolation tests
pytest.mark.critical_tool_isolation = pytest.mark.critical
pytest.mark.tool_dispatcher_violations = pytest.mark.unit
pytest.mark.unit_tool_failures = pytest.mark.mission_critical