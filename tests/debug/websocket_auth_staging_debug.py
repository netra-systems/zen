#!/usr/bin/env python3
"""
WebSocket Authentication Staging Debug Test

This test reproduces the WebSocket 403 authentication issue in staging
and provides comprehensive diagnostics to identify the root cause.

CRITICAL: This test is designed to FAIL and provide diagnostic information
to help fix the JWT secret mismatch issue between REST and WebSocket auth.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Optional

import httpx
import jwt
import websockets
from shared.isolated_environment import get_env


class WebSocketAuthDiagnostic:
    """Diagnostic tool for WebSocket authentication issues"""
    
    def __init__(self):
        """Initialize diagnostic tool"""
        self.env = get_env()
        self.environment = self.env.get("ENVIRONMENT", "development").lower()
        self.staging_base_url = "https://api.staging.netrasystems.ai"
        self.staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
        
        print(f"🔍 WebSocket Auth Diagnostic - Environment: {self.environment}")
        print(f"🔍 Staging API: {self.staging_base_url}")
        print(f"🔍 Staging WebSocket: {self.staging_ws_url}")
    
    def get_jwt_secret_diagnostics(self) -> Dict:
        """Get comprehensive JWT secret diagnostics"""
        diagnostics = {
            "environment": self.environment,
            "jwt_secrets": {}
        }
        
        # Check all possible JWT secret sources
        jwt_sources = [
            f"JWT_SECRET_{self.environment.upper()}",
            "JWT_SECRET_KEY", 
            "JWT_SECRET",
            "AUTH_JWT_SECRET",
            "SECRET_KEY"
        ]
        
        for source in jwt_sources:
            value = self.env.get(source)
            diagnostics["jwt_secrets"][source] = {
                "available": bool(value),
                "length": len(value) if value else 0,
                "hash": hashlib.md5(value.encode()).hexdigest()[:16] if value else None
            }
        
        print("🔍 JWT Secret Sources Analysis:")
        for source, info in diagnostics["jwt_secrets"].items():
            status = "✅" if info["available"] else "❌"
            print(f"   {status} {source}: {info['length']} chars, hash: {info['hash']}")
        
        return diagnostics
    
    def test_unified_jwt_secret_resolution(self) -> Dict:
        """Test the unified JWT secret manager resolution"""
        print("\n🔍 Testing Unified JWT Secret Manager...")
        
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret, get_jwt_secret_manager
            
            # Test direct resolution
            secret = get_unified_jwt_secret()
            secret_hash = hashlib.md5(secret.encode()).hexdigest()[:16]
            
            # Get manager diagnostics
            manager = get_jwt_secret_manager()
            debug_info = manager.get_debug_info()
            validation_result = manager.validate_jwt_configuration()
            
            result = {
                "success": True,
                "secret_hash": secret_hash,
                "secret_length": len(secret),
                "debug_info": debug_info,
                "validation": validation_result
            }
            
            print(f"✅ Unified JWT Secret Resolution SUCCESS")
            print(f"   Secret Hash: {secret_hash}")
            print(f"   Secret Length: {len(secret)}")
            print(f"   Available Keys: {debug_info.get('available_keys', [])}")
            print(f"   Validation Valid: {validation_result.get('valid', False)}")
            
            if validation_result.get('issues'):
                print(f"⚠️  Validation Issues: {validation_result['issues']}")
                
            return result
            
        except Exception as e:
            print(f"❌ Unified JWT Secret Manager FAILED: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def test_websocket_context_extractor(self) -> Dict:
        """Test WebSocket user context extractor JWT secret"""
        print("\n🔍 Testing WebSocket UserContextExtractor JWT Secret...")
        
        try:
            from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
            
            # Create extractor (this will resolve JWT secret)
            extractor = UserContextExtractor()
            
            # Get secret info
            secret_hash = hashlib.md5(extractor.jwt_secret_key.encode()).hexdigest()[:16]
            
            result = {
                "success": True,
                "secret_hash": secret_hash,
                "secret_length": len(extractor.jwt_secret_key),
                "algorithm": extractor.jwt_algorithm
            }
            
            print(f"✅ WebSocket UserContextExtractor SUCCESS")
            print(f"   Secret Hash: {secret_hash}")
            print(f"   Secret Length: {len(extractor.jwt_secret_key)}")
            print(f"   Algorithm: {extractor.jwt_algorithm}")
            
            return result
            
        except Exception as e:
            print(f"❌ WebSocket UserContextExtractor FAILED: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_test_jwt_token(self, secret: str, user_id: str = "test_user_staging") -> str:
        """Create a test JWT token using the given secret"""
        current_time = int(time.time())
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "iat": current_time,  # Issued at
            "exp": current_time + 3600,  # Expires in 1 hour
            "iss": "staging_test_auth",  # Issuer
            "permissions": ["read", "write"],
            "roles": ["user"]
        }
        
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token
    
    async def test_rest_api_with_token(self, token: str) -> Dict:
        """Test REST API authentication with JWT token"""
        print(f"\n🔍 Testing REST API authentication...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        results = {}
        
        # Test multiple REST endpoints
        test_endpoints = [
            "/health",
            "/api/discovery/services", 
            "/api/mcp/config"
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint in test_endpoints:
                try:
                    url = f"{self.staging_base_url}{endpoint}"
                    response = await client.get(url, headers=headers)
                    
                    results[endpoint] = {
                        "status_code": response.status_code,
                        "success": 200 <= response.status_code < 300,
                        "response_size": len(response.content)
                    }
                    
                    status = "✅" if results[endpoint]["success"] else "❌"
                    print(f"   {status} {endpoint}: {response.status_code}")
                    
                except Exception as e:
                    results[endpoint] = {
                        "success": False,
                        "error": str(e)
                    }
                    print(f"   ❌ {endpoint}: {str(e)}")
        
        return results
    
    async def test_websocket_connection_with_token(self, token: str) -> Dict:
        """Test WebSocket connection with JWT token"""
        print(f"\n🔍 Testing WebSocket connection...")
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        connection_result = {
            "connection_attempted": False,
            "connection_succeeded": False,
            "error": None,
            "messages_received": []
        }
        
        try:
            connection_result["connection_attempted"] = True
            
            # Attempt WebSocket connection
            async with websockets.connect(
                self.staging_ws_url,
                additional_headers=headers,
                close_timeout=5
            ) as ws:
                connection_result["connection_succeeded"] = True
                print("✅ WebSocket connection SUCCEEDED!")
                
                # Send test message
                test_message = {
                    "type": "ping",
                    "timestamp": time.time()
                }
                
                await ws.send(json.dumps(test_message))
                print("   📤 Sent test message")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    response_data = json.loads(response)
                    connection_result["messages_received"].append(response_data)
                    print(f"   📥 Received: {response_data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    print("   ⏰ No response within timeout (may be normal)")
                
        except Exception as e:
            connection_result["error"] = str(e)
            print(f"❌ WebSocket connection FAILED: {e}")
            
            # Check if this is a 403 error
            if "403" in str(e) or "Forbidden" in str(e):
                print("❌ CRITICAL: This is the 403 Forbidden error we're investigating!")
                print("   This confirms JWT authentication is failing for WebSocket connections")
        
        return connection_result
    
    async def run_comprehensive_diagnostic(self) -> Dict:
        """Run comprehensive diagnostic of WebSocket auth issue"""
        print("=" * 80)
        print("🔍 COMPREHENSIVE WEBSOCKET AUTHENTICATION DIAGNOSTIC")
        print("=" * 80)
        
        diagnostic_results = {
            "environment": self.environment,
            "timestamp": time.time()
        }
        
        # 1. JWT Secret Sources Analysis
        diagnostic_results["jwt_sources"] = self.get_jwt_secret_diagnostics()
        
        # 2. Test Unified JWT Secret Manager
        diagnostic_results["unified_manager"] = self.test_unified_jwt_secret_resolution()
        
        # 3. Test WebSocket Context Extractor
        diagnostic_results["websocket_extractor"] = self.test_websocket_context_extractor()
        
        # 4. Compare JWT secret hashes
        unified_hash = diagnostic_results["unified_manager"].get("secret_hash")
        websocket_hash = diagnostic_results["websocket_extractor"].get("secret_hash")
        
        print(f"\n🔍 JWT SECRET COMPARISON:")
        print(f"   Unified Manager Hash: {unified_hash}")
        print(f"   WebSocket Extractor Hash: {websocket_hash}")
        
        if unified_hash and websocket_hash:
            if unified_hash == websocket_hash:
                print("✅ JWT secrets MATCH - secret consistency is good")
                diagnostic_results["secret_consistency"] = "MATCH"
            else:
                print("❌ JWT secrets DO NOT MATCH - THIS IS THE ROOT CAUSE!")
                print("   Different JWT secrets will cause signature validation failures")
                diagnostic_results["secret_consistency"] = "MISMATCH"
        else:
            print("⚠️  Cannot compare secrets - one or both failed to resolve")
            diagnostic_results["secret_consistency"] = "UNKNOWN"
        
        # 5. Test with actual tokens if secrets available
        if unified_hash:
            try:
                from shared.jwt_secret_manager import get_unified_jwt_secret
                secret = get_unified_jwt_secret()
                test_token = self.create_test_jwt_token(secret)
                
                print(f"\n🔍 CREATED TEST TOKEN (using unified secret)")
                print(f"   Token length: {len(test_token)}")
                print(f"   Token prefix: {test_token[:30]}...")
                
                # Test REST API
                diagnostic_results["rest_api_test"] = await self.test_rest_api_with_token(test_token)
                
                # Test WebSocket
                diagnostic_results["websocket_test"] = await self.test_websocket_connection_with_token(test_token)
                
                # Final analysis
                rest_success = any(result.get("success") for result in diagnostic_results["rest_api_test"].values())
                websocket_success = diagnostic_results["websocket_test"].get("connection_succeeded", False)
                
                print(f"\n🔍 FINAL AUTHENTICATION TEST RESULTS:")
                print(f"   REST API Success: {'✅' if rest_success else '❌'}")
                print(f"   WebSocket Success: {'✅' if websocket_success else '❌'}")
                
                if rest_success and not websocket_success:
                    print("❌ CONFIRMED: REST works but WebSocket fails - this is our bug!")
                    diagnostic_results["bug_confirmed"] = True
                elif rest_success and websocket_success:
                    print("✅ Both REST and WebSocket work - authentication is functioning")
                    diagnostic_results["bug_confirmed"] = False
                else:
                    print("❌ Both REST and WebSocket fail - broader authentication issue")
                    diagnostic_results["bug_confirmed"] = "BROADER_ISSUE"
                    
            except Exception as e:
                print(f"❌ Token testing failed: {e}")
                diagnostic_results["token_test_error"] = str(e)
        
        print("=" * 80)
        print("🔍 DIAGNOSTIC COMPLETE")
        print("=" * 80)
        
        return diagnostic_results


async def main():
    """Main diagnostic function"""
    diagnostic = WebSocketAuthDiagnostic()
    
    try:
        results = await diagnostic.run_comprehensive_diagnostic()
        
        # Save results to file for analysis
        import json
        with open("websocket_auth_diagnostic_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Diagnostic results saved to: websocket_auth_diagnostic_results.json")
        
        # Provide summary recommendations
        print("\n🎯 RECOMMENDATIONS:")
        
        if results.get("secret_consistency") == "MISMATCH":
            print("1. CRITICAL: Fix JWT secret mismatch between unified manager and WebSocket extractor")
            print("2. Ensure both use the same environment variable source")
            print("3. Check GCP Secret Manager access and configuration")
        elif results.get("bug_confirmed") is True:
            print("1. JWT secrets match but WebSocket still fails - investigate auth flow logic")
            print("2. Check WebSocket-specific authentication requirements")
            print("3. Review staging environment configuration")
        else:
            print("1. Review diagnostic results for specific failure points")
            print("2. Check staging environment setup and connectivity")
        
    except Exception as e:
        print(f"❌ DIAGNOSTIC FAILED: {e}")
        raise


if __name__ == "__main__":
    print("🚀 Starting WebSocket Authentication Diagnostic...")
    asyncio.run(main())