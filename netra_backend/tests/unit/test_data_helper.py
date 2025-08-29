"""Unit tests for DataHelper tool.

Tests the data requirement generation functionality.
Business Value: Ensures accurate data collection for optimization strategies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.tools.data_helper import DataHelper, create_data_helper
from netra_backend.app.llm.llm_manager import LLMManager


class TestDataHelper:
    """Test suite for DataHelper tool."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = MagicMock(spec=LLMManager)
        llm_manager.agenerate = AsyncMock()
        return llm_manager
    
    @pytest.fixture
    def data_helper(self, mock_llm_manager):
        """Create DataHelper instance."""
        return DataHelper(mock_llm_manager)
    
    @pytest.mark.asyncio
    async def test_generate_data_request_success(self, data_helper, mock_llm_manager):
        """Test successful data request generation."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.generations = [[MagicMock(text="""
        **Required Data Sources for LLM Cost Optimization Analysis**
        
        [Current Usage Metrics]
        - Monthly token consumption: Essential for cost baseline
        - API call patterns: Identifies optimization opportunities
        
        [Application Context]
        - Primary use cases: Determines appropriate model selection
        - Latency requirements: Guides performance-cost trade-offs
        
        **Data Collection Instructions for User**
        Please provide your current usage metrics from your LLM provider dashboard.
        """)]]
        mock_llm_manager.agenerate.return_value = mock_response
        
        # Test data request generation
        result = await data_helper.generate_data_request(
            user_request="How to reduce LLM costs?",
            triage_result={"category": "cost_optimization", "data_sufficiency": "insufficient"},
            previous_results=[]
        )
        
        # Verify result structure
        assert result["success"] is True
        assert "data_request" in result
        assert "user_request" in result
        assert "triage_context" in result
        
        # Verify LLM was called
        mock_llm_manager.agenerate.assert_called_once()
        call_args = mock_llm_manager.agenerate.call_args
        assert call_args[1]["temperature"] == 0.3
        assert call_args[1]["max_tokens"] == 2000
    
    @pytest.mark.asyncio
    async def test_generate_data_request_with_previous_results(self, data_helper, mock_llm_manager):
        """Test data request generation with previous agent results."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.generations = [[MagicMock(text="Data request content")]]
        mock_llm_manager.agenerate.return_value = mock_response
        
        # Previous results from other agents
        previous_results = [
            {"agent_name": "triage", "result": {"category": "cost"}},
            {"agent_name": "optimization", "result": {"strategies": ["model_tiering"]}}
        ]
        
        # Generate request
        result = await data_helper.generate_data_request(
            user_request="Optimize costs",
            triage_result={"data_sufficiency": "partial"},
            previous_results=previous_results
        )
        
        # Verify previous results were formatted
        assert result["success"] is True
        
        # Check that prompt included previous results
        prompt_call = mock_llm_manager.agenerate.call_args[0][0][0]
        assert "triage:" in prompt_call or "optimization:" in prompt_call
    
    @pytest.mark.asyncio
    async def test_generate_data_request_error_handling(self, data_helper, mock_llm_manager):
        """Test error handling in data request generation."""
        # Mock LLM error
        mock_llm_manager.agenerate.side_effect = Exception("LLM API error")
        
        # Generate request
        result = await data_helper.generate_data_request(
            user_request="Test request",
            triage_result={},
            previous_results=None
        )
        
        # Verify error handling
        assert result["success"] is False
        assert "error" in result
        assert "LLM API error" in result["error"]
        assert "fallback_message" in result
    
    def test_extract_categories(self, data_helper):
        """Test category extraction from LLM response."""
        text = """
        [Usage Metrics]
        - Token consumption: Track usage patterns
          Justification: Essential for baseline
        - API calls: Monitor frequency
          
        [Performance Requirements]
        - Latency thresholds: Define acceptable delays
        """
        
        categories = data_helper._extract_categories(text)
        
        assert len(categories) == 2
        assert categories[0]["name"] == "Usage Metrics"
        assert len(categories[0]["items"]) == 2
        assert categories[1]["name"] == "Performance Requirements"
    
    def test_extract_instructions(self, data_helper):
        """Test instruction extraction from response."""
        text = """
        Some analysis content...
        
        Data Collection Instructions for User:
        Please export your usage data from the dashboard.
        Contact support if you need assistance.
        """
        
        instructions = data_helper._extract_instructions(text)
        
        assert "Data Collection Instructions" in instructions
        assert "export your usage data" in instructions
    
    def test_structure_data_items(self, data_helper):
        """Test structuring of data items."""
        categories = [
            {
                "name": "Metrics",
                "items": [
                    {"item": "Token count", "justification": "Cost calculation"},
                    {"item": "Response time", "justification": "Performance baseline"}
                ]
            },
            {
                "name": "Requirements",
                "items": [
                    {"item": "Budget limit", "justification": "Cost constraints"}
                ]
            }
        ]
        
        structured = data_helper._structure_data_items(categories)
        
        assert len(structured) == 3
        assert structured[0]["category"] == "Metrics"
        assert structured[0]["data_point"] == "Token count"
        assert structured[0]["justification"] == "Cost calculation"
        assert structured[0]["required"] is True
        
        assert structured[2]["category"] == "Requirements"
        assert structured[2]["data_point"] == "Budget limit"
    
    def test_get_fallback_message(self, data_helper):
        """Test fallback message generation."""
        message = data_helper._get_fallback_message("Optimize my LLM costs")
        
        assert "Optimize my LLM costs" in message
        assert "system metrics" in message.lower()
        assert "performance requirements" in message.lower()
        assert "budget" in message.lower()
    
    def test_format_previous_results_empty(self, data_helper):
        """Test formatting empty previous results."""
        formatted = data_helper._format_previous_results(None)
        assert formatted == "No previous agent results available."
        
        formatted = data_helper._format_previous_results([])
        assert formatted == "No previous agent results available."
    
    def test_format_previous_results_with_data(self, data_helper):
        """Test formatting previous results with data."""
        results = [
            {"agent_name": "triage", "summary": "Cost optimization request"},
            {"agent_name": "data", "result": "Metrics analyzed"},
            {"result": "Anonymous result"}
        ]
        
        formatted = data_helper._format_previous_results(results)
        
        assert "triage: Cost optimization request" in formatted
        assert "data: Metrics analyzed" in formatted
        assert "Agent 3: Anonymous result" in formatted
    
    def test_parse_data_request_with_response(self, data_helper):
        """Test parsing data request from LLM response."""
        mock_response = MagicMock()
        mock_response.generations = [[MagicMock(text="""
        [Category 1]
        - Item 1: Description
          Justification: Reason
        """)]]
        
        parsed = data_helper._parse_data_request(mock_response)
        
        assert "raw_response" in parsed
        assert "data_categories" in parsed
        assert "user_instructions" in parsed
        assert "structured_items" in parsed
        assert len(parsed["data_categories"]) > 0
    
    def test_create_data_helper_factory(self, mock_llm_manager):
        """Test factory function for creating DataHelper."""
        helper = create_data_helper(mock_llm_manager)
        
        assert isinstance(helper, DataHelper)
        assert helper.llm_manager == mock_llm_manager
        assert helper.prompt_template is not None


