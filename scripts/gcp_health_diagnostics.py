#!/usr/bin/env python3
"""
GCP Health Diagnostics - Detailed Analysis Tool

Business Value: Provides detailed diagnostic information for failed services,
helping to identify root causes and estimate recovery times.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import aiohttp
import requests
from colorama import Fore, Style, init

# Fix Unicode encoding issues on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Initialize colorama
init(autoreset=True)

class GCPHealthDiagnostics:
    """Detailed diagnostics for GCP service health issues."""
    
    def __init__(self):
        """Initialize diagnostics system."""
        self.services = {
            "auth": {
                "name": "Auth Service",
                "base_url": "https://netra-auth-service-701982941522.us-central1.run.app",
                "endpoints": [
                    {"path": "/health", "description": "Main health check"},
                    {"path": "/auth/health", "description": "Auth module health"},
                    {"path": "/docs", "description": "API documentation"},
                    {"path": "/auth/validate", "description": "Token validation endpoint"}
                ]
            },
            "backend": {
                "name": "Backend Service", 
                "base_url": "https://netra-backend-staging-701982941522.us-central1.run.app",
                "endpoints": [
                    {"path": "/health", "description": "Main health check"},
                    {"path": "/health/ready", "description": "Readiness probe"},
                    {"path": "/health/database", "description": "Database connectivity"},
                    {"path": "/health/system", "description": "System health"},
                    {"path": "/docs", "description": "API documentation"},
                    {"path": "/api/status", "description": "API status endpoint"}
                ]
            },
            "frontend": {
                "name": "Frontend Service",
                "base_url": "https://netra-frontend-staging-701982941522.us-central1.run.app",
                "endpoints": [
                    {"path": "/", "description": "Main application page"},
                    {"path": "/_next/static/chunks/webpack.js", "description": "Next.js webpack"},
                    {"path": "/api/health", "description": "Frontend API health"},
                    {"path": "/favicon.ico", "description": "Favicon"}
                ]
            }
        }
    
    async def run_comprehensive_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive diagnostics on all services."""
        print(f"{Fore.CYAN}=== GCP Health Diagnostics ==={Style.RESET_ALL}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for service_key, service_config in self.services.items():
                print(f"\n{Fore.CYAN}Analyzing {service_config['name']}...{Style.RESET_ALL}")
                results[service_key] = await self._analyze_service(session, service_config)
        
        # Generate analysis summary
        self._generate_analysis_summary(results)
        return results
    
    async def _analyze_service(self, session: aiohttp.ClientSession, service_config: Dict) -> Dict[str, Any]:
        """Analyze a single service in detail."""
        base_url = service_config["base_url"]
        service_name = service_config["name"]
        
        analysis = {
            "service_name": service_name,
            "base_url": base_url,
            "endpoints": [],
            "overall_status": "unknown",
            "response_patterns": [],
            "error_patterns": [],
            "performance_metrics": {},
            "recommendations": []
        }
        
        # Test all endpoints
        for endpoint in service_config["endpoints"]:
            result = await self._test_endpoint(session, base_url, endpoint)
            analysis["endpoints"].append(result)
        
        # Analyze patterns
        self._analyze_response_patterns(analysis)
        self._generate_recommendations(analysis)
        
        # Display results
        self._display_service_analysis(analysis)
        
        return analysis
    
    async def _test_endpoint(self, session: aiohttp.ClientSession, base_url: str, endpoint: Dict) -> Dict[str, Any]:
        """Test a single endpoint with detailed analysis."""
        url = f"{base_url.rstrip('/')}{endpoint['path']}"
        
        result = {
            "path": endpoint["path"],
            "description": endpoint["description"],
            "url": url,
            "status_code": None,
            "response_time": None,
            "content_length": None,
            "headers": {},
            "error": None,
            "content_sample": None,
            "healthy": False
        }
        
        start_time = time.time()
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                result["response_time"] = time.time() - start_time
                result["status_code"] = response.status
                result["headers"] = dict(response.headers)
                
                # Read content with size limit
                content = await response.read()
                result["content_length"] = len(content)
                
                # Get content sample
                if content:
                    content_text = content.decode('utf-8', errors='ignore')[:500]
                    result["content_sample"] = content_text
                
                # Determine if healthy
                if response.status == 200:
                    # Additional checks for specific endpoints
                    if endpoint["path"] == "/" and "404" in content_text:
                        result["healthy"] = False
                        result["error"] = "Page shows 404 content"
                    else:
                        result["healthy"] = True
                else:
                    result["healthy"] = False
                    
        except asyncio.TimeoutError:
            result["error"] = "Request timeout (15s)"
            result["response_time"] = 15.0
        except Exception as e:
            result["error"] = str(e)
            result["response_time"] = time.time() - start_time
        
        return result
    
    def _analyze_response_patterns(self, analysis: Dict[str, Any]):
        """Analyze response patterns to identify issues."""
        endpoints = analysis["endpoints"]
        
        # Count status codes
        status_codes = {}
        response_times = []
        
        for endpoint in endpoints:
            if endpoint["status_code"]:
                status_codes[endpoint["status_code"]] = status_codes.get(endpoint["status_code"], 0) + 1
            if endpoint["response_time"]:
                response_times.append(endpoint["response_time"])
        
        # Determine overall status
        healthy_endpoints = [e for e in endpoints if e["healthy"]]
        if len(healthy_endpoints) == len(endpoints):
            analysis["overall_status"] = "healthy"
        elif len(healthy_endpoints) > 0:
            analysis["overall_status"] = "degraded"
        else:
            analysis["overall_status"] = "critical"
        
        # Performance metrics
        if response_times:
            analysis["performance_metrics"] = {
                "avg_response_time": sum(response_times) / len(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times)
            }
        
        # Error patterns
        errors = [e["error"] for e in endpoints if e["error"]]
        if errors:
            analysis["error_patterns"] = list(set(errors))
    
    def _generate_recommendations(self, analysis: Dict[str, Any]):
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Check for common patterns
        status_503_count = len([e for e in analysis["endpoints"] if e["status_code"] == 503])
        if status_503_count > 0:
            recommendations.append("Service Unavailable (503) errors suggest backend dependency issues")
            recommendations.append("Check database connections and external service dependencies")
        
        status_404_count = len([e for e in analysis["endpoints"] if "404" in str(e.get("error", ""))])
        if status_404_count > 0:
            recommendations.append("404 errors suggest routing or deployment configuration issues")
            recommendations.append("Verify service deployment and URL routing configuration")
        
        timeout_count = len([e for e in analysis["endpoints"] if "timeout" in str(e.get("error", "")).lower()])
        if timeout_count > 0:
            recommendations.append("Timeout errors suggest performance or connectivity issues")
            recommendations.append("Check service resources and network connectivity")
        
        # Performance recommendations
        if analysis["performance_metrics"].get("avg_response_time", 0) > 5:
            recommendations.append("High response times detected - consider resource scaling")
        
        # Service-specific recommendations
        service_name = analysis["service_name"].lower()
        if "backend" in service_name and analysis["overall_status"] != "healthy":
            recommendations.append("Backend service issues may affect frontend and auth services")
            recommendations.append("Priority: Fix database connectivity and readiness checks")
        
        if "frontend" in service_name and any("404" in str(e.get("error", "")) for e in analysis["endpoints"]):
            recommendations.append("Frontend showing 404 may indicate build or routing issues")
            recommendations.append("Check Next.js build process and deployment configuration")
        
        analysis["recommendations"] = recommendations
    
    def _display_service_analysis(self, analysis: Dict[str, Any]):
        """Display detailed analysis for a service."""
        service_name = analysis["service_name"]
        status = analysis["overall_status"]
        
        # Status header
        if status == "healthy":
            status_color = Fore.GREEN
            status_icon = "[OK]"
        elif status == "degraded":
            status_color = Fore.YELLOW
            status_icon = "[WARN]"
        else:
            status_color = Fore.RED
            status_icon = "[FAIL]"
        
        print(f"\n{status_color}{status_icon} {service_name} - {status.upper()}{Style.RESET_ALL}")
        print("-" * 40)
        
        # Endpoint details
        print(f"\n{Fore.CYAN}Endpoint Analysis:{Style.RESET_ALL}")
        for endpoint in analysis["endpoints"]:
            status_symbol = "[OK]" if endpoint["healthy"] else "[FAIL]"
            color = Fore.GREEN if endpoint["healthy"] else Fore.RED
            
            print(f"{color}{status_symbol} {endpoint['path']:<20} - {endpoint['description']}{Style.RESET_ALL}")
            
            if endpoint["status_code"]:
                print(f"    Status: {endpoint['status_code']}")
            if endpoint["response_time"]:
                print(f"    Time: {endpoint['response_time']:.3f}s")
            if endpoint["error"]:
                print(f"    Error: {endpoint['error']}")
            if endpoint["content_length"]:
                print(f"    Size: {endpoint['content_length']} bytes")
        
        # Performance metrics
        if analysis["performance_metrics"]:
            metrics = analysis["performance_metrics"]
            print(f"\n{Fore.CYAN}Performance Metrics:{Style.RESET_ALL}")
            print(f"  Average Response Time: {metrics.get('avg_response_time', 0):.3f}s")
            print(f"  Max Response Time: {metrics.get('max_response_time', 0):.3f}s")
            print(f"  Min Response Time: {metrics.get('min_response_time', 0):.3f}s")
        
        # Error patterns
        if analysis["error_patterns"]:
            print(f"\n{Fore.RED}Error Patterns:{Style.RESET_ALL}")
            for error in analysis["error_patterns"]:
                print(f"  - {error}")
        
        # Recommendations
        if analysis["recommendations"]:
            print(f"\n{Fore.YELLOW}Recommendations:{Style.RESET_ALL}")
            for rec in analysis["recommendations"]:
                print(f"  - {rec}")
    
    def _generate_analysis_summary(self, results: Dict[str, Any]):
        """Generate overall analysis summary."""
        print(f"\n{Fore.CYAN}=== DIAGNOSTIC SUMMARY ==={Style.RESET_ALL}")
        
        healthy_services = []
        degraded_services = []
        critical_services = []
        
        for service_key, analysis in results.items():
            status = analysis["overall_status"]
            service_name = analysis["service_name"]
            
            if status == "healthy":
                healthy_services.append(service_name)
            elif status == "degraded":
                degraded_services.append(service_name)
            else:
                critical_services.append(service_name)
        
        print(f"\n{Fore.GREEN}Healthy Services: {len(healthy_services)}{Style.RESET_ALL}")
        for service in healthy_services:
            print(f"  - {service}")
        
        if degraded_services:
            print(f"\n{Fore.YELLOW}Degraded Services: {len(degraded_services)}{Style.RESET_ALL}")
            for service in degraded_services:
                print(f"  - {service}")
        
        if critical_services:
            print(f"\n{Fore.RED}Critical Services: {len(critical_services)}{Style.RESET_ALL}")
            for service in critical_services:
                print(f"  - {service}")
        
        # Overall recommendations
        print(f"\n{Fore.CYAN}PRIORITY ACTIONS:{Style.RESET_ALL}")
        if critical_services:
            print(f"1. {Fore.RED}URGENT:{Style.RESET_ALL} Address critical service failures first")
            if "Backend Service" in critical_services:
                print("   - Backend service failure affects entire platform")
                print("   - Focus on database connectivity and readiness checks")
            if "Frontend Service" in critical_services:
                print("   - Frontend issues prevent user access")
                print("   - Check deployment and routing configuration")
        
        if degraded_services:
            print(f"2. {Fore.YELLOW}HIGH:{Style.RESET_ALL} Investigate degraded services")
        
        # Estimated recovery time
        print(f"\n{Fore.CYAN}ESTIMATED RECOVERY TIME:{Style.RESET_ALL}")
        if len(critical_services) >= 2:
            print("  15-30 minutes (multiple critical services)")
        elif len(critical_services) == 1:
            print("  10-20 minutes (single critical service)")
        elif len(degraded_services) > 0:
            print("  5-15 minutes (degraded services only)")
        else:
            print("  System is healthy!")

async def main():
    """Main entry point for diagnostics."""
    diagnostics = GCPHealthDiagnostics()
    results = await diagnostics.run_comprehensive_diagnostics()
    
    # Return appropriate exit code
    critical_count = sum(1 for r in results.values() if r["overall_status"] == "critical")
    return 0 if critical_count == 0 else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Diagnostics interrupted by user{Style.RESET_ALL}")
        sys.exit(1)