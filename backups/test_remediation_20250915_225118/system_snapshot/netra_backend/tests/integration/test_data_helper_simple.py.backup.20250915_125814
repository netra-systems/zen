"""
Simple Data Helper Integration Test - Validates test structure without real services

This test validates that the data helper module works correctly with mocked dependencies.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.tools.data_helper import DataHelper, create_data_helper


class TestDataHelperSimple:
    """Simple test to validate data helper functionality."""
    
    @pytest.mark.asyncio
    async def test_data_helper_basic_functionality(self):
        """Test basic data helper functionality with mocks."""
        # Create mock LLM manager
        mock_llm = AsyncMock()
        mock_response = AsyncMock()
        mock_response.generations = [[AsyncMock()]]
        mock_response.generations[0][0].text = """
**Required Data Sources**

[Cost Data]
- Monthly spending breakdown
  Justification: Essential for cost optimization

[Performance Data]  
- Response time metrics
  Justification: Needed for performance optimization

**Instructions**
Please provide the requested data for analysis.
"""
        mock_llm.agenerate.return_value = mock_response
        
        # Create data helper
        data_helper = create_data_helper(mock_llm)
        
        # Test data request generation
        result = await data_helper.generate_data_request(
            user_request="Help me optimize my AI costs",
            triage_result={
                "category": "Cost Optimization",
                "priority": "high",
                "data_sufficiency": "insufficient"
            },
            previous_results=None
        )
        
        # Validate result
        assert result["success"] is True
        assert "data_request" in result
        assert result["user_request"] == "Help me optimize my AI costs"
        assert result["triage_context"]["category"] == "Cost Optimization"
        
        # Validate data extraction
        data_request = result["data_request"]
        assert "raw_response" in data_request
        assert "data_categories" in data_request
        assert len(data_request["data_categories"]) >= 2
        assert "user_instructions" in data_request
        
        print("Basic data helper test passed")
    
    @pytest.mark.asyncio
    async def test_data_helper_error_handling(self):
        """Test data helper error handling."""
        # Create mock LLM that fails
        mock_llm = AsyncMock()
        mock_llm.agenerate.side_effect = Exception("LLM service unavailable")
        
        # Create data helper
        data_helper = create_data_helper(mock_llm)
        
        # Test error handling
        result = await data_helper.generate_data_request(
            user_request="Optimize my system",
            triage_result={"category": "General"},
            previous_results=None
        )
        
        # Validate error handling
        assert result["success"] is False
        assert "error" in result
        assert "fallback_message" in result
        assert "LLM service unavailable" in result["error"]
        assert "provide optimization recommendations" in result["fallback_message"]
        
        print("Error handling test passed")
    
    @pytest.mark.asyncio
    async def test_data_helper_with_previous_results(self):
        """Test data helper with previous agent results."""
        # Create mock LLM
        mock_llm = AsyncMock()
        mock_response = AsyncMock()
        mock_response.generations = [[AsyncMock()]]
        mock_response.generations[0][0].text = "Data request based on previous results"
        mock_llm.agenerate.return_value = mock_response
        
        # Create data helper
        data_helper = create_data_helper(mock_llm)
        
        # Test with previous results
        previous_results = [
            {"agent_name": "Cost Analyzer", "summary": "High GPU costs detected"},
            {"agent_name": "Performance Agent", "result": "Latency spikes observed"}
        ]
        
        result = await data_helper.generate_data_request(
            user_request="Help with optimization",
            triage_result={"category": "Optimization"},
            previous_results=previous_results
        )
        
        # Validate result incorporates previous context
        assert result["success"] is True
        
        # Check that LLM was called with formatted previous results
        call_args = mock_llm.agenerate.call_args
        prompt = call_args[1]["prompts"][0]
        assert "Cost Analyzer: High GPU costs detected" in prompt
        assert "Performance Agent: Latency spikes observed" in prompt
        
        print("Previous results test passed")


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(TestDataHelperSimple().test_data_helper_basic_functionality())
    asyncio.run(TestDataHelperSimple().test_data_helper_error_handling())
    asyncio.run(TestDataHelperSimple().test_data_helper_with_previous_results())
    print("\nAll simple data helper tests passed!")