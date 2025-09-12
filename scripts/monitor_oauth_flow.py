#!/usr/bin/env python3
"""
Monitor OAuth flow in real-time to verify token persistence fixes.
"""
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta

import httpx


class OAuthMonitor:
    def __init__(self):
        self.auth_url = "https://auth.staging.netrasystems.ai"
        self.app_url = "https://app.staging.netrasystems.ai"
        self.api_url = "https://api.staging.netrasystems.ai"
        
    async def check_services(self):
        """Check all services are healthy"""
        print("\n SEARCH:  Checking service health...")
        async with httpx.AsyncClient() as client:
            services = [
                ("Auth Service", f"{self.auth_url}/auth/health"),
                ("Frontend", self.app_url),
                ("API", f"{self.api_url}/health")
            ]
            
            for name, url in services:
                try:
                    response = await client.get(url, timeout=5.0)
                    if response.status_code == 200:
                        print(f" PASS:  {name}: OK")
                    else:
                        print(f" WARNING: [U+FE0F]  {name}: Status {response.status_code}")
                except Exception as e:
                    print(f" FAIL:  {name}: {str(e)[:50]}")
    
    async def check_oauth_config(self):
        """Verify OAuth configuration"""
        print("\n[U+1F527] OAuth Configuration:")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.auth_url}/auth/config")
                config = response.json()
                
                print(f"  Client ID: {config['google_client_id'][:30]}...")
                print(f"  Callback: {config['endpoints']['callback']}")
                print(f"  Redirect URIs: {config['authorized_redirect_uris']}")
                
                # Check for configuration issues
                if "auth.staging" not in str(config['authorized_redirect_uris']):
                    print("   WARNING: [U+FE0F]  WARNING: Redirect URI should point to auth service!")
                
                return config
            except Exception as e:
                print(f"   FAIL:  Failed to get config: {e}")
                return None
    
    async def test_oauth_initiation(self):
        """Test OAuth login initiation"""
        print("\n[U+1F680] Testing OAuth Initiation:")
        async with httpx.AsyncClient(follow_redirects=False) as client:
            try:
                response = await client.get(
                    f"{self.auth_url}/auth/login",
                    params={"provider": "google"}
                )
                
                if response.status_code == 302:
                    location = response.headers.get('location', '')
                    if 'accounts.google.com' in location:
                        print("   PASS:  Redirects to Google OAuth")
                        
                        # Extract redirect_uri from location
                        if 'redirect_uri=' in location:
                            import urllib.parse
                            parsed = urllib.parse.urlparse(location)
                            params = urllib.parse.parse_qs(parsed.query)
                            redirect_uri = params.get('redirect_uri', [''])[0]
                            print(f"   PIN:  Redirect URI: {redirect_uri}")
                            
                            if "auth.staging" not in redirect_uri:
                                print("   WARNING: [U+FE0F]  WARNING: Redirect URI not pointing to auth service!")
                    else:
                        print(f"   FAIL:  Invalid redirect: {location[:50]}")
                else:
                    print(f"   FAIL:  No redirect: Status {response.status_code}")
                    
            except Exception as e:
                print(f"   FAIL:  Error: {e}")
    
    def monitor_logs(self, duration_seconds=30):
        """Monitor auth service logs for OAuth activity"""
        print(f"\n[U+1F4CB] Monitoring logs for {duration_seconds} seconds...")
        print("  (Looking for OAuth callback and token handling)")
        
        end_time = datetime.now() + timedelta(seconds=duration_seconds)
        
        try:
            # Start log streaming
            cmd = [
                "gcloud", "logging", "read",
                'resource.type="cloud_run_revision" AND '
                'resource.labels.service_name="auth-service" AND '
                '(textPayload:"OAuth" OR textPayload:"token" OR textPayload:"callback")',
                "--project=netra-staging",
                "--format=value(timestamp,textPayload)",
                "--limit=50"
            ]
            
            while datetime.now() < end_time:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if any(keyword in line for keyword in ['OAuth', 'token', 'callback', 'JWT']):
                            print(f"  [U+1F4DD] {line[:100]}")
                
                time.sleep(5)  # Check every 5 seconds
                
        except Exception as e:
            print(f"   FAIL:  Log monitoring error: {e}")
    
    async def simulate_oauth_callback(self):
        """Simulate an OAuth callback to test token handling"""
        print("\n[U+1F9EA] Simulating OAuth Callback (test only):")
        print("  Note: This will fail authentication but tests the flow")
        
        async with httpx.AsyncClient(follow_redirects=False) as client:
            try:
                # This will fail but we can see if logging works
                response = await client.get(
                    f"{self.auth_url}/auth/callback",
                    params={
                        "code": "test-code-invalid",
                        "state": "test-state"
                    }
                )
                
                print(f"  Response: {response.status_code}")
                if response.status_code == 302:
                    print(f"  Redirect: {response.headers.get('location', 'none')}")
                elif response.status_code >= 400:
                    print(f"  Expected error (invalid code): {response.status_code}")
                    
            except Exception as e:
                print(f"  Error: {e}")
    
    async def run_full_diagnostics(self):
        """Run complete OAuth diagnostics"""
        print("="*60)
        print("OAuth Flow Diagnostics - Staging Environment")
        print("="*60)
        print(f"Time: {datetime.now().isoformat()}")
        
        # Check services
        await self.check_services()
        
        # Check OAuth config
        config = await self.check_oauth_config()
        
        # Test OAuth initiation
        await self.test_oauth_initiation()
        
        # Simulate callback (optional)
        # await self.simulate_oauth_callback()
        
        print("\n CHART:  Summary:")
        print("-"*40)
        
        issues = []
        
        if config:
            if "auth.staging" not in str(config.get('authorized_redirect_uris', [])):
                issues.append("Redirect URI should point to auth service (auth.staging.netrasystems.ai)")
            
            if not config.get('google_client_id'):
                issues.append("Google Client ID not configured")
        
        if issues:
            print(" WARNING: [U+FE0F]  Issues found:")
            for issue in issues:
                print(f"  [U+2022] {issue}")
        else:
            print(" PASS:  OAuth configuration appears correct")
        
        print("\n IDEA:  Next Steps:")
        print("1. Try logging in at: https://app.staging.netrasystems.ai")
        print("2. Check browser console for token storage:")
        print("   localStorage.getItem('jwt_token')")
        print("3. Monitor auth service logs during login attempt")
        
        return len(issues) == 0


async def main():
    monitor = OAuthMonitor()
    
    # Run diagnostics
    success = await monitor.run_full_diagnostics()
    
    # Optional: Monitor logs
    if '--monitor' in sys.argv:
        monitor.monitor_logs(duration_seconds=60)
    
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)