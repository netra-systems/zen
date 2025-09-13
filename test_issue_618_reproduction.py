#!/usr/bin/env python3
"""
Issue #618 Reproduction Test Suite
==================================
Test suite specifically designed to reproduce the backend deployment + WebSocket routing issues
described in Issue #618.

Expected Failures:
1. Backend service returning 503 Service Unavailable
2. WebSocket handshake timeout failures  
3. Golden Path user journey failures
4. Service dependency failures

Business Value: $500K+ ARR Protection - Reproduce exact failure modes for remediation
"""

import asyncio
import json
import time
import uuid
import httpx
import websockets
from datetime import datetime
from typing import Dict, Any, List, Optional
import traceback

# Staging URLs based on Issue #618 description
STAGING_URLS = {
    'frontend': 'https://app.staging.netrasystems.ai',
    'backend': 'https://api.staging.netrasystems.ai', 
    'auth': 'https://auth.staging.netrasystems.ai',
    'websocket': 'wss://api.staging.netrasystems.ai/ws'
}

class Issue618TestResults:
    """Container for Issue #618 test results."""
    def __init__(self):
        self.results = []
        self.critical_failures = []
        self.start_time = time.time()
        
    def add_result(self, test_name: str, status: str, duration_ms: int, 
                   details: Dict[str, Any], error: Optional[str] = None):
        """Add a test result."""
        result = {
            'test_name': test_name,
            'status': status,  # PASS, FAIL, ERROR, TIMEOUT
            'duration_ms': duration_ms,
            'details': details,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        self.results.append(result)
        
        # Track critical failures
        if status in ['FAIL', 'ERROR', 'TIMEOUT']:
            self.critical_failures.append(result)
            
        print(f"[{status}] {test_name} - {duration_ms}ms" + (f" | {error}" if error else ""))

async def test_backend_503_errors():
    """Test: Backend service returning 503 Service Unavailable (Issue #618 Expected Failure)"""
    print("\n=== TESTING BACKEND 503 ERRORS (REPRODUCING ISSUE #618) ===")
    results = Issue618TestResults()
    
    # Test multiple backend endpoints for 503 errors
    endpoints = [
        '/health',
        '/api/health', 
        '/api/v1/chat',
        '/api/v1/agents',
        '/',
        '/ws'  # WebSocket endpoint
    ]
    
    async with httpx.AsyncClient(timeout=30) as client:
        for endpoint in endpoints:
            test_name = f"backend_503_check_{endpoint.replace('/', '_').replace('_', '', 1) or 'root'}"
            start_time = time.time()
            url = f"{STAGING_URLS['backend']}{endpoint}"
            
            try:
                response = await client.get(url)
                duration_ms = int((time.time() - start_time) * 1000)
                
                details = {
                    'endpoint': endpoint,
                    'url': url,
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'response_time_ms': duration_ms
                }
                
                # Issue #618 expects 503 errors - so 503 is "successful reproduction"
                if response.status_code == 503:
                    results.add_result(test_name, 'REPRODUCED', duration_ms, details, 
                                     "Successfully reproduced 503 Service Unavailable from Issue #618")
                elif response.status_code == 200:
                    results.add_result(test_name, 'UNEXPECTED_SUCCESS', duration_ms, details,
                                     "Backend is working (unexpected - Issue #618 reports 503 errors)")
                else:
                    results.add_result(test_name, 'OTHER_ERROR', duration_ms, details,
                                     f"Unexpected status code: {response.status_code}")
                    
                # Also capture response content for analysis
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        details['response_json'] = response.json()
                    else:
                        details['response_text'] = response.text[:500]
                except:
                    pass
                    
            except httpx.TimeoutException as e:
                duration_ms = int((time.time() - start_time) * 1000)
                results.add_result(test_name, 'TIMEOUT', duration_ms, 
                                 {'endpoint': endpoint, 'url': url}, f"Timeout: {e}")
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000) 
                results.add_result(test_name, 'ERROR', duration_ms,
                                 {'endpoint': endpoint, 'url': url}, f"Connection error: {e}")
    
    return results

