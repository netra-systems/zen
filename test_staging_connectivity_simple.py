#!/usr/bin/env python3
"""
Simple staging connectivity test for Issue #1278
Tests basic connectivity to staging environment without complex dependencies.
"""

import asyncio
import aiohttp
import time
import sys
from typing import Dict, Any


async def test_staging_connectivity() -> Dict[str, Any]:
    """Test basic connectivity to staging environment."""
    
    # Staging URLs (must use *.netrasystems.ai domains per Issue #1278)
    staging_urls = {
        "backend_health": "https://staging.netrasystems.ai/health",
        "backend_api_health": "https://staging.netrasystems.ai/api/health",
        "frontend": "https://staging.netrasystems.ai"
    }
    
    results = {}
    
    print(f"🔍 Testing Issue #1278 staging connectivity at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
    print(f"📍 Testing staging domains: *.netrasystems.ai (fixed per Issue #1278)")
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30.0)
    ) as session:
        
        for service, url in staging_urls.items():
            start_time = time.time()
            
            try:
                print(f"  🌐 Testing {service}: {url}")
                
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    
                    # Try to read response body
                    try:
                        response_text = await response.text()
                        response_size = len(response_text)
                    except Exception:
                        response_text = "<unable to read>"
                        response_size = 0
                    
                    results[service] = {
                        "status": "success" if response.status == 200 else "error",
                        "status_code": response.status,
                        "response_time": response_time,
                        "response_size": response_size,
                        "headers": dict(response.headers),
                        "url": url
                    }
                    
                    status_icon = "✅" if response.status == 200 else "❌"
                    print(f"    {status_icon} Status: {response.status}, Time: {response_time:.2f}s, Size: {response_size} bytes")
                    
                    if response.status != 200:
                        print(f"    📄 Response: {response_text[:200]}...")
            
            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                results[service] = {
                    "status": "timeout",
                    "status_code": None,
                    "response_time": response_time,
                    "error": "Connection timeout",
                    "url": url
                }
                print(f"    ⏰ Timeout after {response_time:.2f}s")
            
            except Exception as e:
                response_time = time.time() - start_time
                results[service] = {
                    "status": "failed",
                    "status_code": None,
                    "response_time": response_time,
                    "error": str(e),
                    "url": url
                }
                print(f"    💥 Error: {str(e)}")
            
            # Small delay between requests
            await asyncio.sleep(1.0)
    
    return results


def analyze_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze connectivity test results."""
    
    total_tests = len(results)
    successful_tests = len([r for r in results.values() if r["status"] == "success"])
    timeout_tests = len([r for r in results.values() if r["status"] == "timeout"])
    failed_tests = len([r for r in results.values() if r["status"] == "failed"])
    error_tests = len([r for r in results.values() if r["status"] == "error"])
    
    success_rate = successful_tests / total_tests if total_tests > 0 else 0
    
    avg_response_time = 0
    if results:
        total_time = sum(r["response_time"] for r in results.values())
        avg_response_time = total_time / len(results)
    
    # Issue #1278 specific analysis
    http_503_count = len([r for r in results.values() if r.get("status_code") == 503])
    http_503_rate = http_503_count / total_tests if total_tests > 0 else 0
    
    analysis = {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "timeout_tests": timeout_tests,
        "failed_tests": failed_tests,
        "error_tests": error_tests,
        "http_503_count": http_503_count,
        "success_rate": success_rate,
        "http_503_rate": http_503_rate,
        "avg_response_time": avg_response_time,
        "issue_1278_indicators": {
            "has_timeouts": timeout_tests > 0,
            "has_503_errors": http_503_count > 0,
            "high_response_times": avg_response_time > 10.0,
            "connectivity_issues": success_rate < 0.8
        }
    }
    
    return analysis


def print_analysis(analysis: Dict[str, Any], results: Dict[str, Any]):
    """Print detailed analysis of connectivity results."""
    
    print(f"\n📊 STAGING CONNECTIVITY ANALYSIS (Issue #1278)")
    print(f"=" * 50)
    
    print(f"📈 Overall Metrics:")
    print(f"  Tests: {analysis['successful_tests']}/{analysis['total_tests']} successful ({analysis['success_rate']:.1%})")
    print(f"  Average Response Time: {analysis['avg_response_time']:.2f}s")
    print(f"  HTTP 503 Errors: {analysis['http_503_count']} ({analysis['http_503_rate']:.1%})")
    
    print(f"\n🚨 Issue #1278 Indicators:")
    indicators = analysis["issue_1278_indicators"]
    for indicator, value in indicators.items():
        status = "YES ❌" if value else "NO ✅"
        print(f"  {indicator.replace('_', ' ').title()}: {status}")
    
    print(f"\n📝 Service Details:")
    for service, result in results.items():
        status_icon = {"success": "✅", "timeout": "⏰", "failed": "💥", "error": "❌"}[result["status"]]
        print(f"  {service}: {status_icon} {result['status'].upper()}")
        if result.get("status_code"):
            print(f"    Status Code: {result['status_code']}")
        print(f"    Response Time: {result['response_time']:.2f}s")
        if result.get("error"):
            print(f"    Error: {result['error']}")
    
    # Overall assessment
    print(f"\n🎯 STAGING ENVIRONMENT ASSESSMENT:")
    
    if analysis["success_rate"] >= 0.9 and not indicators["has_503_errors"]:
        print(f"  🟢 HEALTHY: Staging environment is operational")
        print(f"  📋 Application-side mitigations appear to be working")
        assessment = "HEALTHY"
    elif analysis["success_rate"] >= 0.7:
        print(f"  🟡 DEGRADED: Staging environment has some issues")
        print(f"  📋 Application-side improvements may be needed")
        assessment = "DEGRADED"
    else:
        print(f"  🔴 CRITICAL: Staging environment has significant issues")
        print(f"  📋 Infrastructure team intervention required")
        assessment = "CRITICAL"
    
    if indicators["has_503_errors"]:
        print(f"  ⚠️  Issue #1278 HTTP 503 errors detected - infrastructure constraints likely")
    
    if indicators["high_response_times"]:
        print(f"  ⚠️  High response times detected - database/VPC connector issues likely")
    
    return assessment


async def main():
    """Main test execution."""
    print(f"🚀 Issue #1278 Staging Connectivity Test")
    print(f"📅 {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Testing application-side mitigations for staging outage")
    
    try:
        # Run connectivity tests
        results = await test_staging_connectivity()
        
        # Analyze results
        analysis = analyze_results(results)
        
        # Print analysis
        assessment = print_analysis(analysis, results)
        
        # Return appropriate exit code
        if assessment == "HEALTHY":
            print(f"\n✅ CONCLUSION: Staging environment is working - application mitigations successful")
            sys.exit(0)
        elif assessment == "DEGRADED":
            print(f"\n⚠️  CONCLUSION: Staging environment degraded - additional application work may help")
            sys.exit(1)
        else:
            print(f"\n❌ CONCLUSION: Staging environment critical - infrastructure team intervention required")
            sys.exit(2)
    
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())