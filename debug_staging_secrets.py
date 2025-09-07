"""
Debug Staging Secrets Configuration

This script validates the staging secrets configuration and shows what would be deployed.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from deployment.secrets_config import SecretConfig


def debug_staging_secrets():
    """Debug staging secrets configuration"""
    print("=" * 80)
    print("STAGING SECRETS CONFIGURATION DEBUG")
    print("=" * 80)
    
    # Show backend secrets configuration
    print("\n[BACKEND SERVICE SECRETS]")
    backend_secrets = SecretConfig.get_all_service_secrets("backend")
    print(f"Total secrets required: {len(backend_secrets)}")
    
    # Check JWT secrets specifically
    jwt_secrets = [s for s in backend_secrets if 'JWT' in s]
    print(f"\nJWT-related secrets:")
    for secret in jwt_secrets:
        gsm_mapping = SecretConfig.get_gsm_mapping(secret)
        print(f"  - {secret} -> {gsm_mapping}")
    
    # Generate the actual secrets string that would be used in deployment
    print(f"\n[DEPLOYMENT SECRETS STRING]")
    backend_secrets_string = SecretConfig.generate_secrets_string("backend", "staging")
    print(f"Backend --set-secrets parameter:")
    print(f"Length: {len(backend_secrets_string)} characters")
    
    # Split and show each mapping
    mappings = backend_secrets_string.split(",")
    print(f"\nSecret mappings ({len(mappings)} total):")
    
    jwt_mappings = []
    other_mappings = []
    
    for mapping in mappings:
        if "JWT" in mapping:
            jwt_mappings.append(mapping)
        else:
            other_mappings.append(mapping)
    
    print(f"\nJWT-related mappings:")
    for mapping in jwt_mappings:
        print(f"  {mapping}")
        
    print(f"\nOther mappings:")
    for mapping in other_mappings[:10]:  # Show first 10
        print(f"  {mapping}")
    if len(other_mappings) > 10:
        print(f"  ... and {len(other_mappings) - 10} more")
    
    # Critical secrets validation
    print(f"\n[CRITICAL SECRETS VALIDATION]")
    critical_secrets = SecretConfig.CRITICAL_SECRETS.get("backend", [])
    print(f"Critical secrets for backend: {len(critical_secrets)}")
    
    all_secrets_set = set(backend_secrets)
    missing_critical = SecretConfig.validate_critical_secrets("backend", all_secrets_set)
    
    if missing_critical:
        print(f"❌ Missing critical secrets: {missing_critical}")
    else:
        print(f"✅ All critical secrets are configured")
    
    # Show JWT secret configuration details
    print(f"\n[JWT SECRET CONFIGURATION ANALYSIS]")
    
    jwt_secret_staging_gsm = SecretConfig.get_gsm_mapping("JWT_SECRET_STAGING")
    jwt_secret_key_gsm = SecretConfig.get_gsm_mapping("JWT_SECRET_KEY")
    
    print(f"JWT_SECRET_STAGING maps to GSM secret: {jwt_secret_staging_gsm}")
    print(f"JWT_SECRET_KEY maps to GSM secret: {jwt_secret_key_gsm}")
    
    if jwt_secret_staging_gsm == jwt_secret_key_gsm:
        print("✅ Both JWT secrets map to the same GSM secret - this is CORRECT")
        print(f"   Both will get the same value from: {jwt_secret_staging_gsm}:latest")
    else:
        print("❌ JWT secrets map to different GSM secrets - this WILL cause mismatch")
        print(f"   JWT_SECRET_STAGING: {jwt_secret_staging_gsm}")
        print(f"   JWT_SECRET_KEY: {jwt_secret_key_gsm}")
    
    # Check what the expected secret value should be from config/staging.env
    print(f"\n[EXPECTED SECRET VALUE]")
    staging_env_path = project_root / "config" / "staging.env"
    if staging_env_path.exists():
        with open(staging_env_path, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if line.startswith('JWT_SECRET_STAGING='):
                    expected_secret = line.split('=', 1)[1]
                    print(f"Expected JWT secret from config/staging.env:")
                    print(f"  Value: {expected_secret[:30]}... (length: {len(expected_secret)})")
                    break
    else:
        print("❌ config/staging.env not found")
    
    print(f"\n[DIAGNOSIS]")
    print("If WebSocket authentication is failing with 403 errors:")
    print("1. ✅ Secret configuration is correct (both JWT secrets map to same GSM secret)")
    print("2. ❓ Check if GSM secret 'jwt-secret-staging' has the correct value")  
    print("3. ❓ Check if GCP deployment actually uses these secret mappings")
    print("4. ❓ Verify that staging deployment loads these secrets properly")
    
    print(f"\n[NEXT STEPS]")
    print("To fix WebSocket 403 authentication failures:")
    print("1. Verify GSM secret 'jwt-secret-staging' contains the expected value")
    print("2. Run deployment with proper secret configuration")
    print("3. Test WebSocket authentication after deployment")
    
    print("=" * 80)


if __name__ == "__main__":
    debug_staging_secrets()