async def test_websocket_handshake_timeouts():
    """Test: WebSocket handshake timeout failures (Issue #618 Expected Failure)"""
    print("\n=== TESTING WEBSOCKET HANDSHAKE TIMEOUTS (REPRODUCING ISSUE #618) ===")
    results = Issue618TestResults()
    
    # Test different WebSocket connection scenarios
    test_scenarios = [
        {
            'name': 'basic_connection_no_auth',
            'url': STAGING_URLS['websocket'],
            'headers': {},
            'timeout': 10
        },
        {
            'name': 'connection_with_invalid_auth', 
            'url': STAGING_URLS['websocket'],
            'headers': {'Authorization': 'Bearer invalid-token'},
            'timeout': 10
        },
        {
            'name': 'connection_with_custom_headers',
            'url': STAGING_URLS['websocket'],
            'headers': {
                'Origin': 'https://app.staging.netrasystems.ai',
                'User-Agent': 'Issue618TestSuite/1.0'
            },
            'timeout': 10
        },
        {
            'name': 'short_timeout_connection',
            'url': STAGING_URLS['websocket'],
            'headers': {},
            'timeout': 2  # Very short timeout to trigger timeout failures
        }
    ]
    
    for scenario in test_scenarios:
        test_name = f"websocket_handshake_{scenario['name']}"
        start_time = time.time()
        
        try:
            # Try to establish WebSocket connection
            async with websockets.connect(
                scenario['url'],
                extra_headers=scenario['headers'],
                close_timeout=scenario['timeout'],
                open_timeout=scenario['timeout']
            ) as websocket:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # If connection succeeds, try to send a message and wait for response
                test_message = {
                    'type': 'ping',
                    'test_id': str(uuid.uuid4()),
                    'timestamp': datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response) if response else None
                    
                    results.add_result(test_name, 'UNEXPECTED_SUCCESS', duration_ms, {
                        'scenario': scenario['name'],
                        'connection_established': True,
                        'message_sent': True,
                        'response_received': True,
                        'response_data': response_data
                    }, "WebSocket working (unexpected - Issue #618 reports handshake timeouts)")
                    
                except asyncio.TimeoutError:
                    results.add_result(test_name, 'PARTIAL_SUCCESS', duration_ms, {
                        'scenario': scenario['name'], 
                        'connection_established': True,
                        'message_sent': True,
                        'response_received': False
                    }, "Connection works but no response (partial reproduction)")
                    
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            results.add_result(test_name, 'REPRODUCED', duration_ms, {
                'scenario': scenario['name'],
                'error_type': 'handshake_timeout'
            }, "Successfully reproduced WebSocket handshake timeout from Issue #618")
            
        except websockets.exceptions.InvalidStatusCode as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if "503" in str(e):
                results.add_result(test_name, 'REPRODUCED', duration_ms, {
                    'scenario': scenario['name'],
                    'error_type': 'service_unavailable',
                    'status_code': 503
                }, "Successfully reproduced 503 Service Unavailable for WebSocket from Issue #618")
            else:
                results.add_result(test_name, 'OTHER_ERROR', duration_ms, {
                    'scenario': scenario['name'],
                    'error_type': 'invalid_status',
                    'error_details': str(e)
                }, f"WebSocket connection failed with status: {e}")
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            results.add_result(test_name, 'ERROR', duration_ms, {
                'scenario': scenario['name'],
                'error_type': type(e).__name__,
                'error_details': str(e)
            }, f"WebSocket connection error: {e}")
    
    return results

