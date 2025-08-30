#!/usr/bin/env python3
"""
Verify JWT secret configuration across all environments.

This script checks that JWT secrets have the correct environment-specific suffixes
for test, dev, staging, and production (GCP) environments.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.secret_mappings import get_secret_mappings

# Expected JWT secret patterns for each environment
EXPECTED_JWT_SECRETS = {
    "test": {
        "jwt-secret-key-test": "JWT_SECRET_KEY",
        "jwt-secret-test": "JWT_SECRET",
        "fernet-key-test": "FERNET_KEY"
    },
    "dev": {
        "jwt-secret-key-dev": "JWT_SECRET_KEY",
        "jwt-secret-dev": "JWT_SECRET",
        "fernet-key-dev": "FERNET_KEY"
    },
    "staging": {
        "jwt-secret-key-staging": "JWT_SECRET_KEY",
        "jwt-secret-staging": "JWT_SECRET",
        "fernet-key-staging": "FERNET_KEY"
    },
    "production": {
        "jwt-secret-key-production": "JWT_SECRET_KEY",
        "jwt-secret-production": "JWT_SECRET",
        "fernet-key-production": "FERNET_KEY"
    }
}

def verify_environment_secrets(env: str) -> Tuple[bool, List[str]]:
    """
    Verify JWT secrets for a specific environment.
    
    Args:
        env: Environment name
        
    Returns:
        Tuple of (success, list of issues)
    """
    issues = []
    mappings = get_secret_mappings(env)
    expected = EXPECTED_JWT_SECRETS.get(env, {})
    
    # Check if mappings exist for the environment
    if not mappings and env in ["staging", "production"]:
        issues.append(f"No secret mappings found for {env} environment")
        return False, issues
    
    # Check each expected JWT secret
    for secret_name, env_var in expected.items():
        if secret_name not in mappings:
            issues.append(f"Missing: {secret_name} -> {env_var}")
        elif mappings[secret_name] != env_var:
            issues.append(f"Mismatch: {secret_name} maps to '{mappings[secret_name]}' instead of '{env_var}'")
    
    # Check for any JWT secrets without proper suffixes
    for secret_name, env_var in mappings.items():
        if "jwt" in secret_name.lower() or "fernet" in secret_name.lower():
            if not secret_name.endswith(f"-{env}") and not secret_name.endswith(f"-{env[:4]}"):  # Handle 'production' -> 'prod'
                # Special case for production which might use 'prod' suffix
                if env == "production" and secret_name.endswith("-prod"):
                    continue
                issues.append(f"Invalid suffix: {secret_name} should end with '-{env}'")
    
    return len(issues) == 0, issues

def check_deployment_script() -> Tuple[bool, List[str]]:
    """
    Check deployment script for correct JWT secret references.
    
    Returns:
        Tuple of (success, list of issues)
    """
    issues = []
    deploy_script = Path(__file__).parent / "deploy_to_gcp.py"
    
    if not deploy_script.exists():
        issues.append("deploy_to_gcp.py not found")
        return False, issues
    
    content = deploy_script.read_text(encoding='utf-8')
    
    # Check staging deployment
    if "JWT_SECRET_KEY=jwt-secret-key-staging:latest" not in content:
        issues.append("Staging deployment missing JWT_SECRET_KEY=jwt-secret-key-staging:latest")
    if "JWT_SECRET=jwt-secret-staging:latest" not in content:
        issues.append("Staging deployment missing JWT_SECRET=jwt-secret-staging:latest")
    
    # Check for incorrect non-suffixed secrets
    if "JWT_SECRET_KEY=jwt-secret-key:latest" in content:
        issues.append("Deployment script uses non-suffixed jwt-secret-key (should have environment suffix)")
    if "JWT_SECRET=jwt-secret:latest" in content:
        issues.append("Deployment script uses non-suffixed jwt-secret (should have environment suffix)")
    
    return len(issues) == 0, issues

def main():
    """Main verification function."""
    print("JWT Secret Suffix Verification")
    print("=" * 50)
    
    all_passed = True
    
    # Check each environment
    for env in ["test", "dev", "staging", "production"]:
        print(f"\n{env.upper()} Environment:")
        print("-" * 30)
        
        passed, issues = verify_environment_secrets(env)
        
        if passed:
            print(f"[PASS] All JWT secrets have correct suffixes")
        else:
            print(f"[FAIL] Issues found:")
            for issue in issues:
                print(f"   - {issue}")
            all_passed = False
    
    # Check deployment script
    print(f"\nDeployment Script:")
    print("-" * 30)
    
    passed, issues = check_deployment_script()
    
    if passed:
        print(f"[PASS] Deployment script uses correct JWT secret names")
    else:
        print(f"❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("[SUCCESS] All JWT secrets have correct environment suffixes")
        return 0
    else:
        print("[FAILURE] JWT secret configuration issues detected")
        print("\nRequired Actions:")
        print("1. Ensure all JWT secrets use environment-specific suffixes")
        print("2. Update secret_mappings.py with correct mappings")
        print("3. Verify deployment scripts use suffixed secret names")
        print("4. Create missing secrets in Google Secret Manager with proper names")
        return 1

if __name__ == "__main__":
    sys.exit(main())