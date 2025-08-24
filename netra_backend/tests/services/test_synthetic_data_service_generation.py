"""
Data Generation Engine Test Suite for Synthetic Data Service
Testing synthetic data generation core functionality
"""

import sys
from pathlib import Path

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest

from netra_backend.app.services.synthetic_data_service import SyntheticDataService
from netra_backend.tests.services.test_synthetic_data_service_fixtures import GenerationConfig

# ==================== Test Suite: Data Generation Engine ====================

class TestDataGenerationEngine:
    """Test synthetic data generation core functionality"""
    @pytest.mark.asyncio
    async def test_workload_distribution_generation(self, generation_service, generation_config):
        """Test generating data with specified workload distribution"""
        records = await generation_service.generate_synthetic_data(
            generation_config,
            corpus_id="test_corpus"
        )
        
        # Check distribution matches configuration
        workload_counts = {}
        for record in records:
            workload_type = record["workload_type"]
            workload_counts[workload_type] = workload_counts.get(workload_type, 0) + 1
        
        for workload, expected_ratio in generation_config.workload_distribution.items():
            actual_ratio = workload_counts.get(workload, 0) / len(records)
            assert abs(actual_ratio - expected_ratio) < 0.05  # 5% tolerance
    @pytest.mark.asyncio
    async def test_temporal_pattern_generation(self, generation_service):
        """Test generating data with realistic temporal patterns"""
        config = GenerationConfig(
            num_traces=1000,
            time_window_hours=168,  # 1 week
            temporal_pattern="business_hours"
        )
        
        records = await generation_service.generate_with_temporal_patterns(config)
        
        # Verify business hours have higher density
        business_hours_count = sum(
            1 for r in records 
            if 9 <= r["timestamp"].hour <= 17 and r["timestamp"].weekday() < 5
        )
        
        assert business_hours_count > len(records) * 0.6  # Most traffic during business hours
    @pytest.mark.asyncio
    async def test_tool_invocation_patterns(self, generation_service):
        """Test generating realistic tool invocation patterns"""
        patterns = await generation_service.generate_tool_invocations(
            num_invocations=100,
            pattern="sequential_chain"
        )
        
        # Verify sequential pattern
        for i in range(len(patterns) - 1):
            current = patterns[i]
            next_inv = patterns[i + 1]
            # Output of current should be input to next
            assert current["trace_id"] == next_inv["trace_id"]
            assert current["end_time"] <= next_inv["start_time"]
    @pytest.mark.asyncio
    async def test_error_scenario_generation(self, generation_service):
        """Test generating error scenarios and failures"""
        config = GenerationConfig(
            num_traces=100,
            error_rate=0.15,
            error_patterns=["timeout", "rate_limit", "invalid_input"]
        )
        
        records = await generation_service.generate_with_errors(config)
        
        error_count = sum(1 for r in records if r.get("status") == "failed")
        error_rate = error_count / len(records)
        
        assert 0.10 <= error_rate <= 0.20  # Within expected range
        
        # Check error types
        error_types = [r.get("error_type") for r in records if r.get("status") == "failed"]
        assert all(et in config.error_patterns for et in error_types)
    @pytest.mark.asyncio
    async def test_trace_hierarchy_generation(self, generation_service):
        """Test generating valid trace and span hierarchies"""
        traces = await generation_service.generate_trace_hierarchies(
            num_traces=10,
            max_depth=3,
            max_branches=5
        )
        
        for trace in traces:
            # Verify parent-child relationships
            spans = trace["spans"]
            span_map = {s["span_id"]: s for s in spans}
            
            for span in spans:
                if span["parent_span_id"]:
                    parent = span_map.get(span["parent_span_id"])
                    assert parent != None
                    # Child span must be within parent time bounds
                    assert span["start_time"] >= parent["start_time"]
                    assert span["end_time"] <= parent["end_time"]
    @pytest.mark.asyncio
    async def test_domain_specific_generation(self, generation_service):
        """Test domain-specific data generation"""
        domains = ["e-commerce", "healthcare", "finance"]
        
        for domain in domains:
            config = GenerationConfig(
                num_traces=100,
                domain_focus=domain
            )
            
            records = await generation_service.generate_domain_specific(config)
            
            # Verify domain-specific fields
            if domain == "e-commerce":
                assert all("cart_value" in r["metadata"] for r in records)
            elif domain == "healthcare":
                assert all("patient_id" in r["metadata"] for r in records)
            elif domain == "finance":
                assert all("transaction_amount" in r["metadata"] for r in records)
    @pytest.mark.asyncio
    async def test_statistical_distribution_generation(self, generation_service):
        """Test generating data with specific statistical distributions"""
        distributions = ["normal", "exponential", "uniform", "bimodal"]
        
        for dist in distributions:
            config = GenerationConfig(
                num_traces=1000,
                latency_distribution=dist
            )
            
            records = await generation_service.generate_with_distribution(config)
            latencies = [r["latency_ms"] for r in records]
            
            # Verify distribution characteristics
            if dist == "normal":
                # Should follow bell curve
                mean = sum(latencies) / len(latencies)
                within_std = sum(1 for l in latencies if abs(l - mean) < 100)
                assert within_std > len(latencies) * 0.68  # ~68% within 1 std
    @pytest.mark.asyncio
    async def test_custom_tool_catalog_generation(self, generation_service):
        """Test generation with custom tool catalog"""
        custom_tools = [
            {"name": "custom_api", "latency_ms": [100, 500], "failure_rate": 0.02},
            {"name": "ml_model", "latency_ms": [1000, 5000], "failure_rate": 0.05},
            {"name": "database_query", "latency_ms": [20, 200], "failure_rate": 0.01}
        ]
        
        config = GenerationConfig(
            num_traces=100,
            tool_catalog=custom_tools
        )
        
        records = await generation_service.generate_with_custom_tools(config)
        
        # Verify custom tools are used
        tool_names = set()
        for record in records:
            if "tool_invocations" in record:
                tool_names.update(record["tool_invocations"])
        
        assert all(tool["name"] in tool_names for tool in custom_tools)
    @pytest.mark.asyncio
    async def test_incremental_generation(self, generation_service):
        """Test incremental data generation with checkpoints"""
        config = GenerationConfig(
            num_traces=10000,
            checkpoint_interval=1000
        )
        
        checkpoints = []
        
        async def checkpoint_callback(checkpoint_data):
            checkpoints.append(checkpoint_data)
        
        await generation_service.generate_incremental(
            config,
            checkpoint_callback=checkpoint_callback
        )
        
        assert len(checkpoints) == 10  # 10000 / 1000
        assert all(cp["records_generated"] % 1000 == 0 for cp in checkpoints)
    @pytest.mark.asyncio
    async def test_generation_with_corpus_sampling(self, generation_service):
        """Test generation using corpus content sampling"""
        corpus_content = [
            {"prompt": f"Prompt {i}", "response": f"Response {i}"}
            for i in range(100)
        ]
        
        config = GenerationConfig(
            num_traces=1000,
            corpus_sampling_strategy="weighted_random"
        )
        
        records = await generation_service.generate_from_corpus(
            config,
            corpus_content
        )
        
        # Verify corpus content is used
        prompts_used = set(r["prompt"] for r in records)
        assert len(prompts_used) > 50  # Should use variety of corpus content

# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])