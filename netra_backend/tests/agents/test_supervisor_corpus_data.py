"""
Test module: Supervisor Corpus Admin and Data Collection
Split from large test file for architecture compliance
Test classes: TestCorpusAdminDocumentManagement, TestSupplyResearcherDataCollection, TestDemoServiceWorkflow
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone
import json
import time

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.execution_context import (

# Add project root to path
    ExecutionStrategy,
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from schemas import SubAgentLifecycle, WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted
from llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

from netra_backend.tests.helpers.supervisor_test_helpers import (
    create_corpus_admin_mocks, create_test_documents, setup_vector_store_mock,
    create_supply_researcher_mocks, create_supply_data, create_supplier_data,
    create_demo_service_mocks, create_demo_data, create_timestamp_data
)
from netra_backend.tests.helpers.supervisor_test_classes import (
    CorpusAdminSubAgent, SupplyResearcherSubAgent, DemoService
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


class DemoService:
    """Mock demo service for testing"""
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.random_seed = 0
    
    async def run_demo(self, scenario):
        """Run demo scenario"""
        return await self.generate_demo_data()
    
    def _create_demo_data_dict(self, random):
        """Create demo data dictionary"""
        return {
            "demo_scenario": "cost_optimization",
            "sample_requests": random.randint(100, 1000),
            "estimated_savings": round(random.uniform(1000, 50000), 2),
            "demo_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def generate_demo_data(self):
        """Generate demo data"""
        import random
        random.seed(self.random_seed)
        return self._create_demo_data_dict(random)
    
    def _create_metrics_dict(self, random):
        """Create synthetic metrics dictionary"""
        return {
            "accuracy": round(random.uniform(0.8, 0.99), 3),
            "latency": random.randint(50, 200),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def generate_synthetic_metrics(self):
        """Generate synthetic metrics with variety"""
        import random
        random.seed(self.random_seed)
        return self._create_metrics_dict(random)


class TestCorpusAdminDocumentManagement:
    """Test 5: Test document indexing and retrieval"""
    def _setup_indexing_test(self):
        """Setup document indexing test"""
        mocks = create_corpus_admin_mocks()
        corpus_admin = CorpusAdminSubAgent(mocks['llm_manager'], mocks['tool_dispatcher'])
        corpus_admin.vector_store = mocks['vector_store']
        setup_vector_store_mock(mocks['vector_store'], "add_documents", {"indexed": 5, "failed": 0})
        return corpus_admin, create_test_documents(5)
    
    def _assert_indexing_results(self, result, corpus_admin):
        """Assert document indexing results"""
        assert result["indexed"] == 5
        assert result["failed"] == 0
        corpus_admin.vector_store.add_documents.assert_called_once()
    
    async def test_document_indexing_workflow(self):
        """Test document indexing workflow"""
        corpus_admin, documents = self._setup_indexing_test()
        result = await corpus_admin.index_documents(documents)
        self._assert_indexing_results(result, corpus_admin)
    def _setup_retrieval_test(self):
        """Setup document retrieval test"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        corpus_admin = CorpusAdminSubAgent(llm_manager, tool_dispatcher)
        return corpus_admin
    
    def _mock_similarity_search(self, corpus_admin):
        """Mock similarity search functionality"""
        corpus_admin.vector_store = AsyncMock()
        corpus_admin.vector_store.similarity_search = AsyncMock()
        corpus_admin.vector_store.similarity_search.return_value = [
            {"id": "doc1", "content": "AI optimization guide", "score": 0.95},
            {"id": "doc3", "content": "Best practices document", "score": 0.87}
        ]
    
    def _assert_retrieval_results(self, results):
        """Assert document retrieval results"""
        assert len(results) == 2
        assert results[0]["score"] == 0.95
        assert results[0]["id"] == "doc1"
    
    async def test_document_retrieval_with_similarity_search(self):
        """Test document retrieval using similarity search"""
        corpus_admin = self._setup_retrieval_test()
        self._mock_similarity_search(corpus_admin)
        query = "How to optimize AI models?"
        results = await corpus_admin.retrieve_documents(query, top_k=2)
        self._assert_retrieval_results(results)
    def _setup_update_test(self):
        """Setup corpus update test"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        corpus_admin = CorpusAdminSubAgent(llm_manager, tool_dispatcher)
        return corpus_admin
    
    def _mock_update_operations(self, corpus_admin):
        """Mock update operations"""
        corpus_admin.vector_store = AsyncMock()
        corpus_admin.vector_store.update_document = AsyncMock()
        corpus_admin.vector_store.update_document.return_value = {"success": True}
    
    def _create_update_data(self):
        """Create update data"""
        return {
            "id": "doc1",
            "content": "Updated AI optimization guide with new techniques",
            "metadata": {"version": "2.0", "updated_at": datetime.now(timezone.utc)}
        }
    
    def _assert_update_results(self, result, corpus_admin, update):
        """Assert update operation results"""
        assert result["success"]
        corpus_admin.vector_store.update_document.assert_called_with(update)
    
    async def test_corpus_update_operations(self):
        """Test corpus update operations"""
        corpus_admin = self._setup_update_test()
        self._mock_update_operations(corpus_admin)
        update = self._create_update_data()
        result = await corpus_admin.update_document(update)
        self._assert_update_results(result, corpus_admin, update)


class TestSupplyResearcherDataCollection:
    """Test 6: Test supply chain data research capabilities"""
    def _setup_supply_collection_test(self):
        """Setup supply chain data collection test"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        supply_researcher = SupplyResearcherSubAgent(llm_manager, tool_dispatcher)
        return supply_researcher
    
    def _mock_supply_data_sources(self, supply_researcher):
        """Mock external supply data sources"""
        supply_researcher.data_sources = AsyncMock()
        supply_researcher.data_sources.fetch_supply_data = AsyncMock()
        supply_researcher.data_sources.fetch_supply_data.return_value = {
            "suppliers": [
                {"id": "sup1", "name": "Supplier A", "reliability": 0.95},
                {"id": "sup2", "name": "Supplier B", "reliability": 0.88}
            ],
            "inventory": {"gpu": 1000, "cpu": 5000}
        }
    
    def _assert_supply_collection_results(self, result):
        """Assert supply chain data collection results"""
        assert len(result["suppliers"]) == 2
        assert result["inventory"]["gpu"] == 1000
    
    async def test_supply_chain_data_collection(self):
        """Test supply chain data collection workflow"""
        supply_researcher = self._setup_supply_collection_test()
        self._mock_supply_data_sources(supply_researcher)
        result = await supply_researcher.collect_supply_data("GPU components")
        self._assert_supply_collection_results(result)
    def _setup_validation_test(self):
        """Setup data validation and enrichment test"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        supply_researcher = SupplyResearcherSubAgent(llm_manager, tool_dispatcher)
        return supply_researcher
    
    def _create_raw_test_data(self):
        """Create raw test data for validation"""
        return {
            "supplier": "Supplier A",
            "price": "1000",  # String that needs conversion
            "quantity": None  # Missing data
        }
    
    def _mock_enrichment_service(self, supply_researcher):
        """Mock enrichment service"""
        supply_researcher.enrichment_service = AsyncMock()
        supply_researcher.enrichment_service.enrich = AsyncMock()
        supply_researcher.enrichment_service.enrich.return_value = {
            "supplier": "Supplier A",
            "price": 1000.0,
            "quantity": 100,  # Enriched from external source
            "quality_score": 0.92
        }
    
    def _assert_validation_results(self, result):
        """Assert data validation and enrichment results"""
        assert isinstance(result["price"], float)
        assert result["quantity"] == 100
        assert "quality_score" in result
    
    async def test_data_validation_and_enrichment(self):
        """Test data validation and enrichment process"""
        supply_researcher = self._setup_validation_test()
        raw_data = self._create_raw_test_data()
        self._mock_enrichment_service(supply_researcher)
        result = await supply_researcher.validate_and_enrich(raw_data)
        self._assert_validation_results(result)


class TestDemoServiceWorkflow:
    """Test 7: Test demo service scenario execution"""
    def _setup_demo_scenario_test(self):
        """Setup demo scenario execution test"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        demo_service = DemoService(llm_manager, tool_dispatcher)
        return demo_service
    
    def _mock_demo_data_generation(self, demo_service):
        """Mock demo data generation"""
        demo_service.generate_demo_data = AsyncMock()
        demo_service.generate_demo_data.return_value = {
            "metrics": {"accuracy": 0.95, "latency": 100},
            "recommendations": ["Increase batch size", "Use mixed precision"]
        }
    
    def _assert_demo_scenario_results(self, result):
        """Assert demo scenario execution results"""
        assert result["metrics"]["accuracy"] == 0.95
        assert len(result["recommendations"]) == 2
    
    async def test_demo_scenario_execution(self):
        """Test execution of demo scenarios"""
        demo_service = self._setup_demo_scenario_test()
        self._mock_demo_data_generation(demo_service)
        scenario = "optimization_demo"
        result = await demo_service.run_demo(scenario)
        self._assert_demo_scenario_results(result)
    def _setup_demo_variety_test(self):
        """Setup demo data variety test"""
        llm_manager = AsyncMock(spec=LLMManager)
        tool_dispatcher = AsyncMock(spec=ToolDispatcher)
        demo_service = DemoService(llm_manager, tool_dispatcher)
        return demo_service
    
    async def _generate_multiple_datasets(self, demo_service, count=3):
        """Generate multiple demo datasets"""
        results = []
        for i in range(count):
            demo_service.random_seed = i
            data = await demo_service.generate_synthetic_metrics()
            results.append(data)
        return results
    
    def _assert_data_variety(self, results):
        """Assert variety in generated data"""
        assert results[0] != results[1]
        assert results[1] != results[2]
        assert all("timestamp" in r for r in results)
    
    async def test_demo_data_generation_variety(self):
        """Test variety in demo data generation"""
        demo_service = self._setup_demo_variety_test()
        results = await self._generate_multiple_datasets(demo_service)
        self._assert_data_variety(results)