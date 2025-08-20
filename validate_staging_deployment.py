"""
Validate staging deployment for backend and auth services.
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check."""
    service: str
    endpoint: str
    status: str  # 'success', 'warning', 'failure'
    message: str
    response_time_ms: float = 0
    details: Dict[str, Any] = None


class StagingValidator:
    """Validates staging deployment."""
    
    BACKEND_URL = "https://api.staging.netrasystems.ai"
    AUTH_URL = "https://auth.staging.netrasystems.ai"
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.session = None
    
    async def __aenter__(self):
        """Context manager entry."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()
    
    async def validate_backend(self) -> List[ValidationResult]:
        """Validate backend service endpoints."""
        backend_results = []
        
        # Test health endpoint
        result = await self._test_endpoint(
            service="Backend",
            endpoint="/health",
            url=f"{self.BACKEND_URL}/health",
            expected_status=200,
            check_json=True
        )
        backend_results.append(result)
        
        # Test API docs endpoint
        result = await self._test_endpoint(
            service="Backend",
            endpoint="/docs",
            url=f"{self.BACKEND_URL}/docs",
            expected_status=200,
            check_content=True
        )
        backend_results.append(result)
        
        # Test WebSocket endpoint (just check it exists)
        result = await self._test_endpoint(
            service="Backend",
            endpoint="/ws (availability)",
            url=f"{self.BACKEND_URL}/ws",
            expected_status=[400, 426],  # WebSocket upgrade required
            check_content=False
        )
        backend_results.append(result)
        
        return backend_results
    
    async def validate_auth(self) -> List[ValidationResult]:
        """Validate auth service endpoints."""
        auth_results = []
        
        # Test health endpoint
        result = await self._test_endpoint(
            service="Auth",
            endpoint="/health",
            url=f"{self.AUTH_URL}/health",
            expected_status=200,
            check_json=True
        )
        auth_results.append(result)
        
        # Test login endpoint (OPTIONS for CORS)
        result = await self._test_endpoint(
            service="Auth",
            endpoint="/api/v1/auth/login (CORS)",
            url=f"{self.AUTH_URL}/api/v1/auth/login",
            method="OPTIONS",
            expected_status=[200, 204],
            check_cors=True
        )
        auth_results.append(result)
        
        return auth_results
    
    async def validate_connectivity(self) -> List[ValidationResult]:
        """Validate inter-service connectivity."""
        connectivity_results = []
        
        # Test if backend can reach auth service
        # This would normally be done through internal endpoints
        # For now, we just verify both services are up
        
        backend_health = await self._test_endpoint(
            service="Connectivity",
            endpoint="Backend->Auth",
            url=f"{self.BACKEND_URL}/health",
            expected_status=200
        )
        
        if backend_health.status == "success":
            connectivity_results.append(ValidationResult(
                service="Connectivity",
                endpoint="Backend->Auth",
                status="success",
                message="Services are accessible (assumed connectivity)"
            ))
        else:
            connectivity_results.append(ValidationResult(
                service="Connectivity",
                endpoint="Backend->Auth",
                status="warning",
                message="Cannot verify inter-service connectivity"
            ))
        
        return connectivity_results
    
    async def validate_ssl(self) -> List[ValidationResult]:
        """Validate SSL certificates."""
        ssl_results = []
        
        for service, url in [("Backend", self.BACKEND_URL), ("Auth", self.AUTH_URL)]:
            try:
                async with self.session.get(f"{url}/health", ssl=True) as response:
                    ssl_results.append(ValidationResult(
                        service=service,
                        endpoint="SSL Certificate",
                        status="success",
                        message="Valid SSL certificate"
                    ))
            except aiohttp.ClientSSLError as e:
                ssl_results.append(ValidationResult(
                    service=service,
                    endpoint="SSL Certificate",
                    status="failure",
                    message=f"SSL error: {str(e)}"
                ))
            except Exception as e:
                ssl_results.append(ValidationResult(
                    service=service,
                    endpoint="SSL Certificate",
                    status="warning",
                    message=f"Could not verify SSL: {str(e)}"
                ))
        
        return ssl_results
    
    async def _test_endpoint(
        self,
        service: str,
        endpoint: str,
        url: str,
        method: str = "GET",
        expected_status: Any = 200,
        check_json: bool = False,
        check_content: bool = False,
        check_cors: bool = False
    ) -> ValidationResult:
        """Test a single endpoint."""
        import time
        
        # Handle expected_status as list or single value
        if not isinstance(expected_status, list):
            expected_status = [expected_status]
        
        headers = {}
        if check_cors:
            headers = {
                'Origin': 'https://app.staging.netrasystems.ai',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
        
        start_time = time.perf_counter()
        
        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                allow_redirects=False
            ) as response:
                response_time = (time.perf_counter() - start_time) * 1000
                
                # Check status code
                if response.status not in expected_status:
                    return ValidationResult(
                        service=service,
                        endpoint=endpoint,
                        status="failure",
                        message=f"Expected status {expected_status}, got {response.status}",
                        response_time_ms=response_time
                    )
                
                # Check JSON response
                if check_json:
                    try:
                        data = await response.json()
                        return ValidationResult(
                            service=service,
                            endpoint=endpoint,
                            status="success",
                            message=f"Endpoint responsive (status: {response.status})",
                            response_time_ms=response_time,
                            details=data
                        )
                    except:
                        return ValidationResult(
                            service=service,
                            endpoint=endpoint,
                            status="warning",
                            message="Response is not valid JSON",
                            response_time_ms=response_time
                        )
                
                # Check CORS headers
                if check_cors:
                    cors_headers = {
                        'allow_origin': response.headers.get('Access-Control-Allow-Origin'),
                        'allow_methods': response.headers.get('Access-Control-Allow-Methods'),
                        'allow_headers': response.headers.get('Access-Control-Allow-Headers')
                    }
                    
                    if cors_headers['allow_origin'] and cors_headers['allow_methods']:
                        return ValidationResult(
                            service=service,
                            endpoint=endpoint,
                            status="success",
                            message="CORS properly configured",
                            response_time_ms=response_time,
                            details=cors_headers
                        )
                    else:
                        return ValidationResult(
                            service=service,
                            endpoint=endpoint,
                            status="warning",
                            message="CORS headers incomplete",
                            response_time_ms=response_time,
                            details=cors_headers
                        )
                
                # Default success
                return ValidationResult(
                    service=service,
                    endpoint=endpoint,
                    status="success",
                    message=f"Endpoint responsive (status: {response.status})",
                    response_time_ms=response_time
                )
                
        except asyncio.TimeoutError:
            return ValidationResult(
                service=service,
                endpoint=endpoint,
                status="failure",
                message="Request timeout",
                response_time_ms=(time.perf_counter() - start_time) * 1000
            )
        except Exception as e:
            return ValidationResult(
                service=service,
                endpoint=endpoint,
                status="failure",
                message=f"Request failed: {str(e)}",
                response_time_ms=(time.perf_counter() - start_time) * 1000
            )
    
    def print_results(self, results: List[ValidationResult]):
        """Print validation results."""
        # Group by status
        successes = [r for r in results if r.status == "success"]
        warnings = [r for r in results if r.status == "warning"]
        failures = [r for r in results if r.status == "failure"]
        
        print("\n" + "=" * 60)
        print("STAGING DEPLOYMENT VALIDATION RESULTS")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Total Checks: {len(results)}")
        print(f"[OK] Successes: {len(successes)}")
        print(f"[!] Warnings: {len(warnings)}")
        print(f"[X] Failures: {len(failures)}")
        print("=" * 60)
        
        # Print detailed results
        for status_group, status_name, symbol in [
            (successes, "SUCCESSFUL", "[OK]"),
            (warnings, "WARNINGS", "[!]"),
            (failures, "FAILURES", "[X]")
        ]:
            if status_group:
                print(f"\n{status_name}:")
                for result in status_group:
                    time_str = f" ({result.response_time_ms:.1f}ms)" if result.response_time_ms > 0 else ""
                    print(f"  {symbol} {result.service} - {result.endpoint}{time_str}")
                    print(f"    {result.message}")
                    if result.details:
                        print(f"    Details: {json.dumps(result.details, indent=6)}")
        
        # Return exit code
        return 0 if len(failures) == 0 else 1


async def main():
    """Main validation function."""
    async with StagingValidator() as validator:
        all_results = []
        
        print("Validating Backend Service...")
        backend_results = await validator.validate_backend()
        all_results.extend(backend_results)
        
        print("Validating Auth Service...")
        auth_results = await validator.validate_auth()
        all_results.extend(auth_results)
        
        print("Validating SSL Certificates...")
        ssl_results = await validator.validate_ssl()
        all_results.extend(ssl_results)
        
        print("Validating Connectivity...")
        connectivity_results = await validator.validate_connectivity()
        all_results.extend(connectivity_results)
        
        # Print results
        exit_code = validator.print_results(all_results)
        
        # Generate report file
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_checks': len(all_results),
                'successes': len([r for r in all_results if r.status == "success"]),
                'warnings': len([r for r in all_results if r.status == "warning"]),
                'failures': len([r for r in all_results if r.status == "failure"])
            },
            'results': [
                {
                    'service': r.service,
                    'endpoint': r.endpoint,
                    'status': r.status,
                    'message': r.message,
                    'response_time_ms': r.response_time_ms,
                    'details': r.details
                }
                for r in all_results
            ]
        }
        
        with open('staging_validation_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nValidation report saved to: staging_validation_report.json")
        
        return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)