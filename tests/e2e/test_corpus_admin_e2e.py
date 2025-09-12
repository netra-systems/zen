"""
Comprehensive E2E Tests for CorpusAdminSubAgent Workflow

PRODUCTION CRITICAL: Complete end-to-end validation of corpus administration workflows.
Tests real user journeys from API request to final response with real services.

Business Value Justification (BVJ):
1. Segment: Enterprise, Mid-tier ($500K+ MRR protection)
2. Business Goal: Zero-downtime corpus operations, enterprise reliability
3. Value Impact: Validates corpus management claims for enterprise clients
4. Revenue Impact: Prevents $500K+ MRR loss from corpus operation failures

CRITICAL E2E COVERAGE:
- Complete user journeys: API  ->  Triage  ->  Supervisor  ->  CorpusAdmin  ->  Database  ->  Response
- Real-time WebSocket communication throughout workflow
- Multi-agent collaboration and orchestration
- Production-like data volumes and scenarios
- Error recovery and graceful degradation
- Performance benchmarks under load

ARCHITECTURAL COMPLIANCE:
- Real services: PostgreSQL, WebSocket, Redis, LLM (when --real-llm)
- Environment-aware testing with markers
- Absolute imports only
- Performance targets: <5 seconds end-to-end response
- Thread safety and concurrent operations
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio
import httpx
from fastapi import WebSocket
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Test framework imports
from test_framework.test_utils import create_test_user
from test_framework.http_client import TestClient as HTTPTestClient

# System imports
from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.agents.corpus_admin.models import (
    CorpusMetadata,
    CorpusOperation,
    CorpusOperationRequest,
    CorpusOperationResult,
    CorpusType,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.schemas.user_plan import PlanTier

# E2E test helpers
from tests.e2e.helpers.auth.auth_service_helpers import AuthServiceHelper
from tests.e2e.helpers.core.unified_flow_helpers import UnifiedFlowHelper
from tests.e2e.helpers.websocket.websocket_test_helpers import WebSocketTestManager
from tests.e2e.real_services_manager import RealServicesManager
from tests.e2e.agent_conversation_helpers import (
    AgentConversationTestCore,
    ConversationFlowValidator,
    RealTimeUpdateValidator,
)


@pytest.mark.e2e
@pytest.mark.corpus_admin
class TestCorpusAdminE2E:
    """Comprehensive E2E tests for CorpusAdminSubAgent workflow."""

    @pytest_asyncio.fixture
    async def real_services(self):
        """Initialize real services for E2E testing."""
        manager = RealServicesManager()
        await manager.start_services()
        yield manager
        await manager.stop_services()

    @pytest_asyncio.fixture
    async def test_environment(self, real_services):
        """Setup complete test environment with real services."""
        env = IsolatedEnvironment()
        
        # Configure for E2E testing with real services
        env.override("DATABASE_URL", await real_services.get_postgres_url())
        env.override("REDIS_URL", await real_services.get_redis_url())
        env.override("WEBSOCKET_ENABLED", "true")
        env.override("CORS_ENABLED", "true")
        
        yield env
        
    @pytest_asyncio.fixture
    async def test_core(self, test_environment):
        """Initialize test core with E2E configuration."""
        core = AgentConversationTestCore(use_real_services=True)
        await core.setup_test_environment()
        yield core
        await core.teardown_test_environment()

    @pytest_asyncio.fixture
    async def authenticated_session(self, test_core):
        """Create authenticated user session."""
        session_data = await test_core.establish_conversation_session(PlanTier.ENTERPRISE)
        yield session_data
        await session_data["client"].close()

    @pytest_asyncio.fixture
    async def websocket_helper(self, test_environment):
        """WebSocket test helper for real-time communication testing."""
        helper = WebSocketTestHelper()
        await helper.setup()
        yield helper
        await helper.teardown()

    # ==================== COMPLETE USER JOURNEY TESTS ====================

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_corpus_creation_journey(
        self, 
        authenticated_session, 
        websocket_helper
    ):
        """Test complete corpus creation journey from API to database.
        
        E2E Flow: API Request  ->  Authentication  ->  Triage  ->  Supervisor  ->  
                 CorpusAdmin  ->  Database  ->  WebSocket Updates  ->  Final Response
        """
        start_time = time.time()
        
        # 1. Establish WebSocket connection for real-time updates
        ws_client = await websocket_helper.connect_authenticated(
            authenticated_session["user_data"].id
        )
        
        # 2. Send corpus creation request via API
        corpus_request = {
            "name": "Enterprise Knowledge Base",
            "type": "knowledge_base", 
            "description": "Critical enterprise documentation corpus",
            "source_documents": ["doc1.pdf", "doc2.md", "doc3.txt"],
            "access_level": "enterprise",
            "auto_index": True
        }
        
        response_future = self._send_corpus_creation_request(
            authenticated_session, corpus_request
        )
        
        # 3. Monitor WebSocket updates throughout workflow
        websocket_updates = []
        update_task = asyncio.create_task(
            self._monitor_websocket_updates(ws_client, websocket_updates, 30)
        )
        
        try:
            # 4. Wait for API response
            api_response = await asyncio.wait_for(response_future, timeout=30)
            
            # 5. Validate API response structure
            self._validate_corpus_creation_response(api_response)
            
            # 6. Wait for workflow completion via WebSocket
            await asyncio.wait_for(update_task, timeout=30)
            
            # 7. Validate complete WebSocket flow
            self._validate_complete_websocket_flow(websocket_updates)
            
            # 8. Verify database persistence
            await self._verify_corpus_database_persistence(
                authenticated_session, api_response["corpus_id"]
            )
            
            # 9. Performance validation
            total_time = time.time() - start_time
            assert total_time < 5.0, f"E2E workflow too slow: {total_time:.2f}s"
            
        finally:
            if not update_task.done():
                update_task.cancel()
            await ws_client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_agent_collaboration_flow(
        self, 
        authenticated_session, 
        websocket_helper
    ):
        """Test complete multi-agent collaboration: Triage  ->  Supervisor  ->  CorpusAdmin.
        
        Validates agent handoff, context preservation, and workflow orchestration.
        """
        # 1. Setup WebSocket monitoring
        ws_client = await websocket_helper.connect_authenticated(
            authenticated_session["user_data"].id
        )
        
        agent_events = []
        monitoring_task = asyncio.create_task(
            self._monitor_agent_collaboration(ws_client, agent_events, 45)
        )
        
        try:
            # 2. Send natural language corpus request
            user_message = (
                "I need to create a comprehensive knowledge base for our "
                "customer support team with all our documentation, FAQs, "
                "and troubleshooting guides. Make it searchable and "
                "categorize everything properly."
            )
            
            # 3. Send request that triggers multi-agent workflow  
            response = await self._send_natural_language_request(
                authenticated_session, user_message
            )
            
            # 4. Wait for complete workflow
            await asyncio.wait_for(monitoring_task, timeout=45)
            
            # 5. Validate agent collaboration sequence
            self._validate_agent_collaboration_sequence(agent_events, [
                "triage_started",
                "triage_completed", 
                "supervisor_started",
                "corpus_admin_delegated",
                "corpus_admin_started",
                "corpus_creation_started",
                "corpus_indexing_started",
                "corpus_admin_completed",
                "supervisor_completed",
                "workflow_completed"
            ])
            
            # 6. Validate context preservation across agents
            self._validate_context_preservation(agent_events)
            
            # 7. Verify final corpus creation
            corpus_id = self._extract_corpus_id_from_events(agent_events)
            await self._verify_corpus_functionality(authenticated_session, corpus_id)
            
        finally:
            if not monitoring_task.done():
                monitoring_task.cancel()
            await ws_client.close()

    @pytest.mark.asyncio 
    @pytest.mark.e2e
    async def test_corpus_search_and_retrieve_flow(
        self, 
        authenticated_session,
        websocket_helper
    ):
        """Test complete search and retrieval flow with real corpus data."""
        # 1. Pre-populate corpus with test data
        corpus_id = await self._create_test_corpus_with_data(authenticated_session)
        
        # 2. Setup WebSocket monitoring
        ws_client = await websocket_helper.connect_authenticated(
            authenticated_session["user_data"].id
        )
        
        search_events = []
        monitoring_task = asyncio.create_task(
            self._monitor_search_flow(ws_client, search_events, 30)
        )
        
        try:
            # 3. Send natural language search query
            search_query = (
                "Find all documentation about API authentication and "
                "authorization workflows, especially OAuth integration"
            )
            
            # 4. Execute search request
            search_response = await self._send_corpus_search_request(
                authenticated_session, corpus_id, search_query
            )
            
            # 5. Wait for search completion
            await asyncio.wait_for(monitoring_task, timeout=30)
            
            # 6. Validate search results quality
            self._validate_search_results_quality(
                search_response, search_query, min_relevance=0.8
            )
            
            # 7. Validate search performance
            search_time = self._extract_search_time_from_events(search_events)
            assert search_time < 2.0, f"Search too slow: {search_time:.2f}s"
            
            # 8. Test result ranking and formatting
            self._validate_search_result_formatting(search_response)
            
        finally:
            if not monitoring_task.done():
                monitoring_task.cancel()
            await ws_client.close()

    # ==================== BULK OPERATIONS & PERFORMANCE TESTS ====================

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance
    async def test_bulk_corpus_operations(
        self, 
        authenticated_session,
        websocket_helper
    ):
        """Test bulk operations with production-like data volumes."""
        # 1. Setup bulk operation monitoring
        ws_client = await websocket_helper.connect_authenticated(
            authenticated_session["user_data"].id
        )
        
        bulk_events = []
        monitoring_task = asyncio.create_task(
            self._monitor_bulk_operations(ws_client, bulk_events, 120)
        )
        
        try:
            # 2. Create multiple corpora concurrently
            corpus_requests = [
                self._generate_corpus_request(f"Bulk Corpus {i}", size="large")
                for i in range(5)
            ]
            
            start_time = time.time()
            
            # 3. Execute bulk creation
            creation_tasks = [
                self._send_corpus_creation_request(authenticated_session, req)
                for req in corpus_requests
            ]
            
            corpus_responses = await asyncio.gather(*creation_tasks)
            
            # 4. Validate all creations succeeded
            for response in corpus_responses:
                self._validate_corpus_creation_response(response)
            
            # 5. Execute bulk search operations
            corpus_ids = [resp["corpus_id"] for resp in corpus_responses]
            search_tasks = [
                self._send_corpus_search_request(
                    authenticated_session, corpus_id, f"test query {i}"
                )
                for i, corpus_id in enumerate(corpus_ids)
            ]
            
            search_responses = await asyncio.gather(*search_tasks)
            
            # 6. Wait for all operations to complete
            await asyncio.wait_for(monitoring_task, timeout=120)
            
            # 7. Performance validation
            total_time = time.time() - start_time
            assert total_time < 60.0, f"Bulk operations too slow: {total_time:.2f}s"
            
            # 8. Validate system stability under load
            self._validate_system_stability_metrics(bulk_events)
            
            # 9. Cleanup bulk test data
            await self._cleanup_bulk_test_corpora(authenticated_session, corpus_ids)
            
        finally:
            if not monitoring_task.done():
                monitoring_task.cancel()
            await ws_client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_user_operations(
        self, 
        test_core, 
        websocket_helper
    ):
        """Test concurrent operations from multiple users."""
        # 1. Create multiple user sessions
        sessions = []
        for i in range(3):
            session = await test_core.establish_conversation_session(PlanTier.PRO)
            sessions.append(session)
        
        try:
            # 2. Setup concurrent WebSocket monitoring
            ws_clients = []
            for session in sessions:
                ws_client = await websocket_helper.connect_authenticated(
                    session["user_data"].id
                )
                ws_clients.append(ws_client)
            
            concurrent_events = []
            monitoring_tasks = [
                asyncio.create_task(
                    self._monitor_user_operations(
                        ws_client, concurrent_events, session["user_data"].id, 60
                    )
                )
                for ws_client, session in zip(ws_clients, sessions)
            ]
            
            # 3. Execute concurrent corpus operations
            concurrent_tasks = []
            for i, session in enumerate(sessions):
                task = asyncio.create_task(
                    self._execute_user_corpus_workflow(
                        session, f"User {i} Corpus", user_id=i
                    )
                )
                concurrent_tasks.append(task)
            
            # 4. Wait for all concurrent operations
            results = await asyncio.gather(*concurrent_tasks)
            await asyncio.gather(*monitoring_tasks)
            
            # 5. Validate user isolation
            self._validate_user_operation_isolation(concurrent_events, sessions)
            
            # 6. Validate all operations succeeded
            for result in results:
                assert result["success"], f"User operation failed: {result}"
            
        finally:
            # Cleanup
            for ws_client in ws_clients:
                await ws_client.close()
            for session in sessions:
                await session["client"].close()

    # ==================== APPROVAL WORKFLOW & ERROR RECOVERY TESTS ====================

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_high_risk_operation_approval_flow(
        self, 
        authenticated_session,
        websocket_helper
    ):
        """Test approval workflow for high-risk operations."""
        ws_client = await websocket_helper.connect_authenticated(
            authenticated_session["user_data"].id
        )
        
        approval_events = []
        monitoring_task = asyncio.create_task(
            self._monitor_approval_workflow(ws_client, approval_events, 60)
        )
        
        try:
            # 1. Send high-risk operation (bulk delete)
            risk_operation = {
                "operation": "bulk_delete",
                "target": "all_user_corpora",
                "confirmation_required": True,
                "risk_level": "high"
            }
            
            # 2. Initiate high-risk operation
            response = await self._send_high_risk_operation(
                authenticated_session, risk_operation
            )
            
            # 3. Verify approval request was generated
            assert response["status"] == "approval_required"
            approval_token = response["approval_token"]
            
            # 4. Wait for approval prompt via WebSocket
            await self._wait_for_approval_prompt(ws_client, approval_token, timeout=10)
            
            # 5. Send user approval
            approval_response = await self._send_user_approval(
                authenticated_session, approval_token, approved=True
            )
            
            # 6. Wait for operation completion
            await asyncio.wait_for(monitoring_task, timeout=60)
            
            # 7. Validate approval workflow events
            self._validate_approval_workflow_events(approval_events, [
                "approval_required",
                "approval_prompt_sent", 
                "user_approval_received",
                "operation_authorized",
                "operation_completed"
            ])
            
            # 8. Verify operation was executed after approval
            assert approval_response["operation_executed"], "Operation not executed after approval"
            
        finally:
            if not monitoring_task.done():
                monitoring_task.cancel()
            await ws_client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_recovery_and_graceful_degradation(
        self, 
        authenticated_session,
        websocket_helper
    ):
        """Test error recovery scenarios and graceful degradation."""
        ws_client = await websocket_helper.connect_authenticated(
            authenticated_session["user_data"].id
        )
        
        error_events = []
        monitoring_task = asyncio.create_task(
            self._monitor_error_recovery(ws_client, error_events, 90)
        )
        
        try:
            # 1. Test database connection failure scenario
            with patch('netra_backend.app.db.database_manager.DatabaseManager') as mock_db:
                mock_db.get_connection.side_effect = Exception("Database connection failed")
                
                # 2. Send corpus operation during DB failure
                response = await self._send_corpus_creation_request(
                    authenticated_session, 
                    {"name": "Test Corpus", "type": "knowledge_base"}
                )
                
                # 3. Verify graceful error handling
                assert response["status"] == "error"
                assert "database connection" in response["error_message"].lower()
                assert response["retry_available"], "Retry not offered for recoverable error"
            
            # 4. Test network failure recovery
            await self._test_network_failure_recovery(
                authenticated_session, ws_client
            )
            
            # 5. Test partial operation failure recovery
            await self._test_partial_operation_recovery(
                authenticated_session, ws_client
            )
            
            # 6. Wait for all error scenarios to complete
            await asyncio.wait_for(monitoring_task, timeout=90)
            
            # 7. Validate error recovery patterns
            self._validate_error_recovery_patterns(error_events)
            
            # 8. Ensure system returned to healthy state
            health_check = await self._perform_system_health_check(authenticated_session)
            assert health_check["status"] == "healthy", "System not recovered after errors"
            
        finally:
            if not monitoring_task.done():
                monitoring_task.cancel()
            await ws_client.close()

    # ==================== PERFORMANCE BENCHMARK TESTS ====================

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance
    async def test_performance_benchmarks(
        self,
        authenticated_session,
        websocket_helper
    ):
        """Establish performance benchmarks for corpus operations."""
        benchmarks = {
            "corpus_creation": {"target": 3.0, "results": []},
            "corpus_search": {"target": 1.0, "results": []},
            "bulk_operations": {"target": 10.0, "results": []},
            "websocket_latency": {"target": 0.1, "results": []}
        }
        
        # 1. Benchmark corpus creation performance
        for i in range(5):
            start_time = time.time()
            
            response = await self._send_corpus_creation_request(
                authenticated_session,
                self._generate_corpus_request(f"Benchmark Corpus {i}")
            )
            
            creation_time = time.time() - start_time
            benchmarks["corpus_creation"]["results"].append(creation_time)
            
            # Cleanup for next iteration
            await self._cleanup_test_corpus(authenticated_session, response["corpus_id"])
        
        # 2. Benchmark search performance
        test_corpus_id = await self._create_test_corpus_with_data(authenticated_session)
        
        for i in range(10):
            start_time = time.time()
            
            await self._send_corpus_search_request(
                authenticated_session, 
                test_corpus_id, 
                f"benchmark search query {i}"
            )
            
            search_time = time.time() - start_time
            benchmarks["corpus_search"]["results"].append(search_time)
        
        # 3. Benchmark WebSocket latency
        ws_client = await websocket_helper.connect_authenticated(
            authenticated_session["user_data"].id
        )
        
        try:
            for i in range(10):
                start_time = time.time()
                
                # Send message and measure round-trip time
                await ws_client.send_json({"type": "ping", "timestamp": start_time})
                response = await ws_client.receive_json()
                
                latency = time.time() - start_time
                benchmarks["websocket_latency"]["results"].append(latency)
        
        finally:
            await ws_client.close()
        
        # 4. Validate all benchmarks
        self._validate_performance_benchmarks(benchmarks)
        
        # 5. Generate performance report
        performance_report = self._generate_performance_report(benchmarks)
        
        # Store results for CI/CD tracking
        await self._store_performance_results(performance_report)

    # ==================== HELPER METHODS ====================

    async def _send_corpus_creation_request(
        self, 
        session: Dict[str, Any], 
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send corpus creation request via HTTP API."""
        client = session["client"]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        response = await client.post(
            "/api/corpus",
            json=request,
            headers=headers
        )
        
        assert response.status_code == 200, f"API request failed: {response.text}"
        return response.json()

    async def _send_natural_language_request(
        self, 
        session: Dict[str, Any], 
        message: str
    ) -> Dict[str, Any]:
        """Send natural language request that triggers agent workflow."""
        client = session["client"]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        response = await client.post(
            "/api/chat/message",
            json={
                "message": message,
                "thread_id": session["thread_id"],
                "stream": False
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Chat request failed: {response.text}"
        return response.json()

    async def _send_corpus_search_request(
        self, 
        session: Dict[str, Any], 
        corpus_id: str, 
        query: str
    ) -> Dict[str, Any]:
        """Send corpus search request."""
        client = session["client"] 
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        response = await client.post(
            f"/api/corpus/{corpus_id}/search",
            json={"query": query, "limit": 20},
            headers=headers
        )
        
        assert response.status_code == 200, f"Search request failed: {response.text}"
        return response.json()

    async def _monitor_websocket_updates(
        self, 
        ws_client, 
        updates: List[Dict[str, Any]], 
        timeout: int
    ):
        """Monitor WebSocket updates for specified duration."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    ws_client.receive_json(), timeout=1.0
                )
                updates.append({
                    "timestamp": time.time(),
                    "message": message
                })
                
                # Check for completion signal
                if message.get("type") == "workflow_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue

    async def _monitor_agent_collaboration(
        self, 
        ws_client,
        events: List[Dict[str, Any]], 
        timeout: int
    ):
        """Monitor multi-agent collaboration events."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    ws_client.receive_json(), timeout=1.0
                )
                
                if message.get("type") in [
                    "agent_started", "agent_completed", "agent_delegated",
                    "triage_started", "triage_completed",
                    "supervisor_started", "supervisor_completed", 
                    "corpus_admin_started", "corpus_admin_completed"
                ]:
                    events.append({
                        "timestamp": time.time(),
                        "event": message.get("type"),
                        "agent": message.get("agent"),
                        "data": message.get("data", {})
                    })
                
                if message.get("type") == "workflow_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue

    def _validate_corpus_creation_response(self, response: Dict[str, Any]):
        """Validate corpus creation API response structure."""
        required_fields = ["corpus_id", "status", "name", "type"]
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"
        
        assert response["status"] in ["created", "processing"], f"Invalid status: {response['status']}"
        assert len(response["corpus_id"]) > 0, "Empty corpus_id"

    def _validate_complete_websocket_flow(self, updates: List[Dict[str, Any]]):
        """Validate complete WebSocket update flow."""
        expected_sequence = [
            "workflow_started",
            "triage_started",
            "triage_completed", 
            "supervisor_started",
            "corpus_admin_started",
            "corpus_creation_started",
            "corpus_creation_completed",
            "corpus_admin_completed",
            "supervisor_completed", 
            "workflow_completed"
        ]
        
        received_events = [update["message"].get("type") for update in updates]
        
        for expected_event in expected_sequence:
            assert expected_event in received_events, f"Missing event: {expected_event}"

    def _validate_agent_collaboration_sequence(
        self, 
        events: List[Dict[str, Any]], 
        expected_sequence: List[str]
    ):
        """Validate agent collaboration event sequence."""
        event_types = [event["event"] for event in events]
        
        for expected_event in expected_sequence:
            assert expected_event in event_types, f"Missing collaboration event: {expected_event}"
        
        # Validate ordering of critical events
        triage_start = next(i for i, e in enumerate(event_types) if e == "triage_started")
        triage_end = next(i for i, e in enumerate(event_types) if e == "triage_completed")
        supervisor_start = next(i for i, e in enumerate(event_types) if e == "supervisor_started")
        
        assert triage_start < triage_end < supervisor_start, "Invalid agent handoff sequence"

    def _validate_context_preservation(self, events: List[Dict[str, Any]]):
        """Validate context preservation across agent transitions."""
        user_context_fields = ["user_id", "thread_id", "user_request"]
        
        for event in events:
            if event.get("data"):
                for field in user_context_fields:
                    if field in event["data"]:
                        assert event["data"][field], f"Empty context field: {field}"

    async def _verify_corpus_database_persistence(
        self, 
        session: Dict[str, Any], 
        corpus_id: str
    ):
        """Verify corpus was persisted correctly in database."""
        client = session["client"]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        # Check corpus exists in database
        response = await client.get(f"/api/corpus/{corpus_id}", headers=headers)
        assert response.status_code == 200, "Corpus not found in database"
        
        corpus_data = response.json()
        assert corpus_data["id"] == corpus_id
        assert corpus_data["status"] in ["active", "processing"]

    async def _create_test_corpus_with_data(self, session: Dict[str, Any]) -> str:
        """Create a test corpus with sample data for search testing."""
        corpus_request = {
            "name": "Test Search Corpus",
            "type": "knowledge_base",
            "documents": [
                {
                    "title": "API Authentication Guide",
                    "content": "OAuth 2.0 implementation details for secure authentication workflows"
                },
                {
                    "title": "Authorization Best Practices", 
                    "content": "Role-based access control and permission management strategies"
                },
                {
                    "title": "Integration Documentation",
                    "content": "Third-party service integration patterns and OAuth implementation"
                }
            ]
        }
        
        response = await self._send_corpus_creation_request(session, corpus_request)
        return response["corpus_id"]

    def _validate_search_results_quality(
        self, 
        response: Dict[str, Any], 
        query: str, 
        min_relevance: float
    ):
        """Validate search results quality and relevance."""
        assert "results" in response, "No search results returned"
        assert len(response["results"]) > 0, "Empty search results"
        
        for result in response["results"]:
            assert "title" in result and "content" in result, "Invalid result structure"
            assert result.get("relevance_score", 0) >= min_relevance, f"Low relevance: {result.get('relevance_score')}"

    def _validate_search_result_formatting(self, response: Dict[str, Any]):
        """Validate search result formatting and structure."""
        required_fields = ["results", "total_count", "query_time"]
        for field in required_fields:
            assert field in response, f"Missing response field: {field}"
        
        for result in response["results"]:
            result_fields = ["id", "title", "content", "relevance_score", "metadata"]
            for field in result_fields:
                assert field in result, f"Missing result field: {field}"

    def _validate_performance_benchmarks(self, benchmarks: Dict[str, Dict[str, Any]]):
        """Validate all performance benchmarks meet targets."""
        for operation, data in benchmarks.items():
            target = data["target"]
            results = data["results"]
            avg_time = sum(results) / len(results)
            
            assert avg_time <= target, f"{operation} benchmark failed: {avg_time:.3f}s > {target}s"
            
            # Validate consistency (90th percentile within 2x of target)
            sorted_results = sorted(results)
            p90 = sorted_results[int(0.9 * len(sorted_results))]
            assert p90 <= target * 2, f"{operation} P90 inconsistent: {p90:.3f}s > {target * 2}s"

    def _generate_performance_report(self, benchmarks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "benchmarks": {},
            "summary": {
                "total_tests": sum(len(data["results"]) for data in benchmarks.values()),
                "passed_benchmarks": 0,
                "failed_benchmarks": 0
            }
        }
        
        for operation, data in benchmarks.items():
            results = data["results"]
            avg_time = sum(results) / len(results)
            
            report["benchmarks"][operation] = {
                "target": data["target"],
                "average": round(avg_time, 3),
                "min": round(min(results), 3),
                "max": round(max(results), 3),
                "p95": round(sorted(results)[int(0.95 * len(results))], 3),
                "passed": avg_time <= data["target"]
            }
            
            if report["benchmarks"][operation]["passed"]:
                report["summary"]["passed_benchmarks"] += 1
            else:
                report["summary"]["failed_benchmarks"] += 1
        
        return report

    def _generate_corpus_request(self, name: str, size: str = "medium") -> Dict[str, Any]:
        """Generate corpus request based on size requirements."""
        base_request = {
            "name": name,
            "type": "knowledge_base", 
            "description": f"Test corpus - {size} size"
        }
        
        if size == "large":
            base_request["documents"] = [
                {"title": f"Document {i}", "content": "Large content " * 100}
                for i in range(50)
            ]
        elif size == "medium":
            base_request["documents"] = [
                {"title": f"Document {i}", "content": "Medium content " * 20}
                for i in range(10)
            ]
        else:  # small
            base_request["documents"] = [
                {"title": f"Document {i}", "content": "Small content " * 5}
                for i in range(3)
            ]
        
        return base_request

    async def _cleanup_test_corpus(self, session: Dict[str, Any], corpus_id: str):
        """Cleanup test corpus after benchmarking."""
        client = session["client"]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        await client.delete(f"/api/corpus/{corpus_id}", headers=headers)

    async def _store_performance_results(self, report: Dict[str, Any]):
        """Store performance results for CI/CD tracking."""
        # Store in test artifacts directory if available
        from shared.isolated_environment import get_env
        env = get_env()
        results_dir = env.get("TEST_RESULTS_DIR", "/tmp")
        if results_dir:
            timestamp = report["timestamp"].replace(":", "-")
            filename = f"{results_dir}/corpus_admin_e2e_performance_{timestamp}.json"
            
            with open(filename, "w") as f:
                json.dump(report, f, indent=2)

    async def _monitor_search_flow(
        self, 
        ws_client, 
        events: List[Dict[str, Any]], 
        timeout: int
    ):
        """Monitor search operation WebSocket events."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    ws_client.receive_json(), timeout=1.0
                )
                
                if message.get("type") in [
                    "search_started", "search_processing", "search_completed", 
                    "search_results_ready"
                ]:
                    events.append({
                        "timestamp": time.time(),
                        "event": message.get("type"),
                        "data": message.get("data", {})
                    })
                
                if message.get("type") == "search_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue

    async def _monitor_bulk_operations(
        self, 
        ws_client, 
        events: List[Dict[str, Any]], 
        timeout: int
    ):
        """Monitor bulk operation events."""
        end_time = time.time() + timeout
        completed_operations = 0
        
        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    ws_client.receive_json(), timeout=1.0
                )
                
                if message.get("type") in [
                    "bulk_operation_started", "bulk_progress_update", 
                    "bulk_operation_completed", "operation_completed"
                ]:
                    events.append({
                        "timestamp": time.time(),
                        "event": message.get("type"),
                        "data": message.get("data", {})
                    })
                    
                    if message.get("type") == "operation_completed":
                        completed_operations += 1
                        
                    # Exit when all operations complete
                    if completed_operations >= 5:  # Expected bulk operations
                        break
                        
            except asyncio.TimeoutError:
                continue

    async def _monitor_user_operations(
        self, 
        ws_client, 
        events: List[Dict[str, Any]], 
        user_id: str,
        timeout: int
    ):
        """Monitor operations for specific user."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    ws_client.receive_json(), timeout=1.0
                )
                
                # Filter events for this user
                if message.get("user_id") == user_id:
                    events.append({
                        "timestamp": time.time(),
                        "user_id": user_id,
                        "event": message.get("type"),
                        "data": message.get("data", {})
                    })
                
                if message.get("type") == "user_workflow_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue

    async def _monitor_approval_workflow(
        self, 
        ws_client, 
        events: List[Dict[str, Any]], 
        timeout: int
    ):
        """Monitor approval workflow events."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    ws_client.receive_json(), timeout=1.0
                )
                
                if message.get("type") in [
                    "approval_required", "approval_prompt_sent", 
                    "user_approval_received", "operation_authorized", 
                    "operation_completed"
                ]:
                    events.append({
                        "timestamp": time.time(),
                        "event": message.get("type"),
                        "data": message.get("data", {})
                    })
                
                if message.get("type") == "operation_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue

    async def _monitor_error_recovery(
        self, 
        ws_client, 
        events: List[Dict[str, Any]], 
        timeout: int
    ):
        """Monitor error recovery events."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    ws_client.receive_json(), timeout=1.0
                )
                
                if message.get("type") in [
                    "error_occurred", "error_recovery_started", 
                    "retry_attempt", "recovery_completed", "fallback_activated"
                ]:
                    events.append({
                        "timestamp": time.time(),
                        "event": message.get("type"),
                        "data": message.get("data", {}),
                        "error_details": message.get("error", {})
                    })
                
                if message.get("type") == "recovery_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue

    async def _execute_user_corpus_workflow(
        self, 
        session: Dict[str, Any], 
        corpus_name: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Execute complete corpus workflow for a user."""
        try:
            # 1. Create corpus
            corpus_request = self._generate_corpus_request(corpus_name)
            response = await self._send_corpus_creation_request(session, corpus_request)
            
            # 2. Perform search operation
            corpus_id = response["corpus_id"]
            await asyncio.sleep(2)  # Allow indexing to complete
            
            search_response = await self._send_corpus_search_request(
                session, corpus_id, f"test search for user {user_id}"
            )
            
            # 3. Cleanup
            await self._cleanup_test_corpus(session, corpus_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "corpus_id": corpus_id,
                "operations_completed": 3
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }

    async def _send_high_risk_operation(
        self, 
        session: Dict[str, Any], 
        operation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send high-risk operation request."""
        client = session["client"]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        response = await client.post(
            "/api/corpus/admin/high-risk-operation",
            json=operation,
            headers=headers
        )
        
        return response.json()

    async def _send_user_approval(
        self, 
        session: Dict[str, Any], 
        approval_token: str,
        approved: bool
    ) -> Dict[str, Any]:
        """Send user approval decision."""
        client = session["client"]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        response = await client.post(
            f"/api/corpus/admin/approval/{approval_token}",
            json={"approved": approved},
            headers=headers
        )
        
        return response.json()

    async def _wait_for_approval_prompt(
        self, 
        ws_client, 
        approval_token: str, 
        timeout: int
    ):
        """Wait for approval prompt via WebSocket."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    ws_client.receive_json(), timeout=1.0
                )
                
                if (message.get("type") == "approval_prompt_sent" and 
                    message.get("approval_token") == approval_token):
                    return True
                    
            except asyncio.TimeoutError:
                continue
        
        raise TimeoutError("Approval prompt not received within timeout")

    async def _test_network_failure_recovery(
        self, 
        session: Dict[str, Any], 
        ws_client
    ):
        """Test network failure recovery scenario."""
        # Simulate network interruption by closing and reopening WebSocket
        await ws_client.close()
        
        # Send request during disconnection
        response = await self._send_corpus_creation_request(
            session, 
            {"name": "Network Test Corpus", "type": "knowledge_base"}
        )
        
        # Reconnect and verify operation completed
        # Mock websocket client for now
        ws_client = AsyncNone  # TODO: Use real service instead of Mock
        
        # Verify corpus was created despite network interruption
        corpus_id = response["corpus_id"]
        await self._verify_corpus_database_persistence(session, corpus_id)
        await self._cleanup_test_corpus(session, corpus_id)

    async def _test_partial_operation_recovery(
        self, 
        session: Dict[str, Any], 
        ws_client
    ):
        """Test partial operation failure recovery."""
        # Create corpus with intentionally problematic document
        problematic_request = {
            "name": "Partial Failure Test", 
            "type": "knowledge_base",
            "documents": [
                {"title": "Good Document", "content": "Valid content"},
                {"title": "Bad Document", "content": ""},  # Empty content should cause issues
                {"title": "Another Good Document", "content": "More valid content"}
            ]
        }
        
        response = await self._send_corpus_creation_request(session, problematic_request)
        
        # Verify partial success handling
        assert response["status"] in ["partial_success", "completed_with_warnings"]
        if "warnings" in response:
            assert len(response["warnings"]) > 0

    async def _perform_system_health_check(
        self, 
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform system health check."""
        client = session["client"]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        response = await client.get("/api/health", headers=headers)
        return response.json()

    def _extract_corpus_id_from_events(self, events: List[Dict[str, Any]]) -> str:
        """Extract corpus ID from agent collaboration events."""
        for event in events:
            if event.get("data", {}).get("corpus_id"):
                return event["data"]["corpus_id"]
        
        raise ValueError("Corpus ID not found in agent events")

    def _extract_search_time_from_events(self, events: List[Dict[str, Any]]) -> float:
        """Extract search time from search events."""
        start_time = None
        end_time = None
        
        for event in events:
            if event["event"] == "search_started":
                start_time = event["timestamp"]
            elif event["event"] == "search_completed":
                end_time = event["timestamp"]
        
        if start_time and end_time:
            return end_time - start_time
        
        raise ValueError("Search timing not found in events")

    async def _verify_corpus_functionality(
        self, 
        session: Dict[str, Any], 
        corpus_id: str
    ):
        """Verify corpus is functional after creation."""
        # Test basic operations
        await self._verify_corpus_database_persistence(session, corpus_id)
        
        # Test search functionality
        search_response = await self._send_corpus_search_request(
            session, corpus_id, "test functionality search"
        )
        assert "results" in search_response

    def _validate_user_operation_isolation(
        self, 
        events: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]]
    ):
        """Validate that user operations are properly isolated."""
        user_events_by_user = {}
        
        for event in events:
            user_id = event.get("user_id")
            if user_id:
                if user_id not in user_events_by_user:
                    user_events_by_user[user_id] = []
                user_events_by_user[user_id].append(event)
        
        # Verify each user had independent operations
        for user_id, user_events in user_events_by_user.items():
            assert len(user_events) > 0, f"No events for user {user_id}"
            
            # Verify user events don't contain other users' data
            for event in user_events:
                event_user_id = event.get("user_id")
                assert event_user_id == user_id, "User data leaked between sessions"

    def _validate_approval_workflow_events(
        self, 
        events: List[Dict[str, Any]], 
        expected_sequence: List[str]
    ):
        """Validate approval workflow event sequence."""
        event_types = [event["event"] for event in events]
        
        for expected_event in expected_sequence:
            assert expected_event in event_types, f"Missing approval event: {expected_event}"
        
        # Validate approval workflow timing
        approval_required_time = None
        user_approval_time = None
        
        for event in events:
            if event["event"] == "approval_required":
                approval_required_time = event["timestamp"]
            elif event["event"] == "user_approval_received":
                user_approval_time = event["timestamp"]
        
        if approval_required_time and user_approval_time:
            approval_delay = user_approval_time - approval_required_time
            assert approval_delay < 30.0, f"Approval took too long: {approval_delay:.2f}s"

    def _validate_error_recovery_patterns(self, events: List[Dict[str, Any]]):
        """Validate error recovery patterns are followed."""
        error_events = [e for e in events if "error" in e["event"]]
        recovery_events = [e for e in events if "recovery" in e["event"]]
        
        assert len(error_events) > 0, "No error events recorded"
        assert len(recovery_events) > 0, "No recovery events recorded"
        
        # Validate that each error had a corresponding recovery attempt
        for error_event in error_events:
            error_time = error_event["timestamp"]
            
            # Find recovery events after this error
            later_recoveries = [
                r for r in recovery_events 
                if r["timestamp"] > error_time
            ]
            
            assert len(later_recoveries) > 0, f"No recovery after error: {error_event}"

    def _validate_system_stability_metrics(self, events: List[Dict[str, Any]]):
        """Validate system stability metrics under load."""
        error_events = [e for e in events if "error" in e.get("event", "")]
        total_events = len(events)
        
        if total_events > 0:
            error_rate = len(error_events) / total_events
            assert error_rate < 0.05, f"Error rate too high: {error_rate:.2%}"
        
        # Validate response times
        operation_times = []
        for i in range(len(events) - 1):
            if events[i]["event"].endswith("_started"):
                start_time = events[i]["timestamp"]
                # Find corresponding completion
                for j in range(i + 1, len(events)):
                    if events[j]["event"] == events[i]["event"].replace("_started", "_completed"):
                        completion_time = events[j]["timestamp"] 
                        operation_times.append(completion_time - start_time)
                        break
        
        if operation_times:
            avg_operation_time = sum(operation_times) / len(operation_times)
            assert avg_operation_time < 10.0, f"Average operation time too high: {avg_operation_time:.2f}s"

    async def _cleanup_bulk_test_corpora(
        self, 
        session: Dict[str, Any], 
        corpus_ids: List[str]
    ):
        """Cleanup multiple test corpora."""
        cleanup_tasks = [
            self._cleanup_test_corpus(session, corpus_id)
            for corpus_id in corpus_ids
        ]
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)


