from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test module: Supervisor Corpus Admin and Data Collection
# REMOVED_SYNTAX_ERROR: Split from large test file for architecture compliance
# REMOVED_SYNTAX_ERROR: Test classes: TestCorpusAdminDocumentManagement, TestSupplyResearcherDataCollection, TestDemoServiceWorkflow
""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from datetime import datetime, timezone

import pytest
# REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas import ( )
AgentCompleted,
AgentStarted,
SubAgentLifecycle,
SubAgentUpdate,
WebSocketMessage,


from netra_backend.app.agents.state import DeepAgentState
# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_context import ( )
AgentExecutionContext,
AgentExecutionResult,

from netra_backend.app.core.interfaces_execution import ExecutionStrategy

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
# REMOVED_SYNTAX_ERROR: from netra_backend.tests.helpers.supervisor_test_classes import ( )
CorpusAdminSubAgent,
DemoService,
SupplyResearcherSubAgent,

# REMOVED_SYNTAX_ERROR: from netra_backend.tests.supervisor_test_helpers import ( )
create_corpus_admin_mocks,
create_demo_data,
create_demo_service_mocks,
create_supplier_data,
create_supply_data,
create_supply_researcher_mocks,
create_test_documents,
create_timestamp_data,
setup_vector_store_mock,


# Mock classes for testing (would normally be imported)
# REMOVED_SYNTAX_ERROR: class CorpusAdminSubAgent:
    # REMOVED_SYNTAX_ERROR: """Mock corpus admin sub-agent for testing"""
# REMOVED_SYNTAX_ERROR: def __init__(self, llm_manager, tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: self.llm_manager = llm_manager
    # REMOVED_SYNTAX_ERROR: self.tool_dispatcher = tool_dispatcher
    # REMOVED_SYNTAX_ERROR: self.vector_store = None

# REMOVED_SYNTAX_ERROR: async def index_documents(self, documents):
    # REMOVED_SYNTAX_ERROR: """Index documents in vector store"""
    # REMOVED_SYNTAX_ERROR: return await self.vector_store.add_documents(documents)

# REMOVED_SYNTAX_ERROR: async def retrieve_documents(self, query, top_k=5):
    # REMOVED_SYNTAX_ERROR: """Retrieve documents using similarity search"""
    # REMOVED_SYNTAX_ERROR: return await self.vector_store.similarity_search(query, top_k)

# REMOVED_SYNTAX_ERROR: async def update_document(self, document):
    # REMOVED_SYNTAX_ERROR: """Update existing document"""
    # REMOVED_SYNTAX_ERROR: return await self.vector_store.update_document(document)

# REMOVED_SYNTAX_ERROR: class SupplyResearcherSubAgent:
    # REMOVED_SYNTAX_ERROR: """Mock SupplyResearcherSubAgent for testing"""
# REMOVED_SYNTAX_ERROR: def __init__(self, llm_manager, tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: self.llm_manager = llm_manager
    # REMOVED_SYNTAX_ERROR: self.tool_dispatcher = tool_dispatcher
    # REMOVED_SYNTAX_ERROR: self.data_sources = None
    # REMOVED_SYNTAX_ERROR: self.enrichment_service = None

# REMOVED_SYNTAX_ERROR: async def collect_supply_data(self, query):
    # REMOVED_SYNTAX_ERROR: return await self.data_sources.fetch_supply_data(query)

# REMOVED_SYNTAX_ERROR: async def validate_and_enrich(self, raw_data):
    # REMOVED_SYNTAX_ERROR: return await self.enrichment_service.enrich(raw_data)

# REMOVED_SYNTAX_ERROR: class DemoService:
    # REMOVED_SYNTAX_ERROR: """Mock demo service for testing"""
# REMOVED_SYNTAX_ERROR: def __init__(self, llm_manager, tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: self.llm_manager = llm_manager
    # REMOVED_SYNTAX_ERROR: self.tool_dispatcher = tool_dispatcher
    # REMOVED_SYNTAX_ERROR: self.random_seed = 0

