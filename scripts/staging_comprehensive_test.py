#!/usr/bin/env python
"""
Comprehensive Staging Environment Test Suite
============================================
Direct testing of staging services with real endpoints and comprehensive validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: Risk Reduction and Platform Stability
- Value Impact: Ensures staging environment reliability before production deployment
- Strategic Impact: Prevents production outages and enables confident releases
"""

import asyncio
import json
import time
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import aiohttp
import requests

# Staging environment URLs
STAGING_URLS = {
    'frontend': 'https://app.staging.netrasystems.ai',
    'backend': 'https://api.staging.netrasystems.ai',
    'auth': 'https://auth.staging.netrasystems.ai'
}

@dataclass
class TestResult:
    """Container for test results with comprehensive details."""
    test_name: str
    service: str
    status: str  # 'PASS', 'FAIL', 'SKIP', 'ERROR'
    duration_ms: int
    details: Dict[str, Any]
    error_message: Optional[str] = None

@dataclass
class ServiceHealthCheck:
    """Service health check result."""
    service: str
    url: str
    status_code: int
    response_time_ms: int
    healthy: bool
    response_data: Optional[Dict] = None
    error: Optional[str] = None

class StagingTestSuite:
    """Comprehensive staging environment test suite."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.health_checks: Dict[str, ServiceHealthCheck] = {}
        
    def record_result(self, test_name: str, service: str, status: str, 
                     duration_ms: int, details: Dict[str, Any], 
                     error_message: Optional[str] = None):
        """Record a test result."""
        result = TestResult(
            test_name=test_name,
            service=service,
            status=status,
            duration_ms=duration_ms,
            details=details,
            error_message=error_message
        )
        self.results.append(result)
        print(f"[{status}] {test_name} ({service}) - {duration_ms}ms")
        if error_message:
            print(f"  Error: {error_message}")
        
    async def test_health_endpoints(self) -> None:
        """Test all health endpoints with different HTTP methods."""
        print("\n=== TESTING HEALTH ENDPOINTS ===")
        
        health_endpoints = {
            'frontend': f"{STAGING_URLS['frontend']}/health",
            'backend': f"{STAGING_URLS['backend']}/health",
            'auth': f"{STAGING_URLS['auth']}/health"
        }
        
        for service, url in health_endpoints.items():
            await self._test_service_health_methods(service, url)
    
    async def _test_service_health_methods(self, service: str, url: str) -> None:
        """Test different HTTP methods for a service health endpoint."""
        methods = ['GET', 'HEAD', 'OPTIONS']
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for method in methods:
                test_name = f"health_endpoint_{method.lower()}_method"
                start_time = time.time()
                
                try:
                    async with session.request(method, url) as response:
                        duration_ms = int((time.time() - start_time) * 1000)
                        
                        details = {
                            'method': method,
                            'url': url,
                            'status_code': response.status,
                            'headers': dict(response.headers),
                            'response_time_ms': duration_ms
                        }
                        
                        if method == 'GET' and response.status == 200:
                            try:
                                response_json = await response.json()
                                details['response_data'] = response_json
                            except:
                                details['response_text'] = (await response.text())[:500]
                        
                        # Determine test status
                        if method == 'GET' and response.status == 200:
                            status = 'PASS'
                        elif method == 'HEAD' and response.status in [200, 204]:
                            status = 'PASS'
                        elif method == 'OPTIONS' and response.status in [200, 204]:
                            status = 'PASS'
                        elif method in ['HEAD', 'OPTIONS'] and response.status == 405:
                            status = 'FAIL'
                            details['expected_support'] = f"{method} should be supported for health endpoints"
                        else:
                            status = 'FAIL'
                            
                        self.record_result(test_name, service, status, duration_ms, details)
                        
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.record_result(
                        test_name, service, 'ERROR', duration_ms, 
                        {'method': method, 'url': url}, str(e)
                    )
    
    async def test_service_integration(self) -> None:
        """Test cross-service integration and dependencies."""
        print("\n=== TESTING SERVICE INTEGRATION ===")
        
        # Test frontend can reach backend and auth
        await self._test_frontend_service_dependencies()
        
        # Test basic API endpoints
        await self._test_basic_api_endpoints()
        
        # Test CORS configuration
        await self._test_cors_configuration()
    
    async def _test_frontend_service_dependencies(self) -> None:
        """Test that frontend can reach its dependencies."""
        frontend_health_url = f"{STAGING_URLS['frontend']}/health"
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(frontend_health_url) as response:
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        data = await response.json()
                        dependencies = data.get('dependencies', {})
                        
                        details = {
                            'frontend_response': data,
                            'backend_status': dependencies.get('backend', {}).get('status'),
                            'auth_status': dependencies.get('auth', {}).get('status'),
                        }
                        
                        # Check if all dependencies are healthy
                        backend_healthy = dependencies.get('backend', {}).get('status') == 'healthy'
                        auth_healthy = dependencies.get('auth', {}).get('status') == 'healthy'
                        
                        status = 'PASS' if backend_healthy and auth_healthy else 'FAIL'
                        if not backend_healthy:
                            details['backend_issue'] = dependencies.get('backend')
                        if not auth_healthy:
                            details['auth_issue'] = dependencies.get('auth')
                            
                        self.record_result(
                            'frontend_service_dependencies', 'integration', 
                            status, duration_ms, details
                        )
                    else:
                        self.record_result(
                            'frontend_service_dependencies', 'integration',
                            'FAIL', duration_ms, 
                            {'status_code': response.status, 'text': await response.text()}
                        )
                        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.record_result(
                'frontend_service_dependencies', 'integration',
                'ERROR', duration_ms, {}, str(e)
            )
    
    async def _test_basic_api_endpoints(self) -> None:
        """Test basic API endpoints availability."""
        api_endpoints = [
            '/api/health',
            '/api/v1/status',
            '/health',
            '/'
        ]
        
        backend_url = STAGING_URLS['backend']
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for endpoint in api_endpoints:
                test_name = f"api_endpoint_{endpoint.replace('/', '_').replace('_', '', 1) or 'root'}"
                url = f"{backend_url}{endpoint}"
                start_time = time.time()
                
                try:
                    async with session.get(url) as response:
                        duration_ms = int((time.time() - start_time) * 1000)
                        
                        details = {
                            'endpoint': endpoint,
                            'url': url,
                            'status_code': response.status,
                            'response_time_ms': duration_ms
                        }
                        
                        if response.status in [200, 404]:  # 404 is acceptable for some endpoints
                            status = 'PASS' if response.status == 200 else 'SKIP'
                        else:
                            status = 'FAIL'
                            
                        if response.status == 200:
                            try:
                                details['response_data'] = await response.json()
                            except:
                                details['response_text'] = (await response.text())[:200]
                                
                        self.record_result(test_name, 'backend', status, duration_ms, details)
                        
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.record_result(
                        test_name, 'backend', 'ERROR', duration_ms, 
                        {'endpoint': endpoint, 'url': url}, str(e)
                    )
    
    async def _test_cors_configuration(self) -> None:
        """Test CORS configuration for cross-origin requests."""
        print("Testing CORS configuration...")
        
        # Test OPTIONS request with CORS headers
        backend_url = f"{STAGING_URLS['backend']}/health"
        
        headers = {
            'Origin': 'https://app.netra.ai',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type,Authorization'
        }
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.options(backend_url, headers=headers) as response:
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    cors_headers = {
                        'access-control-allow-origin': response.headers.get('Access-Control-Allow-Origin'),
                        'access-control-allow-methods': response.headers.get('Access-Control-Allow-Methods'),
                        'access-control-allow-headers': response.headers.get('Access-Control-Allow-Headers'),
                        'access-control-max-age': response.headers.get('Access-Control-Max-Age')
                    }
                    
                    details = {
                        'status_code': response.status,
                        'cors_headers': cors_headers,
                        'response_headers': dict(response.headers)
                    }
                    
                    # Check if CORS is properly configured
                    has_origin = cors_headers.get('access-control-allow-origin') is not None
                    has_methods = cors_headers.get('access-control-allow-methods') is not None
                    
                    status = 'PASS' if (response.status in [200, 204] and has_origin) else 'FAIL'
                    
                    self.record_result('cors_configuration', 'backend', status, duration_ms, details)
                    
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.record_result(
                'cors_configuration', 'backend', 'ERROR', duration_ms, 
                {'headers': headers}, str(e)
            )
    
    async def test_performance_metrics(self) -> None:
        """Test performance metrics for all services."""
        print("\n=== TESTING PERFORMANCE METRICS ===")
        
        performance_thresholds = {
            'health_response_time_ms': 2000,  # 2 seconds max
            'api_response_time_ms': 3000,     # 3 seconds max
            'concurrent_requests': 5          # Test with 5 concurrent requests
        }
        
        for service, base_url in STAGING_URLS.items():
            await self._test_service_performance(service, base_url, performance_thresholds)
    
    async def _test_service_performance(self, service: str, base_url: str, thresholds: Dict[str, int]) -> None:
        """Test performance for a specific service."""
        health_url = f"{base_url}/health"
        
        # Test single request performance
        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(health_url) as response:
                    single_request_time = int((time.time() - start_time) * 1000)
                    
                    status = 'PASS' if single_request_time < thresholds['health_response_time_ms'] else 'FAIL'
                    
                    details = {
                        'response_time_ms': single_request_time,
                        'threshold_ms': thresholds['health_response_time_ms'],
                        'status_code': response.status
                    }
                    
                    self.record_result(
                        'single_request_performance', service, 
                        status, single_request_time, details
                    )
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.record_result(
                'single_request_performance', service, 'ERROR', duration_ms, {}, str(e)
            )
        
        # Test concurrent requests
        await self._test_concurrent_requests(service, health_url, thresholds)
    
    async def _test_concurrent_requests(self, service: str, url: str, thresholds: Dict[str, int]) -> None:
        """Test concurrent request handling."""
        concurrent_count = thresholds['concurrent_requests']
        
        async def make_request(session, request_id):
            start = time.time()
            try:
                async with session.get(url) as response:
                    return {
                        'request_id': request_id,
                        'status_code': response.status,
                        'response_time_ms': int((time.time() - start) * 1000)
                    }
            except Exception as e:
                return {
                    'request_id': request_id,
                    'error': str(e),
                    'response_time_ms': int((time.time() - start) * 1000)
                }
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                tasks = [make_request(session, i) for i in range(concurrent_count)]
                results = await asyncio.gather(*tasks)
                
                total_time = int((time.time() - start_time) * 1000)
                
                successful_requests = [r for r in results if r.get('status_code') == 200]
                failed_requests = [r for r in results if 'error' in r or r.get('status_code') != 200]
                
                avg_response_time = sum(r['response_time_ms'] for r in successful_requests) / len(successful_requests) if successful_requests else 0
                
                status = 'PASS' if len(successful_requests) >= concurrent_count * 0.8 else 'FAIL'  # 80% success rate
                
                details = {
                    'concurrent_requests': concurrent_count,
                    'successful_requests': len(successful_requests),
                    'failed_requests': len(failed_requests),
                    'total_time_ms': total_time,
                    'average_response_time_ms': int(avg_response_time),
                    'results': results
                }
                
                self.record_result(
                    'concurrent_requests_performance', service,
                    status, total_time, details
                )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.record_result(
                'concurrent_requests_performance', service, 'ERROR', duration_ms, 
                {'concurrent_count': concurrent_count}, str(e)
            )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == 'PASS'])
        failed_tests = len([r for r in self.results if r.status == 'FAIL'])
        error_tests = len([r for r in self.results if r.status == 'ERROR'])
        skipped_tests = len([r for r in self.results if r.status == 'SKIP'])
        
        # Group results by service
        by_service = {}
        for result in self.results:
            if result.service not in by_service:
                by_service[result.service] = {'PASS': 0, 'FAIL': 0, 'ERROR': 0, 'SKIP': 0}
            by_service[result.service][result.status] += 1
        
        # Calculate average response times
        response_times = [r.duration_ms for r in self.results if r.duration_ms > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'errors': error_tests,
                'skipped': skipped_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'average_response_time_ms': int(avg_response_time)
            },
            'by_service': by_service,
            'staging_urls': STAGING_URLS,
            'detailed_results': [
                {
                    'test_name': r.test_name,
                    'service': r.service,
                    'status': r.status,
                    'duration_ms': r.duration_ms,
                    'error_message': r.error_message,
                    'details': r.details
                } for r in self.results
            ],
            'critical_issues': [
                {
                    'test_name': r.test_name,
                    'service': r.service,
                    'error': r.error_message,
                    'details': r.details
                }
                for r in self.results if r.status in ['FAIL', 'ERROR']
            ]
        }
        
        return report
    
    def print_report(self):
        """Print a human-readable test report."""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("STAGING ENVIRONMENT TEST REPORT")
        print("="*80)
        
        print(f"\nTEST SUMMARY:")
        print(f"  Total Tests: {report['summary']['total_tests']}")
        print(f"  Passed: {report['summary']['passed']}")
        print(f"  Failed: {report['summary']['failed']}")
        print(f"  Errors: {report['summary']['errors']}")
        print(f"  Skipped: {report['summary']['skipped']}")
        print(f"  Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"  Average Response Time: {report['summary']['average_response_time_ms']}ms")
        
        print(f"\nRESULTS BY SERVICE:")
        for service, counts in report['by_service'].items():
            total_service = sum(counts.values())
            success_rate = (counts['PASS'] / total_service * 100) if total_service > 0 else 0
            print(f"  {service}: {counts['PASS']}/{total_service} tests passed ({success_rate:.1f}%)")
            if counts['FAIL'] > 0 or counts['ERROR'] > 0:
                print(f"    Failures: {counts['FAIL']}, Errors: {counts['ERROR']}")
        
        print(f"\nSTAGING URLS:")
        for service, url in report['staging_urls'].items():
            print(f"  {service}: {url}")
        
        if report['critical_issues']:
            print(f"\nCRITICAL ISSUES ({len(report['critical_issues'])}):")
            for issue in report['critical_issues'][:10]:  # Show first 10
                print(f"  [ISSUE] {issue['test_name']} ({issue['service']})")
                if issue['error']:
                    print(f"    Error: {issue['error']}")
        
        print("\n" + "="*80)

async def main():
    """Run comprehensive staging tests."""
    print("NETRA APEX STAGING ENVIRONMENT COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    suite = StagingTestSuite()
    
    try:
        # Run all test categories
        await suite.test_health_endpoints()
        await suite.test_service_integration()
        await suite.test_performance_metrics()
        
        # Generate and display report
        suite.print_report()
        
        # Save detailed report to file
        report = suite.generate_report()
        with open('staging_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: staging_test_report.json")
        
        # Return exit code based on success rate
        success_rate = report['summary']['success_rate']
        if success_rate >= 90:
            print(f"\n[PASS] STAGING ENVIRONMENT HEALTHY ({success_rate:.1f}% success rate)")
            return 0
        elif success_rate >= 70:
            print(f"\n[WARN] STAGING ENVIRONMENT ISSUES DETECTED ({success_rate:.1f}% success rate)")
            return 1
        else:
            print(f"\n[FAIL] STAGING ENVIRONMENT CRITICAL ISSUES ({success_rate:.1f}% success rate)")
            return 2
            
    except Exception as e:
        print(f"\n[ERROR] CRITICAL ERROR DURING TESTING: {e}")
        print(traceback.format_exc())
        return 3

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))