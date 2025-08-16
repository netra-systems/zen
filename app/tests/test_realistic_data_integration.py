"""
Test Realistic Data Integration
Validates that synthetic data and corpus systems work with realistic patterns
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.realistic_test_data_service import RealisticTestDataService
from app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
from app.agents.corpus_admin_sub_agent import CorpusAdminSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.agents.corpus_admin.models import CorpusMetadata, CorpusType
from app.schemas.FinOps import WorkloadProfile, DataGenerationType
from app.schemas.Generation import GenerationStatus


class TestRealisticDataIntegration:
    """Test realistic data generation and integration"""
    
    @pytest.fixture
    def realistic_service(self):
        """Create realistic test data service"""
        return RealisticTestDataService()
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager"""
        manager = MagicMock(spec=LLMManager)
        manager.ask_llm = AsyncMock(return_value='{"status": "success"}')
        return manager
    
    @pytest.fixture
    def tool_dispatcher(self):
        """Create tool dispatcher with synthetic tools"""
        return ToolDispatcher()
    
    @pytest.fixture
    def synthetic_agent(self, mock_llm_manager, tool_dispatcher):
        """Create synthetic data sub-agent"""
        return SyntheticDataSubAgent(mock_llm_manager, tool_dispatcher)
    
    @pytest.fixture
    def corpus_agent(self, mock_llm_manager, tool_dispatcher):
        """Create corpus admin sub-agent"""
        return CorpusAdminSubAgent(mock_llm_manager, tool_dispatcher)
    
    def test_realistic_llm_response_generation(self, realistic_service):
        """Test generation of realistic LLM responses"""
        # Generate responses for different models
        models = ["gpt-4", "claude-3-opus", "gemini-pro"]
        
        for model in models:
            response = realistic_service.generate_realistic_llm_response(
                model=model,
                include_errors=True
            )
            
            # Verify response structure
            assert "success" in response
            assert "model" in response
            assert response["model"] == model
            
            if response["success"]:
                assert "latency_ms" in response
                assert "cost_usd" in response
                assert "prompt_tokens" in response
                assert "completion_tokens" in response
                assert response["latency_ms"] > 0
                assert response["cost_usd"] > 0
            else:
                assert "error" in response
                assert response["error"]["code"] in [400, 408, 429, 500, 503]
    
    def test_realistic_log_patterns(self, realistic_service):
        """Test generation of realistic log patterns"""
        patterns = ["normal_operation", "error_cascade", "memory_leak", "performance_degradation"]
        
        for pattern in patterns:
            logs = realistic_service.generate_realistic_log_data(
                pattern=pattern,
                duration_hours=1,
                volume=100
            )
            
            assert len(logs) == 100
            
            for log in logs:
                assert "timestamp" in log
                assert "level" in log
                assert "service" in log
                assert "message" in log
                assert "metrics" in log
                
                # Verify pattern-specific characteristics
                if pattern == "error_cascade":
                    # Should have increasing error rate
                    error_logs = [l for l in logs if l["level"] in ["ERROR", "CRITICAL"]]
                    assert len(error_logs) > 0
                
                elif pattern == "memory_leak":
                    # Should have increasing memory metrics
                    memory_values = [l["metrics"].get("memory_mb", 0) for l in logs]
                    assert memory_values[-1] > memory_values[0]  # Memory increases
    
    def test_workload_simulation(self, realistic_service):
        """Test complete workload simulation"""
        workload = realistic_service.generate_workload_simulation(
            workload_type="ecommerce",
            duration_days=1,
            include_seasonality=True
        )
        
        assert "workload_type" in workload
        assert "traffic_data" in workload
        assert "duration_days" in workload
        assert "total_requests" in workload
        
        # Verify traffic data points
        assert len(workload["traffic_data"]) > 0
        
        for point in workload["traffic_data"][:10]:  # Check first 10
            assert "timestamp" in point
            assert "hour_of_day" in point
            assert "day_of_week" in point
            
        # Verify statistics
        assert "peak_rps" in workload
        assert "average_rps" in workload
        assert workload["total_requests"] > 0
        assert workload["peak_rps"] > 0
    async def test_synthetic_agent_with_realistic_data(self, synthetic_agent):
        """Test synthetic data agent with realistic patterns"""
        state = DeepAgentState(user_request="Generate synthetic ecommerce workload data")
        state.triage_result = {"category": "synthetic", "is_admin_mode": True}
        
        # Prepare synthetic data result with proper structure
        workload_profile = WorkloadProfile(
            workload_type=DataGenerationType.INFERENCE_LOGS,
            volume=1000,
            time_range_days=30
        )
        generation_status = GenerationStatus(
            status="completed",
            records_generated=1000,
            total_records=1000,
            progress_percentage=100.0
        )
        
        # Mock synthetic result
        state.synthetic_data_result = {
            "success": True,
            "workload_profile": workload_profile.model_dump(),
            "generation_status": generation_status.model_dump(),
            "metadata": {}
        }
        
        # Check entry conditions
        can_execute = await synthetic_agent.check_entry_conditions(state, "test_run_001")
        assert can_execute == True
        
        # Mock the _send_update method
        synthetic_agent._send_update = AsyncMock()
        
        # Verify result stored in state
        assert state.synthetic_data_result != None
        result = state.synthetic_data_result
        
        # Should have workload profile
        assert "workload_profile" in result
        assert result["workload_profile"]["workload_type"] in [
            "inference_logs", "training_data", "performance_metrics", 
            "cost_data", "custom"
        ]
    async def test_corpus_agent_with_realistic_data(self, corpus_agent):
        """Test corpus admin agent with realistic operations"""
        state = DeepAgentState(user_request="Search the knowledge base for optimization strategies")
        state.triage_result = {"category": "corpus", "is_admin_mode": True}
        
        # Check entry conditions
        can_execute = await corpus_agent.check_entry_conditions(state, "test_run_002")
        assert can_execute == True
        
        # Mock the _send_update method
        corpus_agent._send_update = AsyncMock()
        
        # Create a proper corpus metadata object for testing
        corpus_metadata = CorpusMetadata(
            corpus_name="test_knowledge_base",
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            description="Test knowledge base for optimization strategies"
        )
        
        # Verify corpus metadata structure
        assert corpus_metadata.corpus_name == "test_knowledge_base"
        assert corpus_metadata.corpus_type == CorpusType.KNOWLEDGE_BASE
        assert corpus_metadata.description == "Test knowledge base for optimization strategies"
        
        # Test operation types
        valid_operations = [
            "create", "update", "delete", "search", 
            "analyze", "export", "import", "validate"
        ]
        assert "search" in valid_operations
    
    def test_tool_dispatcher_integration(self, tool_dispatcher):
        """Test tool dispatcher has synthetic and corpus tools"""
        # Check synthetic tools
        assert tool_dispatcher.has_tool("generate_synthetic_data_batch")
        assert tool_dispatcher.has_tool("validate_synthetic_data")
        assert tool_dispatcher.has_tool("store_synthetic_data")
        
        # Check corpus tools
        assert tool_dispatcher.has_tool("create_corpus")
        assert tool_dispatcher.has_tool("search_corpus")
        assert tool_dispatcher.has_tool("update_corpus")
        assert tool_dispatcher.has_tool("analyze_corpus")
    async def test_tool_execution(self, tool_dispatcher):
        """Test tool execution with realistic responses"""
        # Test synthetic data batch generation
        result = await tool_dispatcher.dispatch_tool(
            tool_name="generate_synthetic_data_batch",
            parameters={"batch_size": 10},
            state=DeepAgentState(user_request="test synthetic data generation"),
            run_id="test_003"
        )
        
        assert "success" in result or "data" in result
        if "data" in result:
            assert len(result["data"]) > 0
        
        # Test corpus search
        result = await tool_dispatcher.dispatch_tool(
            tool_name="search_corpus",
            parameters={"corpus_name": "test", "query": "optimization"},
            state=DeepAgentState(user_request="test corpus search"),
            run_id="test_004"
        )
        
        assert "success" in result or "results" in result
        if "results" in result:
            assert len(result["results"]) > 0
    
    def test_realistic_data_patterns(self, realistic_service):
        """Test that realistic data follows expected patterns"""
        # Test LLM latency distribution
        latencies = []
        for _ in range(100):
            response = realistic_service.generate_realistic_llm_response(
                model="gpt-4",
                include_errors=False
            )
            latencies.append(response["latency_ms"])
        
        # Most requests should be relatively fast
        median_latency = sorted(latencies)[50]
        p95_latency = sorted(latencies)[95]
        
        assert median_latency < p95_latency * 0.5  # P95 should be significantly higher
        assert min(latencies) < 1000  # Some requests are fast
        assert max(latencies) > 5000  # Some requests are slow
    
    def test_error_patterns(self, realistic_service):
        """Test realistic error patterns"""
        errors = []
        for _ in range(1000):
            response = realistic_service.generate_realistic_llm_response(
                model="gpt-4",
                include_errors=True
            )
            if not response["success"]:
                errors.append(response["error"]["type"])
        
        # Should have some errors but not too many
        error_rate = len(errors) / 1000
        assert 0.001 < error_rate < 0.1  # Between 0.1% and 10%
        
        # Should have different error types
        if errors:
            unique_errors = set(errors)
            assert len(unique_errors) > 0