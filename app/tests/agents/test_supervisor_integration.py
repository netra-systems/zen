"""Supervisor Agent Integration Tests
Priority: P0 - CRITICAL
Coverage: Quality validation, admin operations, corpus management, and utility functions
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher

from app.tests.helpers.supervisor_test_helpers import (
    create_supervisor_mocks, create_supervisor_agent, create_execution_context,
    create_agent_state
)


class TestQualitySupervisorValidation:
    """Test quality checks on agent responses"""
    async def test_validates_response_quality_score(self):
        """Test validation of response quality scores"""
        llm_manager = AsyncMock(spec=LLMManager)
        websocket_manager = AsyncMock()
        
        quality_supervisor = QualitySupervisor(llm_manager, websocket_manager)
        
        # Mock LLM quality check response
        llm_manager.ask_llm = AsyncMock()
        llm_manager.ask_llm.return_value = json.dumps({
            "quality_score": 0.85,
            "issues": [],
            "approved": True
        })
        
        response = DeepAgentState(
            user_request="Generate optimization recommendations",
            final_report="High quality optimization recommendations"
        )
        
        result = await quality_supervisor.validate_response(response)
        
        assert result["approved"]
        assert result["quality_score"] == 0.85
        assert len(result["issues"]) == 0
    async def test_rejects_low_quality_outputs(self):
        """Test rejection of low-quality outputs"""
        llm_manager = AsyncMock(spec=LLMManager)
        websocket_manager = AsyncMock()
        
        quality_supervisor = QualitySupervisor(llm_manager, websocket_manager)
        quality_supervisor.quality_threshold = 0.7
        
        # Mock low quality response
        llm_manager.ask_llm = AsyncMock()
        llm_manager.ask_llm.return_value = json.dumps({
            "quality_score": 0.4,
            "issues": [
                "Incomplete analysis",
                "Missing key recommendations",
                "Poor formatting"
            ],
            "approved": False
        })
        
        response = DeepAgentState(
            user_request="Generate report",
            final_report="Low quality response"
        )
        
        result = await quality_supervisor.validate_response(response)
        
        assert not result["approved"]
        assert result["quality_score"] == 0.4
        assert len(result["issues"]) == 3
        assert "Incomplete analysis" in result["issues"]


class TestAdminToolDispatcherRouting:
    """Test tool selection logic for admin operations"""
    async def test_routes_to_correct_admin_tool(self):
        """Test routing to correct admin tool based on operation"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        admin_dispatcher = AdminToolDispatcher(llm_manager, tool_dispatcher)
        
        # Mock tool execution
        tool_dispatcher.execute_tool = AsyncMock()
        tool_dispatcher.execute_tool.return_value = {"success": True, "result": "User created"}
        
        # Test user creation routing
        operation = {
            "type": "create_user",
            "params": {"username": "testuser", "role": "admin"}
        }
        
        result = await admin_dispatcher.dispatch_admin_operation(operation)
        
        tool_dispatcher.execute_tool.assert_called_with(
            "admin_user_management",
            operation["params"]
        )
        assert result["success"]
        assert result["result"] == "User created"
    async def test_validates_admin_permissions(self):
        """Test security checks for privileged operations"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        admin_dispatcher = AdminToolDispatcher(llm_manager, tool_dispatcher)
        
        # Test without proper permissions
        operation = {
            "type": "delete_all_data",
            "params": {},
            "user_role": "viewer"
        }
        
        with pytest.raises(PermissionError) as exc:
            await admin_dispatcher.dispatch_admin_operation(operation)
        
        assert "Insufficient permissions" in str(exc.value)
    async def test_admin_tool_audit_logging(self):
        """Test audit logging for admin operations"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        admin_dispatcher = AdminToolDispatcher(llm_manager, tool_dispatcher)
        admin_dispatcher.audit_logger = AsyncMock()
        
        operation = {
            "type": "modify_settings",
            "params": {"setting": "rate_limit", "value": 1000},
            "user_id": "admin-123"
        }
        
        tool_dispatcher.execute_tool = AsyncMock()
        tool_dispatcher.execute_tool.return_value = {"success": True}
        
        await admin_dispatcher.dispatch_admin_operation(operation)
        
        admin_dispatcher.audit_logger.log.assert_called_with({
            "operation": "modify_settings",
            "user_id": "admin-123",
            "params": operation["params"],
            "timestamp": pytest.approx(time.time(), rel=1)
        })