# REMOVED_SYNTAX_ERROR: async def run_demo(self, scenario):
    # REMOVED_SYNTAX_ERROR: """Run demo scenario"""
    # REMOVED_SYNTAX_ERROR: return await self.generate_demo_data()

# REMOVED_SYNTAX_ERROR: def _create_demo_data_dict(self, random):
    # REMOVED_SYNTAX_ERROR: """Create demo data dictionary"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "demo_scenario": "cost_optimization",
    # REMOVED_SYNTAX_ERROR: "sample_requests": random.randint(100, 1000),
    # REMOVED_SYNTAX_ERROR: "estimated_savings": round(random.uniform(1000, 50000), 2),
    # REMOVED_SYNTAX_ERROR: "demo_timestamp": datetime.now(timezone.utc).isoformat()
    

# REMOVED_SYNTAX_ERROR: async def generate_demo_data(self):
    # REMOVED_SYNTAX_ERROR: """Generate demo data"""
    # REMOVED_SYNTAX_ERROR: import random
    # REMOVED_SYNTAX_ERROR: random.seed(self.random_seed)
    # REMOVED_SYNTAX_ERROR: return self._create_demo_data_dict(random)

# REMOVED_SYNTAX_ERROR: def _create_metrics_dict(self, random):
    # REMOVED_SYNTAX_ERROR: """Create synthetic metrics dictionary"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "accuracy": round(random.uniform(0.8, 0.99), 3),
    # REMOVED_SYNTAX_ERROR: "latency": random.randint(50, 200),
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat()
    

# REMOVED_SYNTAX_ERROR: async def generate_synthetic_metrics(self):
    # REMOVED_SYNTAX_ERROR: """Generate synthetic metrics with variety"""
    # REMOVED_SYNTAX_ERROR: import random
    # REMOVED_SYNTAX_ERROR: random.seed(self.random_seed)
    # REMOVED_SYNTAX_ERROR: return self._create_metrics_dict(random)

# REMOVED_SYNTAX_ERROR: class TestCorpusAdminDocumentManagement:
    # REMOVED_SYNTAX_ERROR: """Test 5: Test document indexing and retrieval"""
# REMOVED_SYNTAX_ERROR: def _setup_indexing_test(self):
    # REMOVED_SYNTAX_ERROR: """Setup document indexing test"""
    # REMOVED_SYNTAX_ERROR: mocks = create_corpus_admin_mocks()
    # REMOVED_SYNTAX_ERROR: corpus_admin = CorpusAdminSubAgent(mocks['llm_manager'], mocks['tool_dispatcher'])
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store = mocks['vector_store']
    # REMOVED_SYNTAX_ERROR: setup_vector_store_mock(mocks['vector_store'], "add_documents", {"indexed": 5, "failed": 0])
    # REMOVED_SYNTAX_ERROR: return corpus_admin, create_test_documents(5)

# REMOVED_SYNTAX_ERROR: def _assert_indexing_results(self, result, corpus_admin):
    # REMOVED_SYNTAX_ERROR: """Assert document indexing results"""
    # REMOVED_SYNTAX_ERROR: assert result["indexed"] == 5
    # REMOVED_SYNTAX_ERROR: assert result["failed"] == 0
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store.add_documents.assert_called_once()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_document_indexing_workflow(self):
        # REMOVED_SYNTAX_ERROR: """Test document indexing workflow"""
        # REMOVED_SYNTAX_ERROR: corpus_admin, documents = self._setup_indexing_test()
        # REMOVED_SYNTAX_ERROR: result = await corpus_admin.index_documents(documents)
        # REMOVED_SYNTAX_ERROR: self._assert_indexing_results(result, corpus_admin)
# REMOVED_SYNTAX_ERROR: def _setup_retrieval_test(self):
    # REMOVED_SYNTAX_ERROR: """Setup document retrieval test"""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = AsyncMock(spec=LLMManager)
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = AsyncMock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: corpus_admin = CorpusAdminSubAgent(llm_manager, tool_dispatcher)
    # REMOVED_SYNTAX_ERROR: return corpus_admin

