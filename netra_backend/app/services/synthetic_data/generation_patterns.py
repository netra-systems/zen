"""
Generation patterns for synthetic data
"""

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

import numpy as np

if TYPE_CHECKING:
    from netra_backend.app.schemas.generation import SyntheticDataGenParams


def _setup_temporal_config(config: 'SyntheticDataGenParams'):
    """Extract temporal pattern configuration"""
    num_traces = getattr(config, 'num_traces', 1000)
    pattern = getattr(config, 'temporal_pattern', 'uniform')
    return num_traces, pattern


def _get_business_hour():
    """Get weighted business hour"""
    return random.choices(
        range(24),
        weights=[0.5 if h < 9 or h > 17 else 2.0 for h in range(24)]
    )[0]


def _get_business_weekday():
    """Get weighted business weekday"""
    return random.choices(
        range(7),
        weights=[2.0 if d < 5 else 0.5 for d in range(7)]
    )[0]


def _apply_business_hours_pattern(record: Dict[str, Any]):
    """Apply business hours temporal pattern to record"""
    hour = _get_business_hour()
    weekday = _get_business_weekday()
    base_time = datetime.now(UTC) - timedelta(hours=24)
    record['timestamp'] = base_time.replace(hour=hour, minute=random.randint(0, 59))


async def generate_with_temporal_patterns(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with temporal patterns"""
    records = []
    num_traces, pattern = _setup_temporal_config(config)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        if pattern == 'business_hours':
            _apply_business_hours_pattern(record)
        records.append(record)
    
    return records


def _setup_error_config(config: 'SyntheticDataGenParams'):
    """Extract error generation configuration"""
    num_traces = getattr(config, 'num_traces', 100)
    error_rate = getattr(config, 'error_rate', 0.15)
    error_patterns = getattr(config, 'error_patterns', ['timeout', 'rate_limit', 'invalid_input'])
    return num_traces, error_rate, error_patterns


def _apply_error_injection(record: Dict[str, Any], error_rate: float, error_patterns: List[str]):
    """Apply error injection to record"""
    if random.random() < error_rate:
        record['status'] = 'failed'
        record['error_type'] = random.choice(error_patterns)
        record['error_message'] = f"Simulated {record['error_type']} error"
    else:
        record['status'] = 'success'


async def generate_with_errors(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with error scenarios"""
    records = []
    num_traces, error_rate, error_patterns = _setup_error_config(config)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        _apply_error_injection(record, error_rate, error_patterns)
        records.append(record)
    
    return records


def _setup_domain_config(config: 'SyntheticDataGenParams'):
    """Extract domain-specific configuration"""
    num_traces = getattr(config, 'num_traces', 100)
    domain = getattr(config, 'domain_focus', 'general')
    return num_traces, domain


def _create_ecommerce_metadata() -> Dict[str, Any]:
    """Create e-commerce domain metadata"""
    return {
        'cart_value': random.uniform(10.0, 500.0),
        'product_count': random.randint(1, 10),
        'customer_tier': random.choice(['bronze', 'silver', 'gold'])
    }


def _create_healthcare_metadata() -> Dict[str, Any]:
    """Create healthcare domain metadata"""
    return {
        'patient_id': f"P{random.randint(1000, 9999)}",
        'appointment_type': random.choice(['consultation', 'followup', 'emergency']),
        'department': random.choice(['cardiology', 'neurology', 'orthopedics'])
    }


def _create_finance_metadata() -> Dict[str, Any]:
    """Create finance domain metadata"""
    return {
        'transaction_amount': random.uniform(100.0, 10000.0),
        'account_type': random.choice(['checking', 'savings', 'credit']),
        'risk_score': random.uniform(0.0, 1.0)
    }


def _apply_domain_metadata(record: Dict[str, Any], domain: str):
    """Apply domain-specific metadata to record"""
    if domain == 'e-commerce':
        record['metadata'] = _create_ecommerce_metadata()
    elif domain == 'healthcare':
        record['metadata'] = _create_healthcare_metadata()
    elif domain == 'finance':
        record['metadata'] = _create_finance_metadata()


async def generate_domain_specific(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate domain-specific data"""
    records = []
    num_traces, domain = _setup_domain_config(config)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        _apply_domain_metadata(record, domain)
        records.append(record)
    
    return records


def _setup_distribution_config(config: 'SyntheticDataGenParams'):
    """Extract distribution configuration"""
    num_traces = getattr(config, 'num_traces', 1000)
    distribution = getattr(config, 'latency_distribution', 'normal')
    return num_traces, distribution


def _apply_latency_distribution(record: Dict[str, Any], distribution: str):
    """Apply statistical distribution to latency"""
    if distribution == 'normal':
        record['latency_ms'] = max(0, np.random.normal(200, 50))
    elif distribution == 'exponential':
        record['latency_ms'] = np.random.exponential(150)
    elif distribution == 'uniform':
        record['latency_ms'] = np.random.uniform(50, 500)
    elif distribution == 'bimodal':
        _apply_bimodal_distribution(record)


def _apply_bimodal_distribution(record: Dict[str, Any]):
    """Apply bimodal distribution to latency"""
    if random.random() < 0.5:
        record['latency_ms'] = np.random.normal(100, 25)
    else:
        record['latency_ms'] = np.random.normal(400, 50)


async def generate_with_distribution(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with specific statistical distributions"""
    records = []
    num_traces, distribution = _setup_distribution_config(config)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        _apply_latency_distribution(record, distribution)
        records.append(record)
    
    return records


def _setup_anomaly_config(config: 'SyntheticDataGenParams'):
    """Extract anomaly injection configuration"""
    num_traces = getattr(config, 'num_traces', 1000)
    anomaly_rate = getattr(config, 'anomaly_injection_rate', 0.05)
    return num_traces, anomaly_rate


def _inject_anomaly_spike(record: Dict[str, Any]):
    """Inject spike anomaly into record"""
    record['latency_ms'] = record.get('latency_ms', 100) * random.uniform(5, 10)


def _inject_anomaly_degradation(record: Dict[str, Any]):
    """Inject degradation anomaly into record"""
    record['latency_ms'] = record.get('latency_ms', 100) * random.uniform(2, 3)


def _apply_anomaly_injection(record: Dict[str, Any], anomaly_rate: float):
    """Apply anomaly injection to record"""
    if random.random() < anomaly_rate:
        record['anomaly'] = True
        anomaly_type = random.choice(['spike', 'degradation', 'failure'])
        record['anomaly_type'] = anomaly_type
        _execute_anomaly_modification(record, anomaly_type)


def _execute_anomaly_modification(record: Dict[str, Any], anomaly_type: str):
    """Execute specific anomaly modification"""
    if anomaly_type == 'spike':
        _inject_anomaly_spike(record)
    elif anomaly_type == 'degradation':
        _inject_anomaly_degradation(record)
    elif anomaly_type == 'failure':
        record['status'] = 'failed'


async def generate_with_anomalies(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with injected anomalies"""
    records = []
    num_traces, anomaly_rate = _setup_anomaly_config(config)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        _apply_anomaly_injection(record, anomaly_rate)
        records.append(record)
    
    return records


def _setup_geo_config(config: 'SyntheticDataGenParams'):
    """Extract geo-distribution configuration"""
    num_traces = getattr(config, 'num_traces', 1000)
    geo_distribution = getattr(config, 'geo_distribution', {})
    latency_by_region = getattr(config, 'latency_by_region', {})
    return num_traces, geo_distribution, latency_by_region


def _get_region_selection_data(geo_distribution: Dict[str, float]):
    """Get region and weights for selection"""
    regions = list(geo_distribution.keys())
    weights = list(geo_distribution.values())
    return regions, weights


def _select_region(regions: List[str], weights: List[float]) -> str:
    """Select region based on weights"""
    return random.choices(regions, weights=weights)[0] if regions else "us-east"


def _apply_geo_data(record: Dict[str, Any], geo_distribution: Dict, latency_by_region: Dict):
    """Apply geo-distributed data to record"""
    regions, weights = _get_region_selection_data(geo_distribution)
    region = _select_region(regions, weights)
    record['region'] = region
    _apply_regional_latency(record, region, latency_by_region)


def _apply_regional_latency(record: Dict[str, Any], region: str, latency_by_region: Dict):
    """Apply region-specific latency to record"""
    if region in latency_by_region:
        latency_range = latency_by_region[region]
        record['latency_ms'] = random.uniform(latency_range[0], latency_range[1])


async def generate_geo_distributed(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate geo-distributed workload data"""
    records = []
    num_traces, geo_distribution, latency_by_region = _setup_geo_config(config)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        _apply_geo_data(record, geo_distribution, latency_by_region)
        records.append(record)
    
    return records


def _setup_correlation_config(config: 'SyntheticDataGenParams'):
    """Extract correlation configuration"""
    num_traces = getattr(config, 'num_traces', 1000)
    correlations = getattr(config, 'correlations', [])
    return num_traces, correlations


def _apply_request_size_latency_correlation(record: Dict[str, Any]):
    """Apply request size to latency correlation"""
    request_size = random.uniform(100, 1000)
    latency = 50 + (request_size / 10) + random.uniform(-20, 20)
    record['request_size'] = request_size
    record['latency'] = max(10, latency)


def _apply_error_rate_throughput_correlation(record: Dict[str, Any]):
    """Apply error rate to throughput correlation"""
    error_rate = random.uniform(0.01, 0.10)
    throughput = 1000 - (error_rate * 5000) + random.uniform(-100, 100)
    record['error_rate'] = error_rate
    record['throughput'] = max(100, throughput)


def _apply_correlation_logic(record: Dict[str, Any], corr: Dict[str, Any]):
    """Apply specific correlation logic to record"""
    field1, field2 = corr['field1'], corr['field2']
    
    if field1 == 'request_size' and field2 == 'latency':
        _apply_request_size_latency_correlation(record)
    elif field1 == 'error_rate' and field2 == 'throughput':
        _apply_error_rate_throughput_correlation(record)


async def generate_with_correlations(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with cross-correlations"""
    records = []
    num_traces, correlations = _setup_correlation_config(config)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        for corr in correlations:
            _apply_correlation_logic(record, corr)
        records.append(record)
    
    return records