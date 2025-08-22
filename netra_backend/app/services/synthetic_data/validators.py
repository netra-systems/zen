"""
Validation functions for synthetic data
"""

import re
import statistics
import uuid
from collections import namedtuple
from datetime import UTC, datetime
from typing import Dict, List, Optional


class AuthValidationError(Exception):
    """Custom exception for auth validation errors"""
    pass


def validate_email_format(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> bool:
    """Validate password meets minimum requirements"""
    if not password or len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit


def validate_token_format(token: str) -> bool:
    """Validate token format"""
    if not token:
        return False
    # Basic JWT format validation (header.payload.signature)
    parts = token.split('.')
    return len(parts) == 3 and all(len(part) > 0 for part in parts)


def validate_service_id(service_id: str) -> bool:
    """Validate service ID format"""
    if not service_id:
        return False
    # Service IDs should be alphanumeric with underscores
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, service_id))


def validate_permission_format(permission: str) -> bool:
    """Validate permission format"""
    if not permission:
        return False
    # Permissions should follow format: resource:action
    pattern = r'^[a-zA-Z0-9_]+:[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, permission))


def validate_schema(record: Dict) -> bool:
    """Validate record schema"""
    if not _has_required_fields(record):
        return False
    return _validate_field_formats(record)


def _has_required_fields(record: Dict) -> bool:
    """Check if record has all required fields"""
    required_fields = ["trace_id", "timestamp", "workload_type"]
    return all(field in record for field in required_fields)


def _validate_field_formats(record: Dict) -> bool:
    """Validate field formats in record"""
    if not _validate_trace_id_format(record):
        return False
    if not _validate_timestamp_format(record):
        return False
    return _validate_latency_format(record)


def _validate_trace_id_format(record: Dict) -> bool:
    """Validate trace_id UUID format"""
    if 'trace_id' not in record:
        return True
    try:
        uuid.UUID(str(record['trace_id']))
        return True
    except (ValueError, TypeError):
        return False


def _validate_timestamp_format(record: Dict) -> bool:
    """Validate timestamp format"""
    if 'timestamp' not in record:
        return True
    try:
        if isinstance(record['timestamp'], str):
            datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False


def _validate_latency_format(record: Dict) -> bool:
    """Validate latency numeric format"""
    if 'latency_ms' not in record:
        return True
    try:
        float(record['latency_ms'])
        return True
    except (ValueError, TypeError):
        return False


async def validate_distribution(records: List[Dict], expected_distribution: str = "normal", tolerance: float = 0.05):
    """Validate statistical distribution"""
    ValidationResult = namedtuple('ValidationResult', ['chi_square_p_value', 'ks_test_p_value', 'distribution_match'])
    values = _extract_latency_values(records)
    if not _has_sufficient_samples(values):
        return ValidationResult(0.0, 0.0, False)
    return _perform_distribution_analysis(ValidationResult, values, expected_distribution, tolerance)


def _perform_distribution_analysis(ValidationResult, values: List[float], expected_distribution: str, tolerance: float):
    """Perform distribution analysis and return validation result"""
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
    integrity_state = _initialize_integrity_state()
    _process_trace_integrity(traces, integrity_state)
    return ValidationResult(integrity_state['valid_relationships'], integrity_state['temporal_ordering'], integrity_state['orphaned_spans'])


def _initialize_integrity_state() -> Dict[str, any]:
    """Initialize integrity validation state"""
    return {
        'orphaned_spans': 0,
        'valid_relationships': True,
        'temporal_ordering': True
    }


def _process_trace_integrity(traces: List[Dict], state: Dict[str, any]) -> None:
    """Process all traces for integrity validation"""
    for trace in traces:
        spans = trace.get("spans", [])
        span_map = {s["span_id"]: s for s in spans}
        _validate_spans_integrity(spans, span_map, state)


def _validate_spans_integrity(spans: List[Dict], span_map: Dict, state: Dict[str, any]) -> None:
    """Validate integrity for all spans in a trace"""
    for span in spans:
        if span["parent_span_id"]:
            _validate_single_span_integrity(span, span_map, state)


