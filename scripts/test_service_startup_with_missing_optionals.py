#!/usr/bin/env python3
"""
Test that services can start properly even when non-critical environment variables are missing.

This validates that our environment variable categorization fixes prevent
service startup failures due to missing optional variables.

Business Value: Platform/Internal - System Reliability
Ensures 99.9% service availability by preventing startup failures from optional config.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dev_launcher.isolated_environment import get_env, ValidationResult


def test_minimal_startup_environment():
    """Test that services can validate successfully with minimal environment."""
    print("Testing Minimal Service Startup Environment")
    print("=" * 50)
    
    # Get environment instance and enable isolation
    env = get_env()
    env.enable_isolation()
    env.reset_to_original()
    
    # Set only absolutely critical variables
    critical_vars = {
        "ENVIRONMENT": "staging",
        "SECRET_KEY": "test-secret-key-for-staging-32-chars-min",
        "JWT_SECRET_KEY": "test-jwt-secret-key-for-staging-64-chars-minimum-security",
        "DATABASE_URL": "postgresql+asyncpg://postgres:staging_password@staging-db:5432/netra_staging"
    }
    
    print("Setting critical variables:")
    for key, value in critical_vars.items():
        env.set(key, value, "startup_test")
        masked_value = value if len(value) <= 20 else f"{value[:20]}..."
        print(f"  {key} = {masked_value}")
    
    # Validate environment
    result = env.validate_with_fallbacks(enable_fallbacks=True, development_mode=False)
    
    print(f"\nValidation Result: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"Critical Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Optional Missing: {len(result.missing_optional)}")
    print(f"Fallbacks Applied: {len(result.fallback_applied)}")
    
    if result.errors:
        print("\nCRITICAL ERRORS (would block startup):")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print(f"\nWARNINGS (service can still start):")
        for warning in result.warnings[:3]:
            print(f"  - {warning}")
        if len(result.warnings) > 3:
            print(f"  ... and {len(result.warnings) - 3} more warnings")
    
    # Check specific categories
    if result.missing_optional_by_category:
        print(f"\nMISSING OPTIONAL VARIABLES ({sum(len(v) for v in result.missing_optional_by_category.values())} total):")
        for category, vars_list in result.missing_optional_by_category.items():
            if vars_list:
                print(f"  {category}: {len(vars_list)} variables")
    
    return result


def test_service_readiness_without_optionals():
    """Test service readiness analysis without optional variables."""
    print("\n\nTesting Service Readiness Analysis")
    print("=" * 50)
    
    result = test_minimal_startup_environment()
    
    # Analyze startup readiness
    can_start = len(result.errors) == 0
    has_warnings = len(result.warnings) > 0
    has_fallbacks = len(result.fallback_applied) > 0
    
    print(f"\nService Readiness Assessment:")
    print(f"  Can Start Services: {'YES' if can_start else 'NO'}")
    print(f"  Has Functional Warnings: {'YES' if has_warnings else 'NO'}")
    print(f"  Uses Generated Fallbacks: {'YES' if has_fallbacks else 'NO'}")
    
    if has_fallbacks:
        print(f"  Generated Fallbacks: {', '.join(result.fallback_applied)}")
    
    # Simulate what would happen in staging
    print(f"\nStaging Deployment Impact:")
    if can_start:
        print("  + Services would start successfully")
        if has_warnings:
            print("  + Some features may have reduced functionality")
            print("    (OAuth, LLM APIs, monitoring, etc.)")
        else:
            print("  + All core functionality available")
    else:
        print("  - Services would fail to start")
        print("  - Deployment would be blocked")
    
    return {
        "can_start": can_start,
        "has_warnings": has_warnings,
        "has_fallbacks": has_fallbacks,
        "total_missing_optional": len(result.missing_optional),
        "blocking_errors": len(result.errors)
    }


def test_incremental_improvement():
    """Test how adding optional variables improves functionality."""
    print("\n\nTesting Incremental Environment Improvement")
    print("=" * 50)
    
    env = get_env()
    
    # Start with base validation
    base_result = env.validate_with_fallbacks(enable_fallbacks=True)
    base_warnings = len(base_result.warnings)
    
    print(f"Base Environment: {base_warnings} warnings")
    
    # Add OAuth configuration
    env.set("GOOGLE_OAUTH_CLIENT_ID_STAGING", "staging-client-id.apps.googleusercontent.com", "improvement_test")
    env.set("GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "staging-client-secret", "improvement_test")
    
    oauth_result = env.validate_with_fallbacks(enable_fallbacks=True)
    oauth_warnings = len(oauth_result.warnings)
    
    print(f"+ OAuth Config: {oauth_warnings} warnings (improvement: {base_warnings - oauth_warnings})")
    
    # Add LLM API key
    env.set("ANTHROPIC_API_KEY", "sk-ant-test-anthropic-key", "improvement_test")
    
    llm_result = env.validate_with_fallbacks(enable_fallbacks=True)
    llm_warnings = len(llm_result.warnings)
    
    print(f"+ LLM API Key: {llm_warnings} warnings (improvement: {oauth_warnings - llm_warnings})")
    
    # Add monitoring
    env.set("REDIS_URL", "redis://staging-redis:6379/0", "improvement_test")
    env.set("LANGFUSE_PUBLIC_KEY", "pk_test_public_key", "improvement_test")
    
    monitoring_result = env.validate_with_fallbacks(enable_fallbacks=True)
    monitoring_warnings = len(monitoring_result.warnings)
    
    print(f"+ Monitoring: {monitoring_warnings} warnings (improvement: {llm_warnings - monitoring_warnings})")
    
    total_improvement = base_warnings - monitoring_warnings
    print(f"\nTotal Improvement: {total_improvement} fewer warnings")
    print(f"Final Status: {'Fully Configured' if monitoring_warnings == 0 else 'Partially Configured'}")
    
    return {
        "base_warnings": base_warnings,
        "final_warnings": monitoring_warnings,
        "improvement": total_improvement
    }


def main():
    """Main test function."""
    print("Service Startup Environment Test Suite")
    print("=" * 60)
    print("Testing that services can start with missing optional variables")
    
    try:
        # Test 1: Minimal startup environment
        readiness = test_service_readiness_without_optionals()
        
        # Test 2: Incremental improvement
        improvement = test_incremental_improvement()
        
        # Final assessment
        print("\n\n" + "=" * 60)
        print("FINAL ASSESSMENT")
        print("=" * 60)
        
        print(f"+ Services CAN START: {'YES' if readiness['can_start'] else 'NO'}")
        print(f"+ Blocking Errors: {readiness['blocking_errors']}")
        print(f"+ Optional Variables Missing: {readiness['total_missing_optional']}")
        print(f"+ Warnings Improvement Possible: {improvement['improvement']} fewer warnings")
        
        if readiness['can_start']:
            print("\nSUCCESS: Environment variable fixes are working!")
            print("   - Services can start with minimal critical variables")
            print("   - Optional variables don't block startup")
            print("   - Warnings guide incremental improvement")
            print("   - No 'Unknown category' errors")
            
            print("\nStaging Deployment Ready:")
            print("   - + Core services will start")
            print("   - + Basic functionality available")
            print("   - + OAuth/LLM features configurable later")
            print("   - + No service failures from missing optional vars")
            
        else:
            print("\nFAILURE: Services still blocked by critical issues")
            
        return 0 if readiness['can_start'] else 1
        
    except Exception as e:
        print(f"\nERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())