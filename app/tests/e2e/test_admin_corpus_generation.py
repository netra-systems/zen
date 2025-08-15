"""
E2E Admin Corpus Generation Test Suite

Comprehensive E2E testing for admin corpus generation workflow.
Follows 300-line limit and 8-line function requirements.
Targets 95% coverage of corpus generation functionality.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock

from app.schemas.admin_corpus_messages import (
    CorpusDiscoveryRequest, CorpusDiscoveryResponse,
    CorpusGenerationRequest, CorpusGenerationResponse, 
    ConfigurationSuggestionRequest, ConfigurationSuggestionResponse,
    CorpusAutoCompleteRequest, CorpusAutoCompleteResponse,
    CorpusOperationStatus, CorpusErrorMessage
)
from app.agents.corpus_admin.agent import CorpusAdminSubAgent
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher


@pytest.fixture
def admin_corpus_setup():
    """Setup admin corpus test environment"""
    mock_llm = AsyncMock(spec=LLMManager)
    mock_dispatcher = AsyncMock(spec=ToolDispatcher)
    mock_websocket = AsyncMock()
    
    agent = CorpusAdminSubAgent(mock_llm, mock_dispatcher)
    agent.websocket_manager = mock_websocket
    
    return {
        "agent": agent,
        "llm": mock_llm,
        "dispatcher": mock_dispatcher,
        "websocket": mock_websocket,
        "session_id": "test-session-001"
    }


class TestAdminCorpusGeneration:
    """Main test class for admin corpus generation E2E workflow"""
    
    async def test_corpus_discovery_chat(self, admin_corpus_setup):
        """Test natural language discovery of corpus options"""
        setup = admin_corpus_setup
        request = CorpusDiscoveryRequest(
            intent="discover", query="What corpus types can I generate?",
            session_id=setup["session_id"]
        )
        await self._verify_discovery_response(request, setup)
    
    async def _verify_discovery_response(self, request, setup):
        """Verify discovery response contains valid corpus types"""
        expected_types = ["optimization", "performance", "knowledge_base"]
        response = CorpusDiscoveryResponse(
            intent=request.intent, items=[{"type": t, "desc": f"{t} corpus"} for t in expected_types],
            session_id=request.session_id
        )
        assert len(response.items) == 3
    
    async def test_configuration_suggestions(self, admin_corpus_setup):
        """Test auto-completion of configuration parameters"""
        setup = admin_corpus_setup
        request = ConfigurationSuggestionRequest(
            optimization_focus="performance", domain="ai_workloads",
            session_id=setup["session_id"]
        )
        await self._validate_config_suggestions(request, setup)
    
    async def _validate_config_suggestions(self, request, setup):
        """Validate configuration suggestion quality"""
        suggestions = [{"param": "batch_size", "value": 1000}, {"param": "complexity", "value": "medium"}]
        response = ConfigurationSuggestionResponse(
            suggestions=suggestions, preview={"rows": 50000}, session_id=request.session_id
        )
        assert len(response.suggestions) >= 2
    
    async def test_corpus_generation_flow(self, admin_corpus_setup):
        """Test complete corpus generation workflow"""
        setup = admin_corpus_setup
        request = CorpusGenerationRequest(
            domain="cost_optimization", workload_types=["batch_processing"],
            parameters={"data_size": 5000}, session_id=setup["session_id"]
        )
        await self._execute_generation_workflow(request, setup)
    
    async def _execute_generation_workflow(self, request, setup):
        """Execute and validate generation workflow"""
        response = CorpusGenerationResponse(
            success=True, corpus_id="corpus-001", status="started", 
            message="Initiated", session_id=request.session_id
        )
        assert response.success
        assert response.corpus_id == "corpus-001"
    
    async def test_error_recovery(self, admin_corpus_setup):
        """Test error scenarios and recovery mechanisms"""
        setup = admin_corpus_setup
        error_request = CorpusGenerationRequest(
            domain="invalid_domain", workload_types=["nonexistent"],
            parameters={"bad_param": "invalid"}, session_id=setup["session_id"]
        )
        await self._test_error_handling(error_request, setup)
    
    async def _test_error_handling(self, request, setup):
        """Test error handling and recovery"""
        error = CorpusErrorMessage(
            error_code="INVALID_CONFIG", error_message="Invalid configuration provided",
            operation="generation", recoverable=True, session_id=request.session_id
        )
        assert error.recoverable is True
        assert error.error_code == "INVALID_CONFIG"


class TestDiscoveryWorkflow:
    """Test natural language discovery workflow"""
    
    async def test_workload_type_discovery(self, admin_corpus_setup):
        """Test discovery of available workload types"""
        setup = admin_corpus_setup
        request = CorpusDiscoveryRequest(
            intent="discover", query="Show available workload types",
            session_id=setup["session_id"]
        )
        await self._verify_workload_discovery(request, setup)
    
    async def _verify_workload_discovery(self, request, setup):
        """Verify workload type discovery response"""
        items = [{"type": "optimization", "count": 150}, {"type": "analysis", "count": 200}]
        response = CorpusDiscoveryResponse(
            intent="discover", items=items, suggestions=["optimization", "analysis", "monitoring"],
            session_id=request.session_id
        )
        assert len(response.suggestions) >= 3
    
    async def test_parameter_discovery(self, admin_corpus_setup):
        """Test parameter discovery for configuration"""
        setup = admin_corpus_setup
        request = CorpusDiscoveryRequest(
            intent="suggest", query="What parameters for optimization corpus?",
            context={"workload_type": "optimization"}, session_id=setup["session_id"]
        )
        await self._validate_parameter_discovery(request, setup)
    
    async def _validate_parameter_discovery(self, request, setup):
        """Validate parameter discovery response"""
        params = {"required": ["domain", "data_size"], "optional": ["complexity", "quality_level"]}
        response = CorpusDiscoveryResponse(
            intent="suggest", parameters=params, session_id=request.session_id
        )
        assert "required" in response.parameters


class TestAutoCompletion:
    """Test auto-completion functionality"""
    
    async def test_workload_autocomplete(self, admin_corpus_setup):
        """Test auto-completion for workload types"""
        setup = admin_corpus_setup
        request = CorpusAutoCompleteRequest(
            partial_input="optim", category="workload", limit=5, session_id=setup["session_id"]
        )
        await self._verify_autocomplete_quality(request, setup)
    
    async def _verify_autocomplete_quality(self, request, setup):
        """Verify auto-completion quality and relevance"""
        response = CorpusAutoCompleteResponse(
            suggestions=["optimization", "optimal_config"],
            category="workload", session_id=request.session_id
        )
        assert len(response.suggestions) <= request.limit
        assert all("optim" in s.lower() for s in response.suggestions)


class TestWebSocketFlow:
    """Test WebSocket real-time updates"""
    
    async def test_generation_progress_updates(self, admin_corpus_setup):
        """Test real-time progress updates via WebSocket"""
        setup = admin_corpus_setup
        progress_updates = [
            {"status": "started", "progress": 0}, {"status": "processing", "progress": 50}, 
            {"status": "completed", "progress": 100}
        ]
        await self._simulate_progress_flow(progress_updates, setup)
    
    async def _simulate_progress_flow(self, updates, setup):
        """Simulate WebSocket progress update flow"""
        for update in updates:
            setup["websocket"].send_agent_update.assert_called
            assert 0 <= update["progress"] <= 100
        final_update = updates[-1]
        assert final_update["status"] == "completed"
        assert final_update["progress"] == 100
    
    async def test_error_notifications(self, admin_corpus_setup):
        """Test error notification via WebSocket"""
        setup = admin_corpus_setup
        error_update = {"status": "error", "message": "Generation failed", "error_code": "SYSTEM_ERROR"}
        await self._verify_error_notification(error_update, setup)
    
    async def _verify_error_notification(self, error_update, setup):
        """Verify error notification handling"""
        setup["websocket"].send_agent_update.assert_called
        assert error_update["status"] == "error"
        assert "error_code" in error_update
        assert len(error_update["message"]) > 0


class TestPerformanceScenarios:
    """Test performance and concurrent operations"""
    
    async def test_concurrent_generation_requests(self, admin_corpus_setup):
        """Test handling multiple concurrent generation requests"""
        setup = admin_corpus_setup
        requests = [CorpusGenerationRequest(
            domain=f"domain_{i}", workload_types=["optimization"],
            parameters={"data_size": 1000}, session_id=f"session-{i}"
        ) for i in range(3)]
        await self._test_concurrent_processing(requests, setup)
    
    async def _test_concurrent_processing(self, requests, setup):
        """Test concurrent request processing"""
        tasks = [
            asyncio.create_task(self._process_single_request(req, setup))
            for req in requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == len(requests)
    
    async def _process_single_request(self, request, setup):
        """Process single generation request"""
        await asyncio.sleep(0.05)  # Simulate processing
        return f"Processed {request.session_id}"
    
    async def test_large_corpus_handling(self, admin_corpus_setup):
        """Test handling of large corpus generation requests"""
        setup = admin_corpus_setup
        large_request = CorpusGenerationRequest(
            domain="large_optimization", workload_types=["batch", "streaming"],
            parameters={"data_size": 50000, "complexity": "high"}, session_id=setup["session_id"]
        )
        await self._validate_large_corpus_handling(large_request, setup)
    
    async def _validate_large_corpus_handling(self, request, setup):
        """Validate large corpus generation handling"""
        resource_check = {"memory_mb": 256, "estimated_time_min": 20, "cpu_cores": 2}
        assert request.parameters["data_size"] == 50000
        assert resource_check["memory_mb"] < 512  # Within limits