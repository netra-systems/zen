"""
ClickHouse Metrics Aggregation Tests
Tests LLM metrics and performance metrics aggregation
"""

from datetime import datetime, timedelta
from typing import Dict, List
import random
import uuid
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from netra_backend.app.db.clickhouse_query_fixer import (
    fix_clickhouse_array_syntax,
    validate_clickhouse_query,
)
from netra_backend.app.monitoring.metrics_collector import PerformanceMetric

class TestLLMMetricsAggregation:

    """Test LLM-specific metrics and optimizations"""
    
    def _get_llm_models(self) -> List[str]:

        """Get list of LLM models for testing"""

        return [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "claude-3", "gemini-pro"]

    def _get_workload_types(self) -> List[str]:

        """Get list of workload types for testing"""

        return ["chat", "completion", "embedding", "analysis"]

    def _get_temperature_options(self) -> List[float]:

        """Get temperature options for testing"""

        return [0.0, 0.3, 0.7, 1.0]

    def _create_single_metric(self, i: int, count: int, models: List[str]) -> Dict:

        """Create a single metric record"""

        workload_types = self._get_workload_types()

        temp_options = self._get_temperature_options()

        return {

            "timestamp": datetime.now() - timedelta(minutes=count-i),

            "model": random.choice(models),

            "request_id": str(uuid.uuid4()),

            "input_tokens": random.randint(100, 2000),

            "output_tokens": random.randint(50, 1000),

            "latency_ms": random.uniform(500, 5000),

            "cost_cents": random.uniform(0.1, 5.0),

            "success": random.random() > 0.05,

            "temperature": random.choice(temp_options),

            "user_id": random.randint(1, 50),

            "workload_type": random.choice(workload_types)

        }

    def generate_llm_metrics(self, count: int) -> List[Dict]:

        """Generate realistic LLM metrics"""

        models = self._get_llm_models()

        metrics = []

        for i in range(count):

            metric = self._create_single_metric(i, count, models)

            metrics.append(metric)

        return metrics
    
    def _create_model_costs_cte(self):

        """Create model costs CTE portion of optimization query"""

        return """

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

        )"""

    def _create_optimization_opportunities_cte(self):

        """Create optimization opportunities CTE"""

        return """,

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

        )"""

    def _create_final_select_query(self):

        """Create final SELECT for optimization query"""

        return """

        SELECT * FROM optimization_opportunities

        WHERE potential_savings > 0

        ORDER BY potential_savings DESC

        """

    def _build_complete_optimization_query(self):

        """Build complete LLM cost optimization query"""

        model_costs = self._create_model_costs_cte()

        opportunities = self._create_optimization_opportunities_cte()

        final_select = self._create_final_select_query()

        return model_costs + opportunities + final_select

    def _validate_optimization_query(self, query):

        """Validate the LLM optimization query"""

        is_valid, error = validate_clickhouse_query(query)

        assert is_valid, f"LLM optimization query failed: {error}"

    def test_llm_cost_optimization_query(self):

        """Test query for LLM cost optimization analysis"""

        query = self._build_complete_optimization_query()

        self._validate_optimization_query(query)

    def _get_usage_patterns_query(self):

        """Get LLM usage patterns analysis query"""

        return """

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

        """

    def _validate_usage_patterns_query(self, query):

        """Validate usage patterns query"""

        is_valid, error = validate_clickhouse_query(query)

        assert is_valid

    async def test_llm_usage_patterns(self):

        """Test LLM usage pattern analysis"""

        query = self._get_usage_patterns_query()

        self._validate_usage_patterns_query(query)

class TestPerformanceMetricsWithClickHouse:

    """Test performance metrics extraction from ClickHouse"""
    
    def test_metrics_extraction_with_arrays(self):

        """Test extracting metrics from nested arrays"""

        query = """

        WITH parsed_metrics AS (

            SELECT 

                timestamp,

                user_id,

                workload_id,

                arrayFirstIndex(x -> x = 'gpu_utilization', metrics.name) as gpu_idx,

                arrayFirstIndex(x -> x = 'memory_usage', metrics.name) as mem_idx,

                arrayFirstIndex(x -> x = 'throughput', metrics.name) as tput_idx,

                IF(gpu_idx > 0, arrayElement(metrics.value, gpu_idx), 0) as gpu_util,

                IF(mem_idx > 0, arrayElement(metrics.value, mem_idx), 0) as memory_mb,

                IF(tput_idx > 0, arrayElement(metrics.value, tput_idx), 0) as throughput

            FROM workload_events

            WHERE timestamp >= now() - INTERVAL 1 HOUR

        )

        SELECT 

            toStartOfMinute(timestamp) as minute,

            avg(gpu_util) as avg_gpu,

            max(memory_mb) as max_memory,

            sum(throughput) as total_throughput

        FROM parsed_metrics

        GROUP BY minute

        ORDER BY minute DESC

        """
        
        # Fix any array syntax issues

        fixed_query = fix_clickhouse_array_syntax(query)
        
        # Validate the fixed query

        is_valid, error = validate_clickhouse_query(fixed_query)

        assert is_valid, f"Metrics extraction query failed: {error}"
        
        # Ensure proper array functions are used

        assert "arrayFirstIndex" in fixed_query

        assert "arrayElement" in fixed_query

        assert "metrics.value[" not in fixed_query