#!/usr/bin/env python3
"""
ConfigDependencyMap Integration Demonstration

This script demonstrates how ConfigDependencyMap protects against
configuration deletions and validates configuration values.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from netra_backend.app.core.config_dependencies import ConfigDependencyMap, ConfigImpactLevel
from shared.isolated_environment import get_env
from netra_backend.app.core.configuration.startup_validator import (
    ConfigurationStartupValidator, 
    StartupValidationMode,
    get_critical_config_status
)


def demonstrate_deletion_protection():
    """Demonstrate configuration deletion protection"""
    print("\n=== Configuration Deletion Protection Demo ===")
    
    critical_configs = [
        "DATABASE_URL",
        "JWT_SECRET_KEY", 
        "GOOGLE_OAUTH_CLIENT_ID",
        "REDIS_URL"  # This one allows fallback
    ]
    
    for config_key in critical_configs:
        can_delete, reason = ConfigDependencyMap.can_delete_config(config_key)
        status = "[PROTECTED]" if not can_delete else "[DELETABLE]"
        print(f"{status} {config_key}: {reason}")


def demonstrate_value_validation():
    """Demonstrate configuration value validation"""
    print("\n=== Configuration Value Validation Demo ===")
    
    test_cases = [
        ("DATABASE_URL", "postgresql://user:pass@localhost:5432/db", "Valid PostgreSQL URL"),
        ("DATABASE_URL", "invalid://url", "Invalid database URL"),
        ("JWT_SECRET_KEY", "a" * 32, "Valid 32-character secret"),
        ("JWT_SECRET_KEY", "short", "Too short for security"),
        ("ENVIRONMENT", "production", "Valid environment"),
        ("ENVIRONMENT", "invalid_env", "Invalid environment"),
        ("GOOGLE_OAUTH_CLIENT_ID", "123456789.apps.googleusercontent.com", "Valid Google client ID"),
        ("GOOGLE_OAUTH_CLIENT_ID", "invalid-id", "Invalid Google client ID format"),
    ]
    
    for key, value, description in test_cases:
        is_valid, message = ConfigDependencyMap.validate_config_value(key, value)
        status = "[VALID]" if is_valid else "[INVALID]"
        print(f"{status} {key} = '{value}': {description}")
        if not is_valid:
            print(f"         Validation error: {message}")


def demonstrate_impact_analysis():
    """Demonstrate configuration impact analysis"""
    print("\n=== Configuration Impact Analysis Demo ===")
    
    configs_to_analyze = [
        "DATABASE_URL",
        "REDIS_URL", 
        "ANTHROPIC_API_KEY",
        "EMAIL_HOST"
    ]
    
    for config_key in configs_to_analyze:
        impact = ConfigDependencyMap.get_impact_analysis(config_key)
        print(f"\n{config_key}:")
        print(f"  Impact Level: {impact['impact_level'].value}")
        print(f"  Affected Services: {', '.join(impact.get('affected_services', []))}")
        print(f"  Can Delete: {'Yes' if impact['deletion_allowed'] else 'No'}")
        print(f"  Impact: {impact.get('deletion_impact', 'Unknown')}")
        if impact.get('alternatives'):
            print(f"  Alternatives: {', '.join(impact['alternatives'])}")


def demonstrate_consistency_check():
    """Demonstrate configuration consistency checking"""
    print("\n=== Configuration Consistency Check Demo ===")
    
    # Create test configuration with issues
    test_config = {
        "GOOGLE_CLIENT_ID": "test_client_id",
        # Missing GOOGLE_CLIENT_SECRET (paired config)
        "DATABASE_URL": "postgresql://localhost/test",
        "JWT_SECRET_KEY": "a" * 32,
        "AWS_ACCESS_KEY_ID": "test_key",
        # Missing AWS_SECRET_ACCESS_KEY (paired config)
    }
    
    issues = ConfigDependencyMap.check_config_consistency(test_config)
    
    if issues:
        print("Configuration issues detected:")
        for issue in issues:
            issue_type = "ERROR" if "CRITICAL" in issue else "WARNING"
            print(f"  [{issue_type}] {issue}")
    else:
        print("No configuration issues detected")


def demonstrate_startup_validation():
    """Demonstrate startup configuration validation"""
    print("\n=== Startup Configuration Validation Demo ===")
    
    # Test different validation modes
    modes = [
        (StartupValidationMode.STRICT, "Strict - Fail on any errors"),
        (StartupValidationMode.PERMISSIVE, "Permissive - Warn on non-critical"),
        (StartupValidationMode.EMERGENCY, "Emergency - Minimal checks only")
    ]
    
    for mode, description in modes:
        print(f"\nTesting {description}:")
        validator = ConfigurationStartupValidator(mode)
        is_valid, errors, warnings = validator.validate_startup_configuration()
        
        print(f"  Result: {'PASS' if is_valid else 'FAIL'}")
        print(f"  Errors: {len(errors)}, Warnings: {len(warnings)}")
        
        if errors and len(errors) <= 3:  # Show a few examples
            print("  Sample errors:")
            for error in errors[:3]:
                print(f"    - {error}")


def demonstrate_critical_status():
    """Demonstrate critical configuration status"""
    print("\n=== Critical Configuration Status Demo ===")
    
    status = get_critical_config_status()
    
    print(f"Found {len(status)} critical configurations:")
    
    for config_key, info in list(status.items())[:5]:  # Show first 5
        present_status = "PRESENT" if info["present"] else "MISSING"
        valid_status = "VALID" if info["valid"] else "INVALID"
        
        print(f"\n{config_key}:")
        print(f"  Status: {present_status} & {valid_status}")
        print(f"  Impact: {info['impact_level']}")
        print(f"  Required by: {', '.join(info['required_by'][:2])}{'...' if len(info['required_by']) > 2 else ''}")
        print(f"  Fallback allowed: {'Yes' if info['fallback_allowed'] else 'No'}")


def main():
    """Run all demonstrations"""
    print("ConfigDependencyMap Integration Demonstration")
    print("=" * 60)
    
    print("This demonstration shows how ConfigDependencyMap protects")
    print("against configuration deletions and validates configuration values.")
    
    try:
        # Set environment for testing
        os.environ["ENVIRONMENT"] = "testing"
        
        demonstrate_deletion_protection()
        demonstrate_value_validation()
        demonstrate_impact_analysis()
        demonstrate_consistency_check()
        demonstrate_startup_validation()
        demonstrate_critical_status()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] ConfigDependencyMap integration demonstration complete!")
        print("\nKey Integration Points:")
        print("  1. Pre-deployment validation: scripts/check_config_before_deploy.py")
        print("  2. Regression testing: tests/regression/test_config_regression.py")
        print("  3. Configuration validator: app/core/configuration/validator.py")
        print("  4. Startup validation: app/core/configuration/startup_validator.py")
        
    except Exception as e:
        print(f"\nDemonstration failed with error: {e}")
        return False
        
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)