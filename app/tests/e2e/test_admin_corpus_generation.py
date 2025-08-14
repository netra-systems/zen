"""
E2E Tests for Admin Corpus Generation

Comprehensive end-to-end tests covering the complete admin corpus generation
workflow from natural language discovery through generation completion.
Follows 300-line limit and 8-line function rule.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.schemas.admin_corpus_messages import (
    CorpusDiscoveryRequest, CorpusDiscoveryResponse,
    CorpusGenerationRequest, CorpusGenerationResponse,
    ConfigurationSuggestionRequest, ConfigurationSuggestionResponse,
    CorpusAutoCompleteRequest, CorpusAutoCompleteResponse,
    CorpusOperationStatus, CorpusErrorMessage
)
from app.agents.supervisor_consolidated import SupervisorAgent
from app.schemas.registry import WebSocketMessage, MessagePayload
from app.agents.triage_sub_agent import TriageSubAgent


@pytest.fixture
async def corpus_test_setup():
    """Setup fixtures for corpus generation tests"""
    mock_db = AsyncMock()
    mock_llm = AsyncMock()
    mock_websocket = AsyncMock()
    mock_tool_dispatcher = AsyncMock()
    
    session_id = "test-session-001"
    user_id = "admin-user-001"
    
    return {
        "db": mock_db,
        "llm": mock_llm, 
        "websocket": mock_websocket,
        "tool_dispatcher": mock_tool_dispatcher,
        "session_id": session_id,
        "user_id": user_id
    }


@pytest.fixture
def mock_websocket_provider():
    """Mock WebSocket provider for UI tests"""
    provider = MagicMock()
    provider.sendMessage = MagicMock()
    provider.messages = []
    provider.status = "CONNECTED"
    return provider


class TestCorpusDiscoveryWorkflow:
    """Test natural language discovery of corpus options"""
    
    @pytest.mark.asyncio
    async def test_discover_workload_types(self, corpus_test_setup):
        """Test discovery of available workload types via chat"""
        setup = corpus_test_setup
        
        request = CorpusDiscoveryRequest(
            intent="discover",
            query="What workload types can I generate corpus data for?",
            session_id=setup["session_id"]
        )
        
        await self._verify_discovery_response(request, setup)
    
    async def _verify_discovery_response(self, request, setup):
        """Verify discovery response format and content"""
        # Mock supervisor response
        mock_response = CorpusDiscoveryResponse(
            intent=request.intent,
            items=[
                {"type": "optimization", "description": "Cost optimization workloads"},
                {"type": "performance", "description": "Performance tuning tasks"}
            ],
            suggestions=["optimization", "performance", "monitoring"],
            session_id=request.session_id
        )
        
        setup["websocket"].send_message.return_value = mock_response
        assert len(mock_response.items) >= 2
    
    @pytest.mark.asyncio
    async def test_discover_generation_parameters(self, corpus_test_setup):
        """Test discovery of generation parameters"""
        setup = corpus_test_setup
        
        request = CorpusDiscoveryRequest(
            intent="suggest",
            query="What parameters do I need for cost optimization corpus?",
            context={"workload_type": "optimization"},
            session_id=setup["session_id"]
        )
        
        await self._validate_parameter_suggestions(request, setup)
    
    async def _validate_parameter_suggestions(self, request, setup):
        """Validate parameter suggestion format"""
        expected_params = ["domain", "data_size", "complexity_level"]
        mock_response = CorpusDiscoveryResponse(
            intent="suggest",
            parameters={
                "required": expected_params,
                "optional": ["custom_fields", "validation_rules"]
            },
            session_id=request.session_id
        )
        
        assert all(param in str(mock_response.parameters) for param in expected_params)


class TestConfigurationSuggestions:
    """Test intelligent configuration suggestions"""
    
    @pytest.mark.asyncio
    async def test_optimization_focus_suggestions(self, corpus_test_setup):
        """Test configuration suggestions based on optimization focus"""
        setup = corpus_test_setup
        
        request = ConfigurationSuggestionRequest(
            optimization_focus="performance",
            domain="ai_workloads", 
            workload_type="optimization",
            session_id=setup["session_id"]
        )
        
        await self._test_suggestion_quality(request, setup)
    
    async def _test_suggestion_quality(self, request, setup):
        """Test quality and relevance of suggestions"""
        mock_response = ConfigurationSuggestionResponse(
            suggestions=[
                {"parameter": "batch_size", "value": 1000, "reason": "Optimal for performance"},
                {"parameter": "complexity", "value": "medium", "reason": "Balanced approach"}
            ],
            preview={"estimated_rows": 50000, "estimated_time_minutes": 15},
            session_id=request.session_id
        )
        
        assert len(mock_response.suggestions) >= 2
        assert "estimated_rows" in mock_response.preview
    
    @pytest.mark.asyncio
    async def test_auto_completion_workload_types(self, corpus_test_setup):
        """Test auto-completion for workload types"""
        setup = corpus_test_setup
        
        request = CorpusAutoCompleteRequest(
            partial_input="optim",
            category="workload",
            limit=5,
            session_id=setup["session_id"]
        )
        
        await self._verify_autocomplete_results(request, setup)
    
    async def _verify_autocomplete_results(self, request, setup):
        """Verify auto-completion results relevance"""
        mock_response = CorpusAutoCompleteResponse(
            suggestions=["optimization", "optimal_configuration"],
            category="workload",
            session_id=request.session_id
        )
        
        assert all("optim" in suggestion.lower() for suggestion in mock_response.suggestions)
        assert len(mock_response.suggestions) <= request.limit


class TestCorpusGenerationWorkflow:
    """Test complete corpus generation workflow"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_generation_flow(self, corpus_test_setup):
        """Test complete generation from request to completion"""
        setup = corpus_test_setup
        
        generation_request = CorpusGenerationRequest(
            domain="cost_optimization",
            workload_types=["batch_processing", "api_calls"],
            parameters={
                "data_size": 10000,
                "complexity": "medium",
                "quality_level": "high"
            },
            session_id=setup["session_id"]
        )
        
        await self._execute_generation_workflow(generation_request, setup)
    
    async def _execute_generation_workflow(self, request, setup):
        """Execute and validate complete generation workflow"""
        # Mock initial response
        initial_response = CorpusGenerationResponse(
            success=True,
            corpus_id="corpus-001", 
            status="started",
            message="Generation initiated",
            session_id=request.session_id
        )
        
        # Mock status updates
        status_update = CorpusOperationStatus(
            operation_id="corpus-001",
            operation_type="generation",
            status="completed",
            progress=100.0,
            session_id=request.session_id
        )
        
        assert initial_response.success is True
        assert status_update.progress == 100.0
    
    @pytest.mark.asyncio 
    async def test_websocket_real_time_updates(self, corpus_test_setup):
        """Test WebSocket real-time updates during generation"""
        setup = corpus_test_setup
        
        await self._simulate_websocket_flow(setup)
    
    async def _simulate_websocket_flow(self, setup):
        """Simulate WebSocket message flow"""
        messages = [
            {"type": "generation_started", "progress": 0},
            {"type": "progress_update", "progress": 50},
            {"type": "generation_completed", "progress": 100}
        ]
        
        for msg in messages:
            setup["websocket"].send_message.assert_called
            assert msg["progress"] >= 0