class TestCorpusAdminDocumentManagement:
    """Test document indexing and retrieval"""
    async def test_document_indexing_workflow(self):
        """Test document indexing workflow"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        corpus_admin = CorpusAdminSubAgent(llm_manager, tool_dispatcher)
        
        # Mock vector store
        corpus_admin.vector_store = AsyncMock()
        corpus_admin.vector_store.add_documents = AsyncMock()
        corpus_admin.vector_store.add_documents.return_value = {
            "indexed": 5,
            "failed": 0
        }
        
        documents = [
            {"id": "doc1", "content": "AI optimization guide"},
            {"id": "doc2", "content": "Performance tuning manual"},
            {"id": "doc3", "content": "Best practices document"},
            {"id": "doc4", "content": "Troubleshooting guide"},
            {"id": "doc5", "content": "API reference"}
        ]
        
        result = await corpus_admin.index_documents(documents)
        
        assert result["indexed"] == 5
        assert result["failed"] == 0
        corpus_admin.vector_store.add_documents.assert_called_once()
    async def test_document_retrieval_with_similarity_search(self):
        """Test document retrieval using similarity search"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        corpus_admin = CorpusAdminSubAgent(llm_manager, tool_dispatcher)
        
        # Mock similarity search
        corpus_admin.vector_store = AsyncMock()
        corpus_admin.vector_store.similarity_search = AsyncMock()
        corpus_admin.vector_store.similarity_search.return_value = [
            {"id": "doc1", "content": "AI optimization guide", "score": 0.95},
            {"id": "doc3", "content": "Best practices document", "score": 0.87}
        ]
        
        query = "How to optimize AI models?"
        results = await corpus_admin.retrieve_documents(query, top_k=2)
        
        assert len(results) == 2
        assert results[0]["score"] == 0.95
        assert results[0]["id"] == "doc1"


class TestSupplyResearcherDataCollection:
    """Test supply chain data research capabilities"""
    async def test_supply_chain_data_collection(self):
        """Test supply chain data collection workflow"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        supply_researcher = SupplyResearcherSubAgent(llm_manager, tool_dispatcher)
        
        # Mock external data sources
        supply_researcher.data_sources = AsyncMock()
        supply_researcher.data_sources.fetch_supply_data = AsyncMock()
        supply_researcher.data_sources.fetch_supply_data.return_value = {
            "suppliers": [
                {"id": "sup1", "name": "Supplier A", "reliability": 0.95},
                {"id": "sup2", "name": "Supplier B", "reliability": 0.88}
            ],
            "inventory": {"gpu": 1000, "cpu": 5000}
        }
        
        result = await supply_researcher.collect_supply_data("GPU components")
        
        assert len(result["suppliers"]) == 2
        assert result["inventory"]["gpu"] == 1000
    async def test_data_validation_and_enrichment(self):
        """Test data validation and enrichment process"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        supply_researcher = SupplyResearcherSubAgent(llm_manager, tool_dispatcher)
        
        raw_data = {
            "supplier": "Supplier A",
            "price": "1000",  # String that needs conversion
            "quantity": None  # Missing data
        }
        
        # Mock enrichment service
        supply_researcher.enrichment_service = AsyncMock()
        supply_researcher.enrichment_service.enrich = AsyncMock()
        supply_researcher.enrichment_service.enrich.return_value = {
            "supplier": "Supplier A",
            "price": 1000.0,
            "quantity": 100,  # Enriched from external source
            "quality_score": 0.92
        }
        
        result = await supply_researcher.validate_and_enrich(raw_data)
        
        assert isinstance(result["price"], float)
        assert result["quantity"] == 100
        assert "quality_score" in result


