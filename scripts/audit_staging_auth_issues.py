#!/usr/bin/env python3
"""
Comprehensive audit of staging authentication issues.
Identifies why https://app.staging.netrasystems.ai/login is not working.
"""
import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Tuple


class StagingAuthAuditor:
    """Audit staging authentication configuration and issues"""
    
    def __init__(self):
        # Service URLs
        self.frontend_app_url = "https://app.staging.netrasystems.ai"
        self.frontend_direct_url = "https://netra-frontend-staging-701982941522.us-central1.run.app"
        self.backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"
        self.auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
        self.auth_subdomain = "https://auth.staging.netrasystems.ai"
        
        self.issues_found = []
        
    async def audit_domain_routing(self) -> Dict:
        """Check if app.staging.netrasystems.ai routes correctly"""
        print("\n1. DOMAIN ROUTING AUDIT")
        print("=" * 50)
        
        issues = []
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            # Check app subdomain
            try:
                print(f"Testing {self.frontend_app_url}...")
                response = await client.get(f"{self.frontend_app_url}/")
                print(f"  Status: {response.status_code}")
                print(f"  Headers: {dict(response.headers)}")
                
                if response.status_code == 404:
                    issues.append("app.staging.netrasystems.ai returns 404 - subdomain not configured")
                elif response.status_code >= 500:
                    issues.append(f"app.staging.netrasystems.ai returns {response.status_code} - server error")
                    
            except Exception as e:
                issues.append(f"Cannot reach app.staging.netrasystems.ai: {str(e)}")
                print(f"  ERROR: {str(e)}")
            
            # Check login page specifically
            try:
                print(f"\nTesting {self.frontend_app_url}/login...")
                response = await client.get(f"{self.frontend_app_url}/login")
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 404:
                    issues.append("/login route returns 404 - Next.js routing issue")
                    
            except Exception as e:
                issues.append(f"Cannot reach /login: {str(e)}")
                print(f"  ERROR: {str(e)}")
                
            # Compare with direct URL
            try:
                print(f"\nComparing with direct URL {self.frontend_direct_url}...")
                response = await client.get(self.frontend_direct_url)
                print(f"  Direct URL Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("  [INFO] Direct URL works but subdomain may not")
                    
            except Exception as e:
                print(f"  ERROR: {str(e)}")
                
        return {"domain_routing": issues}
    
    async def audit_oauth_configuration(self) -> Dict:
        """Check OAuth redirect URIs and configuration"""
        print("\n2. OAUTH CONFIGURATION AUDIT")
        print("=" * 50)
        
        issues = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get auth config
            try:
                response = await client.get(f"{self.auth_url}/auth/config")
                if response.status_code == 200:
                    config = response.json()
                    print(f"OAuth Configuration:")
                    print(f"  Redirect URIs: {config.get('redirect_uris', [])}")
                    
                    redirect_uris = config.get('redirect_uris', [])
                    
                    # Check for app.staging subdomain
                    if not any('app.staging.netrasystems.ai' in uri for uri in redirect_uris):
                        issues.append("OAuth redirect URIs do not include app.staging.netrasystems.ai")
                        print("  [CRITICAL] Missing app.staging.netrasystems.ai in redirect URIs")
                        
                    # Check for localhost (should not be in staging)
                    if any('localhost' in uri for uri in redirect_uris):
                        issues.append("OAuth redirect URIs include localhost in staging")
                        print("  [WARNING] Localhost URIs in staging configuration")
                        
            except Exception as e:
                issues.append(f"Cannot fetch auth config: {str(e)}")
                print(f"  ERROR: {str(e)}")
                
            # Test OAuth initiation
            try:
                print(f"\nTesting OAuth initiation...")
                response = await client.get(
                    f"{self.auth_url}/auth/google",
                    params={"return_url": f"{self.frontend_app_url}/dashboard"},
                    follow_redirects=False
                )
                
                if response.status_code in [302, 303]:
                    location = response.headers.get('location', '')
                    if 'accounts.google.com' not in location:
                        issues.append("OAuth redirect does not go to Google")
                        print(f"  [ERROR] Invalid OAuth redirect: {location[:100]}")
                    else:
                        print(f"  [OK] OAuth redirects to Google")
                        
                        # Check redirect_uri parameter
                        if 'redirect_uri=' in location:
                            import urllib.parse
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
                            redirect_uri = parsed.get('redirect_uri', [''])[0]
                            print(f"  Redirect URI: {redirect_uri}")
                            
                            if 'app.staging' not in redirect_uri:
                                issues.append(f"OAuth using wrong redirect URI: {redirect_uri}")
                else:
                    issues.append(f"OAuth initiation failed: {response.status_code}")
                    
            except Exception as e:
                issues.append(f"OAuth initiation error: {str(e)}")
                print(f"  ERROR: {str(e)}")
                
        return {"oauth_config": issues}
    
    async def audit_cors_configuration(self) -> Dict:
        """Check CORS configuration for cross-origin requests"""
        print("\n3. CORS CONFIGURATION AUDIT")
        print("=" * 50)
        
        issues = []
        origins_to_test = [
            self.frontend_app_url,
            "https://app.staging.netrasystems.ai",
            self.frontend_direct_url
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for origin in origins_to_test:
                print(f"\nTesting CORS for origin: {origin}")
                
                # Test preflight request to auth service
                try:
                    response = await client.options(
                        f"{self.auth_url}/auth/refresh",
                        headers={
                            "Origin": origin,
                            "Access-Control-Request-Method": "POST",
                            "Access-Control-Request-Headers": "content-type"
                        }
                    )
                    
                    cors_headers = {
                        "allow-origin": response.headers.get("access-control-allow-origin"),
                        "allow-methods": response.headers.get("access-control-allow-methods"),
                        "allow-headers": response.headers.get("access-control-allow-headers"),
                        "allow-credentials": response.headers.get("access-control-allow-credentials")
                    }
                    
                    print(f"  Auth Service CORS: {cors_headers}")
                    
                    if cors_headers["allow-origin"] != origin and cors_headers["allow-origin"] != "*":
                        issues.append(f"Auth service CORS blocks {origin}")
                        print(f"  [ERROR] Origin not allowed")
                        
                except Exception as e:
                    print(f"  ERROR: {str(e)}")
                    
                # Test backend CORS
                try:
                    response = await client.options(
                        f"{self.backend_url}/api/threads",
                        headers={
                            "Origin": origin,
                            "Access-Control-Request-Method": "GET",
                            "Access-Control-Request-Headers": "authorization"
                        }
                    )
                    
                    cors_headers = {
                        "allow-origin": response.headers.get("access-control-allow-origin"),
                        "allow-credentials": response.headers.get("access-control-allow-credentials")
                    }
                    
                    print(f"  Backend CORS: {cors_headers}")
                    
                    if cors_headers["allow-origin"] != origin and cors_headers["allow-origin"] != "*":
                        issues.append(f"Backend CORS blocks {origin}")
                        print(f"  [ERROR] Origin not allowed")
                        
                except Exception as e:
                    print(f"  ERROR: {str(e)}")
                    
        return {"cors_config": issues}
    
    async def audit_jwt_configuration(self) -> Dict:
        """Check JWT secret synchronization"""
        print("\n4. JWT SECRET SYNCHRONIZATION AUDIT")
        print("=" * 50)
        
        issues = []
        
        # This would require creating a token with auth service and validating with backend
        # For now, check if services are using the same configuration
        
        print("Checking service configurations...")
        print("  [INFO] JWT secrets are in Secret Manager")
        print("  [INFO] Both services should use jwt-secret-key-staging")
        
        # We can't directly verify the secrets, but we can test the flow
        print("\nWould need valid token to test JWT validation across services")
        
        return {"jwt_config": issues}
    
    async def audit_authentication_flow(self) -> Dict:
        """Test the complete authentication flow"""
        print("\n5. AUTHENTICATION FLOW AUDIT")
        print("=" * 50)
        
        issues = []
        
        print("Testing authentication endpoints...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check if auth endpoints are accessible
            endpoints = [
                (f"{self.auth_url}/auth/config", "GET", "Auth Config"),
                (f"{self.auth_url}/auth/google", "GET", "OAuth Google"),
                (f"{self.auth_url}/auth/callback", "GET", "OAuth Callback"),
                (f"{self.auth_url}/auth/refresh", "POST", "Token Refresh"),
                (f"{self.auth_url}/auth/validate", "POST", "Token Validate"),
                (f"{self.backend_url}/api/threads", "GET", "Backend Threads")
            ]
            
            for url, method, name in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(url)
                    else:
                        response = await client.post(url, json={})
                    
                    print(f"  {name}: {response.status_code}")
                    
                    if response.status_code >= 500:
                        issues.append(f"{name} endpoint returns {response.status_code}")
                        
                except Exception as e:
                    issues.append(f"{name} endpoint unreachable: {str(e)}")
                    print(f"  {name}: ERROR - {str(e)[:50]}")
                    
        return {"auth_flow": issues}
    
    async def audit_recent_errors(self) -> Dict:
        """Review recent error patterns"""
        print("\n6. RECENT ERROR PATTERNS")
        print("=" * 50)
        
        print("Common error patterns to check:")
        print("  - 404 on /login route")
        print("  - CORS blocking requests from app.staging")
        print("  - OAuth redirect URI mismatch")
        print("  - JWT validation failures")
        print("  - WebSocket connection failures")
        
        return {"error_patterns": []}
    
    async def run_full_audit(self):
        """Run complete audit"""
        print("=" * 60)
        print("STAGING AUTHENTICATION AUDIT")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Target: {self.frontend_app_url}/login")
        
        all_issues = {}
        
        # Run all audits
        audits = [
            ("Domain Routing", self.audit_domain_routing),
            ("OAuth Config", self.audit_oauth_configuration),
            ("CORS Config", self.audit_cors_configuration),
            ("JWT Config", self.audit_jwt_configuration),
            ("Auth Flow", self.audit_authentication_flow),
            ("Error Patterns", self.audit_recent_errors)
        ]
        
        for name, audit_func in audits:
            try:
                result = await audit_func()
                all_issues.update(result)
            except Exception as e:
                print(f"\n{name} audit failed: {str(e)}")
                all_issues[name.lower()] = [f"Audit failed: {str(e)}"]
                
        # Summarize findings
        print("\n" + "=" * 60)
        print("CRITICAL ISSUES FOUND")
        print("=" * 60)
        
        critical_count = 0
        for category, issues in all_issues.items():
            if issues:
                print(f"\n{category.upper()}:")
                for issue in issues:
                    print(f"  - {issue}")
                    critical_count += len(issues)
                    
        if critical_count == 0:
            print("\nNo critical issues found in configuration.")
        else:
            print(f"\nTotal: {critical_count} critical issues found")
            
        print("\n" + "=" * 60)
        print("RECOMMENDED FIXES")
        print("=" * 60)
        
        fixes = []
        
        # Check for specific issues and recommend fixes
        all_issues_flat = []
        for issues in all_issues.values():
            all_issues_flat.extend(issues)
            
        if any("app.staging.netrasystems.ai returns 404" in i for i in all_issues_flat):
            fixes.append("Configure app.staging.netrasystems.ai subdomain to point to frontend service")
            
        if any("redirect URIs do not include app.staging" in i for i in all_issues_flat):
            fixes.append("Add https://app.staging.netrasystems.ai/auth/callback to OAuth redirect URIs")
            
        if any("CORS blocks" in i for i in all_issues_flat):
            fixes.append("Update CORS configuration to allow app.staging.netrasystems.ai origin")
            
        for i, fix in enumerate(fixes, 1):
            print(f"{i}. {fix}")
            
        return all_issues


async def main():
    """Main entry point"""
    auditor = StagingAuthAuditor()
    issues = await auditor.run_full_audit()
    return 0 if not any(issues.values()) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)