@pytest.mark.e2e
@pytest.mark.corpus_admin
@pytest.mark.real_llm 
class TestCorpusAdminRealLLME2E:
    """E2E tests with real LLM integration for corpus admin workflows."""
    
    @pytest.fixture
    def use_real_llm(self):
        """Check if real LLM testing is enabled."""
        from shared.isolated_environment import get_env
        env = get_env()
        return env.get("TEST_USE_REAL_LLM", "false").lower() == "true"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_real_llm_corpus_analysis(
        self, 
        authenticated_session, 
        websocket_helper,
        use_real_llm
    ):
        """Test corpus operations with real LLM analysis."""
        if not use_real_llm:
            pytest.skip("Real LLM testing disabled")
        
        # Implementation would test real LLM integration
        # with actual API calls and response analysis
        pass


# Environment-aware test markers
from shared.isolated_environment import get_env
_test_env = get_env()

pytest.mark.dev = pytest.mark.skipif(
    _test_env.get("TEST_ENVIRONMENT") != "dev",
    reason="Dev environment only"
)

pytest.mark.staging = pytest.mark.skipif(
    _test_env.get("TEST_ENVIRONMENT") != "staging", 
    reason="Staging environment only"
)

pytest.mark.prod_safe = pytest.mark.skipif(
    _test_env.get("TEST_ENVIRONMENT") == "prod" and not _test_env.get("ALLOW_PROD_TESTS"),
    reason="Production environment - explicit flag required"
)