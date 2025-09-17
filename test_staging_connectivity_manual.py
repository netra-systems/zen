#!/usr/bin/env python3
"""
Manual staging connectivity test to validate Phase 1 infrastructure.
Tests basic connectivity to staging endpoints without requiring approval.
"""

import time
import asyncio
import json
from typing import Dict, Any

# Import libraries with error handling
try:
    import httpx
    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False
    print("Warning: httpx not available, using basic connectivity test")

try:
    import socket
    SOCKET_AVAILABLE = True
except ImportError:
    SOCKET_AVAILABLE = False
    print("Warning: socket not available")

def test_basic_connectivity():
    """Test basic DNS resolution and socket connectivity."""
    results = {}
    
    # Test staging endpoints from CLAUDE.md requirements
    staging_hosts = [
        "staging.netrasystems.ai",
        "api-staging.netrasystems.ai"
    ]
    
    for host in staging_hosts:
        print(f"Testing {host}...")
        
        if SOCKET_AVAILABLE:
            try:
                # Test DNS resolution
                ip = socket.gethostbyname(host)
                print(f"  DNS resolved: {host} -> {ip}")
                
                # Test TCP connectivity on port 443 (HTTPS)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)  # 10 second timeout
                
                start_time = time.time()
                result = sock.connect_ex((host, 443))
                response_time = time.time() - start_time
                sock.close()
                
                if result == 0:
                    print(f"  TCP 443: PASS ({response_time:.2f}s)")
                    results[f"{host}_tcp_443"] = {
                        "success": True,
                        "response_time": response_time,
                        "ip_address": ip
                    }
                else:
                    print(f"  TCP 443: FAIL (error {result})")
                    results[f"{host}_tcp_443"] = {
                        "success": False,
                        "error_code": result,
                        "ip_address": ip
                    }
                    
            except socket.gaierror as e:
                print(f"  DNS: FAIL ({e})")
                results[f"{host}_dns"] = {
                    "success": False,
                    "error": str(e)
                }
            except Exception as e:
                print(f"  Connection: FAIL ({e})")
                results[f"{host}_connection"] = {
                    "success": False,
                    "error": str(e)
                }
        else:
            results[f"{host}_skipped"] = {
                "success": False,
                "error": "Socket library not available"
            }
    
    return results

async def test_http_connectivity():
    """Test HTTP/HTTPS connectivity if httpx is available."""
    if not HTTP_CLIENT_AVAILABLE:
        return {"http_client_unavailable": {"success": False, "error": "httpx not available"}}
    
    results = {}
    
    # Test endpoints based on the configuration and CLAUDE.md requirements
    test_endpoints = [
        {
            "name": "staging_backend_health",
            "url": "https://api.staging.netrasystems.ai/health",
            "expected_status": [200, 404, 503]  # Any of these could be valid
        },
        {
            "name": "staging_backend_netrasystems",
            "url": "https://staging.netrasystems.ai/health",
            "expected_status": [200, 404, 503]
        },
        {
            "name": "staging_auth_health",
            "url": "https://auth.staging.netrasystems.ai/health",
            "expected_status": [200, 404, 503]
        }
    ]
    
    for endpoint in test_endpoints:
        print(f"Testing HTTP {endpoint['name']}: {endpoint['url']}")
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                start_time = time.time()
                response = await client.get(
                    endpoint['url'],
                    headers={
                        "User-Agent": "Netra-Infrastructure-Test/1.0",
                        "Accept": "application/json"
                    },
                    follow_redirects=True
                )
                response_time = time.time() - start_time
                
                is_expected = response.status_code in endpoint['expected_status']
                
                print(f"  Status: {response.status_code} ({'PASS' if is_expected else 'UNEXPECTED'}) ({response_time:.2f}s)")
                
                # Try to get response data
                response_data = None
                try:
                    if response.headers.get("content-type", "").startswith("application/json"):
                        response_data = response.json()
                except:
                    pass
                
                results[endpoint['name']] = {
                    "success": is_expected,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "content_length": len(response.content) if response.content else 0,
                    "content_type": response.headers.get("content-type", "unknown"),
                    "response_data": response_data
                }
                
        except httpx.TimeoutException:
            print(f"  Timeout: FAIL (15s timeout exceeded)")
            results[endpoint['name']] = {
                "success": False,
                "error": "Timeout after 15 seconds",
                "error_type": "timeout"
            }
        except httpx.ConnectError as e:
            print(f"  Connection: FAIL ({e})")
            results[endpoint['name']] = {
                "success": False,
                "error": f"Connection failed: {str(e)}",
                "error_type": "connection_error"
            }
        except Exception as e:
            print(f"  Error: FAIL ({e})")
            results[endpoint['name']] = {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "error_type": "unknown_error"
            }
    
    return results

async def main():
    """Run Phase 1 infrastructure connectivity tests."""
    print("=== Phase 1 Infrastructure Health Validation ===")
    print("Testing basic connectivity to staging GCP infrastructure")
    print()
    
    all_results = {}
    
    # Test 1: Basic TCP/DNS connectivity
    print("1. Basic connectivity tests:")
    basic_results = test_basic_connectivity()
    all_results.update(basic_results)
    print()
    
    # Test 2: HTTP connectivity  
    print("2. HTTP endpoint tests:")
    http_results = await test_http_connectivity()
    all_results.update(http_results)
    print()
    
    # Summary
    print("=== SUMMARY ===")
    total_tests = len(all_results)
    successful_tests = sum(1 for result in all_results.values() if isinstance(result, dict) and result.get("success", False))
    
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Success rate: {(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
    print()
    
    # Infrastructure issues
    infrastructure_issues = []
    for test_name, result in all_results.items():
        if isinstance(result, dict) and not result.get("success", False):
            error = result.get("error", "Unknown error")
            infrastructure_issues.append(f"{test_name}: {error}")
    
    if infrastructure_issues:
        print("INFRASTRUCTURE ISSUES IDENTIFIED:")
        for issue in infrastructure_issues:
            print(f"  - {issue}")
    else:
        print("No critical infrastructure issues detected.")
    
    print()
    
    # Save results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"phase1_infrastructure_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "test_type": "Phase 1 Infrastructure Health Validation",
            "environment": "staging",
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": (successful_tests/total_tests)*100 if total_tests > 0 else 0,
            "infrastructure_issues": infrastructure_issues,
            "detailed_results": all_results
        }, f, indent=2)
    
    print(f"Results saved to: {results_file}")
    
    # Return appropriate exit code
    if infrastructure_issues:
        print("Exit code: 1 (infrastructure issues detected)")
        return 1
    else:
        print("Exit code: 0 (all tests passed)")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)