async def test_golden_path_failures():
    """Test: Golden Path user journey failures (Issue #618 Expected Failure)"""
    print("\n=== TESTING GOLDEN PATH FAILURES (REPRODUCING ISSUE #618) ===")
    results = Issue618TestResults()
    
    # Simulate the complete Golden Path flow
    golden_path_steps = [
        {
            'name': 'frontend_load',
            'method': 'GET',
            'url': f"{STAGING_URLS['frontend']}/",
            'description': 'User loads frontend application'
        },
        {
            'name': 'auth_check',
            'method': 'GET', 
            'url': f"{STAGING_URLS['auth']}/health",
            'description': 'Frontend checks auth service availability'
        },
        {
            'name': 'backend_api_check',
            'method': 'GET',
            'url': f"{STAGING_URLS['backend']}/api/health",
            'description': 'Frontend checks backend API availability'
        },
        {
            'name': 'websocket_connection_attempt',
            'method': 'WEBSOCKET',
            'url': STAGING_URLS['websocket'],
            'description': 'Frontend attempts to establish WebSocket connection'
        },
        {
            'name': 'chat_initialization',
            'method': 'POST',
            'url': f"{STAGING_URLS['backend']}/api/v1/chat/init",
            'description': 'User initiates chat session'
        }
    ]
    
    async with httpx.AsyncClient(timeout=30) as client:
        for step in golden_path_steps:
            test_name = f"golden_path_{step['name']}"
            start_time = time.time()
            
            if step['method'] == 'WEBSOCKET':
                # Handle WebSocket step
                try:
                    async with websockets.connect(
                        step['url'],
                        close_timeout=10,
                        open_timeout=10
                    ) as websocket:
                        duration_ms = int((time.time() - start_time) * 1000)
                        results.add_result(test_name, 'UNEXPECTED_SUCCESS', duration_ms, {
                            'step': step['name'],
                            'description': step['description'],
                            'connection_established': True
                        }, "WebSocket step working (unexpected for Issue #618)")
                        
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    results.add_result(test_name, 'REPRODUCED', duration_ms, {
                        'step': step['name'],
                        'description': step['description'],
                        'error_type': type(e).__name__,
                        'error_details': str(e)
                    }, f"Successfully reproduced Golden Path WebSocket failure: {e}")
            else:
                # Handle HTTP steps
                try:
                    if step['method'] == 'GET':
                        response = await client.get(step['url'])
                    elif step['method'] == 'POST':
                        response = await client.post(step['url'], json={})
                    else:
                        raise ValueError(f"Unsupported method: {step['method']}")
                        
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status_code in [200, 201]:
                        results.add_result(test_name, 'UNEXPECTED_SUCCESS', duration_ms, {
                            'step': step['name'],
                            'description': step['description'],
                            'status_code': response.status_code,
                            'response_time_ms': duration_ms
                        }, f"Golden Path step working (unexpected for Issue #618)")
                    elif response.status_code == 503:
                        results.add_result(test_name, 'REPRODUCED', duration_ms, {
                            'step': step['name'],
                            'description': step['description'],
                            'status_code': response.status_code
                        }, "Successfully reproduced 503 Service Unavailable in Golden Path")
                    else:
                        results.add_result(test_name, 'OTHER_ERROR', duration_ms, {
                            'step': step['name'],
                            'description': step['description'],
                            'status_code': response.status_code
                        }, f"Golden Path step failed with status: {response.status_code}")
                        
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    results.add_result(test_name, 'REPRODUCED', duration_ms, {
                        'step': step['name'],
                        'description': step['description'],
                        'error_type': type(e).__name__,
                        'error_details': str(e)
                    }, f"Successfully reproduced Golden Path failure: {e}")
    
    return results