# REMOVED_SYNTAX_ERROR: def _mock_similarity_search(self, corpus_admin):
    # REMOVED_SYNTAX_ERROR: """Mock similarity search functionality"""
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store.similarity_search = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store.similarity_search.return_value = [ )
    # REMOVED_SYNTAX_ERROR: {"id": "doc1", "content": "AI optimization guide", "score": 0.95},
    # REMOVED_SYNTAX_ERROR: {"id": "doc3", "content": "Best practices document", "score": 0.87}
    

# REMOVED_SYNTAX_ERROR: def _assert_retrieval_results(self, results):
    # REMOVED_SYNTAX_ERROR: """Assert document retrieval results"""
    # REMOVED_SYNTAX_ERROR: assert len(results) == 2
    # REMOVED_SYNTAX_ERROR: assert results[0]["score"] == 0.95
    # REMOVED_SYNTAX_ERROR: assert results[0]["id"] == "doc1"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_document_retrieval_with_similarity_search(self):
        # REMOVED_SYNTAX_ERROR: """Test document retrieval using similarity search"""
        # REMOVED_SYNTAX_ERROR: corpus_admin = self._setup_retrieval_test()
        # REMOVED_SYNTAX_ERROR: self._mock_similarity_search(corpus_admin)
        # REMOVED_SYNTAX_ERROR: query = "How to optimize AI models?"
        # REMOVED_SYNTAX_ERROR: results = await corpus_admin.retrieve_documents(query, top_k=2)
        # REMOVED_SYNTAX_ERROR: self._assert_retrieval_results(results)
# REMOVED_SYNTAX_ERROR: def _setup_update_test(self):
    # REMOVED_SYNTAX_ERROR: """Setup corpus update test"""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = AsyncMock(spec=LLMManager)
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = AsyncMock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: corpus_admin = CorpusAdminSubAgent(llm_manager, tool_dispatcher)
    # REMOVED_SYNTAX_ERROR: return corpus_admin

# REMOVED_SYNTAX_ERROR: def _mock_update_operations(self, corpus_admin):
    # REMOVED_SYNTAX_ERROR: """Mock update operations"""
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store.update_document = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store.update_document.return_value = {"success": True}

# REMOVED_SYNTAX_ERROR: def _create_update_data(self):
    # REMOVED_SYNTAX_ERROR: """Create update data"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "id": "doc1",
    # REMOVED_SYNTAX_ERROR: "content": "Updated AI optimization guide with new techniques",
    # REMOVED_SYNTAX_ERROR: "metadata": {"version": "2.0", "updated_at": datetime.now(timezone.utc)}
    

# REMOVED_SYNTAX_ERROR: def _assert_update_results(self, result, corpus_admin, update):
    # REMOVED_SYNTAX_ERROR: """Assert update operation results"""
    # REMOVED_SYNTAX_ERROR: assert result["success"]
    # REMOVED_SYNTAX_ERROR: corpus_admin.vector_store.update_document.assert_called_with(update)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_corpus_update_operations(self):
        # REMOVED_SYNTAX_ERROR: """Test corpus update operations"""
        # REMOVED_SYNTAX_ERROR: corpus_admin = self._setup_update_test()
        # REMOVED_SYNTAX_ERROR: self._mock_update_operations(corpus_admin)
        # REMOVED_SYNTAX_ERROR: update = self._create_update_data()
        # REMOVED_SYNTAX_ERROR: result = await corpus_admin.update_document(update)
        # REMOVED_SYNTAX_ERROR: self._assert_update_results(result, corpus_admin, update)

# REMOVED_SYNTAX_ERROR: class TestSupplyResearcherDataCollection:
    # REMOVED_SYNTAX_ERROR: """Test 6: Test supply chain data research capabilities"""
# REMOVED_SYNTAX_ERROR: def _setup_supply_collection_test(self):
    # REMOVED_SYNTAX_ERROR: """Setup supply chain data collection test"""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = AsyncMock(spec=LLMManager)
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = AsyncMock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: supply_researcher = SupplyResearcherSubAgent(llm_manager, tool_dispatcher)
    # REMOVED_SYNTAX_ERROR: return supply_researcher

