#!/usr/bin/env python3
"""
Infrastructure Health Monitoring Script for Issue #1278 Remediation

CRITICAL PURPOSE: Monitor staging infrastructure health while infrastructure team
resolves VPC connectivity and Cloud SQL timeout issues.

SCOPE: Development team monitoring tool - does NOT attempt to fix infrastructure issues.
That is the responsibility of the infrastructure team.

Business Impact: Maintains visibility of $500K+ ARR platform during infrastructure issues.
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import aiohttp
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InfrastructureHealthMonitor:
    """Monitor staging infrastructure endpoints for Issue #1278 tracking."""
    
    def __init__(self):
        """Initialize with staging domain configuration per Issue #1278."""
        # CRITICAL: Use correct staging domains (*.netrasystems.ai)
        # DO NOT USE: *.staging.netrasystems.ai (causes SSL failures per Issue #1278)
        self.staging_endpoints = {
            "backend": "https://staging.netrasystems.ai",
            "auth": "https://staging.netrasystems.ai", 
            "frontend": "https://staging.netrasystems.ai",
            "websocket": "wss://api.staging.netrasystems.ai"
        }
        
        # Health check paths
        self.health_paths = {
            "basic": "/health",
            "ready": "/health/ready", 
            "backend": "/health/backend",
            "startup": "/health/startup"
        }
        
        # Timeout configurations aligned with Issue #1263 database timeout fixes
        self.timeouts = {
            "basic": 5.0,
            "ready": 45.0,  # Extended for GCP validator per current health.py
            "backend": 30.0,
            "startup": 60.0
        }
        
    async def check_endpoint_health(self, endpoint_name: str, base_url: str, path: str, timeout: float) -> Dict[str, Any]:
        """Check health of a specific endpoint with proper error handling."""
        full_url = f"{base_url}{path}"
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.get(full_url) as response:
                    response_time = time.time() - start_time
                    
                    # Handle successful responses
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            return {
                                "status": "healthy",
                                "endpoint": endpoint_name,
                                "url": full_url,
                                "response_time_ms": round(response_time * 1000, 2),
                                "http_status": response.status,
                                "response_data": response_data,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        except json.JSONDecodeError:
                            # Non-JSON response but HTTP 200
                            response_text = await response.text()
                            return {
                                "status": "healthy_non_json",
                                "endpoint": endpoint_name,
                                "url": full_url,
                                "response_time_ms": round(response_time * 1000, 2),
                                "http_status": response.status,
                                "response_text": response_text[:500],  # Truncate for logging
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                    
                    # Handle HTTP error responses
                    else:
                        try:
                            error_data = await response.json()
                        except:
                            error_data = {"message": await response.text()}
                            
                        return {
                            "status": "unhealthy",
                            "endpoint": endpoint_name,
                            "url": full_url,
                            "response_time_ms": round(response_time * 1000, 2),
                            "http_status": response.status,
                            "error_data": error_data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "infrastructure_issue": True if response.status in [503, 502, 504] else False
                        }
                        
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "endpoint": endpoint_name,
                "url": full_url,
                "timeout_seconds": timeout,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "infrastructure_issue": True,  # Timeouts often indicate infrastructure issues
                "message": f"Request timed out after {timeout}s - possible VPC/connectivity issue"
            }
            
        except aiohttp.ClientError as e:
            return {
                "status": "connection_error", 
                "endpoint": endpoint_name,
                "url": full_url,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "infrastructure_issue": True,  # Connection errors indicate infrastructure issues
                "message": "Network connectivity issue - check VPC configuration"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "endpoint": endpoint_name, 
                "url": full_url,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "infrastructure_issue": False  # Application-level error
            }
    
    async def check_websocket_connectivity(self) -> Dict[str, Any]:
        """Check WebSocket endpoint connectivity (connection test only - no upgrade)."""
        websocket_url = self.staging_endpoints["websocket"]
        start_time = time.time()
        
        try:
            # Convert WSS to HTTPS for connectivity test
            http_url = websocket_url.replace("wss://", "https://")
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10.0)
            ) as session:
                # Test basic connectivity to WebSocket endpoint
                async with session.get(f"{http_url}/health") as response:
                    response_time = time.time() - start_time
                    
                    return {
                        "status": "reachable" if response.status in [200, 404, 405] else "unreachable",
                        "endpoint": "websocket_connectivity",
                        "url": websocket_url,
                        "test_url": f"{http_url}/health",
                        "response_time_ms": round(response_time * 1000, 2),
                        "http_status": response.status,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "infrastructure_issue": response.status in [502, 503, 504],
                        "note": "Basic connectivity test - actual WebSocket upgrade not tested"
                    }
                    
        except Exception as e:
            return {
                "status": "unreachable",
                "endpoint": "websocket_connectivity", 
                "url": websocket_url,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "infrastructure_issue": True,
                "message": "WebSocket endpoint unreachable - check load balancer configuration"
            }
    
    async def run_full_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check across all staging endpoints."""
        logger.info("Starting comprehensive infrastructure health check...")
        
        start_time = time.time()
        results = {
            "monitor_run_id": f"infra_health_{int(start_time)}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "issue_reference": "#1278",
            "purpose": "Infrastructure monitoring during VPC/Cloud SQL connectivity issues",
            "endpoints": {},
            "websocket": {},
            "summary": {}
        }
        
        # Check all HTTP health endpoints
        tasks = []
        for health_type, path in self.health_paths.items():
            for endpoint_name, base_url in self.staging_endpoints.items():
                if endpoint_name != "websocket":  # Skip websocket for HTTP checks
                    timeout = self.timeouts.get(health_type, 10.0)
                    task_name = f"{endpoint_name}_{health_type}"
                    task = self.check_endpoint_health(task_name, base_url, path, timeout)
                    tasks.append(task)
        
        # Run all health checks concurrently
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process health check results
        for result in health_results:
            if isinstance(result, Exception):
                logger.error(f"Health check task failed: {result}")
                continue
                
            endpoint_key = result["endpoint"]
            results["endpoints"][endpoint_key] = result
        
        # Check WebSocket connectivity separately
        results["websocket"] = await self.check_websocket_connectivity()
        
        # Generate summary
        total_checks = len(results["endpoints"]) + 1  # +1 for WebSocket
        healthy_checks = sum(1 for r in results["endpoints"].values() if r["status"] == "healthy")
        infrastructure_issues = sum(1 for r in results["endpoints"].values() if r.get("infrastructure_issue", False))
        
        if results["websocket"]["status"] == "reachable":
            healthy_checks += 1
        if results["websocket"].get("infrastructure_issue", False):
            infrastructure_issues += 1
        
        results["summary"] = {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "infrastructure_issues": infrastructure_issues,
            "health_percentage": round((healthy_checks / total_checks) * 100, 1),
            "overall_status": "healthy" if infrastructure_issues == 0 else "infrastructure_degraded",
            "check_duration_seconds": round(time.time() - start_time, 2),
            "end_time": datetime.now(timezone.utc).isoformat()
        }
        
        # Log summary
        summary = results["summary"]
        logger.info(f"Health check complete: {summary['health_percentage']}% healthy "
                   f"({summary['healthy_checks']}/{summary['total_checks']} endpoints), "
                   f"{summary['infrastructure_issues']} infrastructure issues detected")
        
        return results
    
    def format_results_for_console(self, results: Dict[str, Any]) -> str:
        """Format results for console output with proper Issue #1278 context."""
        output = []
        output.append("=" * 80)
        output.append(f"INFRASTRUCTURE HEALTH MONITOR - Issue {results['issue_reference']}")
        output.append(f"Run ID: {results['monitor_run_id']}")
        output.append(f"Timestamp: {results['start_time']}")
        output.append("=" * 80)
        
        # Summary section
        summary = results["summary"]
        output.append(f"\nOVERALL STATUS: {summary['overall_status'].upper()}")
        output.append(f"Health Percentage: {summary['health_percentage']}%")
        output.append(f"Infrastructure Issues: {summary['infrastructure_issues']}")
        output.append(f"Check Duration: {summary['check_duration_seconds']}s")
        
        # Endpoint details
        output.append(f"\nENDPOINT HEALTH DETAILS:")
        output.append("-" * 40)
        
        for endpoint, result in results["endpoints"].items():
            status_icon = "✅" if result["status"] == "healthy" else "❌"
            infra_flag = " [INFRA]" if result.get("infrastructure_issue", False) else ""
            
            output.append(f"{status_icon} {endpoint}: {result['status'].upper()}{infra_flag}")
            if "response_time_ms" in result:
                output.append(f"   Response Time: {result['response_time_ms']}ms")
            if "http_status" in result:
                output.append(f"   HTTP Status: {result['http_status']}")
            if "error" in result or "message" in result:
                error_msg = result.get("error") or result.get("message", "")
                output.append(f"   Issue: {error_msg}")
            output.append("")
        
        # WebSocket details
        ws_result = results["websocket"]
        ws_icon = "✅" if ws_result["status"] == "reachable" else "❌"
        ws_infra_flag = " [INFRA]" if ws_result.get("infrastructure_issue", False) else ""
        output.append(f"{ws_icon} WebSocket Connectivity: {ws_result['status'].upper()}{ws_infra_flag}")
        if "response_time_ms" in ws_result:
            output.append(f"   Response Time: {ws_result['response_time_ms']}ms")
        
        # Infrastructure team handoff info
        if summary["infrastructure_issues"] > 0:
            output.append("\n" + "!" * 60)
            output.append("INFRASTRUCTURE TEAM ACTION REQUIRED:")
            output.append("- VPC connector configuration needs review")
            output.append("- Cloud SQL connectivity timeouts detected")
            output.append("- SSL certificate validation for *.netrasystems.ai")
            output.append("- Load balancer health check configuration")
            output.append("!" * 60)
        
        return "\n".join(output)

