"""
Shared fixtures and utilities for custom deployment configuration tests.
BVJ: Enterprise-specific testing infrastructure supporting $200K+ MRR
"""

import pytest
import uuid
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock


@pytest.fixture
async def enterprise_deployment_infrastructure():
    """Setup enterprise deployment infrastructure components"""
    return await _create_deployment_infrastructure()


async def _create_deployment_infrastructure():
    """Create comprehensive deployment infrastructure"""
    # Mock enterprise deployment services
    deployment_manager = Mock()
    config_validator = Mock()
    environment_loader = Mock()
    resource_scaler = Mock()
    health_checker = Mock()
    domain_manager = Mock()
    
    # Mock service discovery for testing to avoid file system issues
    service_discovery = Mock()
    service_discovery.register_service_for_cors = Mock()
    
    return {
        "deployment_manager": deployment_manager,
        "config_validator": config_validator,
        "environment_loader": environment_loader,
        "resource_scaler": resource_scaler,
        "health_checker": health_checker,
        "domain_manager": domain_manager,
        "service_discovery": service_discovery,
        "temp_config_dir": "/tmp/mock_dir"
    }


def create_enterprise_customer_config():
    """Create standard enterprise customer configuration"""
    return {
        "config_id": str(uuid.uuid4()),
        "enterprise_customer": "acme_corp",
        "environment_type": "private_cloud",
        "deployment_tier": "enterprise"
    }


def create_validation_rules():
    """Create standard validation rules for enterprise configurations"""
    return {
        "NETRA_ENTERPRISE_MODE": {"type": "boolean", "required": True},
        "NETRA_COMPLIANCE_LEVEL": {"type": "string", "allowed_values": ["SOC2_TYPE1", "SOC2_TYPE2", "HIPAA", "PCI_DSS"]},
        "NETRA_DATA_RESIDENCY": {"type": "string", "allowed_values": ["US_ONLY", "EU_ONLY", "APAC_ONLY", "GLOBAL"]},
        "NETRA_AUDIT_RETENTION_DAYS": {"type": "integer", "min": 90, "max": 3650},
        "POSTGRES_MAX_CONNECTIONS": {"type": "integer", "min": 10, "max": 1000},
        "MAX_CONCURRENT_REQUESTS": {"type": "integer", "min": 100, "max": 10000}
    }


async def validate_single_env_var(name: str, value: str, rule: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a single environment variable"""
    try:
        if rule["type"] == "boolean":
            parsed_value = value.lower() in ["true", "1", "yes", "on"]
        elif rule["type"] == "integer":
            parsed_value = int(value)
            if "min" in rule and parsed_value < rule["min"]:
                return {"valid": False, "error": f"Value {parsed_value} below minimum {rule['min']}"}
            if "max" in rule and parsed_value > rule["max"]:
                return {"valid": False, "error": f"Value {parsed_value} above maximum {rule['max']}"}
        elif rule["type"] == "string":
            if "allowed_values" in rule and value not in rule["allowed_values"]:
                return {"valid": False, "error": f"Value '{value}' not in allowed values: {rule['allowed_values']}"}
        
        return {"valid": True, "parsed_value": parsed_value if rule["type"] != "string" else value}
    except (ValueError, TypeError) as e:
        return {"valid": False, "error": f"Type conversion error: {str(e)}"}


def create_service_startup_config():
    """Create standard service startup configuration"""
    return {
        "services": ["backend", "frontend", "auth_service"],
        "startup_sequence": [
            {"service": "backend", "dependencies": [], "timeout": 60},
            {"service": "auth_service", "dependencies": ["backend"], "timeout": 30},
            {"service": "frontend", "dependencies": ["backend", "auth_service"], "timeout": 30}
        ]
    }


def assert_enterprise_success(startup_result):
    """Common assertions for enterprise deployment success"""
    assert startup_result["overall_status"] == "all_services_healthy"
    assert len(startup_result["startup_results"]) == 3
    for service_name, result in startup_result["startup_results"].items():
        assert result["environment_loaded"] is True
        assert result["health_check_passed"] is True
        assert result["custom_variables_count"] > 0