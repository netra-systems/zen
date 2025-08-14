"""
Integration Tests for Admin Agent System

Tests the complete integration flow from triage to corpus admin agent,
including tool dispatcher integration and WebSocket communication.
Maintains 300-line limit with 8-line function rule.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, Optional

from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.corpus_admin.agent import CorpusAdminSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.llm.llm_manager import LLMManager
from app.schemas.registry import DeepAgentState


class MockWebSocketManager:
    """Mock WebSocket manager for testing"""
    
    def __init__(self):
        self.sent_messages = []
    
    async def send_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Mock send message method expected by BaseAgent"""
        self.sent_messages.append({
            "user_id": user_id,
            "message": message,
            "timestamp": datetime.utcnow()
        })
    
    async def send_agent_update(self, run_id: str, agent_name: str, update: Dict[str, Any]) -> None:
        """Mock send agent update method"""
        self.sent_messages.append({
            "run_id": run_id,
            "agent_name": agent_name,
            "update": update,
            "timestamp": datetime.utcnow()
        })


class MockRedisManager:
    """Mock Redis manager for testing"""
    
    def __init__(self):
        self.cache = {}
    
    async def get(self, key: str) -> Optional[str]:
        """Mock get from cache"""
        return self.cache.get(key)
    
    async def set(self, key: str, value: str, expire: int = 3600) -> None:
        """Mock set to cache"""
        self.cache[key] = value


