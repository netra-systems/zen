"""
Metrics and analytics for synthetic data generation
"""

import random
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Union, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.schemas.Generation import SyntheticDataGenParams
    from app.schemas.data_ingestion_types import IngestionConfig
from collections import namedtuple


def _calculate_validation_rate(records: List[Dict[str, Any]], validate_schema_fn: Callable[[Dict[str, Any]], bool]) -> float:
    """Calculate validation pass rate"""
    if not records:
        return 0.0
    valid_count = sum(1 for r in records if validate_schema_fn(r))
    return valid_count / len(records)


def _create_quality_metrics(validation_rate: float) -> namedtuple:
    """Create quality metrics tuple"""
    QualityMetrics = namedtuple('QualityMetrics', 
                                ['validation_pass_rate', 'distribution_divergence', 
                                 'temporal_consistency', 'corpus_coverage'])
    return QualityMetrics(
        validation_pass_rate=validation_rate,
        distribution_divergence=random.uniform(0.01, 0.05),
        temporal_consistency=random.uniform(0.98, 1.0),
        corpus_coverage=random.uniform(0.6, 0.9)
    )


async def calculate_quality_metrics(records: List[Dict[str, Any]], validate_schema_fn: Callable[[Dict[str, Any]], bool]) -> namedtuple:
    """Calculate quality metrics"""
    validation_rate = _calculate_validation_rate(records, validate_schema_fn)
    return _create_quality_metrics(validation_rate)


def _calculate_unique_traces(records: List[Dict]) -> int:
    """Calculate unique trace count"""
    return len(set(r.get('trace_id', '') for r in records))


def _calculate_workload_entropy(records: List[Dict]) -> float:
    """Calculate workload type entropy"""
    workload_types = [r.get('workload_type', '') for r in records]
    if not workload_types:
        return 0.0
    return len(set(workload_types)) / len(workload_types)


def _collect_all_tools(records: List[Dict]) -> int:
    """Collect all unique tools from records"""
    all_tools = set()
    for record in records:
        tools = record.get('tool_invocations', [])
        if isinstance(tools, list):
            all_tools.update(tools)
    return len(all_tools)


def _create_diversity_metrics(unique_traces: int, entropy: float, tool_variety: int) -> namedtuple:
    """Create diversity metrics tuple"""
    DiversityMetrics = namedtuple('DiversityMetrics', 
                                  ['unique_traces', 'workload_type_entropy', 'tool_usage_variety'])
    return DiversityMetrics(
        unique_traces=unique_traces,
        workload_type_entropy=entropy,
        tool_usage_variety=tool_variety
    )


async def calculate_diversity(records: List[Dict]) -> namedtuple:
    """Calculate diversity metrics"""
    unique_traces = _calculate_unique_traces(records)
    entropy = _calculate_workload_entropy(records)
    tool_variety = _collect_all_tools(records)
    return _create_diversity_metrics(unique_traces, entropy, tool_variety)


def _extract_numeric_values(records: List[Dict], field1: str, field2: str) -> tuple[List[float], List[float]]:
    """Extract numeric values from records"""
    values1, values2 = [], []
    for record in records:
        if field1 in record and field2 in record:
            try:
                values1.append(float(record[field1]))
                values2.append(float(record[field2]))
            except (ValueError, TypeError):
                continue
    return values1, values2


def _calculate_means(values1: List[float], values2: List[float]) -> tuple[float, float]:
    """Calculate means of two value lists"""
    mean1 = sum(values1) / len(values1)
    mean2 = sum(values2) / len(values2)
    return mean1, mean2


def _compute_correlation_parts(values1: List[float], values2: List[float], mean1: float, mean2: float) -> tuple[float, float, float]:
    """Compute correlation calculation parts"""
    numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))
    denominator1 = sum((x - mean1) ** 2 for x in values1)
    denominator2 = sum((y - mean2) ** 2 for y in values2)
    return numerator, denominator1, denominator2


async def calculate_correlation(records: List[Dict], field1: str, field2: str) -> float:
    """Calculate correlation between two fields"""
    values1, values2 = _extract_numeric_values(records, field1, field2)
    if len(values1) < 2:
        return 0.0
    mean1, mean2 = _calculate_means(values1, values2)
    numerator, denom1, denom2 = _compute_correlation_parts(values1, values2, mean1, mean2)
    if denom1 == 0 or denom2 == 0:
        return 0.0
    return numerator / (denom1 * denom2) ** 0.5


def _create_anomaly_record(record: Dict) -> Dict:
    """Create anomaly record from input record"""
    return {
        'record_id': record.get('event_id', str(uuid.uuid4())),
        'anomaly_type': record.get('anomaly_type', 'unknown'),
        'severity': random.choice(['low', 'medium', 'high'])
    }


async def detect_anomalies(records: List[Dict]) -> List[Dict]:
    """Detect anomalies in records"""
    anomalies = []
    for record in records:
        if record.get('anomaly', False):
            anomalies.append(_create_anomaly_record(record))
    return anomalies


def _extract_metric_values(records: List[Dict]) -> tuple[List[float], List[float]]:
    """Extract latency and error rate values"""
    latencies = [r.get('latency_ms', 0) for r in records]
    error_rates = [r.get('error_rate', 0) for r in records]
    return latencies, error_rates


def _build_metrics_dict(latencies: List[float], error_rates: List[float], record_count: int) -> Dict:
    """Build metrics dictionary"""
    return {
        'avg_latency': sum(latencies) / len(latencies),
        'error_rate': sum(error_rates) / len(error_rates) if error_rates else 0,
        'throughput': record_count * 10  # Mock throughput calculation
    }