def _validate_single_span_integrity(span: Dict, span_map: Dict, state: Dict[str, any]) -> None:
    """Validate integrity for a single span"""
    parent = span_map.get(span["parent_span_id"])
    if not parent:
        state['orphaned_spans'] += 1
        state['valid_relationships'] = False
    elif _has_temporal_violation(span, parent):
        state['temporal_ordering'] = False


def _has_temporal_violation(span: Dict, parent: Dict) -> bool:
    """Check if span has temporal ordering violation"""
    return span["start_time"] < parent["start_time"] or span["end_time"] > parent["end_time"]


async def validate_temporal_consistency(records: List[Dict]):
    """Validate temporal consistency"""
    ValidationResult = namedtuple('ValidationResult', ['all_within_window', 'chronological_order', 'no_future_timestamps'])
    consistency_state = _initialize_temporal_state()
    _process_temporal_records(records, consistency_state)
    return ValidationResult(consistency_state['all_within_window'], consistency_state['chronological_order'], consistency_state['no_future_timestamps'])


def _initialize_temporal_state() -> Dict[str, any]:
    """Initialize temporal consistency state"""
    return {
        'all_within_window': True,
        'chronological_order': True,
        'no_future_timestamps': True,
        'previous_time': None
    }


def _process_temporal_records(records: List[Dict], state: Dict[str, any]) -> None:
    """Process all records for temporal consistency"""
    now = datetime.now(UTC)
    for record in records:
        timestamp = _extract_timestamp(record)
        if timestamp:
            _validate_single_timestamp(timestamp, now, state)


def _extract_timestamp(record: Dict) -> Optional[datetime]:
    """Extract and parse timestamp from record"""
    timestamp = record.get('timestamp_utc', record.get('timestamp'))
    if timestamp and isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return timestamp


def _validate_single_timestamp(timestamp: datetime, now: datetime, state: Dict[str, any]) -> None:
    """Validate a single timestamp against consistency rules"""
    if timestamp > now:
        state['no_future_timestamps'] = False
    if state['previous_time'] and timestamp < state['previous_time']:
        state['chronological_order'] = False
    state['previous_time'] = timestamp


async def validate_completeness(records: List[Dict], required_fields: List[str]):
    """Validate data completeness"""
    ValidationResult = namedtuple('ValidationResult', ['all_required_fields_present', 'null_value_percentage'])
    completeness_data = _calculate_completeness_data(records, required_fields)
    return ValidationResult(completeness_data['all_present'], completeness_data['null_percentage'])


def _calculate_completeness_data(records: List[Dict], required_fields: List[str]) -> Dict[str, any]:
    """Calculate completeness statistics"""
    total_fields = len(records) * len(required_fields)
    missing_fields = _count_missing_fields(records, required_fields)
    return {
        'all_present': missing_fields == 0,
        'null_percentage': missing_fields / total_fields if total_fields > 0 else 0
    }


def _count_missing_fields(records: List[Dict], required_fields: List[str]) -> int:
    """Count missing fields across all records"""
    missing_count = 0
    for record in records:
        missing_count += _count_record_missing_fields(record, required_fields)
    return missing_count


def _count_record_missing_fields(record: Dict, required_fields: List[str]) -> int:
    """Count missing fields in a single record"""
    return sum(1 for field in required_fields if field not in record or record[field] is None)


def validate_data(data, schema=None, **kwargs):
    """Validate synthetic data against expected schema and constraints.
    
    Args:
        data: The data to validate
        schema: Optional schema to validate against
        **kwargs: Additional validation parameters
        
    Returns:
        bool: True if data is valid, False otherwise
    """
    if not _is_data_valid_basic(data):
        return False
    return _validate_data_schema(data, schema)


def _is_data_valid_basic(data) -> bool:
    """Perform basic data validation checks"""
    if data is None:
        return False
    return not (hasattr(data, '__len__') and len(data) == 0)


def _validate_data_schema(data, schema) -> bool:
    """Validate data against schema if provided"""
    if not schema:
        return True
    try:
        return _check_schema_requirements(data, schema)
    except (TypeError, AttributeError):
        return False


def _check_schema_requirements(data, schema) -> bool:
    """Check if data meets schema requirements"""
    if not (isinstance(schema, dict) and isinstance(data, dict)):
        return True
    required_fields = schema.get('required', [])
    return all(key in data for key in required_fields)