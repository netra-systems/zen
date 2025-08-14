"""
Generation patterns for synthetic data
"""

import random
import uuid
import numpy as np
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional, Callable, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.Generation import SyntheticDataGenParams


async def generate_with_temporal_patterns(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with temporal patterns"""
    records = []
    num_traces = getattr(config, 'num_traces', 1000)
    pattern = getattr(config, 'temporal_pattern', 'uniform')
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        
        # Apply temporal pattern
        if pattern == 'business_hours':
            # Weight business hours more heavily
            hour = random.choices(
                range(24),
                weights=[0.5 if h < 9 or h > 17 else 2.0 for h in range(24)]
            )[0]
            
            # Set weekday preference
            weekday = random.choices(
                range(7),
                weights=[2.0 if d < 5 else 0.5 for d in range(7)]
            )[0]
            
            # Adjust timestamp to match pattern
            base_time = datetime.now(UTC) - timedelta(hours=24)
            record['timestamp'] = base_time.replace(hour=hour, minute=random.randint(0, 59))
        
        records.append(record)
    
    return records


async def generate_with_errors(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with error scenarios"""
    records = []
    num_traces = getattr(config, 'num_traces', 100)
    error_rate = getattr(config, 'error_rate', 0.15)
    error_patterns = getattr(config, 'error_patterns', ['timeout', 'rate_limit', 'invalid_input'])
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        
        # Inject errors based on rate
        if random.random() < error_rate:
            record['status'] = 'failed'
            record['error_type'] = random.choice(error_patterns)
            record['error_message'] = f"Simulated {record['error_type']} error"
        else:
            record['status'] = 'success'
        
        records.append(record)
    
    return records


async def generate_domain_specific(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate domain-specific data"""
    records = []
    num_traces = getattr(config, 'num_traces', 100)
    domain = getattr(config, 'domain_focus', 'general')
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        
        # Add domain-specific metadata
        if domain == 'e-commerce':
            record['metadata'] = {
                'cart_value': random.uniform(10.0, 500.0),
                'product_count': random.randint(1, 10),
                'customer_tier': random.choice(['bronze', 'silver', 'gold'])
            }
        elif domain == 'healthcare':
            record['metadata'] = {
                'patient_id': f"P{random.randint(1000, 9999)}",
                'appointment_type': random.choice(['consultation', 'followup', 'emergency']),
                'department': random.choice(['cardiology', 'neurology', 'orthopedics'])
            }
        elif domain == 'finance':
            record['metadata'] = {
                'transaction_amount': random.uniform(100.0, 10000.0),
                'account_type': random.choice(['checking', 'savings', 'credit']),
                'risk_score': random.uniform(0.0, 1.0)
            }
        
        records.append(record)
    
    return records


async def generate_with_distribution(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with specific statistical distributions"""
    records = []
    num_traces = getattr(config, 'num_traces', 1000)
    distribution = getattr(config, 'latency_distribution', 'normal')
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        
        # Apply distribution to latency
        if distribution == 'normal':
            record['latency_ms'] = max(0, np.random.normal(200, 50))
        elif distribution == 'exponential':
            record['latency_ms'] = np.random.exponential(150)
        elif distribution == 'uniform':
            record['latency_ms'] = np.random.uniform(50, 500)
        elif distribution == 'bimodal':
            if random.random() < 0.5:
                record['latency_ms'] = np.random.normal(100, 25)
            else:
                record['latency_ms'] = np.random.normal(400, 50)
        
        records.append(record)
    
    return records


async def generate_with_anomalies(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with injected anomalies"""
    records = []
    num_traces = getattr(config, 'num_traces', 1000)
    anomaly_rate = getattr(config, 'anomaly_injection_rate', 0.05)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        
        # Inject anomalies
        if random.random() < anomaly_rate:
            record['anomaly'] = True
            record['anomaly_type'] = random.choice(['spike', 'degradation', 'failure'])
            
            # Modify record based on anomaly type
            if record['anomaly_type'] == 'spike':
                record['latency_ms'] = record.get('latency_ms', 100) * random.uniform(5, 10)
            elif record['anomaly_type'] == 'degradation':
                record['latency_ms'] = record.get('latency_ms', 100) * random.uniform(2, 3)
            elif record['anomaly_type'] == 'failure':
                record['status'] = 'failed'
        
        records.append(record)
    
    return records


async def generate_geo_distributed(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate geo-distributed workload data"""
    records = []
    num_traces = getattr(config, 'num_traces', 1000)
    geo_distribution = getattr(config, 'geo_distribution', {})
    latency_by_region = getattr(config, 'latency_by_region', {})
    
    # Create region selection based on distribution
    regions = list(geo_distribution.keys())
    weights = list(geo_distribution.values())
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        
        # Select region based on weights
        region = random.choices(regions, weights=weights)[0] if regions else "us-east"
        record['region'] = region
        
        # Apply region-specific latency
        if region in latency_by_region:
            latency_range = latency_by_region[region]
            record['latency_ms'] = random.uniform(latency_range[0], latency_range[1])
        
        records.append(record)
    
    return records


async def generate_with_correlations(config: 'SyntheticDataGenParams', generate_single_record_fn: Callable[..., Awaitable[Dict]]) -> List[Dict[str, Any]]:
    """Generate data with cross-correlations"""
    records = []
    num_traces = getattr(config, 'num_traces', 1000)
    correlations = getattr(config, 'correlations', [])
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        
        # Apply correlations
        for corr in correlations:
            field1, field2 = corr['field1'], corr['field2']
            coefficient = corr['coefficient']
            
            if field1 == 'request_size' and field2 == 'latency':
                request_size = random.uniform(100, 1000)
                # Positive correlation: larger requests -> higher latency
                latency = 50 + (request_size / 10) + random.uniform(-20, 20)
                record['request_size'] = request_size
                record['latency'] = max(10, latency)
            
            elif field1 == 'error_rate' and field2 == 'throughput':
                error_rate = random.uniform(0.01, 0.10)
                # Negative correlation: higher error rate -> lower throughput
                throughput = 1000 - (error_rate * 5000) + random.uniform(-100, 100)
                record['error_rate'] = error_rate
                record['throughput'] = max(100, throughput)
        
        records.append(record)
    
    return records