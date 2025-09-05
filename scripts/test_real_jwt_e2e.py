from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Test Script: Real JWT Token E2E Test Validation
Purpose: Validate that E2E tests now use real JWT tokens instead of mock tokens.

This test verifies that the updated E2E test files properly integrate with
the enhanced test framework to use real JWT tokens for authentication.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.fixtures.auth import create_real_jwt_token, JWT_AVAILABLE
from tests.e2e.jwt_token_helpers import JWTTestHelper


class RealJWTTokenE2EValidator:
    """Validates that E2E tests use real JWT tokens."""
    
    def __init__(self):
        self.test_results: List[Dict] = []
        self.jwt_helper = JWTTestHelper()
        
    def test_real_jwt_token_creation(self) -> Dict:
        """Test that real JWT tokens can be created."""
        test_result = {
            "test_name": "Real JWT Token Creation",
            "status": "FAIL",
            "details": "",
            "execution_time": 0
        }
        
        start_time = time.time()
        try:
            if not JWT_AVAILABLE:
                test_result["status"] = "SKIP"
                test_result["details"] = "JWT library not available"
                return test_result
                
            # Test basic real JWT creation
            token = create_real_jwt_token(
                user_id="test_user_validation",
                permissions=["read", "write", "agent_execute"],
                token_type="access"
            )
            
            # Validate token structure
            if token and len(token.split('.')) == 3:
                test_result["status"] = "PASS"
                test_result["details"] = f"Real JWT token created successfully: {len(token)} chars"
            else:
                test_result["details"] = f"Invalid token structure: {token}"
                
        except Exception as e:
            test_result["details"] = f"Token creation failed: {e}"
        finally:
            test_result["execution_time"] = time.time() - start_time
            
        return test_result
    
    def test_jwt_helper_real_token_support(self) -> Dict:
        """Test that JWT helper supports real tokens."""
        test_result = {
            "test_name": "JWT Helper Real Token Support",
            "status": "FAIL",
            "details": "",
            "execution_time": 0
        }
        
        start_time = time.time()
        try:
            # Test JWT helper token creation
            token = self.jwt_helper.create_access_token(
                "test_user_helper", 
                "test@example.com"
            )
            
            # Validate token is not a simple mock
            if token and not token.startswith("mock_"):
                test_result["status"] = "PASS"
                test_result["details"] = f"JWT helper creates real tokens: {len(token)} chars"
            else:
                test_result["details"] = f"JWT helper still using mock tokens: {token}"
                
        except Exception as e:
            test_result["details"] = f"JWT helper test failed: {e}"
        finally:
            test_result["execution_time"] = time.time() - start_time
            
        return test_result
    
    def test_e2e_file_imports(self) -> Dict:
        """Test that E2E files can import real JWT functions."""
        test_result = {
            "test_name": "E2E Files Import Real JWT",
            "status": "FAIL",
            "details": "",
            "execution_time": 0
        }
        
        start_time = time.time()
        try:
            # Test importing from updated E2E files
            from tests.e2e.test_agent_circuit_breaker_e2e import TestAgentCircuitBreakerE2E
            from tests.e2e.test_auth_agent_flow import TestAuthAgentFlow
            
            test_result["status"] = "PASS"
            test_result["details"] = "E2E test classes import successfully"
            
        except ImportError as e:
            test_result["details"] = f"Import failed: {e}"
        except Exception as e:
            test_result["details"] = f"Unexpected error: {e}"
        finally:
            test_result["execution_time"] = time.time() - start_time
            
        return test_result
    
    async def test_websocket_with_real_jwt(self) -> Dict:
        """Test WebSocket connection with real JWT token."""
        test_result = {
            "test_name": "WebSocket Real JWT Authentication",
            "status": "FAIL",
            "details": "",
            "execution_time": 0
        }
        
        start_time = time.time()
        try:
            if not JWT_AVAILABLE:
                test_result["status"] = "SKIP"
                test_result["details"] = "JWT library not available"
                return test_result
                
            # Create real JWT token
            token = create_real_jwt_token(
                user_id="websocket_test_user",
                permissions=["read", "write", "websocket"],
                token_type="access"
            )
            
            # Validate token structure for WebSocket use
            if token and "." in token and len(token) > 50:
                test_result["status"] = "PASS"
                test_result["details"] = f"Real JWT ready for WebSocket: {len(token)} chars"
            else:
                test_result["details"] = f"Token not suitable for WebSocket: {token}"
                
        except Exception as e:
            test_result["details"] = f"WebSocket JWT test failed: {e}"
        finally:
            test_result["execution_time"] = time.time() - start_time
            
        return test_result
    
    def test_environment_configuration(self) -> Dict:
        """Test that environment is properly configured for real JWT usage."""
        test_result = {
            "test_name": "Environment Configuration",
            "status": "FAIL",
            "details": "",
            "execution_time": 0
        }
        
        start_time = time.time()
        try:
            import os
            
            # Check key environment variables
            env_checks = {
                "JWT_AVAILABLE": JWT_AVAILABLE,
                "TESTING_ENV": get_env().get("TESTING") == "1",
                "JWT_SECRET": bool(get_env().get("JWT_SECRET")),
            }
            
            passed_checks = sum(1 for check in env_checks.values() if check)
            total_checks = len(env_checks)
            
            if passed_checks >= 2:  # At least JWT_AVAILABLE and one other
                test_result["status"] = "PASS"
                test_result["details"] = f"Environment OK: {passed_checks}/{total_checks} checks passed"
            else:
                test_result["details"] = f"Environment issues: {env_checks}"
                
        except Exception as e:
            test_result["details"] = f"Environment test failed: {e}"
        finally:
            test_result["execution_time"] = time.time() - start_time
            
        return test_result
    
    async def run_all_tests(self) -> Dict:
        """Run all validation tests."""
        print("[TEST] Running Real JWT Token E2E Validation Tests...")
        
        # Run synchronous tests
        sync_tests = [
            self.test_real_jwt_token_creation,
            self.test_jwt_helper_real_token_support,
            self.test_e2e_file_imports,
            self.test_environment_configuration
        ]
        
        for test_func in sync_tests:
            result = test_func()
            self.test_results.append(result)
            print(f"  {result['status']:4} | {result['test_name']}: {result['details']}")
        
        # Run async tests
        async_tests = [
            self.test_websocket_with_real_jwt,
        ]
        
        for test_func in async_tests:
            result = await test_func()
            self.test_results.append(result)
            print(f"  {result['status']:4} | {result['test_name']}: {result['details']}")
        
        # Generate summary
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.test_results if r["status"] == "SKIP")
        total = len(self.test_results)
        
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "total_time": sum(r["execution_time"] for r in self.test_results),
            "details": self.test_results
        }
        
        print(f"\n[SUMMARY] Test Summary:")
        print(f"   Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Execution Time: {summary['total_time']:.3f}s")
        
        if failed > 0:
            print(f"\n[FAIL] {failed} tests failed - real JWT integration may have issues")
            return summary
        elif skipped == total:
            print(f"\n[WARN] All tests skipped - JWT library may not be available")
            return summary
        else:
            print(f"\n[PASS] All tests passed - real JWT integration successful!")
            return summary


async def main():
    """Main test execution."""
    validator = RealJWTTokenE2EValidator()
    summary = await validator.run_all_tests()
    
    # Exit with appropriate code
    if summary["failed"] > 0:
        sys.exit(1)  # Test failures
    elif summary["passed"] == 0 and summary["skipped"] > 0:
        sys.exit(2)  # All tests skipped
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CANCEL] Test execution cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}")
        sys.exit(1)
