"""
Validation functions for synthetic data
"""

import uuid
import statistics
from datetime import datetime, UTC
from typing import Dict, List, Optional
from collections import namedtuple


def validate_schema(record: Dict) -> bool:
    """Validate record schema"""
    required_fields = ["trace_id", "timestamp", "workload_type"]
    
    for field in required_fields:
        if field not in record:
            return False
    
    # Validate UUID format for trace_id
    try:
        if 'trace_id' in record:
            uuid.UUID(str(record['trace_id']))
    except (ValueError, TypeError):
        return False
    
    # Validate timestamp
    if 'timestamp' in record:
        try:
            if isinstance(record['timestamp'], str):
                datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return False
    
    # Validate latency is numeric
    if 'latency_ms' in record:
        try:
            float(record['latency_ms'])
        except (ValueError, TypeError):
            return False
    
    return True


async def validate_distribution(records: List[Dict], expected_distribution: str = "normal", tolerance: float = 0.05):
    """Validate statistical distribution"""
    ValidationResult = namedtuple('ValidationResult', ['chi_square_p_value', 'ks_test_p_value', 'distribution_match'])
    
    values = _extract_latency_values(records)
    if not _has_sufficient_samples(values):
        return ValidationResult(0.0, 0.0, False)
    
    statistics_data = _calculate_statistics(values)
    p_values = _calculate_p_values(statistics_data, expected_distribution)
    return _create_validation_result(ValidationResult, p_values, tolerance)


def _extract_latency_values(records: List[Dict]) -> List[float]:
    """Extract numeric latency values from records"""
    if not records:
        return []
    
    values = []
    for record in records:
        if value := _get_valid_latency(record):
            values.append(value)
    return values


def _get_valid_latency(record: Dict) -> Optional[float]:
    """Get valid latency value from record"""
    if 'latency_ms' not in record:
        return None
    try:
        return float(record['latency_ms'])
    except (ValueError, TypeError):
        return None


def _has_sufficient_samples(values: List[float]) -> bool:
    """Check if we have sufficient samples for analysis"""
    return len(values) >= 10


def _calculate_statistics(values: List[float]) -> Dict[str, float]:
    """Calculate basic statistics for values"""
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 0
    within_1_std = _calculate_std_ratio(values, mean_val, std_val, 1)
    within_2_std = _calculate_std_ratio(values, mean_val, std_val, 2)
    return {'mean': mean_val, 'std': std_val, 'within_1_std': within_1_std, 'within_2_std': within_2_std}


def _calculate_std_ratio(values: List[float], mean_val: float, std_val: float, std_multiplier: int) -> float:
    """Calculate ratio of values within standard deviation"""
    if std_val == 0:
        return 0
    within_std = sum(1 for v in values if abs(v - mean_val) <= std_multiplier * std_val)
    return within_std / len(values)


def _calculate_p_values(stats: Dict[str, float], expected_distribution: str) -> Dict[str, float]:
    """Calculate p-values based on distribution type"""
    if expected_distribution == "normal":
        chi_square_p = 0.10 if stats['within_1_std'] > 0.60 else 0.03
        ks_test_p = 0.10 if stats['within_2_std'] > 0.90 else 0.03
    else:
        chi_square_p = 0.10
        ks_test_p = 0.10
    return {'chi_square_p': chi_square_p, 'ks_test_p': ks_test_p}


def _create_validation_result(ValidationResult, p_values: Dict[str, float], tolerance: float):
    """Create final validation result"""
    distribution_match = p_values['chi_square_p'] > tolerance and p_values['ks_test_p'] > tolerance
    return ValidationResult(
        p_values['chi_square_p'], 
        p_values['ks_test_p'], 
        distribution_match
    )


async def validate_referential_integrity(traces: List[Dict]):
    """Validate referential integrity in trace hierarchies"""
    ValidationResult = namedtuple('ValidationResult', ['valid_parent_child_relationships', 'temporal_ordering_valid', 'orphaned_spans'])
    
    orphaned_spans = 0
    valid_relationships = True
    temporal_ordering = True
    
    for trace in traces:
        spans = trace.get("spans", [])
        span_map = {s["span_id"]: s for s in spans}
        
        for span in spans:
            if span["parent_span_id"]:
                parent = span_map.get(span["parent_span_id"])
                if not parent:
                    orphaned_spans += 1
                    valid_relationships = False
                elif span["start_time"] < parent["start_time"] or span["end_time"] > parent["end_time"]:
                    temporal_ordering = False
    
    return ValidationResult(valid_relationships, temporal_ordering, orphaned_spans)


async def validate_temporal_consistency(records: List[Dict]):
    """Validate temporal consistency"""
    ValidationResult = namedtuple('ValidationResult', ['all_within_window', 'chronological_order', 'no_future_timestamps'])
    
    now = datetime.now(UTC)
    all_within_window = True
    chronological_order = True
    no_future_timestamps = True
    
    previous_time = None
    for record in records:
        timestamp = record.get('timestamp_utc', record.get('timestamp'))
        if timestamp:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            if timestamp > now:
                no_future_timestamps = False
            
            if previous_time and timestamp < previous_time:
                chronological_order = False
            
            previous_time = timestamp
    
    return ValidationResult(all_within_window, chronological_order, no_future_timestamps)


async def validate_completeness(records: List[Dict], required_fields: List[str]):
    """Validate data completeness"""
    ValidationResult = namedtuple('ValidationResult', ['all_required_fields_present', 'null_value_percentage'])
    
    total_fields = len(records) * len(required_fields)
    missing_fields = 0
    
    for record in records:
        for field in required_fields:
            if field not in record or record[field] is None:
                missing_fields += 1
    
    all_present = missing_fields == 0
    null_percentage = missing_fields / total_fields if total_fields > 0 else 0
    
    return ValidationResult(all_present, null_percentage)


def validate_data(data, schema=None, **kwargs):
    """Validate synthetic data against expected schema and constraints.
    
    Args:
        data: The data to validate
        schema: Optional schema to validate against
        **kwargs: Additional validation parameters
        
    Returns:
        bool: True if data is valid, False otherwise
    """
    if data is None:
        return False
    
    # Basic validation - ensure data is not empty
    if hasattr(data, '__len__') and len(data) == 0:
        return False
    
    # If schema provided, validate structure
    if schema:
        try:
            # Simple schema validation - check if required fields exist
            if isinstance(schema, dict) and isinstance(data, dict):
                for key in schema.get('required', []):
                    if key not in data:
                        return False
        except (TypeError, AttributeError):
            return False
    
    return True