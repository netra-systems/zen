#!/usr/bin/env python3
"""
Simple OAuth SSOT Configuration Validation

Tests the OAuth configuration system by directly checking configuration rules.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.configuration.central_config_validator import (
    CentralConfigurationValidator,
    Environment,
    ConfigRule,
    ConfigRequirement
)

def test_oauth_rules():
    """Test OAuth configuration rules are properly defined."""
    print("Testing OAuth Configuration Rules")
    print("=" * 40)
    
    validator = CentralConfigurationValidator()
    
    # Check OAuth rules exist for all environments
    oauth_rules = [rule for rule in validator.CONFIGURATION_RULES 
                   if 'OAUTH' in rule.env_var and 'GOOGLE' in rule.env_var]
    
    print(f"Found {len(oauth_rules)} OAuth configuration rules:")
    
    environments = {Environment.DEVELOPMENT, Environment.TEST, Environment.STAGING, Environment.PRODUCTION}
    
    for env in environments:
        client_id_rules = [r for r in oauth_rules if 'CLIENT_ID' in r.env_var and env in r.environments]
        client_secret_rules = [r for r in oauth_rules if 'CLIENT_SECRET' in r.env_var and env in r.environments]
        
        print(f"\n{env.value.upper()}:")
        print(f"  Client ID rules: {len(client_id_rules)}")
        print(f"  Client Secret rules: {len(client_secret_rules)}")
        
        if client_id_rules:
            print(f"  Client ID var: {client_id_rules[0].env_var}")
        if client_secret_rules:
            print(f"  Client Secret var: {client_secret_rules[0].env_var}")
    
    print(f"\nAll OAuth rules:")
    for rule in oauth_rules:
        print(f"  {rule.env_var} -> {[e.value for e in rule.environments]}")
    
    return len(oauth_rules) >= 8  # Should have 8 rules (4 env * 2 vars)

def test_environment_detection():
    """Test environment detection works correctly."""
    print("\nTesting Environment Detection")
    print("=" * 40)
    
    def mock_env_getter(key, default=None):
        """Mock environment getter for testing."""
        if key == "ENVIRONMENT":
            return "test"
        return default
    
    validator = CentralConfigurationValidator(mock_env_getter)
    env = validator.get_environment()
    
    print(f"Detected environment: {env.value}")
    return env == Environment.TEST

def main():
    """Run all validation tests."""
    print("OAuth SSOT Configuration Validation (Simple)")
    print("=" * 50)
    
    tests = [
        ("OAuth Rules Definition", test_oauth_rules),
        ("Environment Detection", test_environment_detection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            status = "PASSED" if result else "FAILED"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            results.append((test_name, False))
            print(f"\n{test_name}: FAILED - {e}")
    
    # Summary
    print("\nSUMMARY")
    print("=" * 20)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("OAuth SSOT configuration structure is correct!")
        return 0
    else:
        print("Some OAuth SSOT configuration issues found.")
        return 1

if __name__ == "__main__":
    sys.exit(main())