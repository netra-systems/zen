from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Verify Auth Configuration Script
Checks that auth service URLs are properly configured for each environment
"""

import os
import sys
from typing import Dict, List, Tuple

import requests


def check_auth_service_endpoints(env: str) -> Tuple[str, List[str], List[str]]:
    """Check auth service endpoints for an environment."""
    if env == 'staging':
        # CRITICAL DOMAIN CONFIGURATION UPDATE (Issue #1278): Use correct staging domains
        base_url = 'https://staging.netrasystems.ai'
        frontend_url = 'https://staging.netrasystems.ai'
    elif env == 'production':
        base_url = 'https://auth.netrasystems.ai'
        frontend_url = 'https://netrasystems.ai'
    else:
        base_url = 'http://localhost:8081'
        frontend_url = 'http://localhost:3000'
    
    endpoints = [
        f"{base_url}/auth/config",
        f"{base_url}/auth/login",
        f"{base_url}/auth/callback",
        f"{base_url}/auth/logout",
        f"{base_url}/auth/token",
        f"{base_url}/auth/me",
    ]
    
    redirect_uris = [
        f"{frontend_url}/auth/callback",
        f"{base_url}/auth/callback",
    ]
    
    return base_url, endpoints, redirect_uris

def verify_environment_config(env: str) -> Dict[str, any]:
    """Verify configuration for an environment."""
    base_url, endpoints, redirect_uris = check_auth_service_endpoints(env)
    
    print(f"\n{'='*60}")
    print(f"Checking {env.upper()} Environment")
    print(f"{'='*60}")
    print(f"Auth Service URL: {base_url}")
    
    results = {
        'environment': env,
        'base_url': base_url,
        'endpoints': {},
        'redirect_uris': redirect_uris,
        'errors': []
    }
    
    print("\nExpected Endpoints:")
    for endpoint in endpoints:
        print(f"  - {endpoint}")
        results['endpoints'][endpoint] = 'configured'
    
    print("\nExpected Redirect URIs:")
    for uri in redirect_uris:
        print(f"  - {uri}")
    
    # Check OAuth configuration
    print("\nOAuth Configuration:")
    if env == 'staging':
        client_id_var = 'GOOGLE_OAUTH_CLIENT_ID_STAGING'
        client_secret_var = 'GOOGLE_OAUTH_CLIENT_SECRET_STAGING'
    elif env == 'production':
        client_id_var = 'GOOGLE_OAUTH_CLIENT_ID_PROD'
        client_secret_var = 'GOOGLE_OAUTH_CLIENT_SECRET_PROD'
    else:
        client_id_var = 'GOOGLE_OAUTH_CLIENT_ID_DEV'
        client_secret_var = 'GOOGLE_OAUTH_CLIENT_SECRET_DEV'
    
    client_id = get_env().get(client_id_var) or get_env().get('GOOGLE_CLIENT_ID')
    client_secret = get_env().get(client_secret_var) or get_env().get('GOOGLE_CLIENT_SECRET')
    
    if client_id:
        print(f"  [OK] Client ID configured ({client_id_var})")
        results['oauth_client_id'] = 'configured'
    else:
        print(f"  [MISSING] Client ID NOT configured ({client_id_var})")
        results['errors'].append(f"Missing {client_id_var}")
    
    if client_secret:
        print(f"  [OK] Client Secret configured ({client_secret_var})")
        results['oauth_client_secret'] = 'configured'
    else:
        print(f"  [MISSING] Client Secret NOT configured ({client_secret_var})")
        results['errors'].append(f"Missing {client_secret_var}")
    
    return results

def main():
    """Main verification function."""
    print("\nAuth Service Configuration Verification")
    print("="*60)
    
    environments = ['development', 'staging', 'production']
    all_results = {}
    
    for env in environments:
        results = verify_environment_config(env)
        all_results[env] = results
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for env, results in all_results.items():
        if results['errors']:
            print(f"\n{env.upper()}: [ISSUES FOUND]")
            for error in results['errors']:
                print(f"  - {error}")
        else:
            print(f"\n{env.upper()}: [OK] Properly configured")
    
    print("\nIMPORTANT NOTES:")
    print("1. Ensure OAuth credentials are set in environment variables")
    print("2. Update Google OAuth console with correct redirect URIs")
    print("3. Auth service must be deployed at the configured URLs")
    print("4. Frontend must use auth service for all auth operations")
    
    # Return exit code based on errors
    has_errors = any(results['errors'] for results in all_results.values())
    return 1 if has_errors else 0

if __name__ == "__main__":
    sys.exit(main())
