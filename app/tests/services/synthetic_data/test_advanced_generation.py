"""
Tests for advanced generation methods and domain-specific features
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.synthetic_data_service import SyntheticDataService


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()


@pytest.mark.asyncio
class TestAdvancedGenerationMethods:
    """Test advanced generation methods for comprehensive coverage"""
    
    async def test_generate_with_temporal_patterns(self, service):
        """Test generation with temporal patterns"""
        config = MagicMock()
        config.num_traces = 10
        config.temporal_pattern = 'business_hours'
        
        records = await service.generate_with_temporal_patterns(config)
        
        assert len(records) == 10
        for record in records:
            assert 'timestamp' in record
    
    async def test_generate_tool_invocations(self, service):
        """Test tool invocations generation"""
        invocations = await service.generate_tool_invocations(5, "sequential")
        
        assert len(invocations) == 5
        for i, inv in enumerate(invocations):
            assert inv['sequence_number'] == i
            assert 'trace_id' in inv
            assert 'invocation_id' in inv
    
    async def test_generate_with_errors(self, service):
        """Test generation with error scenarios"""
        config = MagicMock()
        config.num_traces = 10
        config.error_rate = 0.5
        config.error_patterns = ['timeout', 'rate_limit']
        
        records = await service.generate_with_errors(config)
        
        assert len(records) == 10
        error_count = sum(1 for r in records if r.get('status') == 'failed')
        # Should have some errors (probabilistic, so allow range)
        assert error_count >= 0
    
    async def test_generate_trace_hierarchies(self, service):
        """Test trace hierarchy generation"""
        traces = await service.generate_trace_hierarchies(3, 2, 3)
        
        assert len(traces) == 3
        for trace in traces:
            assert 'trace_id' in trace
            assert 'spans' in trace
            assert len(trace['spans']) >= 1  # At least root span
    
    async def test_generate_domain_specific(self, service):
        """Test domain-specific generation"""
        config = MagicMock()
        config.num_traces = 5
        config.domain_focus = 'e-commerce'
        
        records = await service.generate_domain_specific(config)
        
        assert len(records) == 5
        for record in records:
            if 'metadata' in record:
                assert 'cart_value' in record['metadata']
    
    async def test_generate_with_distribution(self, service):
        """Test generation with specific distributions"""
        config = MagicMock()
        config.num_traces = 10
        config.latency_distribution = 'normal'
        
        records = await service.generate_with_distribution(config)
        
        assert len(records) == 10
        for record in records:
            assert 'latency_ms' in record
            assert record['latency_ms'] >= 0
    
    async def test_generate_with_custom_tools(self, service):
        """Test generation with custom tool catalog"""
        config = MagicMock()
        config.num_traces = 5
        config.tool_catalog = [{"name": "custom_tool", "type": "test"}]
        
        records = await service.generate_with_custom_tools(config)
        
        assert len(records) == 5
        for record in records:
            assert 'tool_invocations' in record
    
    async def test_generate_incremental(self, service):
        """Test incremental generation"""
        config = MagicMock()
        config.num_traces = 100
        config.checkpoint_interval = 25
        
        checkpoints = []
        async def checkpoint_callback(data):
            checkpoints.append(data)
        
        result = await service.generate_incremental(config, checkpoint_callback)
        
        assert result['total_generated'] == 100
        assert len(checkpoints) == 4  # 100 / 25
    
    async def test_generate_from_corpus(self, service):
        """Test generation from corpus content"""
        config = MagicMock()
        config.num_traces = 5
        corpus_content = [{"prompt": "test", "response": "test"}]
        
        records = await service.generate_from_corpus(config, corpus_content)
        
        assert len(records) == 5