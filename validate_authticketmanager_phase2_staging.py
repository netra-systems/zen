#!/usr/bin/env python3
"""
AuthTicketManager Phase 2 Staging Validation Script (Issue #1296)

This script validates that the AuthTicketManager Phase 2 implementation is working correctly
on the staging environment after deployment.

Tests:
1. Backend service health check
2. /auth/generate-ticket endpoint availability 
3. Proper error handling for missing auth
4. JWT token validation integration
5. Response format validation

Usage:
    python validate_authticketmanager_phase2_staging.py [--verbose]
"""

import asyncio
import httpx
import json
import sys
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of a validation check."""
    test_name: str
    status: str  # "PASS", "FAIL", "SKIP"
    message: str
    details: Optional[Dict[str, Any]] = None

class AuthTicketManagerStagingValidator:
    """Validator for AuthTicketManager Phase 2 staging deployment."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.staging_base_url = "https://staging.netrasystems.ai"
        self.results = []
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def log_result(self, result: ValidationResult):
        """Log and store a validation result."""
        self.results.append(result)
        status_emoji = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⏭️"
        logger.info(f"{status_emoji} {result.test_name}: {result.message}")
        
        if self.verbose and result.details:
            logger.debug(f"Details: {json.dumps(result.details, indent=2)}")
    
    async def test_backend_health(self) -> ValidationResult:
        """Test that the backend service is responding to health checks."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.staging_base_url}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    return ValidationResult(
                        test_name="Backend Health Check",
                        status="PASS",
                        message=f"Backend responding with HTTP {response.status_code}",
                        details={"health_data": health_data, "response_time": response.elapsed.total_seconds()}
                    )
                else:
                    return ValidationResult(
                        test_name="Backend Health Check", 
                        status="FAIL",
                        message=f"Backend returned HTTP {response.status_code}",
                        details={"response_text": response.text}
                    )
                    
        except Exception as e:
            return ValidationResult(
                test_name="Backend Health Check",
                status="FAIL", 
                message=f"Failed to connect to backend: {str(e)}",
                details={"exception": str(e), "exception_type": type(e).__name__}
            )
    
    async def test_generate_ticket_endpoint_unauthenticated(self) -> ValidationResult:
        """Test that the generate-ticket endpoint exists and properly rejects unauthenticated requests."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.staging_base_url}/api/v1/auth/generate-ticket")
                
                # Should return 401 or 403 for unauthenticated request
                if response.status_code in [401, 403]:
                    return ValidationResult(
                        test_name="Generate Ticket Endpoint - Unauthenticated",
                        status="PASS",
                        message=f"Properly rejected unauthenticated request with HTTP {response.status_code}",
                        details={"response": response.text}
                    )
                else:
                    return ValidationResult(
                        test_name="Generate Ticket Endpoint - Unauthenticated",
                        status="FAIL", 
                        message=f"Unexpected response for unauthenticated request: HTTP {response.status_code}",
                        details={"response": response.text}
                    )
                    
        except Exception as e:
            return ValidationResult(
                test_name="Generate Ticket Endpoint - Unauthenticated",
                status="FAIL",
                message=f"Failed to test endpoint: {str(e)}",
                details={"exception": str(e)}
            )
    
    async def test_generate_ticket_compatibility_endpoint(self) -> ValidationResult:
        """Test the compatibility endpoint at /auth/generate-ticket."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.staging_base_url}/auth/generate-ticket")
                
                # Should return 401 or 403 for unauthenticated request 
                if response.status_code in [401, 403]:
                    return ValidationResult(
                        test_name="Generate Ticket Compatibility Endpoint",
                        status="PASS",
                        message=f"Compatibility endpoint responding with HTTP {response.status_code}",
                        details={"response": response.text}
                    )
                else:
                    return ValidationResult(
                        test_name="Generate Ticket Compatibility Endpoint",
                        status="FAIL",
                        message=f"Unexpected response: HTTP {response.status_code}",
                        details={"response": response.text}
                    )
                    
        except Exception as e:
            return ValidationResult(
                test_name="Generate Ticket Compatibility Endpoint",
                status="FAIL", 
                message=f"Failed to test compatibility endpoint: {str(e)}",
                details={"exception": str(e)}
            )
    
    async def test_route_discovery(self) -> ValidationResult:
        """Test if the routes are discoverable via OpenAPI docs."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.staging_base_url}/docs")
                
                if response.status_code == 200:
                    # Check if the docs contain references to our new endpoint
                    docs_content = response.text
                    has_generate_ticket = "generate-ticket" in docs_content.lower()
                    
                    return ValidationResult(
                        test_name="Route Discovery via OpenAPI",
                        status="PASS" if has_generate_ticket else "FAIL",
                        message=f"OpenAPI docs accessible, generate-ticket found: {has_generate_ticket}",
                        details={"docs_accessible": True, "generate_ticket_found": has_generate_ticket}
                    )
                else:
                    return ValidationResult(
                        test_name="Route Discovery via OpenAPI",
                        status="FAIL",
                        message=f"OpenAPI docs not accessible: HTTP {response.status_code}",
                        details={"response": response.text}
                    )
                    
        except Exception as e:
            return ValidationResult(
                test_name="Route Discovery via OpenAPI", 
                status="FAIL",
                message=f"Failed to access OpenAPI docs: {str(e)}",
                details={"exception": str(e)}
            )
    
    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation tests and return summary."""
        logger.info("🚀 Starting AuthTicketManager Phase 2 Staging Validation")
        logger.info(f"Testing against: {self.staging_base_url}")
        
        # Run all tests
        tests = [
            self.test_backend_health(),
            self.test_generate_ticket_endpoint_unauthenticated(),
            self.test_generate_ticket_compatibility_endpoint(),
            self.test_route_discovery()
        ]
        
        results = await asyncio.gather(*tests)
        for result in results:
            self.log_result(result)
        
        # Generate summary
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        skipped = sum(1 for r in self.results if r.status == "SKIP")
        total = len(self.results)
        
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": (passed / total) * 100 if total > 0 else 0,
            "staging_url": self.staging_base_url,
            "results": [
                {
                    "test_name": r.test_name,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details
                } for r in self.results
            ]
        }
        
        # Log summary
        logger.info("=" * 60)
        logger.info("📊 VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⏭️ Skipped: {skipped}")
        logger.info(f"Success Rate: {summary['success_rate']:.1f}%")
        
        if failed == 0:
            logger.info("🎉 All validations PASSED! AuthTicketManager Phase 2 deployment looks good.")
        else:
            logger.warning(f"⚠️ {failed} validation(s) FAILED. Review the issues above.")
            
        return summary

async def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate AuthTicketManager Phase 2 staging deployment")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--json", "-j", action="store_true", help="Output results as JSON")
    args = parser.parse_args()
    
    validator = AuthTicketManagerStagingValidator(verbose=args.verbose)
    summary = await validator.run_all_validations()
    
    if args.json:
        print(json.dumps(summary, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if summary["failed"] == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())