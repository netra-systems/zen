from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Secret Manager Diagnostic Script

This script helps diagnose secret manager issues in staging and production environments.
It provides detailed information about GCP connectivity, secret availability, and fallbacks.

Usage:
    python scripts/diagnose_secret_manager.py [--environment staging|production]

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity, System Reliability
- Value Impact: Reduces time to diagnose and fix secret manager issues
- Strategic Impact: Faster resolution of staging deployment issues
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def diagnose_netra_backend_secret_manager(environment: str = None):
    """Diagnose netra_backend SecretManager status."""
    print("=== Netra Backend SecretManager Diagnostic ===")
    
    if environment:
        os.environ["ENVIRONMENT"] = environment
    
    try:
        from netra_backend.app.core.configuration.secrets import SecretManager
        
        secret_manager = SecretManager()
        summary = secret_manager.get_secret_summary()
        
        print(f"Environment: {summary['environment']}")
        print(f"Secrets Loaded: {summary['secrets_loaded']}")
        print(f"Required Secrets: {summary['required_secrets']}")
        print(f"GCP Available: {summary['gcp_available']}")
        print(f"GCP Project ID: {summary.get('gcp_project_id', 'N/A')}")
        print(f"GCP Disabled: {summary.get('gcp_disabled', False)}")
        print(f"Cache Valid: {summary['cache_valid']}")
        
        if summary.get('gcp_library_available') is not None:
            print(f"GCP Library Available: {summary['gcp_library_available']}")
        
        if summary.get('env_variables'):
            print("\nEnvironment Variables:")
            for key, value in summary['env_variables'].items():
                print(f"  {key}: {value}")
        
        # Try to load secrets
        print("\n--- Testing Secret Loading ---")
        try:
            secrets = secret_manager.load_all_secrets()
            print(f"Successfully loaded {len(secrets)} secrets")
            
            # Check for critical secrets
            critical_secrets = ["JWT_SECRET_KEY", "FERNET_KEY", "SERVICE_SECRET"]
            missing_critical = []
            for secret in critical_secrets:
                if secret in secrets and secrets[secret]:
                    print(f"[OK] {secret}: Available")
                else:
                    print(f"[MISSING] {secret}: Missing")
                    missing_critical.append(secret)
            
            if missing_critical:
                print(f"\n[WARNING] Missing critical secrets: {', '.join(missing_critical)}")
            else:
                print("\n[OK] All critical secrets available")
                
        except Exception as e:
            print(f"[ERROR] ERROR loading secrets: {e}")
            return False
            
    except ImportError as e:
        print(f"[ERROR] ERROR importing SecretManager: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] UNEXPECTED ERROR: {e}")
        return False
    
    return True


def diagnose_shared_secret_manager_builder(environment: str = None):
    """Diagnose shared SecretManagerBuilder status."""
    print("\n=== Shared SecretManagerBuilder Diagnostic ===")
    
    env_vars = {"ENVIRONMENT": environment} if environment else None
    
    try:
        from shared.secret_manager_builder import SecretManagerBuilder
        
        builder = SecretManagerBuilder(env_vars=env_vars, service="diagnostic")
        debug_info = builder.get_debug_info()
        
        print(f"Environment: {debug_info['environment']}")
        print(f"Service: {debug_info['service']}")
        print(f"Project ID: {debug_info['project_id']}")
        
        # GCP connectivity
        gcp_info = debug_info['gcp_connectivity']
        print(f"GCP Connectivity: {'[OK] Valid' if gcp_info['is_valid'] else '[ERROR] Failed'}")
        if not gcp_info['is_valid'] and gcp_info.get('error'):
            print(f"  Error: {gcp_info['error']}")
        
        # Validation
        validation_info = debug_info['validation']
        print(f"Validation: {'[OK] Valid' if validation_info['is_valid'] else '[ERROR] Failed'}")
        if validation_info['error_count'] > 0:
            print(f"  Errors ({validation_info['error_count']}):")
            for error in validation_info['errors']:
                print(f"    - {error}")
        
        if validation_info['warning_count'] > 0:
            print(f"  Warnings ({validation_info['warning_count']}):")
            for warning in validation_info['warnings']:
                print(f"    - {warning}")
        
        # Features
        features = debug_info['features']
        print(f"\nFeatures:")
        print(f"  GCP Enabled: {features['gcp_enabled']}")
        print(f"  Encryption Available: {features['encryption_available']}")
        print(f"  Fallbacks Allowed: {features['fallbacks_allowed']}")
        
        # Cache stats
        cache_stats = debug_info['cache_stats']
        print(f"\nCache:")
        print(f"  Cached Secrets: {cache_stats['cached_secrets']}")
        print(f"  Cache Enabled: {cache_stats['cache_enabled']}")
        
        # Test secret loading
        print("\n--- Testing Secret Loading ---")
        try:
            secrets = builder.load_all_secrets()
            print(f"Successfully loaded {len(secrets)} secrets")
            
            # Test individual secret access
            jwt_secret = builder.get_secret("JWT_SECRET_KEY")
            print(f"JWT Secret: {'[OK] Available' if jwt_secret else '[ERROR] Not available'}")
            
        except Exception as e:
            print(f"[ERROR] ERROR loading secrets: {e}")
            return False
            
    except ImportError as e:
        print(f"[ERROR] ERROR importing SecretManagerBuilder: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] UNEXPECTED ERROR: {e}")
        return False
    
    return True


