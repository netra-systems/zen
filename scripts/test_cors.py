#!/usr/bin/env python3
"""
CORS Testing and Debugging Script

Business Value Justification (BVJ):
- Segment: ALL (Operational tooling)
- Business Goal: Rapidly diagnose and fix CORS issues
- Value Impact: Reduces time to resolution for CORS-related incidents
- Strategic Impact: Enables proactive CORS testing and validation

This script provides comprehensive CORS testing capabilities:
- Test CORS configuration for any endpoint
- Show which origins are allowed
- Validate current environment settings
- Generate CORS configuration reports
- Test WebSocket CORS support
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin
import time
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import websockets

# Optional dependency for table formatting
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.cors_config_builder import (
    CORSConfigurationBuilder,
    get_cors_origins, get_cors_config, is_origin_allowed,
    get_websocket_cors_origins, get_cors_health_info, validate_cors_config
)


class CORSTester:
    """CORS testing and debugging utility."""
    
    def __init__(self, base_url: str = "http://localhost:8000", environment: str = "development"):
        """Initialize CORS tester."""
        self.base_url = base_url.rstrip('/')
        self.environment = environment
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_cors_preflight(self, endpoint: str, origin: str, method: str = "POST") -> Dict[str, Any]:
        """Test CORS preflight request."""
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        headers = {
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "Authorization, Content-Type, X-Request-ID"
        }
        
        try:
            async with self.session.options(url, headers=headers) as response:
                response_headers = dict(response.headers)
                return {
                    "success": True,
                    "status_code": response.status,
                    "url": url,
                    "request_headers": headers,
                    "response_headers": response_headers,
                    "cors_analysis": self._analyze_cors_headers(response_headers, origin),
                    "response_time": response.headers.get('X-Response-Time', 'unknown')
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "request_headers": headers
            }
    
    async def test_cors_actual_request(self, endpoint: str, origin: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """Test actual CORS request."""
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        headers = {
            "Origin": origin,
            "Content-Type": "application/json"
        }
        
        try:
            request_kwargs = {"headers": headers}
            if data and method.upper() in ["POST", "PUT", "PATCH"]:
                request_kwargs["json"] = data
            
            async with self.session.request(method, url, **request_kwargs) as response:
                response_headers = dict(response.headers)
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                return {
                    "success": True,
                    "status_code": response.status,
                    "url": url,
                    "request_headers": headers,
                    "response_headers": response_headers,
                    "response_data": response_data,
                    "cors_analysis": self._analyze_cors_headers(response_headers, origin)
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "request_headers": headers
            }
    
    async def test_websocket_cors(self, ws_endpoint: str, origin: str) -> Dict[str, Any]:
        """Test WebSocket CORS."""
        ws_url = self.base_url.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url = urljoin(ws_url, ws_endpoint.lstrip('/'))
        
        extra_headers = {"Origin": origin}
        
        try:
            # Try to connect with origin header
            start_time = time.time()
            websocket = await websockets.connect(ws_url, additional_headers=extra_headers)
            connection_time = time.time() - start_time
            
            # Send a test message
            await websocket.send(json.dumps({"type": "test", "data": "cors_test"}))
            
            # Try to receive response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                await websocket.close()
                
                return {
                    "success": True,
                    "connection_successful": True,
                    "connection_time": connection_time,
                    "origin": origin,
                    "url": ws_url,
                    "test_message_response": response
                }
            except asyncio.TimeoutError:
                await websocket.close()
                return {
                    "success": True,
                    "connection_successful": True,
                    "connection_time": connection_time,
                    "origin": origin,
                    "url": ws_url,
                    "note": "Connection successful, no response to test message (expected)"
                }
                
        except websockets.exceptions.InvalidStatus as e:
            return {
                "success": False,
                "connection_successful": False,
                "status_code": e.status_code,
                "origin": origin,
                "url": ws_url,
                "error": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "connection_successful": False,
                "origin": origin,
                "url": ws_url,
                "error": str(e)
            }
    
    def _analyze_cors_headers(self, headers: Dict[str, str], origin: str) -> Dict[str, Any]:
        """Analyze CORS headers in response."""
        # Normalize header names (case-insensitive)
        normalized = {k.lower(): v for k, v in headers.items()}
        
        analysis = {
            "origin_allowed": False,
            "credentials_allowed": False,
            "methods_allowed": [],
            "headers_allowed": [],
            "max_age": None,
            "vary_header": False,
            "issues": [],
            "recommendations": []
        }
        
        # Check Access-Control-Allow-Origin
        cors_origin = normalized.get("access-control-allow-origin")
        if cors_origin:
            if cors_origin == origin:
                analysis["origin_allowed"] = True
            elif cors_origin == "*":
                analysis["origin_allowed"] = True
                analysis["recommendations"].append("Using wildcard (*) origin - consider specific origins for security")
            else:
                analysis["issues"].append(f"Origin mismatch: expected {origin}, got {cors_origin}")
        else:
            analysis["issues"].append("Missing Access-Control-Allow-Origin header")
        
        # Check credentials
        credentials = normalized.get("access-control-allow-credentials")
        if credentials == "true":
            analysis["credentials_allowed"] = True
        elif credentials:
            analysis["issues"].append(f"Invalid credentials header value: {credentials}")
        
        # Check methods
        methods = normalized.get("access-control-allow-methods", "")
        analysis["methods_allowed"] = [m.strip() for m in methods.split(",") if m.strip()]
        
        # Check headers  
        allowed_headers = normalized.get("access-control-allow-headers", "")
        analysis["headers_allowed"] = [h.strip() for h in allowed_headers.split(",") if h.strip()]
        
        # Check max age
        max_age = normalized.get("access-control-max-age")
        if max_age:
            try:
                analysis["max_age"] = int(max_age)
            except ValueError:
                analysis["issues"].append(f"Invalid max-age value: {max_age}")
        
        # Check Vary header
        vary = normalized.get("vary", "")
        analysis["vary_header"] = "origin" in vary.lower()
        if not analysis["vary_header"]:
            analysis["recommendations"].append("Add 'Vary: Origin' header for proper caching")
        
        # Security recommendations
        if cors_origin == "*" and analysis["credentials_allowed"]:
            analysis["issues"].append("Security issue: Cannot use wildcard origin with credentials")
        
        return analysis
    
    def generate_cors_report(self, environment: str = None) -> Dict[str, Any]:
        """Generate comprehensive CORS configuration report."""
        if environment is None:
            environment = self.environment
            
        report = {
            "environment": environment,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "configuration": {},
            "origins": {},
            "validation": {},
            "recommendations": []
        }
        
        try:
            # Get configuration
            config = get_cors_config(environment)
            report["configuration"] = config
            
            # Get origins
            origins = get_cors_origins(environment)
            report["origins"] = {
                "count": len(origins),
                "origins": origins,
                "by_type": self._categorize_origins(origins)
            }
            
            # Validate configuration
            validation = validate_cors_config(config)
            report["validation"]["config_valid"] = validation
            
            # Health info
            health_info = get_cors_health_info(environment)
            report["health"] = health_info
            
            # Generate recommendations
            report["recommendations"] = self._generate_recommendations(config, origins, environment)
            
        except Exception as e:
            report["error"] = str(e)
            
        return report
    
    def _categorize_origins(self, origins: List[str]) -> Dict[str, List[str]]:
        """Categorize origins by type."""
        categories = {
            "localhost": [],
            "staging": [],
            "production": [],
            "cloud_run": [],
            "https": [],
            "http": [],
            "other": []
        }
        
        for origin in origins:
            if "localhost" in origin or "127.0.0.1" in origin:
                categories["localhost"].append(origin)
            elif "staging" in origin:
                categories["staging"].append(origin)
            elif "netrasystems.ai" in origin and "staging" not in origin:
                categories["production"].append(origin)
            elif "run.app" in origin:
                categories["cloud_run"].append(origin)
            elif origin.startswith("https://"):
                categories["https"].append(origin)
            elif origin.startswith("http://"):
                categories["http"].append(origin)
            else:
                categories["other"].append(origin)
                
        return {k: v for k, v in categories.items() if v}  # Remove empty categories
    
    def _generate_recommendations(self, config: Dict, origins: List[str], environment: str) -> List[str]:
        """Generate CORS configuration recommendations."""
        recommendations = []
        
        # Check origin count
        if len(origins) > 50:
            recommendations.append(f"Large number of origins ({len(origins)}) - consider wildcards or dynamic validation")
        
        # Check for HTTP origins in production
        if environment == "production":
            http_origins = [o for o in origins if o.startswith("http://")]
            if http_origins:
                recommendations.append(f"HTTP origins in production: {http_origins} - security risk")
        
        # Check for localhost in production
        if environment == "production":
            localhost_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                recommendations.append(f"Localhost origins in production: {localhost_origins} - remove for security")
        
        # Check max age
        if config.get("max_age", 0) < 3600:
            recommendations.append("Consider increasing max_age to reduce preflight requests")
        
        # Check exposed headers
        exposed = config.get("expose_headers", [])
        if not exposed:
            recommendations.append("Consider exposing useful headers (X-Request-ID, etc.)")
        
        return recommendations


def format_cors_test_results(results: List[Dict[str, Any]], format_type: str = "table") -> str:
    """Format CORS test results for display."""
    if not results:
        return "No results to display"
    
    if format_type == "json":
        return json.dumps(results, indent=2, default=str)
    
    # Table format
    headers = ["Endpoint", "Origin", "Status", "CORS OK", "Issues"]
    rows = []
    
    for result in results:
        if result.get("success"):
            cors_analysis = result.get("cors_analysis", {})
            status = result.get("status_code", "N/A")
            cors_ok = "✓" if cors_analysis.get("origin_allowed") else "✗"
            issues = "; ".join(cors_analysis.get("issues", []))[:50]
            
            rows.append([
                result.get("url", "N/A")[-30:],  # Last 30 chars of URL
                result.get("request_headers", {}).get("Origin", "N/A")[-25:],
                status,
                cors_ok,
                issues or "None"
            ])
        else:
            rows.append([
                result.get("url", "N/A")[-30:],
                result.get("request_headers", {}).get("Origin", "N/A")[-25:],
                "ERROR",
                "✗",
                result.get("error", "Unknown error")[:50]
            ])
    
    if HAS_TABULATE:
        return tabulate(rows, headers=headers, tablefmt="grid")
    else:
        # Fallback to simple text table
        output = []
        # Header
        header_row = " | ".join(f"{h:15}" for h in headers)
        output.append(header_row)
        output.append("-" * len(header_row))
        
        # Rows
        for row in rows:
            row_str = " | ".join(f"{str(cell)[:15]:15}" for cell in row)
            output.append(row_str)
        
        return "\n".join(output)


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="CORS Testing and Debugging Tool")
    
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL for testing (default: http://localhost:8000)")
    parser.add_argument("--environment", default="development",
                       choices=["development", "staging", "production"],
                       help="Environment to test (default: development)")
    parser.add_argument("--endpoint", default="/health",
                       help="Endpoint to test (default: /health)")
    parser.add_argument("--origin", action="append",
                       help="Origin to test (can be specified multiple times)")
    parser.add_argument("--method", default="GET",
                       help="HTTP method for actual requests (default: GET)")
    parser.add_argument("--test-websocket", action="store_true",
                       help="Also test WebSocket CORS")
    parser.add_argument("--ws-endpoint", default="/ws",
                       help="WebSocket endpoint to test (default: /ws)")
    parser.add_argument("--format", choices=["table", "json"], default="table",
                       help="Output format (default: table)")
    parser.add_argument("--report-only", action="store_true",
                       help="Only generate configuration report")
    parser.add_argument("--test-all-origins", action="store_true",
                       help="Test all configured origins for the environment")
    parser.add_argument("--preflight-only", action="store_true",
                       help="Only test preflight requests")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Initialize tester
    async with CORSTester(args.base_url, args.environment) as tester:
        
        if args.report_only:
            # Generate and display configuration report
            report = tester.generate_cors_report(args.environment)
            
            if args.format == "json":
                print(json.dumps(report, indent=2, default=str))
            else:
                print("CORS Configuration Report")
                print("=" * 50)
                print(f"Environment: {report['environment']}")
                print(f"Timestamp: {report['timestamp']}")
                print(f"Origin Count: {report['origins']['count']}")
                print(f"Config Valid: {report['validation']['config_valid']}")
                
                if report.get("origins", {}).get("by_type"):
                    print("\nOrigins by Type:")
                    for origin_type, origins in report["origins"]["by_type"].items():
                        print(f"  {origin_type}: {len(origins)}")
                        if args.verbose:
                            for origin in origins[:5]:  # Show first 5
                                print(f"    - {origin}")
                            if len(origins) > 5:
                                print(f"    ... and {len(origins) - 5} more")
                
                if report.get("recommendations"):
                    print("\nRecommendations:")
                    for rec in report["recommendations"]:
                        print(f"  - {rec}")
            
            return
        
        # Determine origins to test
        test_origins = args.origin or []
        
        if args.test_all_origins or not test_origins:
            config_origins = get_cors_origins(args.environment)
            if args.test_all_origins:
                test_origins = config_origins[:10]  # Limit to first 10 for sanity
            else:
                # Default test origins
                if args.environment == "development":
                    test_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
                elif args.environment == "staging":
                    test_origins = ["https://app.staging.netrasystems.ai", "http://localhost:3000"]
                else:
                    test_origins = ["https://app.netrasystems.ai"]
        
        if not test_origins:
            print("No origins specified for testing")
            return
        
        print(f"Testing CORS for {args.base_url} ({args.environment})")
        print(f"Endpoint: {args.endpoint}")
        print(f"Origins: {', '.join(test_origins)}")
        print("-" * 50)
        
        results = []
        
        # Test each origin
        for origin in test_origins:
            print(f"Testing origin: {origin}")
            
            # Test preflight
            preflight_result = await tester.test_cors_preflight(args.endpoint, origin)
            results.append({**preflight_result, "test_type": "preflight"})
            
            if args.verbose:
                print(f"  Preflight: {'✓' if preflight_result.get('success') else '✗'}")
            
            # Test actual request (unless preflight-only)
            if not args.preflight_only:
                actual_result = await tester.test_cors_actual_request(args.endpoint, origin, args.method)
                results.append({**actual_result, "test_type": "actual"})
                
                if args.verbose:
                    print(f"  Actual: {'✓' if actual_result.get('success') else '✗'}")
            
            # Test WebSocket if requested
            if args.test_websocket:
                ws_result = await tester.test_websocket_cors(args.ws_endpoint, origin)
                results.append({**ws_result, "test_type": "websocket"})
                
                if args.verbose:
                    print(f"  WebSocket: {'✓' if ws_result.get('success') else '✗'}")
        
        # Display results
        print("\nResults:")
        print(format_cors_test_results(results, args.format))
        
        # Summary
        successful = len([r for r in results if r.get("success")])
        total = len(results)
        print(f"\nSummary: {successful}/{total} tests passed")
        
        # Show CORS issues if any
        issues = []
        for result in results:
            if result.get("cors_analysis", {}).get("issues"):
                issues.extend(result["cors_analysis"]["issues"])
        
        if issues:
            print(f"\nCORS Issues Found:")
            for issue in set(issues):  # Deduplicate
                print(f"  - {issue}")


if __name__ == "__main__":
    asyncio.run(main())