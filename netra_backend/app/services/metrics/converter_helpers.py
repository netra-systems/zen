"""
Helper functions for converting metrics objects to dictionaries
Used for JSON export functionality
"""

from typing import Dict, List, Any
from netra_backend.app.schemas.Metrics import (
    CorpusMetric, TimeSeriesPoint, ResourceUsage, QualityMetrics
)


async def convert_operation_metrics(operation_metrics) -> List[Dict[str, Any]]:
    """Convert operation metrics to dictionaries."""
    return [await _operation_metrics_to_dict(op) for op in operation_metrics]


async def convert_resource_usage(resource_usage) -> List[Dict[str, Any]]:
    """Convert resource usage to dictionaries."""
    return [await _resource_usage_to_dict(ru) for ru in resource_usage]


async def convert_custom_metrics(custom_metrics) -> List[Dict[str, Any]]:
    """Convert custom metrics to dictionaries."""
    return [await _corpus_metric_to_dict(cm) for cm in custom_metrics]


async def convert_quality_metrics(quality_metrics: QualityMetrics) -> Dict[str, Any]:
    """Convert quality metrics to dictionary."""
    return await _quality_metrics_to_dict(quality_metrics)


async def convert_corpus_metric(metric: CorpusMetric) -> Dict[str, Any]:
    """Convert corpus metric to dictionary."""
    return await _corpus_metric_to_dict(metric)


async def convert_time_series_point(point: TimeSeriesPoint) -> Dict[str, Any]:
    """Convert time series point to dictionary."""
    return await _time_series_to_dict(point)


async def _operation_metrics_to_dict(op_metrics) -> Dict[str, Any]:
    """Convert operation metrics to dictionary"""
    base_data = _build_operation_base_data(op_metrics)
    timing_data = _build_operation_timing_data(op_metrics)
    performance_data = _build_operation_performance_data(op_metrics)
    return {**base_data, **timing_data, **performance_data}


def _build_operation_base_data(op_metrics) -> Dict[str, Any]:
    """Build base operation metrics data."""
    return {
        "operation_type": op_metrics.operation_type,
        "success": op_metrics.success,
        "error_message": op_metrics.error_message
    }


def _build_operation_timing_data(op_metrics) -> Dict[str, Any]:
    """Build timing data for operation metrics."""
    return {
        "start_time": op_metrics.start_time.isoformat(),
        "end_time": op_metrics.end_time.isoformat() if op_metrics.end_time else None,
        "duration_ms": op_metrics.duration_ms
    }


def _build_operation_performance_data(op_metrics) -> Dict[str, Any]:
    """Build performance data for operation metrics."""
    return {
        "records_processed": op_metrics.records_processed,
        "throughput_per_second": op_metrics.throughput_per_second
    }


async def _resource_usage_to_dict(resource_usage: ResourceUsage) -> Dict[str, Any]:
    """Convert resource usage to dictionary"""
    base_data = _build_resource_base_data(resource_usage)
    value_data = _build_resource_value_data(resource_usage)
    return {**base_data, **value_data}


def _build_resource_base_data(resource_usage: ResourceUsage) -> Dict[str, Any]:
    """Build base resource usage data."""
    return {
        "resource_type": resource_usage.resource_type.value,
        "unit": resource_usage.unit,
        "timestamp": resource_usage.timestamp.isoformat()
    }


def _build_resource_value_data(resource_usage: ResourceUsage) -> Dict[str, Any]:
    """Build value data for resource usage."""
    return {
        "current_value": resource_usage.current_value,
        "max_value": resource_usage.max_value,
        "average_value": resource_usage.average_value
    }


async def _corpus_metric_to_dict(metric: CorpusMetric) -> Dict[str, Any]:
    """Convert corpus metric to dictionary"""
    base_data = _build_corpus_metric_base_data(metric)
    value_data = _build_corpus_metric_value_data(metric)
    extended_data = _build_corpus_metric_extended_data(metric)
    return {**base_data, **value_data, **extended_data}


def _build_corpus_metric_base_data(metric: CorpusMetric) -> Dict[str, Any]:
    """Build base corpus metric data."""
    return {
        "metric_id": metric.metric_id,
        "corpus_id": metric.corpus_id,
        "metric_type": metric.metric_type.value
    }


def _build_corpus_metric_value_data(metric: CorpusMetric) -> Dict[str, Any]:
    """Build value data for corpus metric."""
    return {
        "value": metric.value,
        "unit": metric.unit,
        "timestamp": metric.timestamp.isoformat()
    }


def _build_corpus_metric_extended_data(metric: CorpusMetric) -> Dict[str, Any]:
    """Build extended data for corpus metric."""
    return {
        "tags": metric.tags,
        "metadata": metric.metadata
    }


async def _quality_metrics_to_dict(quality: QualityMetrics) -> Dict[str, Any]:
    """Convert quality metrics to dictionary"""
    scores_data = _build_quality_scores_data(quality)
    meta_data = _build_quality_meta_data(quality)
    return {**scores_data, **meta_data}


def _build_quality_scores_data(quality: QualityMetrics) -> Dict[str, Any]:
    """Build quality scores data."""
    return {
        "overall_score": quality.overall_score,
        "validation_score": quality.validation_score,
        "completeness_score": quality.completeness_score,
        "consistency_score": quality.consistency_score,
        "accuracy_score": quality.accuracy_score
    }


def _build_quality_meta_data(quality: QualityMetrics) -> Dict[str, Any]:
    """Build quality metadata."""
    return {
        "timestamp": quality.timestamp.isoformat(),
        "issues_detected": quality.issues_detected
    }


async def _time_series_to_dict(point: TimeSeriesPoint) -> Dict[str, Any]:
    """Convert time series point to dictionary"""
    return {
        "timestamp": point.timestamp.isoformat(),
        "value": point.value,
        "tags": point.tags
    }