class TestDataHelperIntegration:
    """Integration tests for DataHelper with real prompt templates."""
    
    @pytest.mark.asyncio
    async def test_prompt_template_formatting(self):
        """Test that prompt template formats correctly."""
        from netra_backend.app.agents.prompts.supervisor_prompts import data_helper_prompt_template
        
        # Format the template with test data
        prompt = data_helper_prompt_template.format(
            user_request="Reduce GPT-4 costs",
            triage_result="{'category': 'cost_optimization'}",
            previous_results="No previous results"
        )
        
        # Verify formatting
        assert "Reduce GPT-4 costs" in prompt
        assert "cost_optimization" in prompt
        assert "No previous results" in prompt
        assert "Required Data Sources" in prompt
    
    @pytest.mark.asyncio
    async def test_complex_scenario(self):
        """Test complex scenario with multiple data categories."""
        mock_llm = MagicMock(spec=LLMManager)
        mock_llm.agenerate = AsyncMock()
        
        # Complex response with multiple categories
        mock_llm.agenerate.return_value = MagicMock(
            generations=[[MagicMock(text="""
            **Required Data Sources for LLM Cost Optimization Analysis**
            
            [1. Current Usage Metrics]
            - Monthly/daily token consumption (input vs output tokens)
              Justification: Essential for understanding cost baseline
            - API call volume and patterns
              Justification: Identifies peak usage for optimization
            
            [2. Application Context]
            - Primary use cases (chat, analysis, code generation)
              Justification: Determines appropriate model selection strategy
            - Latency requirements (real-time vs batch)
              Justification: Guides performance-cost trade-off decisions
            
            [3. Cost Breakdown]
            - Current monthly spend on GPT-4
              Justification: Establishes savings target
            - Cost per feature/endpoint
              Justification: Enables targeted optimization
            
            **Data Collection Instructions for User**
            Please provide the following information:
            1. Export usage metrics from OpenAI dashboard
            2. Document your main use cases and requirements
            3. Share current cost reports
            
            This data will enable comprehensive optimization strategies.
            """)]]
        )
        
        helper = DataHelper(mock_llm)
        result = await helper.generate_data_request(
            user_request="How to reduce LLM costs using GPT-4?",
            triage_result={
                "category": "cost_optimization",
                "data_sufficiency": "insufficient",
                "priority": "high"
            },
            previous_results=[
                {"agent_name": "triage", "result": "Categorized as cost optimization"}
            ]
        )
        
        # Verify comprehensive result
        assert result["success"] is True
        assert len(result["data_request"]["data_categories"]) >= 3
        assert "Export usage metrics" in result["data_request"]["user_instructions"]
        assert len(result["data_request"]["structured_items"]) >= 6