# REMOVED_SYNTAX_ERROR: def _mock_supply_data_sources(self, supply_researcher):
    # REMOVED_SYNTAX_ERROR: """Mock external supply data sources"""
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: supply_researcher.data_sources = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: supply_researcher.data_sources.fetch_supply_data = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: supply_researcher.data_sources.fetch_supply_data.return_value = { )
    # REMOVED_SYNTAX_ERROR: "suppliers": [ )
    # REMOVED_SYNTAX_ERROR: {"id": "sup1", "name": "Supplier A", "reliability": 0.95},
    # REMOVED_SYNTAX_ERROR: {"id": "sup2", "name": "Supplier B", "reliability": 0.88}
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: "inventory": {"gpu": 1000, "cpu": 5000}
    

# REMOVED_SYNTAX_ERROR: def _assert_supply_collection_results(self, result):
    # REMOVED_SYNTAX_ERROR: """Assert supply chain data collection results"""
    # REMOVED_SYNTAX_ERROR: assert len(result["suppliers"]) == 2
    # REMOVED_SYNTAX_ERROR: assert result["inventory"]["gpu"] == 1000

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_supply_chain_data_collection(self):
        # REMOVED_SYNTAX_ERROR: """Test supply chain data collection workflow"""
        # REMOVED_SYNTAX_ERROR: supply_researcher = self._setup_supply_collection_test()
        # REMOVED_SYNTAX_ERROR: self._mock_supply_data_sources(supply_researcher)
        # REMOVED_SYNTAX_ERROR: result = await supply_researcher.collect_supply_data("GPU components")
        # REMOVED_SYNTAX_ERROR: self._assert_supply_collection_results(result)
# REMOVED_SYNTAX_ERROR: def _setup_validation_test(self):
    # REMOVED_SYNTAX_ERROR: """Setup data validation and enrichment test"""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = AsyncMock(spec=LLMManager)
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = AsyncMock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: supply_researcher = SupplyResearcherSubAgent(llm_manager, tool_dispatcher)
    # REMOVED_SYNTAX_ERROR: return supply_researcher

# REMOVED_SYNTAX_ERROR: def _create_raw_test_data(self):
    # REMOVED_SYNTAX_ERROR: """Create raw test data for validation"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "supplier": "Supplier A",
    # REMOVED_SYNTAX_ERROR: "price": "1000",  # String that needs conversion
    # REMOVED_SYNTAX_ERROR: "quantity": None  # Missing data
    

# REMOVED_SYNTAX_ERROR: def _mock_enrichment_service(self, supply_researcher):
    # REMOVED_SYNTAX_ERROR: """Mock enrichment service"""
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: supply_researcher.enrichment_service = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: supply_researcher.enrichment_service.enrich = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: supply_researcher.enrichment_service.enrich.return_value = { )
    # REMOVED_SYNTAX_ERROR: "supplier": "Supplier A",
    # REMOVED_SYNTAX_ERROR: "price": 1000.0,
    # REMOVED_SYNTAX_ERROR: "quantity": 100,  # Enriched from external source
    # REMOVED_SYNTAX_ERROR: "quality_score": 0.92
    

# REMOVED_SYNTAX_ERROR: def _assert_validation_results(self, result):
    # REMOVED_SYNTAX_ERROR: """Assert data validation and enrichment results"""
    # REMOVED_SYNTAX_ERROR: assert isinstance(result["price"], float)
    # REMOVED_SYNTAX_ERROR: assert result["quantity"] == 100
    # REMOVED_SYNTAX_ERROR: assert "quality_score" in result

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_data_validation_and_enrichment(self):
        # REMOVED_SYNTAX_ERROR: """Test data validation and enrichment process"""
        # REMOVED_SYNTAX_ERROR: supply_researcher = self._setup_validation_test()
        # REMOVED_SYNTAX_ERROR: raw_data = self._create_raw_test_data()
        # REMOVED_SYNTAX_ERROR: self._mock_enrichment_service(supply_researcher)
        # REMOVED_SYNTAX_ERROR: result = await supply_researcher.validate_and_enrich(raw_data)
        # REMOVED_SYNTAX_ERROR: self._assert_validation_results(result)

