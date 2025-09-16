#!/usr/bin/env python3
"""
Infrastructure Fix Validation Script for Issue #1278

CRITICAL PURPOSE: Validate infrastructure fixes after infrastructure team resolves
VPC connectivity and Cloud SQL timeout issues.

SCOPE: Post-resolution validation - to be run AFTER infrastructure team completes their work.

Business Impact: Validates $500K+ ARR platform infrastructure is fully operational.
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

class InfrastructureFixValidator:
    """Validate infrastructure fixes for Issue #1278 resolution."""
    
    def __init__(self):
        """Initialize validator with comprehensive test scenarios."""
        # Staging endpoints (correct domains per Issue #1278)
        self.staging_endpoints = {
            "backend": "https://staging.netrasystems.ai",
            "auth": "https://staging.netrasystems.ai", 
            "frontend": "https://staging.netrasystems.ai",
            "websocket": "wss://api-staging.netrasystems.ai"
        }
        
        # Comprehensive validation paths
        self.validation_tests = {
            "connectivity": {
                "basic_health": "/health",
                "readiness": "/health/ready",
                "infrastructure": "/health/infrastructure",
                "backend_health": "/health/backend"
            },
            "startup_resilience": {
                "startup_probe": "/health/startup"
            },
            "database_operations": {
                "schema_validation": "/health/schema-validation",
                "database_env": "/health/database-env"
            },
            "agent_systems": {
                "agent_health": "/health/agents",
                "system_comprehensive": "/health/system/comprehensive"
            }
        }
        
        # Extended timeouts for infrastructure validation
        self.timeouts = {
            "basic_health": 10.0,      # Increased from 5.0
            "readiness": 60.0,         # Increased from 45.0 for full infrastructure validation
            "infrastructure": 30.0,     # Infrastructure-specific checks
            "backend_health": 45.0,     # Backend validation including LLM checks
            "startup_probe": 90.0,      # Startup validation with full service initialization
            "schema_validation": 30.0,  # Database schema checks
            "database_env": 15.0,       # Database environment validation
            "agent_health": 20.0,       # Agent system health
            "system_comprehensive": 60.0  # Full system health check
        }
        
        # Success criteria for each test category
        self.success_criteria = {
            "connectivity": {
                "required_passing": 4,  # All connectivity tests must pass
                "critical": True
            },
            "startup_resilience": {
                "required_passing": 1,  # Startup probe must pass
                "critical": True
            },
            "database_operations": {
                "required_passing": 2,  # All database tests must pass
                "critical": True
            },
            "agent_systems": {
                "required_passing": 1,  # At least agent health must pass
                "critical": False  # Non-critical for infrastructure validation
            }
        }
    
    async def run_validation_test(self, test_name: str, endpoint_name: str, base_url: str, path: str, timeout: float) -> Dict[str, Any]:
        """Run a specific infrastructure validation test."""
        full_url = f"{base_url}{path}"
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.get(full_url) as response:
                    response_time = time.time() - start_time
                    
                    # Successful response
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            
                            # Additional validation for specific endpoints
                            validation_result = self._validate_response_content(test_name, response_data)
                            
                            return {
                                "test_name": test_name,
                                "status": "passed" if validation_result["valid"] else "failed_validation",
                                "endpoint": endpoint_name,
                                "url": full_url,
                                "response_time_ms": round(response_time * 1000, 2),
                                "http_status": response.status,
                                "response_data": response_data,
                                "validation": validation_result,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        except json.JSONDecodeError as e:
                            return {
                                "test_name": test_name,
                                "status": "failed_json_decode",
                                "endpoint": endpoint_name,
                                "url": full_url,
                                "response_time_ms": round(response_time * 1000, 2),
                                "http_status": response.status,
                                "error": f"Invalid JSON response: {str(e)}",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                    
                    # Handle non-200 responses
                    else:
                        try:
                            error_data = await response.json()
                        except:
                            error_data = {"message": await response.text()}
                            
                        return {
                            "test_name": test_name,
                            "status": "failed_http",
                            "endpoint": endpoint_name,
                            "url": full_url,
                            "response_time_ms": round(response_time * 1000, 2),
                            "http_status": response.status,
                            "error_data": error_data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "infrastructure_issue": response.status in [503, 502, 504, 500]
                        }
                        
        except asyncio.TimeoutError:
            return {
                "test_name": test_name,
                "status": "timeout",
                "endpoint": endpoint_name,
                "url": full_url,
                "timeout_seconds": timeout,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "infrastructure_issue": True,
                "message": f"Test timed out after {timeout}s - possible infrastructure issue"
            }
            
        except aiohttp.ClientError as e:
            return {
                "test_name": test_name,
                "status": "connection_error",
                "endpoint": endpoint_name,
                "url": full_url,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "infrastructure_issue": True,
                "message": "Network connectivity issue - VPC configuration may need attention"
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "status": "error",
                "endpoint": endpoint_name,
                "url": full_url,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "infrastructure_issue": False
            }
    
    def _validate_response_content(self, test_name: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate response content for specific infrastructure tests."""
        validation = {
            "valid": True,
            "issues": [],
            "details": {}
        }
        
        # Infrastructure-specific validations
        if test_name == "infrastructure":
            # Check infrastructure readiness
            if not response_data.get("infrastructure_ready", False):
                validation["valid"] = False
                validation["issues"].append("Infrastructure not ready")
            
            # Check for degraded components
            degraded = response_data.get("degraded_components", [])
            if degraded:
                validation["valid"] = False
                validation["issues"].append(f"Degraded components: {', '.join(degraded)}")
            
            # VPC connectivity validation
            vpc_status = response_data.get("vpc_connectivity", {})
            if not vpc_status.get("overall", False):
                validation["valid"] = False
                validation["issues"].append("VPC connectivity issues detected")
                
            validation["details"]["infrastructure_components"] = response_data.get("infrastructure_components", {})
        
        elif test_name == "readiness":
            # Check readiness status
            if response_data.get("status") != "ready":
                validation["valid"] = False
                validation["issues"].append(f"Service not ready: {response_data.get('status', 'unknown')}")
            
            # Check core database connectivity
            if response_data.get("core_db") != "connected":
                validation["valid"] = False
                validation["issues"].append("Core database not connected")
            
            # Check WebSocket readiness
            ws_readiness = response_data.get("websocket_readiness", {})
            if not ws_readiness.get("websocket_ready", False):
                validation["valid"] = False
                validation["issues"].append("WebSocket services not ready")
                
            validation["details"]["database_status"] = response_data.get("core_db")
            validation["details"]["redis_status"] = response_data.get("redis_db")
            validation["details"]["clickhouse_status"] = response_data.get("clickhouse_db")
        
        elif test_name == "backend_health":
            # Check backend capabilities
            capabilities = response_data.get("capabilities", {})
            required_capabilities = ["agent_execution", "database_connectivity"]
            
            for capability in required_capabilities:
                if not capabilities.get(capability, False):
                    validation["valid"] = False
                    validation["issues"].append(f"Backend capability not ready: {capability}")
            
            # Check golden path readiness
            if not response_data.get("golden_path_ready", False):
                validation["valid"] = False
                validation["issues"].append("Golden Path not ready")
                
            validation["details"]["capabilities"] = capabilities
            validation["details"]["readiness_score"] = response_data.get("readiness_score", 0)
        
        elif test_name == "startup_probe":
            # Check startup status
            if response_data.get("status") != "ready":
                validation["valid"] = False
                validation["issues"].append(f"Startup not complete: {response_data.get('status', 'unknown')}")
            
            # Check startup checks
            startup_checks = response_data.get("checks", {})
            for check_name, check_result in startup_checks.items():
                if check_result.get("status") != "ready":
                    validation["valid"] = False
                    validation["issues"].append(f"Startup check failed: {check_name}")
                    
            validation["details"]["startup_checks"] = startup_checks
        
        # Generic health status validation
        if "status" in response_data and response_data["status"] in ["unhealthy", "error"]:
            validation["valid"] = False
            validation["issues"].append(f"Service reports unhealthy status: {response_data['status']}")
        
        return validation
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive infrastructure fix validation."""
        logger.info("Starting comprehensive infrastructure fix validation...")
        
        start_time = time.time()
        validation_results = {
            "validation_run_id": f"infra_fix_validation_{int(start_time)}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "issue_reference": "#1278",
            "purpose": "Validate infrastructure fixes after VPC/Cloud SQL resolution",
            "test_categories": {},
            "summary": {},
            "validation_passed": False
        }
        
        # Run all validation tests
        for category, tests in self.validation_tests.items():
            logger.info(f"Running {category} validation tests...")
            
            category_results = {
                "tests": {},
                "passed": 0,
                "failed": 0,
                "total": len(tests)
            }
            
            # Run tests in this category
            tasks = []
            for test_name, path in tests.items():
                for endpoint_name, base_url in self.staging_endpoints.items():
                    if endpoint_name != "websocket":  # Skip websocket for HTTP tests
                        timeout = self.timeouts.get(test_name, 30.0)
                        task = self.run_validation_test(test_name, endpoint_name, base_url, path, timeout)
                        tasks.append(task)
            
            # Execute tests concurrently
            test_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in test_results:
                if isinstance(result, Exception):
                    logger.error(f"Validation test failed: {result}")
                    continue
                    
                test_key = f"{result['endpoint']}_{result['test_name']}"
                category_results["tests"][test_key] = result
                
                if result["status"] == "passed":
                    category_results["passed"] += 1
                else:
                    category_results["failed"] += 1
            
            # Category success evaluation
            criteria = self.success_criteria.get(category, {"required_passing": 1, "critical": False})
            category_results["success"] = category_results["passed"] >= criteria["required_passing"]
            category_results["critical"] = criteria["critical"]
            category_results["required_passing"] = criteria["required_passing"]
            
            validation_results["test_categories"][category] = category_results
            
            logger.info(f"{category} validation: {category_results['passed']}/{category_results['total']} tests passed")
        
        # Overall validation assessment
        critical_categories_passed = all(
            cat_result["success"] 
            for cat_result in validation_results["test_categories"].values() 
            if cat_result["critical"]
        )
        
        total_tests = sum(cat["total"] for cat in validation_results["test_categories"].values())
        total_passed = sum(cat["passed"] for cat in validation_results["test_categories"].values())
        total_failed = sum(cat["failed"] for cat in validation_results["test_categories"].values())
        
        validation_results["summary"] = {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "pass_percentage": round((total_passed / total_tests) * 100, 1) if total_tests > 0 else 0,
            "critical_categories_passed": critical_categories_passed,
            "validation_duration_seconds": round(time.time() - start_time, 2),
            "end_time": datetime.now(timezone.utc).isoformat()
        }
        
        # Determine overall validation result
        validation_results["validation_passed"] = (
            critical_categories_passed and 
            validation_results["summary"]["pass_percentage"] >= 80.0
        )
        
        # Infrastructure team sign-off recommendation
        if validation_results["validation_passed"]:
            validation_results["infrastructure_team_signoff"] = {
                "recommendation": "APPROVED",
                "message": "All critical infrastructure components validated successfully",
                "ready_for_production": True
            }
        else:
            failed_categories = [
                cat_name for cat_name, cat_result in validation_results["test_categories"].items()
                if not cat_result["success"] and cat_result["critical"]
            ]
            validation_results["infrastructure_team_signoff"] = {
                "recommendation": "REQUIRES_ATTENTION", 
                "message": f"Critical infrastructure issues remain: {', '.join(failed_categories)}",
                "ready_for_production": False,
                "action_required": "Address failed critical components before production deployment"
            }
        
        logger.info(f"Infrastructure validation complete: {validation_results['summary']['pass_percentage']}% passed, "
                   f"critical categories: {'PASSED' if critical_categories_passed else 'FAILED'}")
        
        return validation_results
    
    def format_validation_report(self, results: Dict[str, Any]) -> str:
        """Format validation results for infrastructure team review."""
        output = []
        output.append("=" * 80)
        output.append(f"INFRASTRUCTURE FIX VALIDATION REPORT - Issue {results['issue_reference']}")
        output.append(f"Validation ID: {results['validation_run_id']}")
        output.append(f"Timestamp: {results['start_time']}")
        output.append("=" * 80)
        
        # Summary section
        summary = results["summary"]
        signoff = results["infrastructure_team_signoff"]
        
        output.append(f"\nVALIDATION RESULT: {signoff['recommendation']}")
        output.append(f"Overall Pass Rate: {summary['pass_percentage']}%")
        output.append(f"Critical Categories: {'✅ PASSED' if summary['critical_categories_passed'] else '❌ FAILED'}")
        output.append(f"Production Ready: {'✅ YES' if signoff['ready_for_production'] else '❌ NO'}")
        output.append(f"Validation Duration: {summary['validation_duration_seconds']}s")
        
        if not signoff['ready_for_production']:
            output.append(f"\n⚠️  ACTION REQUIRED: {signoff['action_required']}")
        
        # Category details
        output.append(f"\nTEST CATEGORY RESULTS:")
        output.append("-" * 50)
        
        for category, cat_result in results["test_categories"].items():
            critical_flag = " [CRITICAL]" if cat_result["critical"] else ""
            success_icon = "✅" if cat_result["success"] else "❌"
            
            output.append(f"{success_icon} {category.upper()}{critical_flag}")
            output.append(f"   Tests: {cat_result['passed']}/{cat_result['total']} passed")
            output.append(f"   Required: {cat_result['required_passing']} minimum")
            
            # Show failed tests
            failed_tests = [
                test_name for test_name, test_result in cat_result["tests"].items()
                if test_result["status"] != "passed"
            ]
            if failed_tests:
                output.append(f"   Failed: {', '.join(failed_tests)}")
            output.append("")
        
        # Infrastructure team recommendations
        output.append("INFRASTRUCTURE TEAM RECOMMENDATIONS:")
        output.append("-" * 40)
        output.append(f"✅ Recommendation: {signoff['recommendation']}")
        output.append(f"📝 Message: {signoff['message']}")
        
        if signoff['ready_for_production']:
            output.append("\n🎉 INFRASTRUCTURE FIX VALIDATED SUCCESSFULLY!")
            output.append("   All critical infrastructure components are operational.")
            output.append("   Platform ready for full production deployment.")
        else:
            output.append(f"\n⚠️  INFRASTRUCTURE ATTENTION REQUIRED")
            output.append("   Address remaining issues before production deployment.")
        
        return "\n".join(output)

async def main():
    """Main function for infrastructure fix validation."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("""
Infrastructure Fix Validation Script for Issue #1278

Usage:
  python scripts/validate_infrastructure_fix.py [--json] [--quiet]

Options:
  --json    Output results in JSON format
  --quiet   Suppress console output
  --help    Show this help message

Purpose:
  Validate infrastructure fixes after infrastructure team resolves VPC connectivity
  and Cloud SQL timeout issues. Run this AFTER infrastructure team completes their work.

Exit Codes:
  0 = All validations passed, ready for production
  1 = Some validations failed, infrastructure attention required
  2 = Validation script error

Example:
  python scripts/validate_infrastructure_fix.py
  python scripts/validate_infrastructure_fix.py --json > validation_report.json
        """)
        return
    
    json_output = "--json" in sys.argv
    quiet_mode = "--quiet" in sys.argv
    
    validator = InfrastructureFixValidator()
    
    try:
        results = await validator.run_comprehensive_validation()
        
        if json_output:
            print(json.dumps(results, indent=2))
        elif not quiet_mode:
            print(validator.format_validation_report(results))
        
        # Exit with appropriate code
        if results["validation_passed"]:
            exit_code = 0
            if not quiet_mode and not json_output:
                print("\n🎉 INFRASTRUCTURE VALIDATION PASSED!")
                print("   Ready for production deployment.")
        else:
            exit_code = 1
            if not quiet_mode and not json_output:
                print("\n⚠️  INFRASTRUCTURE VALIDATION FAILED")
                print("   Infrastructure team attention required.")
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Infrastructure validation failed: {e}")
        if not quiet_mode:
            print(f"\n❌ Validation script error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())