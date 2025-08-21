"""
Domain and Workload Optimization Profiles

Contains domain-specific and workload-specific configuration profiles
extracted from suggestions.py to maintain 450-line limit.
"""

from typing import Dict, Any, List


def _get_performance_optimization_rules() -> Dict[str, Any]:
    """Get performance optimization rules."""
    return {
        "batch_size": {"value": 256, "impact": "Higher throughput"},
        "concurrency": {"value": 20, "impact": "Parallel processing"},
        "compression": {"value": "lz4", "impact": "Fast compression"}
    }


def _get_quality_optimization_rules() -> Dict[str, Any]:
    """Get quality optimization rules."""
    return {
        "error_rate": {"value": 0.001, "impact": "High accuracy"},
        "validation": {"value": True, "impact": "Data integrity"},
        "sampling_rate": {"value": 1.0, "impact": "Complete data"}
    }


def _get_balanced_optimization_rules() -> Dict[str, Any]:
    """Get balanced optimization rules."""
    return {
        "batch_size": {"value": 128, "impact": "Balanced load"},
        "error_rate": {"value": 0.01, "impact": "Acceptable accuracy"},
        "concurrency": {"value": 10, "impact": "Moderate parallelism"}
    }


def get_optimization_rules() -> Dict[str, Dict[str, Any]]:
    """Initialize optimization rules for different focuses"""
    performance_rules = _get_performance_optimization_rules()
    quality_rules = _get_quality_optimization_rules()
    balanced_rules = _get_balanced_optimization_rules()
    return {"performance": performance_rules, "quality": quality_rules, "balanced": balanced_rules}


def get_domain_profiles() -> Dict[str, Dict[str, Any]]:
    """Initialize domain-specific configuration profiles"""
    fintech_profile = _get_fintech_profile()
    healthcare_profile = _get_healthcare_profile()
    ecommerce_profile = _get_ecommerce_profile()
    return _build_domain_profiles_dict(fintech_profile, healthcare_profile, ecommerce_profile)

def _build_domain_profiles_dict(fintech_profile: Dict[str, Any], healthcare_profile: Dict[str, Any], ecommerce_profile: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build domain profiles dictionary."""
    return {
        "fintech": fintech_profile,
        "healthcare": healthcare_profile,
        "ecommerce": ecommerce_profile
    }

def _get_fintech_profile() -> Dict[str, Any]:
    """Get fintech domain configuration profile."""
    return {
        "precision": "high",
        "audit_logging": True,
        "encryption": "AES-256",
        "compliance": ["PCI-DSS", "SOX"]
    }

def _get_healthcare_profile() -> Dict[str, Any]:
    """Get healthcare domain configuration profile."""
    return {
        "privacy": "HIPAA",
        "anonymization": True,
        "retention": "7y",
        "validation": "strict"
    }

def _get_ecommerce_profile() -> Dict[str, Any]:
    """Get ecommerce domain configuration profile."""
    return {
        "scalability": "elastic",
        "cache_ttl": 300,
        "real_time": True,
        "analytics": "enabled"
    }


def get_workload_optimizations() -> Dict[str, Dict[str, Any]]:
    """Initialize workload-specific optimizations"""
    ml_optimizations = _get_machine_learning_optimizations()
    web_optimizations = _get_web_services_optimizations()
    data_optimizations = _get_data_processing_optimizations()
    return _build_workload_optimizations_dict(ml_optimizations, web_optimizations, data_optimizations)

def _build_workload_optimizations_dict(ml_optimizations: Dict[str, Any], web_optimizations: Dict[str, Any], data_optimizations: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build workload optimizations dictionary."""
    return {
        "machine_learning": ml_optimizations,
        "web_services": web_optimizations,
        "data_processing": data_optimizations
    }

def _get_machine_learning_optimizations() -> Dict[str, Any]:
    """Get machine learning workload optimizations."""
    return {
        "gpu_enabled": True,
        "tensor_format": True,
        "shuffle": True,
        "augmentation": "auto"
    }

def _get_web_services_optimizations() -> Dict[str, Any]:
    """Get web services workload optimizations."""
    return {
        "rate_limiting": True,
        "circuit_breaker": True,
        "timeout": 30,
        "retry_policy": "exponential"
    }

def _get_data_processing_optimizations() -> Dict[str, Any]:
    """Get data processing workload optimizations."""
    return {
        "streaming": True,
        "checkpointing": True,
        "exactly_once": True,
        "windowing": "sliding"
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
        _apply_fintech_rules(config)
    elif domain == "healthcare":
        _apply_healthcare_rules(config)
    return config

def _apply_fintech_rules(config: Dict) -> None:
    """Apply fintech-specific business rules."""
    config["audit_logging"] = True
    config["encryption"] = config.get("encryption", "AES-256")

def _apply_healthcare_rules(config: Dict) -> None:
    """Apply healthcare-specific business rules."""
    config["anonymization"] = True
    config["retention"] = config.get("retention", "7y")


def merge_domain_settings(config: Dict, domain_settings: Dict) -> Dict[str, Any]:
    """Merge domain-specific settings into configuration"""
    for key, value in domain_settings.items():
        if key not in config:
            config[key] = value
    return config