async def test_service_dependency_failures():
    """Test: Service dependency interaction failures (Issue #618 Expected Failure)"""
    print("\n=== TESTING SERVICE DEPENDENCY FAILURES (REPRODUCING ISSUE #618) ===")
    results = Issue618TestResults()
    
    # Test inter-service communication that should fail according to Issue #618
    dependency_tests = [
        {
            'name': 'frontend_to_backend',
            'description': 'Frontend trying to reach backend API',
            'source': 'frontend',
            'target': 'backend',
            'url': f"{STAGING_URLS['backend']}/api/health",
            'headers': {'Origin': STAGING_URLS['frontend']}
        },
        {
            'name': 'frontend_to_auth', 
            'description': 'Frontend trying to reach auth service',
            'source': 'frontend',
            'target': 'auth',
            'url': f"{STAGING_URLS['auth']}/health",
            'headers': {'Origin': STAGING_URLS['frontend']}
        },
        {
            'name': 'backend_to_auth',
            'description': 'Backend trying to validate auth token',
            'source': 'backend', 
            'target': 'auth',
            'url': f"{STAGING_URLS['auth']}/api/validate",
            'headers': {'Authorization': 'Bearer test-token'}
        },
        {
            'name': 'websocket_backend_routing',
            'description': 'WebSocket routing to backend services',
            'source': 'websocket',
            'target': 'backend',
            'url': STAGING_URLS['websocket'],
            'headers': {}
        }
    ]
    
    async with httpx.AsyncClient(timeout=30) as client:
        for test in dependency_tests:
            test_name = f"dependency_{test['name']}"
            start_time = time.time()
            
            if test['name'] == 'websocket_backend_routing':
                # Handle WebSocket dependency test
                try:
                    async with websockets.connect(
                        test['url'],
                        extra_headers=test['headers'],
                        close_timeout=10,
                        open_timeout=10
                    ) as websocket:
                        # Try to send a message that requires backend processing
                        test_message = {
                            'type': 'agent_request',
                            'data': {'message': 'test dependency routing'},
                            'request_id': str(uuid.uuid4())
                        }
                        await websocket.send(json.dumps(test_message))
                        
                        # Wait for backend response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            duration_ms = int((time.time() - start_time) * 1000)
                            
                            results.add_result(test_name, 'UNEXPECTED_SUCCESS', duration_ms, {
                                'test': test['name'],
                                'description': test['description'],
                                'message_sent': True,
                                'response_received': True,
                                'response_data': response[:200] if response else None
                            }, "WebSocket backend routing working (unexpected for Issue #618)")
                            
                        except asyncio.TimeoutError:
                            duration_ms = int((time.time() - start_time) * 1000)
                            results.add_result(test_name, 'REPRODUCED', duration_ms, {
                                'test': test['name'],
                                'description': test['description'],
                                'message_sent': True,
                                'response_received': False
                            }, "Successfully reproduced WebSocket backend routing timeout")
                            
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    results.add_result(test_name, 'REPRODUCED', duration_ms, {
                        'test': test['name'],
                        'description': test['description'],
                        'error_type': type(e).__name__,
                        'error_details': str(e)
                    }, f"Successfully reproduced WebSocket dependency failure: {e}")
            else:
                # Handle HTTP dependency tests
                try:
                    response = await client.get(test['url'], headers=test['headers'])
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status_code in [200, 201]:
                        results.add_result(test_name, 'UNEXPECTED_SUCCESS', duration_ms, {
                            'test': test['name'],
                            'description': test['description'],
                            'source': test['source'],
                            'target': test['target'],
                            'status_code': response.status_code
                        }, f"Service dependency working (unexpected for Issue #618)")
                    elif response.status_code == 503:
                        results.add_result(test_name, 'REPRODUCED', duration_ms, {
                            'test': test['name'],
                            'description': test['description'],
                            'source': test['source'],
                            'target': test['target'],
                            'status_code': response.status_code
                        }, "Successfully reproduced 503 Service Unavailable in dependency")
                    else:
                        results.add_result(test_name, 'OTHER_ERROR', duration_ms, {
                            'test': test['name'],
                            'description': test['description'],
                            'source': test['source'],
                            'target': test['target'],
                            'status_code': response.status_code
                        }, f"Dependency failed with status: {response.status_code}")
                        
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    results.add_result(test_name, 'REPRODUCED', duration_ms, {
                        'test': test['name'],
                        'description': test['description'],
                        'source': test['source'],
                        'target': test['target'],
                        'error_type': type(e).__name__,
                        'error_details': str(e)
                    }, f"Successfully reproduced dependency failure: {e}")
    
    return results

def analyze_results(all_results: List[Issue618TestResults]) -> Dict[str, Any]:
    """Analyze all test results and determine Issue #618 reproduction status."""
    total_tests = sum(len(results.results) for results in all_results)
    total_failures = sum(len(results.critical_failures) for results in all_results)
    
    # Count different types of results
    reproduced_count = 0
    unexpected_success_count = 0
    error_count = 0
    
    all_test_results = []
    for results in all_results:
        all_test_results.extend(results.results)
    
    for result in all_test_results:
        if result['status'] == 'REPRODUCED':
            reproduced_count += 1
        elif result['status'] in ['UNEXPECTED_SUCCESS', 'PARTIAL_SUCCESS']:
            unexpected_success_count += 1
        elif result['status'] in ['ERROR', 'TIMEOUT', 'OTHER_ERROR']:
            error_count += 1
    
    # Determine overall reproduction status
    if reproduced_count > 0:
        reproduction_status = "PARTIAL_REPRODUCTION"
        if reproduced_count >= total_tests * 0.5:  # 50% or more reproduced
            reproduction_status = "SUBSTANTIAL_REPRODUCTION"
    else:
        reproduction_status = "NO_REPRODUCTION"
    
    # Determine if staging environment is actually working (contradicting Issue #618)
    staging_working = unexpected_success_count > reproduced_count
    
    analysis = {
        'summary': {
            'total_tests': total_tests,
            'reproduced_failures': reproduced_count,
            'unexpected_successes': unexpected_success_count,
            'errors': error_count,
            'reproduction_status': reproduction_status,
            'staging_environment_working': staging_working
        },
        'issue_618_assessment': {
            'backend_503_reproduced': any(
                r['status'] == 'REPRODUCED' and 'backend_503' in r['test_name']
                for r in all_test_results
            ),
            'websocket_timeout_reproduced': any(
                r['status'] == 'REPRODUCED' and 'websocket_handshake' in r['test_name']
                for r in all_test_results
            ),
            'golden_path_failures_reproduced': any(
                r['status'] == 'REPRODUCED' and 'golden_path' in r['test_name']
                for r in all_test_results
            ),
            'dependency_failures_reproduced': any(
                r['status'] == 'REPRODUCED' and 'dependency' in r['test_name']
                for r in all_test_results
            )
        },
        'detailed_results': all_test_results,
        'critical_failures': [r for r in all_test_results if r['status'] in ['REPRODUCED', 'ERROR', 'TIMEOUT']],
        'unexpected_successes': [r for r in all_test_results if r['status'] in ['UNEXPECTED_SUCCESS', 'PARTIAL_SUCCESS']]
    }
    
    return analysis