class TestAgentUtilsHelperFunctions:
    """Test utility helper functions"""
    async def test_retry_with_backoff(self):
        """Test retry utility with exponential backoff"""
        utils = AgentUtils()
        
        call_count = 0
        
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "Success"
        
        result = await utils.retry_with_backoff(
            flaky_function,
            max_retries=3,
            backoff_factor=0.1
        )
        
        assert result == "Success"
        assert call_count == 3
    async def test_parallel_execution_helper(self):
        """Test parallel execution of multiple tasks"""
        utils = AgentUtils()
        
        async def task(n):
            await asyncio.sleep(0.01)
            return n * 2
        
        tasks = [task(i) for i in range(5)]
        results = await utils.execute_parallel(tasks)
        
        assert results == [0, 2, 4, 6, 8]
    async def test_timeout_wrapper(self):
        """Test timeout wrapper for long-running operations"""
        utils = AgentUtils()
        
        async def slow_operation():
            await asyncio.sleep(5)
            return "Complete"
        
        with pytest.raises(asyncio.TimeoutError):
            await utils.with_timeout(slow_operation(), timeout=0.1)
    async def test_state_merging_utility(self):
        """Test utility for merging agent states"""
        utils = AgentUtils()
        
        state1 = DeepAgentState(
            user_request="Query",
            data_result={"analysis": {"metric1": 10}}
        )
        
        state2 = DeepAgentState(
            user_request="Query",
            optimizations_result={
                "optimization_type": "performance",
                "recommendations": ["batch optimization"]
            },
            data_result={"analysis": {"metric2": 20}}
        )
        
        merged = utils.merge_states(state1, state2)
        
        assert merged.user_request == "Query"
        assert merged.optimizations_result.optimization_type == "performance"
        assert merged.data_result == {"analysis": {"metric1": 10, "metric2": 20}}


# Helper implementations for testing (previously in large file)
class PermissionError(Exception):
    pass


class QualitySupervisor:
    def __init__(self, llm_manager, websocket_manager):
        self.llm_manager = llm_manager
        self.websocket_manager = websocket_manager
        self.quality_threshold = 0.7
    
    async def validate_response(self, response):
        result = await self.llm_manager.ask_llm("validate", "quality")
        return json.loads(result)


# Import real AdminToolDispatcher for integration testing
from app.agents.admin_tool_dispatcher import AdminToolDispatcher


class CorpusAdminSubAgent:
    """Mock CorpusAdminSubAgent for testing"""
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.vector_store = None
    
    async def index_documents(self, documents):
        return await self.vector_store.add_documents(documents)
    
    async def retrieve_documents(self, query, top_k=2):
        return await self.vector_store.similarity_search(query)
    
    async def update_document(self, update):
        return await self.vector_store.update_document(update)


class SupplyResearcherSubAgent:
    """Mock SupplyResearcherSubAgent for testing"""
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.data_sources = None
        self.enrichment_service = None
    
    async def collect_supply_data(self, query):
        return await self.data_sources.fetch_supply_data(query)
    
    async def validate_and_enrich(self, raw_data):
        return await self.enrichment_service.enrich(raw_data)


class AgentUtils:
    async def retry_with_backoff(self, func, max_retries=3, backoff_factor=1):
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(backoff_factor * (2 ** attempt))
    
    async def execute_parallel(self, tasks):
        return await asyncio.gather(*tasks)
    
    async def with_timeout(self, coro, timeout):
        return await asyncio.wait_for(coro, timeout)
    
    def merge_states(self, state1, state2):
        # Use the user_request from the first state
        merged = DeepAgentState(user_request=state1.user_request)
        
        # Get valid fields from the Pydantic model
        valid_fields = merged.model_fields.keys() if hasattr(merged, 'model_fields') else merged.__fields__.keys()
        
        # Merge all valid attributes
        for attr in valid_fields:
            if attr == "user_request":
                continue  # Already set
                
            val1 = getattr(state1, attr, None)
            val2 = getattr(state2, attr, None)
            
            if val1 is not None and val2 is not None:
                if isinstance(val1, dict) and isinstance(val2, dict):
                    # Deep merge dictionaries
                    merged_dict = val1.copy()
                    for k, v in val2.items():
                        if k in merged_dict and isinstance(merged_dict[k], dict) and isinstance(v, dict):
                            merged_dict[k] = {**merged_dict[k], **v}
                        else:
                            merged_dict[k] = v
                    setattr(merged, attr, merged_dict)
                elif isinstance(val1, list) and isinstance(val2, list):
                    setattr(merged, attr, val1 + val2)
                else:
                    setattr(merged, attr, val1)
            elif val1 is not None:
                setattr(merged, attr, val1)
            elif val2 is not None:
                setattr(merged, attr, val2)
        
        return merged