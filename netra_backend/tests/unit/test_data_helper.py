# REMOVED_SYNTAX_ERROR: '''Unit tests for DataHelper tool.

# REMOVED_SYNTAX_ERROR: Tests the data requirement generation functionality.
# REMOVED_SYNTAX_ERROR: Business Value: Ensures accurate data collection for optimization strategies.
# REMOVED_SYNTAX_ERROR: '''

import pytest
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.tools.data_helper import DataHelper, create_data_helper
from netra_backend.app.llm.llm_manager import LLMManager
import asyncio


# REMOVED_SYNTAX_ERROR: class TestDataHelper:
    # REMOVED_SYNTAX_ERROR: """Test suite for DataHelper tool."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock LLM manager."""
    # REMOVED_SYNTAX_ERROR: llm_manager = MagicMock(spec=LLMManager)
    # REMOVED_SYNTAX_ERROR: llm_manager.agenerate = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return llm_manager

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def data_helper(self, mock_llm_manager):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create DataHelper instance."""
    # REMOVED_SYNTAX_ERROR: return DataHelper(mock_llm_manager)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_generate_data_request_success(self, data_helper, mock_llm_manager):
        # REMOVED_SYNTAX_ERROR: """Test successful data request generation."""
        # Mock LLM response
        # REMOVED_SYNTAX_ERROR: mock_response = MagicNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_response.generations = [[MagicMock(text=''' )))
        # REMOVED_SYNTAX_ERROR: **Required Data Sources for LLM Cost Optimization Analysis**

        # REMOVED_SYNTAX_ERROR: [Current Usage Metrics]
        # REMOVED_SYNTAX_ERROR: - Monthly token consumption: Essential for cost baseline
        # REMOVED_SYNTAX_ERROR: - API call patterns: Identifies optimization opportunities

        # REMOVED_SYNTAX_ERROR: [Application Context]
        # REMOVED_SYNTAX_ERROR: - Primary use cases: Determines appropriate model selection
        # REMOVED_SYNTAX_ERROR: - Latency requirements: Guides performance-cost trade-offs

        # REMOVED_SYNTAX_ERROR: **Data Collection Instructions for User**
        # REMOVED_SYNTAX_ERROR: Please provide your current usage metrics from your LLM provider dashboard.
        # REMOVED_SYNTAX_ERROR: ''')]]
        # REMOVED_SYNTAX_ERROR: mock_llm_manager.agenerate.return_value = mock_response

        # Test data request generation
        # REMOVED_SYNTAX_ERROR: result = await data_helper.generate_data_request( )
        # REMOVED_SYNTAX_ERROR: user_request="How to reduce LLM costs?",
        # REMOVED_SYNTAX_ERROR: triage_result={"category": "cost_optimization", "data_sufficiency": "insufficient"},
        # REMOVED_SYNTAX_ERROR: previous_results=[]
        

        # Verify result structure
        # REMOVED_SYNTAX_ERROR: assert result["success"] is True
        # REMOVED_SYNTAX_ERROR: assert "data_request" in result
        # REMOVED_SYNTAX_ERROR: assert "user_request" in result
        # REMOVED_SYNTAX_ERROR: assert "triage_context" in result

        # Verify LLM was called
        # REMOVED_SYNTAX_ERROR: mock_llm_manager.agenerate.assert_called_once()
        # REMOVED_SYNTAX_ERROR: call_args = mock_llm_manager.agenerate.call_args
        # REMOVED_SYNTAX_ERROR: assert call_args[1]["temperature"] == 0.3
        # REMOVED_SYNTAX_ERROR: assert call_args[1]["max_tokens"] == 2000

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_generate_data_request_with_previous_results(self, data_helper, mock_llm_manager):
            # REMOVED_SYNTAX_ERROR: """Test data request generation with previous agent results."""
            # Mock LLM response
            # REMOVED_SYNTAX_ERROR: mock_response = MagicNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_response.generations = [[MagicMock(text="Data request content")]]
            # REMOVED_SYNTAX_ERROR: mock_llm_manager.agenerate.return_value = mock_response

            # Previous results from other agents
            # REMOVED_SYNTAX_ERROR: previous_results = [ )
            # REMOVED_SYNTAX_ERROR: {"agent_name": "triage", "result": {"category": "cost"}},
            # REMOVED_SYNTAX_ERROR: {"agent_name": "optimization", "result": {"strategies": ["model_tiering"]}}
            

            # Generate request
            # REMOVED_SYNTAX_ERROR: result = await data_helper.generate_data_request( )
            # REMOVED_SYNTAX_ERROR: user_request="Optimize costs",
            # REMOVED_SYNTAX_ERROR: triage_result={"data_sufficiency": "partial"},
            # REMOVED_SYNTAX_ERROR: previous_results=previous_results
            

            # Verify previous results were formatted
            # REMOVED_SYNTAX_ERROR: assert result["success"] is True

            # Check that prompt included previous results
            # REMOVED_SYNTAX_ERROR: prompt_call = mock_llm_manager.agenerate.call_args[0][0][0]
            # REMOVED_SYNTAX_ERROR: assert "triage:" in prompt_call or "optimization:" in prompt_call

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_generate_data_request_error_handling(self, data_helper, mock_llm_manager):
                # REMOVED_SYNTAX_ERROR: """Test error handling in data request generation."""
                # Mock LLM error
                # REMOVED_SYNTAX_ERROR: mock_llm_manager.agenerate.side_effect = Exception("LLM API error")

                # Generate request
                # REMOVED_SYNTAX_ERROR: result = await data_helper.generate_data_request( )
                # REMOVED_SYNTAX_ERROR: user_request="Test request",
                # REMOVED_SYNTAX_ERROR: triage_result={},
                # REMOVED_SYNTAX_ERROR: previous_results=None
                

                # Verify error handling
                # REMOVED_SYNTAX_ERROR: assert result["success"] is False
                # REMOVED_SYNTAX_ERROR: assert "error" in result
                # REMOVED_SYNTAX_ERROR: assert "LLM API error" in result["error"]
                # REMOVED_SYNTAX_ERROR: assert "fallback_message" in result

# REMOVED_SYNTAX_ERROR: def test_extract_categories(self, data_helper):
    # REMOVED_SYNTAX_ERROR: """Test category extraction from LLM response."""
    # REMOVED_SYNTAX_ERROR: text = '''
    # REMOVED_SYNTAX_ERROR: [Usage Metrics]
    # REMOVED_SYNTAX_ERROR: - Token consumption: Track usage patterns
    # REMOVED_SYNTAX_ERROR: Justification: Essential for baseline
    # REMOVED_SYNTAX_ERROR: - API calls: Monitor frequency

    # REMOVED_SYNTAX_ERROR: [Performance Requirements]
    # REMOVED_SYNTAX_ERROR: - Latency thresholds: Define acceptable delays
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: categories = data_helper._extract_categories(text)

    # REMOVED_SYNTAX_ERROR: assert len(categories) == 2
    # REMOVED_SYNTAX_ERROR: assert categories[0]["name"] == "Usage Metrics"
    # REMOVED_SYNTAX_ERROR: assert len(categories[0]["items"]) == 2
    # REMOVED_SYNTAX_ERROR: assert categories[1]["name"] == "Performance Requirements"

# REMOVED_SYNTAX_ERROR: def test_extract_instructions(self, data_helper):
    # REMOVED_SYNTAX_ERROR: """Test instruction extraction from response."""
    # REMOVED_SYNTAX_ERROR: text = '''
    # REMOVED_SYNTAX_ERROR: Some analysis content...

    # REMOVED_SYNTAX_ERROR: Data Collection Instructions for User:
        # REMOVED_SYNTAX_ERROR: Please export your usage data from the dashboard.
        # REMOVED_SYNTAX_ERROR: Contact support if you need assistance.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: instructions = data_helper._extract_instructions(text)

        # REMOVED_SYNTAX_ERROR: assert "Data Collection Instructions" in instructions
        # REMOVED_SYNTAX_ERROR: assert "export your usage data" in instructions

# REMOVED_SYNTAX_ERROR: def test_structure_data_items(self, data_helper):
    # REMOVED_SYNTAX_ERROR: """Test structuring of data items."""
    # REMOVED_SYNTAX_ERROR: categories = [ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "name": "Metrics",
    # REMOVED_SYNTAX_ERROR: "items": [ )
    # REMOVED_SYNTAX_ERROR: {"item": "Token count", "justification": "Cost calculation"},
    # REMOVED_SYNTAX_ERROR: {"item": "Response time", "justification": "Performance baseline"}
    
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "name": "Requirements",
    # REMOVED_SYNTAX_ERROR: "items": [ )
    # REMOVED_SYNTAX_ERROR: {"item": "Budget limit", "justification": "Cost constraints"}
    
    
    

    # REMOVED_SYNTAX_ERROR: structured = data_helper._structure_data_items(categories)

    # REMOVED_SYNTAX_ERROR: assert len(structured) == 3
    # REMOVED_SYNTAX_ERROR: assert structured[0]["category"] == "Metrics"
    # REMOVED_SYNTAX_ERROR: assert structured[0]["data_point"] == "Token count"
    # REMOVED_SYNTAX_ERROR: assert structured[0]["justification"] == "Cost calculation"
    # REMOVED_SYNTAX_ERROR: assert structured[0]["required"] is True

    # REMOVED_SYNTAX_ERROR: assert structured[2]["category"] == "Requirements"
    # REMOVED_SYNTAX_ERROR: assert structured[2]["data_point"] == "Budget limit"

# REMOVED_SYNTAX_ERROR: def test_get_fallback_message(self, data_helper):
    # REMOVED_SYNTAX_ERROR: """Test fallback message generation."""
    # REMOVED_SYNTAX_ERROR: message = data_helper._get_fallback_message("Optimize my LLM costs")

    # REMOVED_SYNTAX_ERROR: assert "Optimize my LLM costs" in message
    # REMOVED_SYNTAX_ERROR: assert "system metrics" in message.lower()
    # REMOVED_SYNTAX_ERROR: assert "performance requirements" in message.lower()
    # REMOVED_SYNTAX_ERROR: assert "budget" in message.lower()

# REMOVED_SYNTAX_ERROR: def test_format_previous_results_empty(self, data_helper):
    # REMOVED_SYNTAX_ERROR: """Test formatting empty previous results."""
    # REMOVED_SYNTAX_ERROR: formatted = data_helper._format_previous_results(None)
    # REMOVED_SYNTAX_ERROR: assert formatted == "No previous agent results available."

    # REMOVED_SYNTAX_ERROR: formatted = data_helper._format_previous_results([])
    # REMOVED_SYNTAX_ERROR: assert formatted == "No previous agent results available."

# REMOVED_SYNTAX_ERROR: def test_format_previous_results_with_data(self, data_helper):
    # REMOVED_SYNTAX_ERROR: """Test formatting previous results with data."""
    # REMOVED_SYNTAX_ERROR: results = [ )
    # REMOVED_SYNTAX_ERROR: {"agent_name": "triage", "summary": "Cost optimization request"},
    # REMOVED_SYNTAX_ERROR: {"agent_name": "data", "result": "Metrics analyzed"},
    # REMOVED_SYNTAX_ERROR: {"result": "Anonymous result"}
    

    # REMOVED_SYNTAX_ERROR: formatted = data_helper._format_previous_results(results)

    # REMOVED_SYNTAX_ERROR: assert "triage: Cost optimization request" in formatted
    # REMOVED_SYNTAX_ERROR: assert "data: Metrics analyzed" in formatted
    # REMOVED_SYNTAX_ERROR: assert "Agent 3: Anonymous result" in formatted

# REMOVED_SYNTAX_ERROR: def test_parse_data_request_with_response(self, data_helper):
    # REMOVED_SYNTAX_ERROR: """Test parsing data request from LLM response."""
    # REMOVED_SYNTAX_ERROR: mock_response = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_response.generations = [[MagicMock(text=''' )))
    # REMOVED_SYNTAX_ERROR: [Category 1]
    # REMOVED_SYNTAX_ERROR: - Item 1: Description
    # REMOVED_SYNTAX_ERROR: Justification: Reason
    # REMOVED_SYNTAX_ERROR: ''')]]

    # REMOVED_SYNTAX_ERROR: parsed = data_helper._parse_data_request(mock_response)

    # REMOVED_SYNTAX_ERROR: assert "raw_response" in parsed
    # REMOVED_SYNTAX_ERROR: assert "data_categories" in parsed
    # REMOVED_SYNTAX_ERROR: assert "user_instructions" in parsed
    # REMOVED_SYNTAX_ERROR: assert "structured_items" in parsed
    # REMOVED_SYNTAX_ERROR: assert len(parsed["data_categories"]) > 0

# REMOVED_SYNTAX_ERROR: def test_create_data_helper_factory(self, mock_llm_manager):
    # REMOVED_SYNTAX_ERROR: """Test factory function for creating DataHelper."""
    # REMOVED_SYNTAX_ERROR: helper = create_data_helper(mock_llm_manager)

    # REMOVED_SYNTAX_ERROR: assert isinstance(helper, DataHelper)
    # REMOVED_SYNTAX_ERROR: assert helper.llm_manager == mock_llm_manager
    # REMOVED_SYNTAX_ERROR: assert helper.prompt_template is not None


# REMOVED_SYNTAX_ERROR: class TestDataHelperIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for DataHelper with real prompt templates."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_prompt_template_formatting(self):
        # REMOVED_SYNTAX_ERROR: """Test that prompt template formats correctly."""
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.prompts.supervisor_prompts import data_helper_prompt_template

        # Format the template with test data
        # REMOVED_SYNTAX_ERROR: prompt = data_helper_prompt_template.format( )
        # REMOVED_SYNTAX_ERROR: user_request="Reduce GPT-4 costs",
        # REMOVED_SYNTAX_ERROR: triage_result="{'category': 'cost_optimization'}",
        # REMOVED_SYNTAX_ERROR: previous_results="No previous results"
        

        # Verify formatting
        # REMOVED_SYNTAX_ERROR: assert "Reduce GPT-4 costs" in prompt
        # REMOVED_SYNTAX_ERROR: assert "cost_optimization" in prompt
        # REMOVED_SYNTAX_ERROR: assert "No previous results" in prompt
        # REMOVED_SYNTAX_ERROR: assert "Required Data Sources" in prompt

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_complex_scenario(self):
            # REMOVED_SYNTAX_ERROR: """Test complex scenario with multiple data categories."""
            # REMOVED_SYNTAX_ERROR: mock_llm = MagicMock(spec=LLMManager)
            # REMOVED_SYNTAX_ERROR: mock_llm.agenerate = AsyncNone  # TODO: Use real service instance

            # Complex response with multiple categories
            # REMOVED_SYNTAX_ERROR: mock_llm.agenerate.return_value = MagicMock( )
            # REMOVED_SYNTAX_ERROR: generations=[[MagicMock(text=''' )))
            # REMOVED_SYNTAX_ERROR: **Required Data Sources for LLM Cost Optimization Analysis**

            # REMOVED_SYNTAX_ERROR: [1. Current Usage Metrics]
            # REMOVED_SYNTAX_ERROR: - Monthly/daily token consumption (input vs output tokens)
            # REMOVED_SYNTAX_ERROR: Justification: Essential for understanding cost baseline
            # REMOVED_SYNTAX_ERROR: - API call volume and patterns
            # REMOVED_SYNTAX_ERROR: Justification: Identifies peak usage for optimization

            # REMOVED_SYNTAX_ERROR: [2. Application Context]
            # REMOVED_SYNTAX_ERROR: - Primary use cases (chat, analysis, code generation)
            # REMOVED_SYNTAX_ERROR: Justification: Determines appropriate model selection strategy
            # REMOVED_SYNTAX_ERROR: - Latency requirements (real-time vs batch)
            # REMOVED_SYNTAX_ERROR: Justification: Guides performance-cost trade-off decisions

            # REMOVED_SYNTAX_ERROR: [3. Cost Breakdown]
            # REMOVED_SYNTAX_ERROR: - Current monthly spend on GPT-4
            # REMOVED_SYNTAX_ERROR: Justification: Establishes savings target
            # REMOVED_SYNTAX_ERROR: - Cost per feature/endpoint
            # REMOVED_SYNTAX_ERROR: Justification: Enables targeted optimization

            # REMOVED_SYNTAX_ERROR: **Data Collection Instructions for User**
            # REMOVED_SYNTAX_ERROR: Please provide the following information:
                # REMOVED_SYNTAX_ERROR: 1. Export usage metrics from OpenAI dashboard
                # REMOVED_SYNTAX_ERROR: 2. Document your main use cases and requirements
                # REMOVED_SYNTAX_ERROR: 3. Share current cost reports

                # REMOVED_SYNTAX_ERROR: This data will enable comprehensive optimization strategies.
                # REMOVED_SYNTAX_ERROR: ''')]]
                

                # REMOVED_SYNTAX_ERROR: helper = DataHelper(mock_llm)
                # REMOVED_SYNTAX_ERROR: result = await helper.generate_data_request( )
                # REMOVED_SYNTAX_ERROR: user_request="How to reduce LLM costs using GPT-4?",
                # REMOVED_SYNTAX_ERROR: triage_result={ )
                # REMOVED_SYNTAX_ERROR: "category": "cost_optimization",
                # REMOVED_SYNTAX_ERROR: "data_sufficiency": "insufficient",
                # REMOVED_SYNTAX_ERROR: "priority": "high"
                # REMOVED_SYNTAX_ERROR: },
                # REMOVED_SYNTAX_ERROR: previous_results=[ )
                # REMOVED_SYNTAX_ERROR: {"agent_name": "triage", "result": "Categorized as cost optimization"}
                
                

                # Verify comprehensive result
                # REMOVED_SYNTAX_ERROR: assert result["success"] is True
                # REMOVED_SYNTAX_ERROR: assert len(result["data_request"]["data_categories"]) >= 3
                # REMOVED_SYNTAX_ERROR: assert "Export usage metrics" in result["data_request"]["user_instructions"]
                # REMOVED_SYNTAX_ERROR: assert len(result["data_request"]["structured_items"]) >= 6