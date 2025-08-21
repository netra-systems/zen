"""
Data operations tests for Data Sub Agent
Focuses on data transformation and enrichment
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent

# Add project root to path


class TestDataTransformation:
    """Test data transformation capabilities"""
    @pytest.mark.asyncio
    async def test_transform_text_data(self):
        """Test transformation of text data"""
        mock_llm_manager = Mock()
        mock_tool_dispatcher = Mock()
        
        with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager'):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        input_data = {
            "type": "text",
            "content": "Hello World",
            "format": "plain"
        }
        
        result = await agent._transform_data(input_data)
        
        assert result != None
        assert "transformed" in result
        assert result["type"] == "text"

    @pytest.mark.asyncio
    async def test_transform_json_data(self):
        """Test transformation of JSON data"""
        mock_llm_manager = Mock()
        mock_tool_dispatcher = Mock()
        
        with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager'):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        input_data = {
            "type": "json",
            "content": '{"key": "value"}',
            "format": "json"
        }
        
        result = await agent._transform_data(input_data)
        
        assert result != None
        assert "parsed" in result
        assert result["parsed"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_transform_with_pipeline(self):
        """Test transformation with processing pipeline"""
        mock_llm_manager = Mock()
        mock_tool_dispatcher = Mock()
        
        with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager'):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        pipeline = [
            {"operation": "normalize"},
            {"operation": "enrich"},
            {"operation": "validate"}
        ]
        
        input_data = {
            "content": "test data",
            "pipeline": pipeline
        }
        
        with patch.object(agent, '_apply_operation', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {"processed": True}
            
            result = await agent._transform_with_pipeline(input_data, pipeline)
            
        assert mock_op.call_count == 3


class TestDataEnrichment:
    """Test data enrichment functionality"""
    @pytest.mark.asyncio
    async def test_enrich_with_metadata(self):
        """Test data enrichment with metadata"""
        mock_llm_manager = Mock()
        mock_tool_dispatcher = Mock()
        
        with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager'):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        input_data = {
            "content": "raw data",
            "source": "api"
        }
        
        enriched = await agent.enrich_data(input_data)
        
        assert "metadata" in enriched
        assert "timestamp" in enriched["metadata"]
        assert "source" in enriched["metadata"]
        assert enriched["metadata"]["source"] == "api"

    @pytest.mark.asyncio
    async def test_enrich_with_external_source(self):
        """Test enrichment with external data source"""
        mock_llm_manager = Mock()
        mock_tool_dispatcher = Mock()
        
        with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager'):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        # The enrich_data method handles external enrichment internally
        input_data = {"id": "123", "enrich": True}
        enriched = await agent.enrich_data(input_data, external=True)
        
        # Check that external enrichment adds the additional data
        assert "additional" in enriched
        assert enriched["additional"] == "data"
        assert "metadata" in enriched
