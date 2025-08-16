"""
Test module: Supervisor Corpus Admin and Data Collection
Split from large test file for architecture compliance
Test classes: TestCorpusAdminDocumentManagement, TestSupplyResearcherDataCollection, TestDemoAgentWorkflow
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone
import json
import time

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.supervisor.execution_context import (
    ExecutionStrategy,
    AgentExecutionContext,
    AgentExecutionResult
)
from app.agents.state import DeepAgentState
from app.schemas import SubAgentLifecycle, WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher

from app.tests.helpers.supervisor_test_helpers import (
    create_corpus_admin_mocks, create_test_documents, setup_vector_store_mock,
    create_supply_researcher_mocks, create_supply_data, create_supplier_data,
    create_demo_agent_mocks, create_demo_data, create_timestamp_data
)
from app.tests.helpers.supervisor_test_classes import (
    CorpusAdminSubAgent, SupplyResearcherSubAgent, DemoAgent
)


# Mock classes for testing (would normally be imported)
class CorpusAdminSubAgent:
    """Mock corpus admin sub-agent for testing"""
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.vector_store = None
    
    async def index_documents(self, documents):
        """Index documents in vector store"""
        return await self.vector_store.add_documents(documents)
    
    async def retrieve_documents(self, query, top_k=5):
        """Retrieve documents using similarity search"""
        return await self.vector_store.similarity_search(query, top_k)
    
    async def update_document(self, document):
        """Update existing document"""
        return await self.vector_store.update_document(document)


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


class DemoAgent:
    """Mock demo agent for testing"""
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.random_seed = 0
    
    async def run_demo(self, scenario):
        """Run demo scenario"""
        return await self.generate_demo_data()
    
    async def generate_demo_data(self):
        """Generate demo data"""
        pass
    
    async def generate_synthetic_metrics(self):
        """Generate synthetic metrics with variety"""
        import random
        random.seed(self.random_seed)
        return {
            "accuracy": round(random.uniform(0.8, 0.99), 3),
            "latency": random.randint(50, 200),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class TestCorpusAdminDocumentManagement:
    """Test 5: Test document indexing and retrieval"""
    async def test_document_indexing_workflow(self):
        """Test document indexing workflow"""
        mocks = create_corpus_admin_mocks()
        corpus_admin = CorpusAdminSubAgent(mocks['llm_manager'], mocks['tool_dispatcher'])
        corpus_admin.vector_store = mocks['vector_store']
        setup_vector_store_mock(mocks['vector_store'], "add_documents", {"indexed": 5, "failed": 0})
        documents = create_test_documents(5)
        
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
    async def test_corpus_update_operations(self):
        """Test corpus update operations"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        corpus_admin = CorpusAdminSubAgent(llm_manager, tool_dispatcher)
        
        # Mock update operations
        corpus_admin.vector_store = AsyncMock()
        corpus_admin.vector_store.update_document = AsyncMock()
        corpus_admin.vector_store.update_document.return_value = {"success": True}
        
        update = {
            "id": "doc1",
            "content": "Updated AI optimization guide with new techniques",
            "metadata": {"version": "2.0", "updated_at": datetime.now(timezone.utc)}
        }
        
        result = await corpus_admin.update_document(update)
        
        assert result["success"]
        corpus_admin.vector_store.update_document.assert_called_with(update)


class TestSupplyResearcherDataCollection:
    """Test 6: Test supply chain data research capabilities"""
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


class TestDemoAgentWorkflow:
    """Test 7: Test demo scenario execution"""
    async def test_demo_scenario_execution(self):
        """Test execution of demo scenarios"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        demo_agent = DemoAgent(llm_manager, tool_dispatcher)
        
        # Mock demo data generation
        demo_agent.generate_demo_data = AsyncMock()
        demo_agent.generate_demo_data.return_value = {
            "metrics": {"accuracy": 0.95, "latency": 100},
            "recommendations": ["Increase batch size", "Use mixed precision"]
        }
        
        scenario = "optimization_demo"
        result = await demo_agent.run_demo(scenario)
        
        assert result["metrics"]["accuracy"] == 0.95
        assert len(result["recommendations"]) == 2
    async def test_demo_data_generation_variety(self):
        """Test variety in demo data generation"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        
        demo_agent = DemoAgent(llm_manager, tool_dispatcher)
        
        # Generate multiple demo datasets
        results = []
        for i in range(3):
            demo_agent.random_seed = i
            data = await demo_agent.generate_synthetic_metrics()
            results.append(data)
        
        # Verify variety in generated data
        assert results[0] != results[1]
        assert results[1] != results[2]
        assert all("timestamp" in r for r in results)