async def main():
    """Run Issue #618 reproduction test suite."""
    print("=" * 100)
    print(" ISSUE #618 REPRODUCTION TEST SUITE")
    print(" Backend Deployment + WebSocket Routing Issues")
    print(" Expected: 503 Service Unavailable & WebSocket Handshake Timeouts")
    print(f" Environment: Staging")
    print(f" Timestamp: {datetime.now().isoformat()}")
    print("=" * 100)
    
    overall_start = time.time()
    all_results = []
    
    try:
        # Run all test categories
        print("\n🔍 Running comprehensive Issue #618 reproduction tests...")
        
        backend_results = await test_backend_503_errors()
        all_results.append(backend_results)
        
        websocket_results = await test_websocket_handshake_timeouts()
        all_results.append(websocket_results)
        
        golden_path_results = await test_golden_path_failures()
        all_results.append(golden_path_results)
        
        dependency_results = await test_service_dependency_failures()
        all_results.append(dependency_results)
        
        # Analyze results
        analysis = analyze_results(all_results)
        total_time = time.time() - overall_start
        
        # Generate comprehensive report
        print("\n" + "=" * 100)
        print(" ISSUE #618 REPRODUCTION TEST RESULTS")
        print("=" * 100)
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total Tests Executed: {analysis['summary']['total_tests']}")
        print(f"  Issue #618 Failures Reproduced: {analysis['summary']['reproduced_failures']}")
        print(f"  Unexpected Successes: {analysis['summary']['unexpected_successes']}")
        print(f"  Technical Errors: {analysis['summary']['errors']}")
        print(f"  Reproduction Status: {analysis['summary']['reproduction_status']}")
        print(f"  Staging Environment Working: {analysis['summary']['staging_environment_working']}")
        print(f"  Total Execution Time: {total_time:.3f}s")
        
        print(f"\n🎯 ISSUE #618 SPECIFIC ASSESSMENTS:")
        for key, value in analysis['issue_618_assessment'].items():
            status = "✅ REPRODUCED" if value else "❌ NOT REPRODUCED"
            print(f"  {key.replace('_', ' ').title()}: {status}")
        
        if analysis['critical_failures']:
            print(f"\n🚨 CRITICAL FAILURES REPRODUCED ({len(analysis['critical_failures'])}):")
            for failure in analysis['critical_failures'][:10]:  # Show first 10
                print(f"  • {failure['test_name']}: {failure['error']}")
        
        if analysis['unexpected_successes']:
            print(f"\n⚠️  UNEXPECTED SUCCESSES ({len(analysis['unexpected_successes'])}):")
            for success in analysis['unexpected_successes'][:10]:  # Show first 10
                print(f"  • {success['test_name']}: {success['error']}")
        
        # Save detailed report
        report_filename = f"issue_618_reproduction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_filename}")
        
        # Determine exit code and recommendation
        if analysis['summary']['reproduction_status'] in ['SUBSTANTIAL_REPRODUCTION', 'PARTIAL_REPRODUCTION']:
            print(f"\n✅ ISSUE #618 REPRODUCTION: {analysis['summary']['reproduction_status']}")
            print("   RECOMMENDATION: Proceed with remediation based on reproduced failures")
            exit_code = 0  # Success - we reproduced the issue
        elif analysis['summary']['staging_environment_working']:
            print(f"\n⚠️  ISSUE #618 NOT REPRODUCED - STAGING ENVIRONMENT APPEARS FUNCTIONAL")
            print("   RECOMMENDATION: Re-evaluate Issue #618 - staging may already be fixed")
            exit_code = 1  # Warning - issue not reproduced
        else:
            print(f"\n❌ UNABLE TO ASSESS ISSUE #618 - TECHNICAL ERRORS ENCOUNTERED")
            print("   RECOMMENDATION: Fix test infrastructure before proceeding")
            exit_code = 2  # Error - can't assess
        
        return exit_code
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR IN ISSUE #618 REPRODUCTION TESTS: {e}")
        print(traceback.format_exc())
        return 3

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)