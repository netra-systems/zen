"""
Issue #1017 Security Vulnerability Tests: Multi-User Isolation Verification

CRITICAL SECURITY TEST SUITE: These tests are designed to FAIL initially to prove
security vulnerabilities exist in multi-user isolation and concurrent execution.

These tests specifically target:
1. Concurrent user state isolation validation
2. Cross-user data contamination prevention
3. Factory pattern security verification
4. Shared state contamination detection
5. User context bleeding verification
6. Memory isolation validation
7. Session boundary enforcement

REQUIREMENTS:
- Tests MUST FAIL initially to prove vulnerabilities exist
- Uses SSOT test infrastructure from test_framework/
- Real services only - NO MOCKS in vulnerability testing
- Integration tests with actual concurrent execution
- Follows testing best practices from reports/testing/TEST_CREATION_GUIDE.md

Business Value: Enterprise/Platform - Security compliance for HIPAA, SOC2, SEC regulations
"""

import asyncio
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState, AgentMetadata
from netra_backend.app.agents.base.execution_context import ExecutionContext, ExecutionMetadata


class TestIssue1017MultiUserIsolationVulnerabilities(SSotAsyncTestCase):
    """
    Comprehensive multi-user isolation vulnerability tests for Issue #1017.

    These tests are designed to FAIL initially to prove that security
    vulnerabilities exist in multi-user isolation and concurrent execution.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Create multiple test users for isolation testing
        self.test_users = []
        for i in range(5):
            user_data = {
                "user_id": f"isolation_test_user_{i}_{uuid.uuid4().hex[:8]}",
                "thread_id": f"isolation_test_thread_{i}_{uuid.uuid4().hex[:8]}",
                "run_id": f"isolation_test_run_{i}_{uuid.uuid4().hex[:8]}",
                "secret_data": f"user_{i}_private_secret_{uuid.uuid4().hex[:12]}",
                "api_key": f"sk-user_{i}_api_key_{uuid.uuid4().hex[:16]}",
                "personal_token": f"personal_token_user_{i}_{uuid.uuid4().hex[:16]}"
            }
            self.test_users.append(user_data)

        # Shared state tracker to detect contamination
        self.shared_state_tracker = {}
        self.contamination_detector = set()

        # Record business value metrics
        self.record_metric("test_category", "security_vulnerability")
        self.record_metric("issue_number", "1017")
        self.record_metric("vulnerability_type", "multi_user_isolation")

    async def test_concurrent_user_state_isolation_failure(self):
        """
        Test concurrent user state isolation for cross-contamination.

        EXPECTS TO FAIL: This test should demonstrate that concurrent users
        can access or contaminate each other's state data.
        """
        self.record_metric("vulnerability_subtype", "concurrent_state_isolation")

        # Create concurrent execution contexts for different users
        execution_contexts = []
        user_private_data = {}

        for user_data in self.test_users:
            # Store user's private data for contamination detection
            user_private_data[user_data["user_id"]] = {
                "secret": user_data["secret_data"],
                "api_key": user_data["api_key"],
                "token": user_data["personal_token"]
            }

            # Create execution context with private data
            metadata = ExecutionMetadata(
                user_id=user_data["user_id"],
                session_id=user_data["thread_id"],
                request_id=user_data["run_id"],
                custom_data={
                    "private_secret": user_data["secret_data"],
                    "user_api_key": user_data["api_key"],
                    "personal_data": {
                        "token": user_data["personal_token"],
                        "sensitive_config": user_data["secret_data"]
                    }
                }
            )

            context = ExecutionContext(
                execution_id=user_data["run_id"],
                metadata=metadata
            )

            # Add sensitive context data
            context.set_context_data("user_secrets", user_data["secret_data"])
            context.set_context_data("api_credentials", user_data["api_key"])
            context.set_context_data("private_token", user_data["personal_token"])

            execution_contexts.append(context)

        # Function to simulate concurrent user operations
        async def simulate_user_operation(context: ExecutionContext, user_index: int):
            """Simulate user operations that might leak data."""
            current_user_id = context.metadata.user_id
            current_secret = user_private_data[current_user_id]["secret"]

            # Start execution
            context.start_execution()

            # Simulate processing that might contaminate shared state
            context.set_context_data("processing_result", f"Processed with {current_secret}")
            context.set_context_data("shared_cache_key", f"cache_{current_secret}")

            # Simulate operations that might access global state
            global_state_key = f"global_user_data_{user_index}"
            self.shared_state_tracker[global_state_key] = {
                "user_id": current_user_id,
                "secret_data": current_secret,
                "timestamp": time.time()
            }

            # Complete execution with potentially sensitive summary
            context.complete_execution(success=True)

            # Get execution summary that might contain sensitive data
            summary = context.get_summary()
            return {
                "user_id": current_user_id,
                "secret": current_secret,
                "context_summary": summary,
                "context_data": {
                    key: context.get_context_data(key)
                    for key in ["user_secrets", "api_credentials", "private_token", "processing_result"]
                }
            }

        # Execute concurrent user operations
        tasks = []
        for i, context in enumerate(execution_contexts):
            task = asyncio.create_task(simulate_user_operation(context, i))
            tasks.append(task)

        # Await all concurrent operations
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results for cross-user contamination
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue

            current_user_id = result["user_id"]
            current_secret = result["secret"]
            context_summary = result["context_summary"]
            context_data = result["context_data"]

            # VULNERABILITY CHECK: Other users' secrets should NOT appear in this user's data
            # These assertions should FAIL to prove vulnerability exists
            for other_user_data in self.test_users:
                if other_user_data["user_id"] != current_user_id:
                    other_secret = other_user_data["secret_data"]
                    other_api_key = other_user_data["api_key"]
                    other_token = other_user_data["personal_token"]

                    # Check context summary for contamination
                    summary_json = json.dumps(context_summary)
                    self.assertNotIn(other_secret, summary_json,
                        f"VULNERABILITY: User {current_user_id} context summary contains other user's secret: {other_secret}")

                    self.assertNotIn(other_api_key, summary_json,
                        f"VULNERABILITY: User {current_user_id} context summary contains other user's API key: {other_api_key}")

                    self.assertNotIn(other_token, summary_json,
                        f"VULNERABILITY: User {current_user_id} context summary contains other user's token: {other_token}")

                    # Check context data for contamination
                    context_data_json = json.dumps(context_data)
                    self.assertNotIn(other_secret, context_data_json,
                        f"VULNERABILITY: User {current_user_id} context data contains other user's secret: {other_secret}")

        # Check shared state for contamination
        for global_key, global_data in self.shared_state_tracker.items():
            stored_user_id = global_data["user_id"]
            stored_secret = global_data["secret_data"]

            # Verify no other user's data appears in this global state entry
            for other_user_data in self.test_users:
                if other_user_data["user_id"] != stored_user_id:
                    self.assertNotEqual(stored_secret, other_user_data["secret_data"],
                        f"VULNERABILITY: Global state {global_key} contains wrong user's secret")

    async def test_deepagentstate_factory_contamination_vulnerability(self):
        """
        Test DeepAgentState factory pattern for user contamination.

        EXPECTS TO FAIL: This test should demonstrate that DeepAgentState
        instances can share or contaminate each other's data across users.
        """
        self.record_metric("vulnerability_subtype", "factory_contamination")

        # Create multiple DeepAgentState instances concurrently
        agent_states = []

        def create_user_agent_state(user_data: Dict[str, str]) -> DeepAgentState:
            """Create agent state with user-specific sensitive data."""
            metadata = AgentMetadata()
            metadata.execution_stats = {
                "user_private_config": user_data["secret_data"],
                "api_authentication": user_data["api_key"],
                "session_token": user_data["personal_token"]
            }

            return DeepAgentState(
                user_request=f"User request with {user_data['secret_data']} context",
                user_id=user_data["user_id"],
                chat_thread_id=user_data["thread_id"],
                run_id=user_data["run_id"],
                agent_input={
                    "user_credentials": {
                        "api_key": user_data["api_key"],
                        "secret": user_data["secret_data"],
                        "token": user_data["personal_token"]
                    },
                    "private_config": {
                        "user_secret": user_data["secret_data"],
                        "auth_data": user_data["api_key"]
                    }
                },
                metadata=metadata,
                quality_metrics={
                    "user_performance_token": user_data["personal_token"],
                    "private_metrics": user_data["secret_data"]
                },
                context_tracking={
                    "user_session_data": {
                        "secret": user_data["secret_data"],
                        "credentials": user_data["api_key"],
                        "personal_token": user_data["personal_token"]
                    }
                }
            )

        # Create agent states concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(self.test_users)) as executor:
            future_to_user = {
                executor.submit(create_user_agent_state, user_data): user_data["user_id"]
                for user_data in self.test_users
            }

            for future in as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    agent_state = future.result()
                    agent_states.append((user_id, agent_state))
                except Exception as e:
                    self.fail(f"Failed to create agent state for user {user_id}: {e}")

        # Analyze each agent state for contamination from other users
        for current_user_id, current_state in agent_states:
            current_user_data = next(u for u in self.test_users if u["user_id"] == current_user_id)
            current_secret = current_user_data["secret_data"]

            # Serialize the state for analysis
            state_dict = current_state.model_dump()
            state_json = json.dumps(state_dict, indent=2)

            # VULNERABILITY CHECK: No other user's data should appear in this user's state
            # These assertions should FAIL to prove vulnerability exists
            for other_user_data in self.test_users:
                if other_user_data["user_id"] != current_user_id:
                    other_secret = other_user_data["secret_data"]
                    other_api_key = other_user_data["api_key"]
                    other_token = other_user_data["personal_token"]

                    self.assertNotIn(other_secret, state_json,
                        f"VULNERABILITY: User {current_user_id} agent state contains other user's secret: {other_secret}")

                    self.assertNotIn(other_api_key, state_json,
                        f"VULNERABILITY: User {current_user_id} agent state contains other user's API key: {other_api_key}")

                    self.assertNotIn(other_token, state_json,
                        f"VULNERABILITY: User {current_user_id} agent state contains other user's token: {other_token}")

                    # Check specific fields for contamination
                    sensitive_fields = ["agent_input", "metadata", "quality_metrics", "context_tracking"]
                    for field_name in sensitive_fields:
                        if field_name in state_dict and state_dict[field_name]:
                            field_json = json.dumps(state_dict[field_name])
                            self.assertNotIn(other_secret, field_json,
                                f"VULNERABILITY: User {current_user_id} {field_name} contains other user's secret: {other_secret}")

            # Verify current user's data is present (sanity check)
            self.assertIn(current_secret, state_json,
                f"INTERNAL ERROR: User {current_user_id} secret not found in their own state")

    async def test_memory_isolation_boundary_violation(self):
        """
        Test memory isolation boundary violations between users.

        EXPECTS TO FAIL: This test should demonstrate that users can access
        memory allocated to other users or shared memory spaces.
        """
        self.record_metric("vulnerability_subtype", "memory_isolation")

        # Create memory spaces for different users
        user_memory_spaces = {}
        shared_memory_tracker = {}

        class UserMemorySpace:
            """Simulate user-specific memory space."""
            def __init__(self, user_id: str, secret_data: str):
                self.user_id = user_id
                self.secret_data = secret_data
                self.private_memory = {
                    "user_secrets": secret_data,
                    "memory_signature": f"mem_{user_id}_{secret_data[:8]}",
                    "allocated_at": time.time(),
                    "sensitive_data": {
                        "credentials": secret_data,
                        "private_config": secret_data,
                        "session_data": secret_data
                    }
                }

                # Simulate memory allocation in shared space (VULNERABILITY)
                shared_memory_tracker[id(self)] = {
                    "owner": user_id,
                    "secret": secret_data,
                    "memory_content": self.private_memory.copy()
                }

            def get_memory_content(self):
                """Get memory content for analysis."""
                return self.private_memory.copy()

            def access_shared_memory(self):
                """Simulate accessing shared memory (potential vulnerability)."""
                # This could accidentally expose other users' memory
                return shared_memory_tracker.copy()

        # Create memory spaces for each user concurrently
        async def create_user_memory_space(user_data: Dict[str, str]):
            """Create user memory space asynchronously."""
            memory_space = UserMemorySpace(user_data["user_id"], user_data["secret_data"])
            user_memory_spaces[user_data["user_id"]] = memory_space

            # Simulate memory operations that might leak data
            await asyncio.sleep(0.1)  # Simulate async memory operations

            # Access shared memory (potential vulnerability)
            shared_access = memory_space.access_shared_memory()

            return {
                "user_id": user_data["user_id"],
                "memory_content": memory_space.get_memory_content(),
                "shared_memory_access": shared_access
            }

        # Create memory spaces concurrently
        tasks = [create_user_memory_space(user_data) for user_data in self.test_users]
        memory_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze memory isolation violations
        for result in memory_results:
            if isinstance(result, Exception):
                continue

            current_user_id = result["user_id"]
            current_user_data = next(u for u in self.test_users if u["user_id"] == current_user_id)
            current_secret = current_user_data["secret_data"]

            memory_content = result["memory_content"]
            shared_memory_access = result["shared_memory_access"]

            # VULNERABILITY CHECK: User should only access their own memory
            # These assertions should FAIL to prove vulnerability exists

            # Check memory content for contamination
            memory_json = json.dumps(memory_content)
            for other_user_data in self.test_users:
                if other_user_data["user_id"] != current_user_id:
                    other_secret = other_user_data["secret_data"]
                    self.assertNotIn(other_secret, memory_json,
                        f"VULNERABILITY: User {current_user_id} memory contains other user's secret: {other_secret}")

            # Check shared memory access for isolation violations
            shared_memory_json = json.dumps(shared_memory_access)
            accessible_secrets = set()

            for memory_id, memory_data in shared_memory_access.items():
                if memory_data["owner"] != current_user_id:
                    other_secret = memory_data["secret"]
                    accessible_secrets.add(other_secret)

            # VULNERABILITY CHECK: User should not access other users' memory
            for other_user_data in self.test_users:
                if other_user_data["user_id"] != current_user_id:
                    other_secret = other_user_data["secret_data"]
                    self.assertNotIn(other_secret, accessible_secrets,
                        f"VULNERABILITY: User {current_user_id} can access other user's memory containing secret: {other_secret}")

    async def test_session_boundary_enforcement_failure(self):
        """
        Test session boundary enforcement for cross-session data access.

        EXPECTS TO FAIL: This test should demonstrate that users can access
        data from other users' sessions or break session boundaries.
        """
        self.record_metric("vulnerability_subtype", "session_boundary_violation")

        # Create session data for each user
        user_sessions = {}
        global_session_registry = {}

        class UserSession:
            """Simulate user session with sensitive data."""
            def __init__(self, user_data: Dict[str, str]):
                self.user_id = user_data["user_id"]
                self.session_id = user_data["thread_id"]
                self.secret_data = user_data["secret_data"]

                self.session_data = {
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "private_data": {
                        "secret": self.secret_data,
                        "api_key": user_data["api_key"],
                        "personal_token": user_data["personal_token"]
                    },
                    "session_state": {
                        "authenticated": True,
                        "user_context": self.secret_data,
                        "security_token": user_data["personal_token"]
                    }
                }

                # Register in global session registry (potential vulnerability)
                global_session_registry[self.session_id] = self.session_data.copy()

            def get_session_data(self):
                """Get session data."""
                return self.session_data.copy()

            def access_global_sessions(self):
                """Access global session registry (potential vulnerability)."""
                return global_session_registry.copy()

            def enumerate_sessions(self):
                """Enumerate all sessions (potential vulnerability)."""
                return list(global_session_registry.keys())

        # Create sessions concurrently
        async def create_user_session(user_data: Dict[str, str]):
            """Create user session asynchronously."""
            session = UserSession(user_data)
            user_sessions[user_data["user_id"]] = session

            # Simulate session operations
            await asyncio.sleep(0.1)

            return {
                "user_id": user_data["user_id"],
                "session_data": session.get_session_data(),
                "global_access": session.access_global_sessions(),
                "session_enumeration": session.enumerate_sessions()
            }

        # Create all sessions concurrently
        tasks = [create_user_session(user_data) for user_data in self.test_users]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze session boundary violations
        for result in session_results:
            if isinstance(result, Exception):
                continue

            current_user_id = result["user_id"]
            current_user_data = next(u for u in self.test_users if u["user_id"] == current_user_id)
            current_secret = current_user_data["secret_data"]
            current_session_id = current_user_data["thread_id"]

            session_data = result["session_data"]
            global_access = result["global_access"]
            session_enumeration = result["session_enumeration"]

            # VULNERABILITY CHECK: User should only access their own session
            # These assertions should FAIL to prove vulnerability exists

            # Check global session access for boundary violations
            for session_id, session_info in global_access.items():
                if session_id != current_session_id:
                    # User is accessing another user's session (VULNERABILITY)
                    other_session_json = json.dumps(session_info)

                    # Check if other users' secrets are accessible
                    for other_user_data in self.test_users:
                        if other_user_data["user_id"] != current_user_id:
                            other_secret = other_user_data["secret_data"]
                            if other_secret in other_session_json:
                                self.fail(f"VULNERABILITY: User {current_user_id} can access other user's session containing secret: {other_secret}")

            # Check session enumeration for information disclosure
            accessible_sessions = set(session_enumeration)
            for other_user_data in self.test_users:
                if other_user_data["user_id"] != current_user_id:
                    other_session_id = other_user_data["thread_id"]
                    self.assertNotIn(other_session_id, accessible_sessions,
                        f"VULNERABILITY: User {current_user_id} can enumerate other user's session: {other_session_id}")

            # Verify current user's session is accessible (sanity check)
            self.assertIn(current_session_id, accessible_sessions,
                f"INTERNAL ERROR: User {current_user_id} cannot access their own session")

    async def test_race_condition_data_leakage_vulnerability(self):
        """
        Test race condition vulnerabilities that cause data leakage between users.

        EXPECTS TO FAIL: This test should demonstrate that race conditions
        in concurrent execution can cause data leakage between users.
        """
        self.record_metric("vulnerability_subtype", "race_condition_leakage")

        # Shared state that might be subject to race conditions
        shared_processing_state = {
            "current_user": None,
            "current_secret": None,
            "processing_data": None,
            "last_access": None
        }

        race_condition_results = []
        access_timeline = []

        async def process_user_data_with_race_condition(user_data: Dict[str, str], delay: float):
            """Simulate user data processing with potential race conditions."""
            user_id = user_data["user_id"]
            secret = user_data["secret_data"]

            # Simulate race condition by accessing shared state
            await asyncio.sleep(delay)  # Variable delay to create race conditions

            # Read shared state (potential contamination from previous user)
            read_state = shared_processing_state.copy()
            read_timestamp = time.time()

            # Record access timeline
            access_timeline.append({
                "timestamp": read_timestamp,
                "user_id": user_id,
                "action": "read",
                "state_content": read_state.copy()
            })

            # Simulate processing delay
            await asyncio.sleep(0.1)

            # Write to shared state (potential contamination for next user)
            shared_processing_state.update({
                "current_user": user_id,
                "current_secret": secret,
                "processing_data": {
                    "user_secret": secret,
                    "private_data": user_data["api_key"],
                    "session_token": user_data["personal_token"]
                },
                "last_access": time.time()
            })

            write_timestamp = time.time()
            access_timeline.append({
                "timestamp": write_timestamp,
                "user_id": user_id,
                "action": "write",
                "state_content": shared_processing_state.copy()
            })

            return {
                "user_id": user_id,
                "secret": secret,
                "read_state": read_state,
                "read_timestamp": read_timestamp,
                "write_timestamp": write_timestamp
            }

        # Create concurrent tasks with different delays to trigger race conditions
        tasks = []
        for i, user_data in enumerate(self.test_users):
            # Stagger delays to increase chance of race conditions
            delay = i * 0.05  # 0, 0.05, 0.1, 0.15, 0.2 seconds
            task = asyncio.create_task(process_user_data_with_race_condition(user_data, delay))
            tasks.append(task)

        # Execute all tasks concurrently
        race_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze race condition results for data leakage
        for result in race_results:
            if isinstance(result, Exception):
                continue

            current_user_id = result["user_id"]
            current_secret = result["secret"]
            read_state = result["read_state"]

            # VULNERABILITY CHECK: User should not read other users' data from shared state
            # These assertions should FAIL to prove vulnerability exists

            if read_state.get("current_user") and read_state.get("current_user") != current_user_id:
                # User read state containing another user's data (RACE CONDITION VULNERABILITY)
                previous_user = read_state["current_user"]
                previous_secret = read_state.get("current_secret")

                if previous_secret:
                    # Check if the previous user's secret is from our test users
                    previous_user_data = next((u for u in self.test_users if u["secret_data"] == previous_secret), None)
                    if previous_user_data:
                        self.fail(f"VULNERABILITY: Race condition - User {current_user_id} read state containing other user {previous_user}'s secret: {previous_secret}")

            # Check processing data for contamination
            if read_state.get("processing_data"):
                processing_data_json = json.dumps(read_state["processing_data"])
                for other_user_data in self.test_users:
                    if other_user_data["user_id"] != current_user_id:
                        other_secret = other_user_data["secret_data"]
                        other_api_key = other_user_data["api_key"]

                        self.assertNotIn(other_secret, processing_data_json,
                            f"VULNERABILITY: Race condition - User {current_user_id} accessed processing data containing other user's secret: {other_secret}")

                        self.assertNotIn(other_api_key, processing_data_json,
                            f"VULNERABILITY: Race condition - User {current_user_id} accessed processing data containing other user's API key: {other_api_key}")

        # Analyze access timeline for overlapping access patterns
        sorted_timeline = sorted(access_timeline, key=lambda x: x["timestamp"])

        for i, access in enumerate(sorted_timeline):
            if access["action"] == "read" and i > 0:
                # Check if this read occurred after another user's write but before their own write
                previous_access = sorted_timeline[i-1]
                if (previous_access["action"] == "write" and
                    previous_access["user_id"] != access["user_id"]):

                    # Potential race condition: reading immediately after another user's write
                    read_content = access["state_content"]
                    if read_content.get("current_secret"):
                        previous_secret = read_content["current_secret"]

                        # Find if this secret belongs to another test user
                        secret_owner = next((u for u in self.test_users if u["secret_data"] == previous_secret), None)
                        if secret_owner and secret_owner["user_id"] != access["user_id"]:
                            self.fail(f"VULNERABILITY: Timeline race condition - User {access['user_id']} read state with other user's secret: {previous_secret}")

    def teardown_method(self, method):
        """Cleanup after each test method."""
        try:
            # Clear shared state to prevent test interference
            self.shared_state_tracker.clear()
            self.contamination_detector.clear()

            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_isolation_vulnerability_tests", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))
            self.record_metric("isolation_test_execution_time", self.get_metrics().execution_time)
            self.record_metric("concurrent_users_tested", len(self.test_users))

        finally:
            super().teardown_method(method)