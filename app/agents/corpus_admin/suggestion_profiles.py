"""
Domain and Workload Optimization Profiles

Contains domain-specific and workload-specific configuration profiles
extracted from suggestions.py to maintain 300-line limit.
"""

from typing import Dict, Any, List


def get_optimization_rules() -> Dict[str, Dict[str, Any]]:
    """Initialize optimization rules for different focuses"""
    return {
        "performance": {
            "batch_size": {"value": 256, "impact": "Higher throughput"},
            "concurrency": {"value": 20, "impact": "Parallel processing"},
            "compression": {"value": "lz4", "impact": "Fast compression"}
        },
        "quality": {
            "error_rate": {"value": 0.001, "impact": "High accuracy"},
            "validation": {"value": True, "impact": "Data integrity"},
            "sampling_rate": {"value": 1.0, "impact": "Complete data"}
        },
        "balanced": {
            "batch_size": {"value": 128, "impact": "Balanced load"},
            "error_rate": {"value": 0.01, "impact": "Acceptable accuracy"},
            "concurrency": {"value": 10, "impact": "Moderate parallelism"}
        }
    }


def get_domain_profiles() -> Dict[str, Dict[str, Any]]:
    """Initialize domain-specific configuration profiles"""
    return {
        "fintech": {
            "precision": "high",
            "audit_logging": True,
            "encryption": "AES-256",
            "compliance": ["PCI-DSS", "SOX"]
        },
        "healthcare": {
            "privacy": "HIPAA",
            "anonymization": True,
            "retention": "7y",
            "validation": "strict"
        },
        "ecommerce": {
            "scalability": "elastic",
            "cache_ttl": 300,
            "real_time": True,
            "analytics": "enabled"
        }
    }


def get_workload_optimizations() -> Dict[str, Dict[str, Any]]:
    """Initialize workload-specific optimizations"""
    return {
        "machine_learning": {
            "gpu_enabled": True,
            "tensor_format": True,
            "shuffle": True,
            "augmentation": "auto"
        },
        "web_services": {
            "rate_limiting": True,
            "circuit_breaker": True,
            "timeout": 30,
            "retry_policy": "exponential"
        },
        "data_processing": {
            "streaming": True,
            "checkpointing": True,
            "exactly_once": True,
            "windowing": "sliding"
        }
    }


def get_parameter_dependencies() -> Dict[str, List[str]]:
    """Initialize parameter dependencies"""
    return {
        "batch_size": ["memory_limit", "concurrency"],
        "concurrency": ["cpu_cores", "memory_limit"],
        "compression": ["storage_type", "performance_mode"],
        "encryption": ["compliance", "performance_mode"]
    }


def get_category_options(category: str) -> List[str]:
    """Get available options for a category"""
    category_map = {
        "workload": list(get_workload_optimizations().keys()),
        "domain": list(get_domain_profiles().keys()),
        "parameter": ["batch_size", "concurrency", "error_rate", "compression"]
    }
    return category_map.get(category, [])


def apply_domain_rules(config: Dict, domain: str) -> Dict[str, Any]:
    """Apply domain-specific business rules"""
    if domain == "fintech":
        config["audit_logging"] = True
        config["encryption"] = config.get("encryption", "AES-256")
    elif domain == "healthcare":
        config["anonymization"] = True
        config["retention"] = config.get("retention", "7y")
    return config


def merge_domain_settings(config: Dict, domain_settings: Dict) -> Dict[str, Any]:
    """Merge domain-specific settings into configuration"""
    for key, value in domain_settings.items():
        if key not in config:
            config[key] = value
    return config