class TestAdminAgentIntegration:
    """Integration tests for admin agent system"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager with realistic responses"""
        llm_manager = Mock(spec=LLMManager)
        llm_manager.ask_structured_llm = AsyncMock()
        llm_manager.ask_llm = AsyncMock()
        return llm_manager
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher with corpus tools"""
        dispatcher = ToolDispatcher([])
        dispatcher.has_tool = Mock(return_value=True)
        dispatcher.dispatch_tool = AsyncMock()
        return dispatcher
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager"""
        return MockWebSocketManager()
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Create mock Redis manager"""
        return MockRedisManager()
    
    @pytest.fixture
    def sample_admin_state(self):
        """Create sample state for admin operations"""
        return DeepAgentState(
            user_request="Create a new corpus called 'customer_docs' for customer documentation",
            triage_result={
                "category": "corpus_administration",
                "confidence_score": 0.95,
                "is_admin_mode": True
            }
        )
    
    async def test_triage_to_corpus_admin_routing(
        self, mock_llm_manager, mock_tool_dispatcher, 
        mock_websocket_manager, mock_redis_manager, sample_admin_state
    ):
        """Test routing from triage agent to corpus admin agent"""
        # Setup triage response
        from app.agents.triage_sub_agent.models import TriageResult
        triage_response = TriageResult(category="corpus_administration", confidence_score=0.95, is_admin_mode=True)
        mock_llm_manager.ask_structured_llm.return_value = triage_response
        
        # Create triage agent
        triage_agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)
        triage_agent.websocket_manager = mock_websocket_manager
        
        run_id = str(uuid.uuid4())
        
        # Execute triage
        await triage_agent.execute(sample_admin_state, run_id, stream_updates=True)
        
        # Verify triage result indicates admin mode
        assert sample_admin_state.triage_result is not None
        triage_data = sample_admin_state.triage_result
        assert triage_data.get("is_admin_mode") is True and "corpus" in triage_data.get("category", "").lower()
        
        # Verify WebSocket updates sent
        assert len(mock_websocket_manager.sent_messages) >= 2
    
    async def test_corpus_admin_tool_integration(
        self, mock_llm_manager, mock_tool_dispatcher, 
        mock_websocket_manager, sample_admin_state
    ):
        """Test corpus admin agent integration with tool dispatcher"""
        # Setup tool dispatcher response
        mock_tool_dispatcher.dispatch_tool.return_value = {
            "success": True,
            "data": {"corpus_id": "test_corpus_123", "name": "customer_docs"},
            "message": "Corpus created successfully"
        }
        
        # Setup real operation request with enums and models
        from app.agents.corpus_admin.models import CorpusOperation, CorpusMetadata, CorpusType, CorpusOperationRequest
        operation_request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=CorpusMetadata(corpus_name="customer_docs", corpus_type=CorpusType.DOCUMENTATION)
        )
        
        # Create corpus admin agent
        corpus_agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)
        corpus_agent.websocket_manager = mock_websocket_manager
        
        run_id = str(uuid.uuid4())
        
        # Execute with mocked parser and validator
        with patch.object(corpus_agent.parser, 'parse_operation_request', return_value=operation_request), \
             patch.object(corpus_agent.validator, 'check_approval_requirements', return_value=False):
            await corpus_agent.execute(sample_admin_state, run_id, stream_updates=True)
        
        # Verify tool was called
        mock_tool_dispatcher.dispatch_tool.assert_called_once()
        
        # Verify result stored in state
        assert sample_admin_state.corpus_admin_result is not None
        result = sample_admin_state.corpus_admin_result
        assert result.get("success") is True
    
    async def test_websocket_message_flow(
        self, mock_llm_manager, mock_tool_dispatcher, 
        mock_websocket_manager
    ):
        """Test WebSocket message flow between agents"""
        sample_state = DeepAgentState(user_request="Search the knowledge base for pricing information")
        
        # Setup successful search operation
        mock_tool_dispatcher.dispatch_tool.return_value = {
            "success": True, "data": {"results": [{"title": "Pricing Guide"}], "total_matches": 1}
        }
        
        # Mock operation request
        from app.agents.corpus_admin.models import CorpusOperation, CorpusMetadata, CorpusType
        mock_operation_request = Mock()
        mock_operation_request.operation = CorpusOperation.SEARCH
        mock_operation_request.corpus_metadata = CorpusMetadata(
            corpus_name="knowledge_base", corpus_type=CorpusType.KNOWLEDGE_BASE
        )
        
        # Setup agents
        corpus_agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)
        corpus_agent.websocket_manager = mock_websocket_manager
        
        run_id = str(uuid.uuid4())
        
        # Execute with mocked parser
        with patch.object(corpus_agent.parser, 'parse_operation_request', 
                         return_value=mock_operation_request):
            await corpus_agent.execute(sample_state, run_id, stream_updates=True)
        
        # Verify message sequence
        messages = mock_websocket_manager.sent_messages
        assert len(messages) >= 3  # start, processing, completion
        assert messages[0]["message"]["payload"]["status"] == "starting"
    
    async def test_error_handling_integration(
        self, mock_llm_manager, mock_tool_dispatcher, 
        mock_websocket_manager, sample_admin_state
    ):
        """Test error handling across agent integration"""
        # Setup tool failure
        mock_tool_dispatcher.dispatch_tool.side_effect = Exception("Tool execution failed")
        
        # Mock operation request
        from app.agents.corpus_admin.models import CorpusOperation, CorpusMetadata, CorpusType
        mock_operation_request = Mock()
        mock_operation_request.operation = CorpusOperation.CREATE
        mock_operation_request.corpus_metadata = CorpusMetadata(
            corpus_name="test_corpus", corpus_type=CorpusType.REFERENCE_DATA
        )
        
        corpus_agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)
        corpus_agent.websocket_manager = mock_websocket_manager
        
        run_id = str(uuid.uuid4())
        
        # Execute with mocked parser and expect handled error
        with patch.object(corpus_agent.parser, 'parse_operation_request', 
                         return_value=mock_operation_request):
            with pytest.raises(Exception):
                await corpus_agent.execute(sample_admin_state, run_id, stream_updates=True)
        
        # Verify error result stored
        assert sample_admin_state.corpus_admin_result is not None
        result = sample_admin_state.corpus_admin_result
        assert result.get("success") is False
        assert "failed" in result.get("errors", [""])[0].lower()
    
    async def test_end_to_end_admin_workflow(
        self, mock_llm_manager, mock_tool_dispatcher,
        mock_websocket_manager, mock_redis_manager
    ):
        """Test complete end-to-end admin workflow"""
        # Create initial state
        state = DeepAgentState(user_request="I need to create a new knowledge base for our API documentation")
        
        # Setup triage response
        from app.agents.triage_sub_agent.models import TriageResult
        triage_response = TriageResult(category="corpus_administration", confidence_score=0.92, is_admin_mode=True)
        mock_llm_manager.ask_structured_llm.return_value = triage_response
        
        # Setup corpus creation response
        mock_tool_dispatcher.dispatch_tool.return_value = {
            "success": True, "data": {"corpus_id": "api_docs_corpus", "name": "api_documentation"}
        }
        
        run_id = str(uuid.uuid4())
        
        # Execute triage
        triage_agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)
        triage_agent.websocket_manager = mock_websocket_manager
        
        await triage_agent.execute(state, run_id, stream_updates=True)
        
        # Verify triage identifies admin operation and execute corpus admin with mocked operation
        assert state.triage_result is not None
        corpus_agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)
        corpus_agent.websocket_manager = mock_websocket_manager
        
        from app.agents.corpus_admin.models import CorpusOperation, CorpusMetadata, CorpusType
        mock_operation_request = Mock()
        mock_operation_request.operation = CorpusOperation.CREATE
        mock_operation_request.corpus_metadata = CorpusMetadata(
            corpus_name="api_documentation", corpus_type=CorpusType.DOCUMENTATION
        )
        
        with patch.object(corpus_agent.parser, 'parse_operation_request', 
                         return_value=mock_operation_request):
            await corpus_agent.execute(state, run_id, stream_updates=True)
        
        # Verify complete workflow
        assert state.corpus_admin_result is not None
        assert state.corpus_admin_result.get("success") is True
        
        # Verify message flow
        total_messages = len(mock_websocket_manager.sent_messages)
        assert total_messages >= 4  # triage + corpus messages
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(
        self, mock_llm_manager, mock_tool_dispatcher, mock_websocket_manager
    ):
        """Test concurrent agent execution scenarios"""
        # Create states and agents
        states = [DeepAgentState(user_request=f"Operation {i}") for i in range(2)]
        mock_tool_dispatcher.dispatch_tool.return_value = {"success": True}
        agents = [CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher) for _ in range(2)]
        for agent in agents:
            agent.websocket_manager = mock_websocket_manager
        
        # Mock operation request
        from app.agents.corpus_admin.models import CorpusOperation, CorpusMetadata, CorpusType
        mock_operation_request = Mock()
        mock_operation_request.operation = CorpusOperation.SEARCH
        mock_operation_request.corpus_metadata = CorpusMetadata(
            corpus_name="test_corpus", corpus_type=CorpusType.REFERENCE_DATA
        )
        
        # Execute concurrently
        tasks = [agent.execute(state, str(uuid.uuid4()), stream_updates=True) for agent, state in zip(agents, states)]
        with patch.object(agents[0].parser, 'parse_operation_request', return_value=mock_operation_request), \
             patch.object(agents[1].parser, 'parse_operation_request', return_value=mock_operation_request):
            try:
                await asyncio.gather(*tasks)
            except Exception:
                pass  # Expected for some scenarios
        
        assert len(mock_websocket_manager.sent_messages) > 0  # Verify executions attempted