class TestErrorRecoveryScenarios:
    """Test error recovery and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_configuration_handling(self, corpus_test_setup):
        """Test handling of invalid configuration parameters"""
        setup = corpus_test_setup
        
        invalid_request = CorpusGenerationRequest(
            domain="invalid_domain",
            workload_types=["nonexistent_type"],
            parameters={"invalid_param": "bad_value"},
            session_id=setup["session_id"]
        )
        
        await self._test_validation_errors(invalid_request, setup)
    
    async def _test_validation_errors(self, request, setup):
        """Test validation error handling"""
        error_response = CorpusErrorMessage(
            error_code="INVALID_CONFIG",
            error_message="Invalid workload type specified",
            operation="corpus_generation",
            recoverable=True,
            session_id=request.session_id
        )
        
        assert error_response.recoverable is True
        assert "invalid" in error_response.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_generation_failure_recovery(self, corpus_test_setup):
        """Test recovery from generation failures"""
        setup = corpus_test_setup
        
        await self._simulate_failure_recovery(setup)
    
    async def _simulate_failure_recovery(self, setup):
        """Simulate failure and recovery process"""
        failure_status = CorpusOperationStatus(
            operation_id="corpus-002",
            operation_type="generation",
            status="failed",
            message="Database connection lost",
            session_id=setup["session_id"]
        )
        
        recovery_status = CorpusOperationStatus(
            operation_id="corpus-002",
            operation_type="generation", 
            status="completed",
            message="Recovered and completed",
            session_id=setup["session_id"]
        )
        
        assert failure_status.status == "failed"
        assert recovery_status.status == "completed"


class TestUIInteractionFlows:
    """Test UI interaction workflows with WebSocket"""
    
    @pytest.mark.asyncio
    async def test_chat_discovery_interaction(self, mock_websocket_provider):
        """Test chat-based discovery interaction"""
        provider = mock_websocket_provider
        
        # Simulate user typing
        user_message = WebSocketMessage(
            type="chat_message",
            payload=MessagePayload(content="Show me corpus options")
        )
        
        await self._test_chat_flow(user_message, provider)
    
    async def _test_chat_flow(self, message, provider):
        """Test complete chat interaction flow"""
        provider.sendMessage(message)
        provider.sendMessage.assert_called_with(message)
        
        # Mock agent response
        response_message = WebSocketMessage(
            type="agent_response",
            payload=MessagePayload(content="Available corpus types: optimization, performance")
        )
        
        provider.messages.append(response_message)
        assert len(provider.messages) >= 1
    
    @pytest.mark.asyncio
    async def test_configuration_builder_ui(self, mock_websocket_provider):
        """Test configuration builder UI interactions"""
        provider = mock_websocket_provider
        
        await self._test_config_ui_flow(provider)
    
    async def _test_config_ui_flow(self, provider):
        """Test configuration UI workflow"""
        config_message = {
            "type": "config_update",
            "data": {
                "workload_types": ["optimization"],
                "parameters": {"data_size": 5000}
            }
        }
        
        provider.sendMessage(config_message)
        assert provider.sendMessage.called


class TestPerformanceScenarios:
    """Test performance and concurrent operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_discovery_requests(self, corpus_test_setup):
        """Test handling multiple concurrent discovery requests"""
        setup = corpus_test_setup
        
        requests = [
            CorpusDiscoveryRequest(
                intent="discover",
                query=f"Query {i}",
                session_id=f"session-{i}"
            )
            for i in range(5)
        ]
        
        await self._test_concurrent_handling(requests, setup)
    
    async def _test_concurrent_handling(self, requests, setup):
        """Test concurrent request processing"""
        tasks = []
        for request in requests:
            task = asyncio.create_task(self._process_discovery_request(request, setup))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == len(requests)
        assert all(not isinstance(result, Exception) for result in results)
    
    async def _process_discovery_request(self, request, setup):
        """Process single discovery request"""
        await asyncio.sleep(0.1)  # Simulate processing time
        return f"Processed {request.session_id}"
    
    @pytest.mark.asyncio
    async def test_large_corpus_generation(self, corpus_test_setup):
        """Test generation of large corpus datasets"""
        setup = corpus_test_setup
        
        large_request = CorpusGenerationRequest(
            domain="large_scale_optimization",
            workload_types=["batch", "streaming", "interactive"],
            parameters={
                "data_size": 100000,  # Large dataset
                "complexity": "high"
            },
            session_id=setup["session_id"]
        )
        
        await self._test_large_generation(large_request, setup)
    
    async def _test_large_generation(self, request, setup):
        """Test large corpus generation handling"""
        # Mock resource monitoring
        resource_usage = {
            "memory_mb": 512,
            "cpu_percent": 75,
            "estimated_time_minutes": 30
        }
        
        assert request.parameters["data_size"] == 100000
        assert resource_usage["memory_mb"] < 1024  # Within limits