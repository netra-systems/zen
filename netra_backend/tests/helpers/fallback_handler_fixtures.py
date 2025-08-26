"""
Test fixtures for fallback handler tests
Provides reusable test data, metadata objects, and mock configurations
"""

from typing import Any, Dict, List, Tuple
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest

from netra_backend.app.core.fallback_handler import FallbackHandler, FallbackMetadata

@pytest.fixture
def fallback_handler():
    """Create FallbackHandler instance"""
    return FallbackHandler()

@pytest.fixture
def sample_metadata():
    """Create sample fallback metadata"""
    return FallbackMetadata(
        error_type="ValidationError",
        error_message="Quality score below threshold",
        agent_name="optimization_agent",
        user_input="Optimize my GPU workload for better performance",
        partial_data={
            "metrics": {"latency": 150, "throughput": 1200},
            "bottlenecks": ["memory_bandwidth", "compute_utilization"],
            "recommendations": ["Enable KV cache", "Use tensor parallelism"]
        },
        attempted_operations=["analyze_workload", "identify_bottlenecks"],
        stacktrace="File test.py, line 42, in optimize_gpu"
    )

@pytest.fixture
def data_failure_metadata():
    """Create metadata for data failure tests"""
    return FallbackMetadata(
        error_type="ConnectionError",
        error_message="Database connection timeout",
        agent_name="data_agent",
        user_input="Analyze system performance data",
        partial_data={
            "source": "performance_database",
            "collected_rows": 1250,
            "tables": ["metrics", "logs"]
        }
    )

@pytest.fixture
def report_failure_metadata():
    """Create metadata for report failure tests"""
    return FallbackMetadata(
        error_type="TemplateError",
        error_message="Report template compilation failed",
        agent_name="reporting_agent",
        user_input="Generate monthly performance report",
        partial_data={
            "summary": "System performance analysis complete",
            "metrics": {"cpu": 75, "memory": 68, "disk": 45},
            "findings": ["High CPU during peak hours", "Memory usage trending up"]
        }
    )

@pytest.fixture
def llm_failure_metadata():
    """Create metadata for LLM failure tests"""
    return FallbackMetadata(
        error_type="APIError",
        error_message="OpenAI API rate limit exceeded",
        agent_name="generation_agent",
        user_input="Explain quantum computing basics",
        partial_data={
            "model": LLMModel.GEMINI_2_5_FLASH.value,
            "operation": "text_generation",
            "tokens": 450
        }
    )

@pytest.fixture
def validation_failure_metadata():
    """Create metadata for validation failure tests"""
    return FallbackMetadata(
        error_type="QualityError",
        error_message="Output quality score too low",
        agent_name="optimization_agent",
        user_input="Improve model inference speed",
        partial_data={
            "quality_issues": ["Too many generic phrases", "Lack of specific metrics"],
            "quality_score": 0.35,
            "threshold": 0.7
        }
    )

@pytest.fixture
def domain_detection_test_cases():
    """Test cases for domain detection"""
    return [
        ("optimize model latency", "model optimization"),
        ("reduce training time", "training"),
        ("deploy to production", "deployment"),
        ("analyze cost breakdown", "cost"),
        ("improve performance metrics", "performance"),
        ("debug memory issues", "debugging"),
        ("design new architecture", "architecture"),
        ("process large dataset", "data")
    ]

@pytest.fixture
def error_reason_test_cases():
    """Test cases for error reason extraction"""
    return [
        ("ValueError: Invalid input format", "Invalid input format"),
        ("ConnectionError: Database timeout after 30s\nStack trace...", "Database timeout after 30s"),
        ("Very long error message " + "x" * 200, "Very long error message " + "x" * 77 + "..."),
        ("TimeoutError: Operation timed out", "Operation timed out"),
    ]

@pytest.fixture
def partial_data_test_cases():
    """Test cases for partial data formatting"""
    return [
        (None, "Initial analysis suggests this is an optimization-related query"),
        ({}, "Partial analysis completed"),
        ({"count": 42}, "- count: 42"),
        ({"items": [1, 2, 3, 4, 5]}, "- items: 5 items collected"),
        ({"config": {"batch_size": 32, "lr": 0.001}}, "- config: Data structure with 2 fields"),
        ({"mixed": "value", "list": [1, 2], "dict": {"a": 1}}, 
         "- mixed: value\n- list: 2 items collected\n- dict: Data structure with 1 fields")
    ]

@pytest.fixture
def summarize_data_test_cases():
    """Test cases for data summarization"""
    return [
        (None, "No data was successfully collected before the error"),
        ({"metrics": [1, 2, 3], "logs": [{"a": 1}, {"b": 2}]}, 
         "Collected 5 total items: 3 metrics, 2 logs entries"),
        ({"single": "value"}, "Some preliminary data was collected"),
        ({"empty_list": [], "empty_dict": {}}, "Some preliminary data was collected")
    ]

@pytest.fixture
def data_source_test_cases():
    """Test cases for data source extraction"""
    return [
        (FallbackMetadata("", "", partial_data={"source": "redis_cache"}), "redis_cache"),
        (FallbackMetadata("", "Database connection failed", partial_data=None), "database"),
        (FallbackMetadata("", "API endpoint returned 500", partial_data=None), "API endpoint"),
        (FallbackMetadata("", "File not found error", partial_data=None), "file system"),
        (FallbackMetadata("", "Unknown error", partial_data=None), "data source")
    ]

@pytest.fixture
def alternative_sources_test_cases():
    """Test cases for alternative source suggestions"""
    return [
        ("database", ["Cache layer", "Read replica", "Data warehouse"]),
        ("API endpoint", ["Alternative API", "GraphQL", "Webhook"]),
        ("file system", ["Object storage", "Database export", "API data"]),
        ("unknown_source", ["Manual data export", "Alternative API", "Cached results"])
    ]

@pytest.fixture
def limitation_test_cases():
    """Test cases for limitation identification"""
    return [
        ("Operation timeout after 30 seconds", "processing timeout"),
        ("Out of memory error occurred", "memory constraints"),
        ("Rate limit exceeded: 429", "rate limiting"),
        ("Permission denied: insufficient privileges", "permission restrictions"),
        ("Connection refused by server", "connection issues"),
        ("Unknown error occurred", "technical constraints")
    ]

@pytest.fixture
def optimization_results_test_cases():
    """Test cases for optimization results formatting"""
    return [
        (None, "Initial optimization scan completed"),
        ({}, "Preliminary analysis completed"),
        ({"metrics": "latency, throughput"}, "Metrics analyzed: latency, throughput"),
        ({"bottlenecks": ["cpu", "memory"]}, "Bottlenecks identified: ['cpu', 'memory']"),
        ({"recommendations": ["cache", "batch", "parallel"]}, "Recommendations generated: 3"),
    ]

@pytest.fixture
def comprehensive_test_scenarios():
    """Comprehensive test scenarios for all contexts"""
    return [
        ("triage_failure", "analyze user query"),
        ("data_failure", "collect performance metrics"),
        ("optimization_failure", "optimize GPU workload"),
        ("action_failure", "create deployment plan"),
        ("report_failure", "generate analysis report"),
        ("llm_failure", "generate explanation"),
        ("validation_failure", "validate output quality"),
        ("general_failure", "process request")
    ]