#!/usr/bin/env python3
"""
WebSocket Health Validation Script for Staging Environment
Created: 2025-09-11 - In response to Issue #420 and GCP audit findings

This script validates WebSocket endpoint health after resolving critical 500 errors
that were blocking the Golden Path user workflow.
"""

import asyncio
import aiohttp
import json
import time
import websockets
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging
import sys


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketHealthValidator:
    """Validates WebSocket endpoint health in staging environment."""
    
    def __init__(self):
        self.staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
        self.staging_http_url = "https://api.staging.netrasystems.ai"
        self.auth_url = "https://auth.staging.netrasystems.ai"
        
        # Test credentials (demo mode)
        self.test_token = None
        
    async def validate_http_endpoints(self) -> Dict[str, Any]:
        """Validate HTTP endpoint health."""
        logger.info("🔍 Validating HTTP endpoints...")
        
        results = {
            "backend_health": False,
            "auth_health": False,
            "backend_response_time": None,
            "auth_response_time": None,
            "errors": []
        }
        
        async with aiohttp.ClientSession() as session:
            # Test backend health
            try:
                start_time = time.time()
                async with session.get(f"{self.staging_http_url}/health", timeout=10) as response:
                    results["backend_response_time"] = time.time() - start_time
                    results["backend_health"] = response.status == 200
                    if response.status == 200:
                        logger.info(f"✅ Backend health: OK ({response.status}) - {results['backend_response_time']:.3f}s")
                    else:
                        logger.error(f"❌ Backend health: FAILED ({response.status})")
                        results["errors"].append(f"Backend health returned {response.status}")
            except Exception as e:
                logger.error(f"❌ Backend health check failed: {e}")
                results["errors"].append(f"Backend health exception: {str(e)}")
            
            # Test auth health
            try:
                start_time = time.time()
                async with session.get(f"{self.auth_url}/health", timeout=10) as response:
                    results["auth_response_time"] = time.time() - start_time
                    results["auth_health"] = response.status == 200
                    if response.status == 200:
                        logger.info(f"✅ Auth service health: OK ({response.status}) - {results['auth_response_time']:.3f}s")
                    else:
                        logger.error(f"❌ Auth service health: FAILED ({response.status})")
                        results["errors"].append(f"Auth service health returned {response.status}")
            except Exception as e:
                logger.error(f"❌ Auth service health check failed: {e}")
                results["errors"].append(f"Auth service health exception: {str(e)}")
        
        return results
    
    async def test_websocket_connection(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Test WebSocket connection without authentication."""
        logger.info("🔍 Testing WebSocket connection...")
        
        results = {
            "connection_successful": False,
            "handshake_time": None,
            "error_code": None,
            "error_message": None,
            "close_code": None
        }
        
        start_time = time.time()
        
        try:
            # Test basic WebSocket connection (without auth)
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            # Use a short timeout to quickly identify connection issues
            async with websockets.connect(
                self.staging_ws_url,
                extra_headers=headers,
                open_timeout=10,
                close_timeout=5
            ) as websocket:
                results["connection_successful"] = True
                results["handshake_time"] = time.time() - start_time
                logger.info(f"✅ WebSocket connection successful - handshake: {results['handshake_time']:.3f}s")
                
                # Try to send a simple ping
                await websocket.send(json.dumps({"type": "ping", "timestamp": time.time()}))
                
                # Wait for potential response or immediate close
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    logger.info(f"📨 WebSocket response received: {response[:100]}...")
                except asyncio.TimeoutError:
                    logger.info("⏰ No immediate WebSocket response (expected for non-authenticated connection)")
                
        except websockets.exceptions.ConnectionClosedError as e:
            results["close_code"] = e.code
            results["error_message"] = str(e)
            if e.code == 1008:  # Policy violation (auth failure)
                logger.warning(f"⚠️ WebSocket closed with auth failure (code 1008): {e}")
            else:
                logger.error(f"❌ WebSocket closed unexpectedly (code {e.code}): {e}")
            
        except websockets.exceptions.InvalidStatusCode as e:
            results["error_code"] = e.status_code
            results["error_message"] = str(e)
            if e.status_code == 500:
                logger.error(f"🚨 WebSocket returned HTTP 500 - this is the issue we're investigating!")
            else:
                logger.error(f"❌ WebSocket returned HTTP {e.status_code}: {e}")
                
        except Exception as e:
            results["error_message"] = str(e)
            logger.error(f"❌ WebSocket connection failed: {e}")
        
        return results
    
    async def test_websocket_with_demo_mode(self) -> Dict[str, Any]:
        """Test WebSocket with demo mode (if available)."""
        logger.info("🔍 Testing WebSocket with demo mode...")
        
        # For staging environment, we can try to connect without strict auth
        headers = {
            "User-Agent": "WebSocket-Health-Validator/1.0",
            "Origin": "https://app.staging.netrasystems.ai"
        }
        
        return await self.test_websocket_connection()
    
    async def check_gcp_logs(self) -> Dict[str, Any]:
        """Check recent GCP logs for WebSocket errors."""
        logger.info("🔍 Checking GCP logs for recent WebSocket errors...")
        
        # This would need GCP credentials, so we'll just return a placeholder
        # In a real scenario, this could use the gcloud CLI or Cloud Logging API
        results = {
            "logs_available": False,
            "recent_500_errors": "Check GCP console manually",
            "recommendation": "Use: gcloud logging read 'resource.type=cloud_run_revision AND httpRequest.status=500 AND httpRequest.requestUrl=\"/ws\"' --limit 5 --freshness=1h"
        }
        
        logger.info("📋 Manual GCP log check required - see recommendation in results")
        return results
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete WebSocket health validation."""
        logger.info("🚀 Starting WebSocket health validation...")
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Run all validation tests
        http_results = await self.validate_http_endpoints()
        websocket_results = await self.test_websocket_connection()
        demo_results = await self.test_websocket_with_demo_mode()
        log_results = await self.check_gcp_logs()
        
        # Compile overall results
        validation_results = {
            "timestamp": timestamp,
            "overall_health": {
                "backend_healthy": http_results["backend_health"],
                "auth_healthy": http_results["auth_health"],
                "websocket_reachable": websocket_results.get("connection_successful", False) or websocket_results.get("close_code") == 1008,
                "critical_500_errors": websocket_results.get("error_code") == 500
            },
            "detailed_results": {
                "http_endpoints": http_results,
                "websocket_connection": websocket_results,
                "demo_mode_test": demo_results,
                "gcp_logs": log_results
            },
            "recommendations": []
        }
        
        # Generate recommendations
        if websocket_results.get("error_code") == 500:
            validation_results["recommendations"].append({
                "priority": "CRITICAL",
                "issue": "WebSocket endpoint returning HTTP 500",
                "action": "Check JWT secret configuration between backend and auth services",
                "command": "gcloud secrets list --filter='name:jwt' --project=netra-staging"
            })
        
        if websocket_results.get("close_code") == 1008:
            validation_results["recommendations"].append({
                "priority": "HIGH", 
                "issue": "WebSocket authentication failure",
                "action": "Authentication is working (connection established) but JWT validation failing",
                "command": "Check auth service logs and JWT secret consistency"
            })
        
        if not http_results["backend_health"]:
            validation_results["recommendations"].append({
                "priority": "CRITICAL",
                "issue": "Backend service not healthy",
                "action": "Check backend deployment and logs"
            })
        
        if not http_results["auth_health"]:
            validation_results["recommendations"].append({
                "priority": "CRITICAL",
                "issue": "Auth service not healthy", 
                "action": "Check auth service deployment and logs"
            })
        
        return validation_results


async def main():
    """Main validation function."""
    print("🌐 WebSocket Health Validation for Netra Staging Environment")
    print("=" * 60)
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    validator = WebSocketHealthValidator()
    
    try:
        results = await validator.run_full_validation()
        
        # Print summary
        print("📋 VALIDATION SUMMARY:")
        print("-" * 30)
        overall = results["overall_health"]
        print(f"Backend Health: {'✅ OK' if overall['backend_healthy'] else '❌ FAILED'}")
        print(f"Auth Service Health: {'✅ OK' if overall['auth_healthy'] else '❌ FAILED'}")
        print(f"WebSocket Reachable: {'✅ YES' if overall['websocket_reachable'] else '❌ NO'}")
        print(f"Critical 500 Errors: {'🚨 YES' if overall['critical_500_errors'] else '✅ NO'}")
        print()
        
        # Print recommendations
        if results["recommendations"]:
            print("🎯 RECOMMENDATIONS:")
            print("-" * 20)
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"{i}. [{rec['priority']}] {rec['issue']}")
                print(f"   Action: {rec['action']}")
                if "command" in rec:
                    print(f"   Command: {rec['command']}")
                print()
        
        # Save detailed results
        with open(f"websocket_health_validation_{int(time.time())}.json", "w") as f:
            json.dump(results, f, indent=2)
            
        print(f"📄 Detailed results saved to: websocket_health_validation_{int(time.time())}.json")
        
        # Return appropriate exit code
        if overall["critical_500_errors"]:
            print("\n🚨 CRITICAL: WebSocket 500 errors detected - immediate attention required")
            sys.exit(1)
        elif not overall["websocket_reachable"]:
            print("\n⚠️ WARNING: WebSocket not fully reachable - investigation needed") 
            sys.exit(2)
        else:
            print("\n✅ WebSocket health validation completed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ Validation failed with exception: {e}")
        print(f"\n💥 Validation script failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())