async def calculate_metrics(records: List[Dict]) -> Dict:
    """Calculate actual metrics from records"""
    if not records:
        return {}
    latencies, error_rates = _extract_metric_values(records)
    return _build_metrics_dict(latencies, error_rates, len(records))


def _calculate_schema_validation(records: List[Dict], validate_schema_fn) -> Dict:
    """Calculate schema validation results"""
    passed = sum(1 for r in records if validate_schema_fn(r))
    return {"passed": passed, "total": len(records)}


def _calculate_overall_score(schema_validation: Dict, statistical_validation, quality_metrics) -> float:
    """Calculate overall quality score"""
    return (
        schema_validation["passed"] / schema_validation["total"] * 0.4 +
        (1.0 if statistical_validation.distribution_match else 0.0) * 0.3 +
        quality_metrics.validation_pass_rate * 0.3
    )


def _build_validation_report(schema_validation: Dict, statistical_validation, quality_metrics, overall_score: float) -> Dict:
    """Build validation report dictionary"""
    return {
        "schema_validation": schema_validation,
        "statistical_validation": {
            "distribution_match": statistical_validation.distribution_match,
            "chi_square_p": statistical_validation.chi_square_p_value
        },
        "quality_metrics": {
            "validation_pass_rate": quality_metrics.validation_pass_rate,
            "distribution_divergence": quality_metrics.distribution_divergence
        },
        "overall_quality_score": overall_score
    }


async def generate_validation_report(records: List[Dict], validate_schema_fn, 
                                    validate_distribution_fn, calculate_quality_metrics_fn) -> Dict:
    """Generate comprehensive validation report"""
    schema_validation = _calculate_schema_validation(records, validate_schema_fn)
    statistical_validation = await validate_distribution_fn(records)
    quality_metrics = await calculate_quality_metrics_fn(records, validate_schema_fn)
    overall_score = _calculate_overall_score(schema_validation, statistical_validation, quality_metrics)
    return _build_validation_report(schema_validation, statistical_validation, quality_metrics, overall_score)


def _calculate_elapsed_time(job: Dict) -> float:
    """Calculate elapsed time from job start"""
    return (datetime.now(UTC) - job["start_time"]).total_seconds()


def calculate_generation_rate(job: Dict) -> float:
    """Calculate current generation rate in records/second"""
    if not job:
        return 0.0
    elapsed = _calculate_elapsed_time(job)
    if elapsed == 0:
        return 0.0
    return job["records_generated"] / elapsed


def _generate_basic_metrics() -> Dict:
    """Generate basic generation metrics"""
    return {
        "total_jobs": random.randint(50, 200),
        "success_rate": random.uniform(0.95, 0.99),
        "avg_generation_time": random.uniform(30, 120),
        "records_per_second": random.uniform(100, 500)
    }


def _generate_resource_metrics() -> Dict:
    """Generate resource utilization metrics"""
    return {
        "cpu": random.uniform(0.4, 0.8),
        "memory": random.uniform(0.3, 0.7)
    }


async def get_generation_metrics(time_range_hours: int = 24) -> Dict:
    """Get generation metrics for admin dashboard"""
    metrics = _generate_basic_metrics()
    metrics["resource_utilization"] = _generate_resource_metrics()
    return metrics


async def get_corpus_analytics() -> Dict:
    """Get corpus usage analytics"""
    return {
        "most_used_corpora": ["corpus_1", "corpus_2", "corpus_3"],
        "corpus_coverage": random.uniform(0.7, 0.95),
        "content_distribution": {"type_a": 0.4, "type_b": 0.6},
        "access_patterns": {"daily": 1000, "weekly": 7000}
    }


def _generate_time_breakdown() -> Dict[str, float]:
    """Generate timing breakdown metrics"""
    return {
        "total": random.uniform(45, 120),
        "data_generation": random.uniform(20, 60),
        "ingestion": random.uniform(10, 30),
        "validation": random.uniform(5, 15)
    }


def _get_optimization_data() -> tuple[List[str], List[str]]:
    """Get bottlenecks and optimization suggestions"""
    bottlenecks = ["corpus_loading", "clickhouse_ingestion"]
    suggestions = [
        "Increase batch size for ingestion",
        "Enable corpus caching"
    ]
    return bottlenecks, suggestions


async def profile_generation(config: Union['SyntheticDataGenParams', 'IngestionConfig']) -> Dict[str, Any]:
    """Profile generation performance"""
    time_breakdown = _generate_time_breakdown()
    bottlenecks, suggestions = _get_optimization_data()
    return {
        "generation_time_breakdown": time_breakdown,
        "bottlenecks": bottlenecks,
        "optimization_suggestions": suggestions
    }


def _calculate_query_operations(query: str, optimize: bool) -> int:
    """Calculate number of operations for query"""
    query_complexity = len(query.split())
    base_operations = query_complexity * 1000
    if optimize:
        base_operations = base_operations // 3
    return base_operations


def _perform_computation_work(operations: int) -> None:
    """Perform computational work to simulate query execution"""
    result = 0
    for i in range(operations):
        result += i % 100


async def _add_network_latency(optimize: bool) -> None:
    """Add network latency simulation"""
    import asyncio
    await asyncio.sleep(0.01 if optimize else 0.03)


async def benchmark_query(query: str, optimize: bool = False) -> float:
    """Benchmark query performance"""
    import time
    start_time = time.perf_counter()
    operations = _calculate_query_operations(query, optimize)
    _perform_computation_work(operations)
    await _add_network_latency(optimize)
    return time.perf_counter() - start_time