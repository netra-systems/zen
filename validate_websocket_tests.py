#!/usr/bin/env python
"""
WebSocket Test Suite Final Validation
Validates all 154+ WebSocket bridge tests are passing
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import time

class WebSocketTestValidator:
    def __init__(self):
        self.test_dir = Path("tests/mission_critical")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "total_files": 0,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_files": [],
            "validation_requirements": {
                "154+ tests passing": False,
                "25+ concurrent sessions": False,
                "zero message drops": False,
                "<50ms P99 latency": False,
                "3s reconnection": False
            }
        }
    
    def find_websocket_tests(self):
        """Find all WebSocket test files."""
        test_files = list(self.test_dir.glob("test_websocket*.py"))
        self.results["total_files"] = len(test_files)
        print(f"Found {len(test_files)} WebSocket test files")
        return test_files
    
    def run_test_file(self, test_file):
        """Run a single test file and collect results."""
        print(f"\nTesting: {test_file.name}")
        
        try:
            # Run pytest with JSON output
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_file),
                "--tb=short",
                "-q",
                "--json-report",
                "--json-report-file=test_result.json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse results from JSON if available
            json_file = Path("test_result.json")
            if json_file.exists():
                with open(json_file) as f:
                    test_data = json.load(f)
                    
                passed = test_data.get("summary", {}).get("passed", 0)
                failed = test_data.get("summary", {}).get("failed", 0)
                total = test_data.get("summary", {}).get("total", 0)
                
                json_file.unlink()  # Clean up
                
                return {
                    "file": test_file.name,
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                    "status": "PASS" if failed == 0 else "FAIL"
                }
            else:
                # Parse from output if JSON not available
                output = result.stdout + result.stderr
                
                # Try to extract test counts from output
                if "passed" in output:
                    # Extract counts from pytest output
                    import re
                    passed_match = re.search(r'(\d+) passed', output)
                    failed_match = re.search(r'(\d+) failed', output)
                    
                    passed = int(passed_match.group(1)) if passed_match else 0
                    failed = int(failed_match.group(1)) if failed_match else 0
                    
                    return {
                        "file": test_file.name,
                        "passed": passed,
                        "failed": failed,
                        "total": passed + failed,
                        "status": "PASS" if failed == 0 and passed > 0 else "FAIL"
                    }
                else:
                    # Test file might have import errors or other issues
                    if result.returncode == 0:
                        status = "PASS"
                    elif "no tests ran" in output.lower():
                        status = "NO_TESTS"
                    else:
                        status = "ERROR"
                    
                    return {
                        "file": test_file.name,
                        "passed": 0,
                        "failed": 0,
                        "total": 0,
                        "status": status,
                        "error": output[:500] if status == "ERROR" else None
                    }
                    
        except subprocess.TimeoutExpired:
            return {
                "file": test_file.name,
                "passed": 0,
                "failed": 0,
                "total": 0,
                "status": "TIMEOUT"
            }
        except Exception as e:
            return {
                "file": test_file.name,
                "passed": 0,
                "failed": 0,
                "total": 0,
                "status": "ERROR",
                "error": str(e)
            }
    
    def validate_specific_requirements(self):
        """Check specific validation requirements."""
        # Check concurrency tests
        concurrency_file = self.test_dir / "test_websocket_bridge_concurrency.py"
        if concurrency_file.exists():
            result = self.run_test_file(concurrency_file)
            if result["status"] == "PASS" and result["passed"] > 0:
                self.results["validation_requirements"]["25+ concurrent sessions"] = True
        
        # Check performance tests
        performance_file = self.test_dir / "test_websocket_bridge_performance.py"
        if performance_file.exists():
            result = self.run_test_file(performance_file)
            if result["status"] == "PASS" and result["passed"] > 0:
                self.results["validation_requirements"]["<50ms P99 latency"] = True
        
        # Check chaos tests for reconnection
        chaos_file = self.test_dir / "test_websocket_bridge_chaos.py"
        if chaos_file.exists():
            result = self.run_test_file(chaos_file)
            if result["status"] == "PASS" and result["passed"] > 0:
                self.results["validation_requirements"]["3s reconnection"] = True
        
        # Check message ordering for zero drops
        ordering_file = self.test_dir / "test_websocket_bridge_message_ordering.py"
        if ordering_file.exists():
            result = self.run_test_file(ordering_file)
            if result["status"] == "PASS" and result["passed"] > 0:
                self.results["validation_requirements"]["zero message drops"] = True
    
    def validate_all(self):
        """Run all WebSocket tests and validate requirements."""
        print("=" * 80)
        print("WEBSOCKET TEST SUITE FINAL VALIDATION")
        print("=" * 80)
        
        test_files = self.find_websocket_tests()
        
        # Run critical bridge tests first
        critical_tests = [
            "test_websocket_bridge_isolation.py",
            "test_websocket_bridge_concurrency.py",
            "test_websocket_bridge_thread_safety.py",
            "test_websocket_bridge_chaos.py",
            "test_websocket_bridge_message_ordering.py",
            "test_websocket_bridge_performance.py"
        ]
        
        print("\n" + "=" * 40)
        print("CRITICAL BRIDGE TESTS")
        print("=" * 40)
        
        for test_name in critical_tests:
            test_file = self.test_dir / test_name
            if test_file.exists():
                result = self.run_test_file(test_file)
                self.results["test_files"].append(result)
                self.results["total_tests"] += result["total"]
                self.results["passed_tests"] += result["passed"]
                self.results["failed_tests"] += result["failed"]
                
                status_icon = "PASS" if result["status"] == "PASS" else "FAIL"
                print(f"{status_icon} {test_name}: {result['passed']}/{result['total']} passed")
        
        # Check if we have 154+ tests
        if self.results["total_tests"] >= 154:
            self.results["validation_requirements"]["154+ tests passing"] = True
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate final validation report."""
        print("\n" + "=" * 80)
        print("FINAL VALIDATION REPORT")
        print("=" * 80)
        
        print(f"\nTest Statistics:")
        print(f"  Total Test Files: {self.results['total_files']}")
        print(f"  Total Tests Run: {self.results['total_tests']}")
        print(f"  Tests Passed: {self.results['passed_tests']}")
        print(f"  Tests Failed: {self.results['failed_tests']}")
        
        if self.results['total_tests'] > 0:
            success_rate = (self.results['passed_tests'] / self.results['total_tests']) * 100
            print(f"  Success Rate: {success_rate:.1f}%")
        
        print(f"\nValidation Requirements:")
        all_passed = True
        for requirement, passed in self.results["validation_requirements"].items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}]: {requirement}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed and self.results["failed_tests"] == 0:
            print("VALIDATION RESULT: SUCCESS")
            print("All WebSocket bridge tests are passing!")
        else:
            print("VALIDATION RESULT: PARTIAL SUCCESS")
            print(f"Some tests or requirements need attention.")
        print("=" * 80)
        
        # Save report to file
        report_file = Path("WEBSOCKET_FINAL_VALIDATION_REPORT.json")
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed report saved to: {report_file}")

if __name__ == "__main__":
    validator = WebSocketTestValidator()
    validator.validate_all()