# REMOVED_SYNTAX_ERROR: class TestDemoServiceWorkflow:
    # REMOVED_SYNTAX_ERROR: """Test 7: Test demo service scenario execution"""
# REMOVED_SYNTAX_ERROR: def _setup_demo_scenario_test(self):
    # REMOVED_SYNTAX_ERROR: """Setup demo scenario execution test"""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = AsyncMock(spec=LLMManager)
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = AsyncMock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: demo_service = DemoService(llm_manager, tool_dispatcher)
    # REMOVED_SYNTAX_ERROR: return demo_service

# REMOVED_SYNTAX_ERROR: def _mock_demo_data_generation(self, demo_service):
    # REMOVED_SYNTAX_ERROR: """Mock demo data generation"""
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: demo_service.generate_demo_data = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: demo_service.generate_demo_data.return_value = { )
    # REMOVED_SYNTAX_ERROR: "metrics": {"accuracy": 0.95, "latency": 100},
    # REMOVED_SYNTAX_ERROR: "recommendations": ["Increase batch size", "Use mixed precision"]
    

# REMOVED_SYNTAX_ERROR: def _assert_demo_scenario_results(self, result):
    # REMOVED_SYNTAX_ERROR: """Assert demo scenario execution results"""
    # REMOVED_SYNTAX_ERROR: assert result["metrics"]["accuracy"] == 0.95
    # REMOVED_SYNTAX_ERROR: assert len(result["recommendations"]) == 2

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_demo_scenario_execution(self):
        # REMOVED_SYNTAX_ERROR: """Test execution of demo scenarios"""
        # REMOVED_SYNTAX_ERROR: demo_service = self._setup_demo_scenario_test()
        # REMOVED_SYNTAX_ERROR: self._mock_demo_data_generation(demo_service)
        # REMOVED_SYNTAX_ERROR: scenario = "optimization_demo"
        # REMOVED_SYNTAX_ERROR: result = await demo_service.run_demo(scenario)
        # REMOVED_SYNTAX_ERROR: self._assert_demo_scenario_results(result)
# REMOVED_SYNTAX_ERROR: def _setup_demo_variety_test(self):
    # REMOVED_SYNTAX_ERROR: """Setup demo data variety test"""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = AsyncMock(spec=LLMManager)
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = AsyncMock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: demo_service = DemoService(llm_manager, tool_dispatcher)
    # REMOVED_SYNTAX_ERROR: return demo_service

# REMOVED_SYNTAX_ERROR: async def _generate_multiple_datasets(self, demo_service, count=3):
    # REMOVED_SYNTAX_ERROR: """Generate multiple demo datasets"""
    # REMOVED_SYNTAX_ERROR: results = []
    # REMOVED_SYNTAX_ERROR: for i in range(count):
        # REMOVED_SYNTAX_ERROR: demo_service.random_seed = i
        # REMOVED_SYNTAX_ERROR: data = await demo_service.generate_synthetic_metrics()
        # REMOVED_SYNTAX_ERROR: results.append(data)
        # REMOVED_SYNTAX_ERROR: return results

# REMOVED_SYNTAX_ERROR: def _assert_data_variety(self, results):
    # REMOVED_SYNTAX_ERROR: """Assert variety in generated data"""
    # REMOVED_SYNTAX_ERROR: assert results[0] != results[1]
    # REMOVED_SYNTAX_ERROR: assert results[1] != results[2]
    # REMOVED_SYNTAX_ERROR: assert all("timestamp" in r for r in results)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_demo_data_generation_variety(self):
        # REMOVED_SYNTAX_ERROR: """Test variety in demo data generation"""
        # REMOVED_SYNTAX_ERROR: demo_service = self._setup_demo_variety_test()
        # REMOVED_SYNTAX_ERROR: results = await self._generate_multiple_datasets(demo_service)
        # REMOVED_SYNTAX_ERROR: self._assert_data_variety(results)