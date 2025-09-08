#!/usr/bin/env python3
"""
CRITICAL DEBUG SCRIPT: Environment Detection Analysis for GCP Staging

This script analyzes the environment variables available in the current environment
to understand why the staging-safe validation might not be triggering correctly.
"""

import os
import json
from shared.isolated_environment import get_env

def analyze_environment():
    """Analyze current environment for staging detection issues."""
    
    print("ENVIRONMENT ANALYSIS FOR STAGING DETECTION")
    print("=" * 60)
    
    # Get environment using our SSOT method
    try:
        env = get_env()
        print("Successfully got environment using get_env()")
    except Exception as e:
        print(f"Failed to get environment: {e}")
        env = {}
    
    # Check all the environment variables we use for staging detection
    staging_vars = {
        "ENVIRONMENT": env.get("ENVIRONMENT", "<NOT SET>"),
        "K_SERVICE": env.get("K_SERVICE", "<NOT SET>"),
        "K_REVISION": env.get("K_REVISION", "<NOT SET>"),
        "K_CONFIGURATION": env.get("K_CONFIGURATION", "<NOT SET>"),
        "GOOGLE_CLOUD_PROJECT": env.get("GOOGLE_CLOUD_PROJECT", "<NOT SET>"),
        "GAE_SERVICE": env.get("GAE_SERVICE", "<NOT SET>"),
        "CLOUD_RUN_INSTANCE_ID": env.get("CLOUD_RUN_INSTANCE_ID", "<NOT SET>"),
        "PORT": env.get("PORT", "<NOT SET>"),
        "E2E_TESTING": env.get("E2E_TESTING", "<NOT SET>"),
        "PYTEST_RUNNING": env.get("PYTEST_RUNNING", "<NOT SET>"),
        "STAGING_E2E_TEST": env.get("STAGING_E2E_TEST", "<NOT SET>"),
        "E2E_TEST_ENV": env.get("E2E_TEST_ENV", "<NOT SET>"),
        "TESTING": env.get("TESTING", "<NOT SET>"),
    }
    
    print("\nSTAGING DETECTION VARIABLES:")
    for var, value in staging_vars.items():
        print(f"  {var}: {value}")
    
    # Replicate our NEW ultra-defensive detection logic
    current_env = env.get("ENVIRONMENT", "unknown").lower()
    
    # Enhanced GCP detection
    is_gcp_cloud_run = bool(
        env.get("K_SERVICE") or        # Standard GCP Cloud Run service indicator
        env.get("K_REVISION") or       # Cloud Run revision indicator
        env.get("K_CONFIGURATION") or  # Cloud Run configuration indicator
        env.get("GAE_SERVICE") or      # Google App Engine service indicator
        env.get("CLOUD_RUN_INSTANCE_ID")  # Additional Cloud Run indicator
    )
    
    is_gcp_project = bool(env.get("GOOGLE_CLOUD_PROJECT"))
    
    # Enhanced staging detection with multiple patterns
    is_staging_explicit = current_env == "staging"
    is_staging_by_project = bool(env.get("GOOGLE_CLOUD_PROJECT") and "staging" in env.get("GOOGLE_CLOUD_PROJECT", "").lower())
    is_staging_by_service = bool(env.get("K_SERVICE") and "staging" in env.get("K_SERVICE", "").lower())
    
    # ULTRA DEFENSIVE: Consider it staging if it's GCP and has staging indicators OR if it's cloud deployment
    is_staging = is_staging_explicit or is_staging_by_project or is_staging_by_service
    
    # Cloud Run detection includes ANY GCP indicator
    is_cloud_run = is_gcp_cloud_run or is_gcp_project or (env.get("PORT") and current_env in ["staging", "production"])
    
    # Enhanced E2E testing detection with more patterns
    is_e2e_testing = (
        env.get("E2E_TESTING", "0") == "1" or 
        env.get("PYTEST_RUNNING", "0") == "1" or
        env.get("STAGING_E2E_TEST", "0") == "1" or
        env.get("E2E_TEST_ENV") == "staging" or
        env.get("TESTING", "0") == "1" or
        env.get("TESTING", "").lower() == "true"  # Handle "true" string values
    )
    
    # ULTRA DEFENSIVE: If we detect ANY cloud/staging/testing indicators, use staging-safe validation
    ultra_defensive_staging = (
        is_staging or 
        is_cloud_run or 
        is_e2e_testing or
        is_gcp_project or  # ANY GCP project indicator
        current_env in ["staging", "test", "testing", "dev", "development"] or  # Known safe environments
        env.get("PORT") is not None  # Any service with PORT (likely deployed)
    )
    
    will_use_staging_safe = ultra_defensive_staging
    
    print(f"\nDETECTION RESULTS (ULTRA DEFENSIVE):")
    print(f"  current_env: {current_env}")
    print(f"  is_gcp_cloud_run: {is_gcp_cloud_run}")
    print(f"  is_gcp_project: {is_gcp_project}")
    print(f"  is_staging_explicit: {is_staging_explicit}")
    print(f"  is_staging_by_project: {is_staging_by_project}")
    print(f"  is_staging_by_service: {is_staging_by_service}")
    print(f"  is_staging: {is_staging}")
    print(f"  is_cloud_run: {is_cloud_run}")
    print(f"  is_e2e_testing: {is_e2e_testing}")
    print(f"  ultra_defensive_staging: {ultra_defensive_staging}")
    print(f"  WILL USE STAGING-SAFE VALIDATION: {will_use_staging_safe}")
    
    if not will_use_staging_safe:
        print(f"\nCRITICAL ISSUE DETECTED:")
        print(f"   Environment will use STRICT validation instead of staging-safe!")
        print(f"   This explains why WebSocket connections are failing with 'Factory SSOT validation failed'")
        
        print(f"\nSOLUTIONS:")
        if not is_staging and current_env != "unknown":
            print(f"   - Set ENVIRONMENT=staging (currently: {current_env})")
        if not is_cloud_run:
            print(f"   - Ensure GCP Cloud Run environment variables are present")
            print(f"   - Expected: K_SERVICE, K_REVISION, or GOOGLE_CLOUD_PROJECT")
    else:
        print(f"\nEnvironment detection looks correct - issue must be elsewhere")
    
    # Check all environment variables for additional context
    print(f"\nALL ENVIRONMENT VARIABLES (first 20):")
    all_env_vars = dict(os.environ)
    sorted_vars = sorted(all_env_vars.items())[:20]
    for var, value in sorted_vars:
        # Mask potentially sensitive values
        if any(sensitive in var.upper() for sensitive in ["SECRET", "KEY", "PASSWORD", "TOKEN"]):
            display_value = "<MASKED>"
        else:
            display_value = value
        print(f"  {var}: {display_value}")
    
    if len(all_env_vars) > 20:
        print(f"  ... and {len(all_env_vars) - 20} more variables")

if __name__ == "__main__":
    analyze_environment()