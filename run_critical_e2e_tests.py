#!/usr/bin/env python
"""
Run Critical E2E Tests with Proper Service Management
Business Value: $510K MRR Protection through comprehensive E2E testing
"""
import sys
import os
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

class E2ETestRunner:
    """Manages execution of critical E2E tests."""
    
    def __init__(self):
        self.results = {}
        self.critical_tests = [
            ("test_real_oauth_google_flow.py", "$100K MRR - OAuth"),
            ("test_multi_tab_websocket.py", "$50K MRR - Multi-Tab"),
            ("test_concurrent_agent_load.py", "$75K MRR - Concurrent Load"),
            ("test_real_network_failure.py", "$40K MRR - Network Recovery"),
            ("test_cross_service_transaction.py", "$60K MRR - Cross-Service TX"),
            ("test_token_expiry_refresh.py", "$30K MRR - Token Refresh"),
            ("test_file_upload_pipeline.py", "$45K MRR - File Upload"),
            ("test_real_rate_limiting.py", "$25K MRR - Rate Limiting"),
            ("test_error_cascade_prevention.py", "$35K MRR - Error Prevention"),
            ("test_memory_leak_detection.py::test_memory_leak_detection_mock", "$50K MRR - Memory Leaks"),
        ]
    
    def run_test(self, test_file: str, business_value: str) -> Tuple[bool, str]:
        """Run a single E2E test."""
        print(f"\n{'='*60}")
        print(f"Running: {test_file}")
        print(f"Business Value: {business_value}")
        print(f"{'='*60}")
        
        try:
            # Build test path
            test_path = f"tests/unified/e2e/{test_file}"
            
            # Run pytest with timeout and capture output
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", 
                 "--timeout=30", "--no-header"],
                capture_output=True,
                text=True,
                timeout=35,
                cwd=project_root
            )
            
            # Check if test passed
            success = result.returncode == 0
            
            if success:
                print(f"[PASSED]: {test_file}")
                output = "Test passed successfully"
            else:
                print(f"[FAILED]: {test_file}")
                output = result.stdout + result.stderr
                
            return success, output
            
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT]: {test_file} - Test took too long")
            return False, "Test timed out after 35 seconds"
        except Exception as e:
            print(f"[ERROR]: {test_file} - {str(e)}")
            return False, str(e)
    
    def run_all_tests(self):
        """Run all critical E2E tests."""
        print("\n" + "="*80)
        print("CRITICAL E2E TEST EXECUTION - PROTECTING $510K MRR")
        print("="*80)
        
        total = len(self.critical_tests)
        passed = 0
        failed = 0
        
        for test_file, business_value in self.critical_tests:
            success, output = self.run_test(test_file, business_value)
            
            self.results[test_file] = {
                "success": success,
                "business_value": business_value,
                "output": output[:500] if len(output) > 500 else output
            }
            
            if success:
                passed += 1
            else:
                failed += 1
        
        # Print summary
        self.print_summary(total, passed, failed)
        
        # Save results
        self.save_results()
        
        return passed == total
    
    def print_summary(self, total: int, passed: int, failed: int):
        """Print test execution summary."""
        print("\n" + "="*80)
        print("E2E TEST EXECUTION SUMMARY")
        print("="*80)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Calculate business value at risk
        total_value = 510  # $510K MRR total
        protected_value = (passed / total) * total_value
        at_risk_value = total_value - protected_value
        
        print(f"\nBusiness Impact:")
        print(f"Protected: ${protected_value:.0f}K MRR")
        print(f"At Risk: ${at_risk_value:.0f}K MRR")
        
        # Show failed tests
        if failed > 0:
            print("\nFailed Tests:")
            for test_file, data in self.results.items():
                if not data["success"]:
                    print(f"  - {test_file}: {data['business_value']}")
    
    def save_results(self):
        """Save test results to file."""
        results_file = project_root / "test_reports" / "e2e_critical_tests_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")


class ServiceChecker:
    """Check if required services are available."""
    
    @staticmethod
    def check_services() -> Dict[str, bool]:
        """Check availability of required services."""
        services = {
            "Auth Service (8001)": ServiceChecker.check_port(8001),
            "Backend Service (8000)": ServiceChecker.check_port(8000),
            "Frontend (3000)": ServiceChecker.check_port(3000),
            "PostgreSQL (5432)": ServiceChecker.check_port(5432),
            "Redis (6379)": ServiceChecker.check_port(6379),
        }
        
        return services
    
    @staticmethod  
    def check_port(port: int) -> bool:
        """Check if a port is open."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    
    @staticmethod
    def print_service_status():
        """Print status of required services."""
        print("\n" + "="*60)
        print("SERVICE STATUS CHECK")
        print("="*60)
        
        services = ServiceChecker.check_services()
        all_up = True
        
        for service, is_up in services.items():
            status = "[UP]" if is_up else "[DOWN]"
            print(f"{service}: {status}")
            if not is_up:
                all_up = False
        
        if not all_up:
            print("\n[WARNING]: Some services are not running!")
            print("The tests will use mock mode where possible.")
            print("\nTo run with real services:")
            print("  python scripts/dev_launcher.py")
        
        return all_up


def main():
    """Main entry point."""
    print("Netra Apex - Critical E2E Test Runner")
    print("Protecting $510K MRR through comprehensive testing")
    
    # Check service status
    services_ready = ServiceChecker.print_service_status()
    
    if not services_ready:
        # Auto-continue in batch mode
        print("\nServices not fully ready. Continuing with mock tests...")
        print("Note: Real E2E tests require all services running.")
    
    # Run tests
    runner = E2ETestRunner()
    success = runner.run_all_tests()
    
    # Return appropriate exit code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())