def check_gcp_library():
    """Check if GCP Secret Manager library is installed."""
    print("\n=== GCP Library Check ===")
    
    try:
        import google.cloud.secretmanager
        print("[OK] google-cloud-secretmanager library is installed")
        
        # Check version
        try:
            import importlib.metadata
            version = importlib.metadata.version("google-cloud-secret-manager")
            print(f"   Version: {version}")
        except Exception:
            print("   Version: Unknown")
        
        return True
    except ImportError as e:
        print(f"[ERROR] google-cloud-secretmanager library not installed: {e}")
        print("   Install with: pip install google-cloud-secret-manager")
        return False


def check_environment_variables():
    """Check relevant environment variables."""
    print("\n=== Environment Variables Check ===")
    
    important_vars = [
        "ENVIRONMENT",
        "GCP_PROJECT_ID", 
        "GOOGLE_APPLICATION_CREDENTIALS",
        "DISABLE_GCP_SECRET_MANAGER",
        "LOAD_SECRETS",
        "JWT_SECRET_KEY",
        "FERNET_KEY",
        "SERVICE_SECRET"
    ]
    
    for var in important_vars:
        value = os.environ.get(var)
        if value:
            # Mask secret values for security
            if "SECRET" in var or "KEY" in var:
                masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
                print(f"  {var}: {masked_value}")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: NOT SET")


def provide_remediation_steps(environment: str):
    """Provide environment-specific remediation steps."""
    print(f"\n=== Remediation Steps for {environment.upper()} ===")
    
    if environment == "staging":
        print("1. Check Cloud Run service account IAM roles:")
        print("   - Secret Manager Secret Accessor")
        print("   - Cloud SQL Client (if using Cloud SQL)")
        print()
        print("2. Verify secrets exist in GCP Secret Manager:")
        print("   gcloud secrets list --project=netra-staging")
        print()
        print("3. Check Cloud Run environment variables:")
        print("   - GCP_PROJECT_ID should be set to 'netra-staging' or '701982941522'")
        print("   - ENVIRONMENT should be 'staging'")
        print()
        print("4. Test secret access from Cloud Run:")
        print("   gcloud secrets versions access latest --secret=jwt-secret-key-staging --project=netra-staging")
        print()
        print("5. Check deployment configuration in scripts/deploy_to_gcp.py")
        print("   Ensure all required secrets are mapped to environment variables")
    
    elif environment == "production":
        print("1. Check production service account IAM roles")
        print("2. Verify production secrets exist and are not placeholder values")
        print("3. Check production GCP project ID configuration")
        print("4. Ensure network connectivity to GCP APIs")
    
    else:
        print("For development environments:")
        print("1. Use .env.local file for local development")
        print("2. Set environment variables directly")
        print("3. GCP Secret Manager is disabled by default in development")


def main():
    """Main diagnostic function."""
    parser = argparse.ArgumentParser(description="Diagnose Secret Manager issues")
    parser.add_argument("--environment", "-e", choices=["staging", "production"], 
                       help="Environment to test (defaults to current environment)")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    if not args.json:
        print("Secret Manager Diagnostic Tool")
        print("=" * 50)
        
        # Check basic prerequisites
        gcp_lib_ok = check_gcp_library()
        check_environment_variables()
        
        # Diagnose secret managers
        netra_ok = diagnose_netra_backend_secret_manager(args.environment)
        shared_ok = diagnose_shared_secret_manager_builder(args.environment)
        
        # Overall status
        print("\n" + "=" * 50)
        if netra_ok and shared_ok and gcp_lib_ok:
            print("SECRET MANAGER STATUS: HEALTHY")
        else:
            print("SECRET MANAGER STATUS: ISSUES DETECTED")
            if args.environment:
                provide_remediation_steps(args.environment)
        
        return 0 if (netra_ok and shared_ok) else 1
    
    else:
        # JSON output for programmatic use
        result = {
            "gcp_library_available": False,
            "netra_backend_ok": False,
            "shared_builder_ok": False,
            "overall_status": "error"
        }
        
        try:
            result["gcp_library_available"] = check_gcp_library()
            result["netra_backend_ok"] = diagnose_netra_backend_secret_manager(args.environment)
            result["shared_builder_ok"] = diagnose_shared_secret_manager_builder(args.environment)
            
            if all([result["gcp_library_available"], result["netra_backend_ok"], result["shared_builder_ok"]]):
                result["overall_status"] = "healthy"
            else:
                result["overall_status"] = "degraded"
        except Exception as e:
            result["error"] = str(e)
        
        print(json.dumps(result, indent=2))
        return 0 if result["overall_status"] == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
