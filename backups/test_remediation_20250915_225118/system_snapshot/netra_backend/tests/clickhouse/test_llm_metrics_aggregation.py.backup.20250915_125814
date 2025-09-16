from unittest.mock import Mock, patch, MagicMock
import asyncio

"""
LLM Metrics Aggregation Tests
Test LLM-specific metrics and optimizations
"""""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import IsolatedEnvironment


# Test framework import - using pytest fixtures instead

import pytest

from netra_backend.app.db.clickhouse_query_fixer import validate_clickhouse_query
# Mock fixtures for missing imports
@pytest.fixture
def llm_metrics_batch():
    """Mock fixture for LLM metrics batch data"""
    return {
"model": LLMModel.GEMINI_2_5_FLASH.value,
"workload_type": "analysis",
"latency_ms": 150,
"cost_cents": 5,
"success": True
}

def generate_llm_metrics():
    """Mock function for generating LLM metrics"""
    return [
{
"model": LLMModel.GEMINI_2_5_FLASH.value,
"workload_type": "analysis",
"latency_ms": 150,
"cost_cents": 5,
"success": True
}
]

class TestLLMMetricsAggregation:
    """Test LLM-specific metrics and optimizations"""

    def test_llm_cost_optimization_query(self):
        """Test query for LLM cost optimization analysis"""
        query = """
        WITH model_costs AS (
        SELECT 
        model,
        workload_type,
        avg(cost_cents) as avg_cost,
        avg(latency_ms) as avg_latency,
        quantile(0.95)(latency_ms) as p95_latency,
        sum(input_tokens + output_tokens) as total_tokens,
        count() as request_count,
        sum(cost_cents) as total_cost
        FROM llm_events
        WHERE timestamp >= now() - INTERVAL 7 DAY
        AND success = true
        GROUP BY model, workload_type
        ),
        optimization_opportunities AS (
        SELECT 
        workload_type,
        model as current_model,
        avg_cost as current_avg_cost,
        avg_latency as current_avg_latency,
        (SELECT model FROM model_costs mc2 
        WHERE mc2.workload_type = mc1.workload_type 
        AND mc2.avg_cost < mc1.avg_cost
        AND mc2.p95_latency < mc1.p95_latency * 1.2
        ORDER BY mc2.avg_cost ASC
        LIMIT 1) as recommended_model,
        (current_avg_cost - 
        (SELECT avg_cost FROM model_costs mc3 
        WHERE mc3.workload_type = mc1.workload_type 
        AND mc3.avg_cost < mc1.avg_cost
        ORDER BY mc3.avg_cost ASC
        LIMIT 1)) * request_count as potential_savings
        FROM model_costs mc1
        WHERE request_count > 100
        )
        SELECT * FROM optimization_opportunities
        WHERE potential_savings > 0
        ORDER BY potential_savings DESC
        """""

        # This complex query should be valid
        is_valid, error = validate_clickhouse_query(query)
        assert is_valid, f"LLM optimization query failed: {error}"

        @pytest.mark.asyncio
        async def test_llm_usage_patterns(self):
            """Test LLM usage pattern analysis"""
            query = """
            SELECT 
            toHour(timestamp) as hour,
            model,
            workload_type,
            count() as requests,
            avg(latency_ms) as avg_latency,
            sum(cost_cents) as total_cost,
            avg(temperature) as avg_temperature,
            sum(input_tokens) as total_input_tokens,
            sum(output_tokens) as total_output_tokens
            FROM llm_events
            WHERE timestamp >= now() - INTERVAL 24 HOUR
            GROUP BY hour, model, workload_type
            ORDER BY hour DESC, total_cost DESC
            """""

            is_valid, error = validate_clickhouse_query(query)
            assert is_valid

            def test_llm_performance_benchmarking(self, llm_metrics_batch):
                """Test LLM performance benchmarking queries"""
        # Simulate performance comparison query
                performance_query = """
                WITH model_performance AS (
                SELECT 
                model,
                workload_type,
                avg(latency_ms) as avg_latency,
                quantile(0.5)(latency_ms) as median_latency,
                quantile(0.95)(latency_ms) as p95_latency,
                quantile(0.99)(latency_ms) as p99_latency,
                stddevPop(latency_ms) as latency_stddev,
                countIf(success = false) / count() as error_rate,
                avg(input_tokens + output_tokens) as avg_tokens
                FROM llm_events
                WHERE timestamp >= now() - INTERVAL 7 DAY
                GROUP BY model, workload_type
                HAVING count() > 50
                )
                SELECT 
                workload_type,
                model,
                avg_latency,
                p95_latency,
                error_rate,
                avg_tokens,
                -- Performance ranking within workload type
                rank() OVER (PARTITION BY workload_type ORDER BY avg_latency ASC) as latency_rank,
                rank() OVER (PARTITION BY workload_type ORDER BY error_rate ASC) as reliability_rank
                FROM model_performance
                ORDER BY workload_type, latency_rank
                """""

                is_valid, error = validate_clickhouse_query(performance_query)
                assert is_valid, f"Performance benchmarking query failed: {error}"

                def test_llm_token_efficiency_analysis(self):
                    """Test token efficiency analysis across models"""
                    efficiency_query = """
                    SELECT 
                    model,
                    workload_type,
                    avg(output_tokens / nullIf(input_tokens, 0)) as output_input_ratio,
                    avg(cost_cents / nullIf(output_tokens, 0)) as cost_per_output_token,
                    avg(latency_ms / nullIf(output_tokens, 0)) as latency_per_output_token,
                    sum(output_tokens) as total_output_generated,
                    countIf(output_tokens > input_tokens * 2) as verbose_responses,
                    count() as total_requests
                    FROM llm_events
                    WHERE timestamp >= now() - INTERVAL 7 DAY
                    AND success = true
                    AND input_tokens > 0
                    AND output_tokens > 0
                    GROUP BY model, workload_type
                    HAVING total_requests > 20
                    ORDER BY cost_per_output_token ASC
                    """""

                    is_valid, error = validate_clickhouse_query(efficiency_query)
                    assert is_valid, f"Token efficiency query failed: {error}"

                    def test_llm_user_behavior_analysis(self):
                        """Test user behavior analysis with LLM usage"""
                        behavior_query = """
                        WITH user_sessions AS (
                        SELECT 
                        user_id,
                        toDate(timestamp) as date,
                        count() as requests_per_day,
                        sum(cost_cents) as daily_cost,
                        avg(temperature) as avg_temperature,
                        uniq(model) as models_used,
                        uniq(workload_type) as workload_types_used,
                        sum(input_tokens + output_tokens) as daily_tokens
                        FROM llm_events
                        WHERE timestamp >= now() - INTERVAL 30 DAY
                        GROUP BY user_id, date
                        )
                        SELECT 
                        user_id,
                        avg(requests_per_day) as avg_daily_requests,
                        sum(daily_cost) as total_cost_30d,
                        avg(daily_cost) as avg_daily_cost,
                        max(models_used) as max_models_per_day,
                        sum(daily_tokens) as total_tokens_30d,
                        count() as active_days
                        FROM user_sessions
                        GROUP BY user_id
                        HAVING active_days >= 5
                        ORDER BY total_cost_30d DESC
                        """""

                        is_valid, error = validate_clickhouse_query(behavior_query)
                        assert is_valid, f"User behavior analysis query failed: {error}"

                        def test_llm_quality_metrics(self):
                            """Test LLM output quality metrics"""
                            quality_query = """
                            SELECT 
                            model,
                            workload_type,
                            countIf(success = true) / count() as success_rate,
                            avg(length(input_text)) as avg_input_length,
                            avg(length(output_text)) as avg_output_length,
                            avgIf(length(output_text), success = true) as avg_successful_output_length,
                            countIf(length(output_text) < 10 AND success = true) as short_responses,
                            countIf(length(output_text) > 5000 AND success = true) as long_responses,
                            sum(input_tokens + output_tokens) / count() as avg_total_tokens_per_request
                            FROM llm_events
                            WHERE timestamp >= now() - INTERVAL 7 DAY
                            GROUP BY model, workload_type
                            HAVING count() > 10
                            ORDER BY success_rate DESC, avg_total_tokens_per_request ASC
                            """""

                            is_valid, error = validate_clickhouse_query(quality_query)
                            assert is_valid, f"Quality metrics query failed: {error}"