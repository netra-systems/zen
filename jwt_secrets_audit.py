#!/usr/bin/env python3
"""JWT Secrets Audit Script

This script audits JWT secret configuration across services to identify mismatches
that could cause authentication failures in staging.
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def load_env_file(file_path):
    """Load environment variables from a .env file"""
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    return env_vars

def audit_jwt_secrets():
    """Audit JWT secrets across different configurations"""
    print("🔍 JWT Secrets Audit Report")
    print("=" * 60)
    
    # Check different environment configurations
    env_files = [
        ('development', 'config/development.env'),
        ('staging', 'config/staging.env'),
        ('root', '.env'),
    ]
    
    jwt_secrets = {}
    service_secrets = {}
    
    for env_name, file_path in env_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            env_vars = load_env_file(full_path)
            jwt_secret = env_vars.get('JWT_SECRET_KEY', 'NOT_FOUND')
            service_secret = env_vars.get('SERVICE_SECRET', 'NOT_FOUND')
            
            print(f"\n📁 {env_name.upper()} ({file_path}):")
            print(f"  JWT_SECRET_KEY: {jwt_secret[:20]}...{jwt_secret[-10:] if len(jwt_secret) > 30 else jwt_secret}")
            print(f"  SERVICE_SECRET: {service_secret[:20]}...{service_secret[-10:] if len(service_secret) > 30 else service_secret}")
            print(f"  JWT Secret Length: {len(jwt_secret) if jwt_secret != 'NOT_FOUND' else 0}")
            
            jwt_secrets[env_name] = jwt_secret
            service_secrets[env_name] = service_secret
        else:
            print(f"\n📁 {env_name.upper()} ({file_path}): FILE NOT FOUND")
    
    # Check for inconsistencies
    print("\n🔍 JWT Secret Consistency Analysis:")
    print("-" * 40)
    
    unique_jwt_secrets = set(v for v in jwt_secrets.values() if v != 'NOT_FOUND')
    if len(unique_jwt_secrets) > 1:
        print("⚠️  WARNING: Multiple different JWT secrets found!")
        for env_name, secret in jwt_secrets.items():
            if secret != 'NOT_FOUND':
                print(f"  {env_name}: {secret[:20]}...{secret[-10:]}")
    elif len(unique_jwt_secrets) == 1:
        print("✅ All environments use the same JWT secret")
    else:
        print("❌ No JWT secrets found in any environment!")
    
    # Security validation
    print("\n🔒 Security Validation:")
    print("-" * 40)
    
    for env_name, secret in jwt_secrets.items():
        if secret == 'NOT_FOUND':
            continue
        
        print(f"\n{env_name.upper()}:")
        # Check length
        if len(secret) < 32:
            print(f"  ❌ JWT secret too short: {len(secret)} chars (minimum: 32)")
        else:
            print(f"  ✅ JWT secret length acceptable: {len(secret)} chars")
        
        # Check for insecure patterns (for staging/production)
        if env_name in ['staging']:
            insecure_patterns = ['default', 'secret', 'password', 'dev', 'test', 'demo', 'example', 'change', 'jwt']
            insecure_found = [pattern for pattern in insecure_patterns if pattern in secret.lower()]
            if insecure_found:
                print(f"  ⚠️  Contains potentially insecure patterns: {insecure_found}")
            else:
                print(f"  ✅ No insecure patterns detected")
    
    print("\n📊 Summary:")
    print("-" * 40)
    print(f"Total environments checked: {len(env_files)}")
    print(f"Environments with JWT secrets: {len([s for s in jwt_secrets.values() if s != 'NOT_FOUND'])}")
    print(f"Unique JWT secrets found: {len(unique_jwt_secrets)}")
    
    if len(unique_jwt_secrets) > 1:
        print("\n🚨 CRITICAL ISSUE: JWT secret mismatch detected!")
        print("   This will cause authentication failures between services.")
        print("   All services must use the same JWT_SECRET_KEY.")
        return False
    
    return True

if __name__ == "__main__":
    success = audit_jwt_secrets()
    sys.exit(0 if success else 1)