async def main():
    """Main function for command-line execution."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("""
Infrastructure Health Monitor for Issue #1278

Usage:
  python scripts/monitor_infrastructure_health.py [--json] [--quiet]

Options:
  --json    Output results in JSON format
  --quiet   Suppress console output (useful for logging)
  --help    Show this help message

Purpose:
  Monitor staging infrastructure health during Issue #1278 VPC/connectivity fixes.
  This script does NOT attempt to fix infrastructure issues - that's for the
  infrastructure team. It provides visibility during the remediation process.

Example:
  python scripts/monitor_infrastructure_health.py
  python scripts/monitor_infrastructure_health.py --json > health_report.json
        """)
        return
    
    json_output = "--json" in sys.argv
    quiet_mode = "--quiet" in sys.argv
    
    monitor = InfrastructureHealthMonitor()
    
    try:
        results = await monitor.run_full_health_check()
        
        if json_output:
            print(json.dumps(results, indent=2))
        elif not quiet_mode:
            print(monitor.format_results_for_console(results))
        
        # Exit with appropriate code
        infrastructure_issues = results["summary"]["infrastructure_issues"]
        exit_code = 1 if infrastructure_issues > 0 else 0
        
        if not quiet_mode and not json_output:
            if exit_code == 0:
                print("\n✅ All infrastructure endpoints healthy")
            else:
                print(f"\n❌ {infrastructure_issues} infrastructure issue(s) detected")
                print("   Contact infrastructure team for VPC/connectivity resolution")
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Infrastructure monitoring failed: {e}")
        if not quiet_mode:
            print(f"\n❌ Monitoring script error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())