#!/usr/bin/env python3
"""
Starlette Routing Error Test Runner
Automated execution of the comprehensive test suite to reproduce routing.py line 716 errors.

MISSION: Execute systematic test strategy to reproduce the Starlette routing error
CRITICAL: Follows the test execution guide with automated result analysis
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class TestResult:
    """Structured test result for analysis."""
    test_name: str
    status: str  # passed, failed, error, skipped
    duration: float
    error_message: Optional[str] = None
    routing_error_indicators: List[str] = None
    middleware_conflicts: List[str] = None
    
    def __post_init__(self):
        if self.routing_error_indicators is None:
            self.routing_error_indicators = []
        if self.middleware_conflicts is None:
            self.middleware_conflicts = []


class StarletteRoutingErrorTestRunner:
    """Automated test runner for Starlette routing error reproduction."""
    
    def __init__(self):
        self.test_directory = Path(__file__).parent
        self.results: List[TestResult] = []
        self.environment_setup = False
        
        # Target error patterns to detect
        self.target_patterns = [
            r"routing\.py.*line 716",
            r"middleware_stack.*scope.*receive.*send", 
            r"_exception_handler\.py.*line 42",
            r"starlette.*routing.*middleware_stack"
        ]
        
        # High correlation patterns
        self.correlation_patterns = [
            r"middleware_stack.*error",
            r"websocket.*upgrade.*routing",
            r"sessionmiddleware.*must be installed",
            r"scope.*corruption",
            r"routing.*conflict"
        ]
    
    def setup_environment(self):
        """Set up test environment for maximum error reproduction potential."""
        print("🔧 Setting up test environment...")
        
        # Set environment variables for production-like conditions
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["K_SERVICE"] = "netra-staging-backend"  
        os.environ["GCP_PROJECT_ID"] = "netra-staging"
        os.environ["SECRET_KEY"] = "test_secret_key_32_chars_minimum_length"
        os.environ["DEBUG"] = "true"
        os.environ["PYTEST_VERBOSITY"] = "2"
        
        # Ensure we're in the right directory
        os.chdir(self.test_directory.parent.parent)  # Navigate to project root
        
        self.environment_setup = True
        print("✅ Environment configured for routing error reproduction")
    
    def run_test_phase(self, phase_name: str, test_commands: List[str]) -> List[TestResult]:
        """Run a phase of tests and capture results."""
        print(f"\n🚀 PHASE: {phase_name}")
        print("=" * 60)
        
        phase_results = []
        
        for i, command in enumerate(test_commands):
            print(f"\n📋 Running test {i+1}/{len(test_commands)}: {command}")
            
            start_time = time.time()
            result = self._run_single_test(command)
            result.duration = time.time() - start_time
            
            phase_results.append(result)
            self.results.append(result)
            
            # Analyze result immediately
            self._analyze_test_result(result)
        
        return phase_results
    
    def _run_single_test(self, command: str) -> TestResult:
        """Execute a single test command and capture results."""
        try:
            # Run the test with comprehensive output capture
            process = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per test
                cwd=self.test_directory.parent.parent
            )
            
            # Create test result
            result = TestResult(
                test_name=self._extract_test_name(command),
                status="passed" if process.returncode == 0 else "failed",
                duration=0,  # Will be set by caller
                error_message=process.stderr if process.returncode != 0 else None
            )
            
            # Analyze output for routing error patterns
            full_output = process.stdout + process.stderr
            result.routing_error_indicators = self._find_routing_patterns(full_output)
            result.middleware_conflicts = self._find_middleware_conflicts(full_output)
            
            # Print immediate feedback
            if result.status == "passed":
                print(f"   ✅ PASSED")
            else:
                print(f"   ❌ FAILED")
                if result.routing_error_indicators:
                    print(f"   🎯 ROUTING PATTERNS DETECTED: {len(result.routing_error_indicators)}")
                
            return result
            
        except subprocess.TimeoutExpired:
            return TestResult(
                test_name=self._extract_test_name(command),
                status="timeout",
                duration=300,
                error_message="Test timed out after 5 minutes"
            )
        except Exception as e:
            return TestResult(
                test_name=self._extract_test_name(command),
                status="error",
                duration=0,
                error_message=str(e)
            )
    
    def _extract_test_name(self, command: str) -> str:
        """Extract a readable test name from command."""
        parts = command.split("::")
        if len(parts) > 1:
            return parts[-1]
        else:
            # Extract from file path
            for part in command.split():
                if "test_" in part and ".py" in part:
                    return Path(part).stem
        return command.split()[-1]
    
    def _find_routing_patterns(self, output: str) -> List[str]:
        """Find routing error patterns in test output."""
        import re
        patterns_found = []
        
        for pattern in self.target_patterns + self.correlation_patterns:
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE):
                patterns_found.append(pattern)
        
        return patterns_found
    
    def _find_middleware_conflicts(self, output: str) -> List[str]:
        """Find middleware conflict indicators in output."""
        conflict_indicators = [
            "SessionMiddleware must be installed",
            "middleware ordering",
            "CORS.*WebSocket",
            "authentication.*WebSocket", 
            "scope corruption",
            "middleware_stack processing"
        ]
        
        import re
        conflicts_found = []
        
        for indicator in conflict_indicators:
            if re.search(indicator, output, re.IGNORECASE):
                conflicts_found.append(indicator)
        
        return conflicts_found
    
    def _analyze_test_result(self, result: TestResult):
        """Analyze individual test result for success indicators."""
        if result.routing_error_indicators:
            # Check for exact target match
            target_matches = [p for p in result.routing_error_indicators if p in self.target_patterns]
            if target_matches:
                print(f"      🎯 TARGET ERROR PATTERN MATCH: {target_matches}")
            
            # Check for high correlation patterns
            correlation_matches = [p for p in result.routing_error_indicators if p in self.correlation_patterns]
            if correlation_matches:
                print(f"      ⚠️ HIGH CORRELATION PATTERNS: {correlation_matches}")
        
        if result.middleware_conflicts:
            print(f"      🔧 MIDDLEWARE CONFLICTS: {result.middleware_conflicts}")
    
    def run_quick_reproduction_phase(self) -> List[TestResult]:
        """Phase 1: Quick reproduction attempts for immediate wins."""
        commands = [
            "python -m pytest tests/middleware_routing/test_starlette_routing_error_reproduction.py::StarletteRoutingErrorReproduction::test_production_middleware_stack_exact_reproduction -v",
            "python -m pytest tests/middleware_routing/test_e2e_websocket_middleware_routing.py::WebSocketMiddlewareE2ETests::test_production_websocket_endpoint_exact_reproduction -v",
            "python -m pytest tests/middleware_routing/test_starlette_routing_error_reproduction.py::MiddlewareOrderingTests::test_all_possible_middleware_orders -v"
        ]
        
        return self.run_test_phase("Quick Reproduction Attempts", commands)
    
    def run_comprehensive_pattern_testing(self) -> List[TestResult]:
        """Phase 2: Comprehensive pattern testing across all scenarios."""
        commands = [
            "python -m pytest tests/middleware_routing/test_starlette_routing_error_reproduction.py -v",
            "python -m pytest tests/middleware_routing/test_route_middleware_integration.py -v",
            "python -m pytest tests/middleware_routing/test_e2e_websocket_middleware_routing.py -v",
            "python -m pytest tests/middleware_routing/test_incomplete_error_logging_reproduction.py -v"
        ]
        
        return self.run_test_phase("Comprehensive Pattern Testing", commands)
    
    def run_stress_testing_phase(self) -> List[TestResult]:
        """Phase 3: Stress testing for race conditions and edge cases."""
        commands = [
            "python -m pytest tests/middleware_routing/test_e2e_websocket_middleware_routing.py::WebSocketMiddlewareE2ETests::test_concurrent_websocket_connections_middleware_stress -v",
            "python -m pytest tests/middleware_routing/test_route_middleware_integration.py::RouteMiddlewareIntegrationTests::test_asgi_scope_corruption_routing_error -v"
        ]
        
        return self.run_test_phase("Stress Testing & Edge Cases", commands)
    
    def generate_comprehensive_report(self):
        """Generate comprehensive analysis report."""
        print("\n" + "="*80)
        print("🎯 STARLETTE ROUTING ERROR REPRODUCTION ANALYSIS REPORT")
        print("="*80)
        
        # Summary statistics
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == "passed"])
        failed_tests = len([r for r in self.results if r.status == "failed"])
        error_tests = len([r for r in self.results if r.status == "error"])
        
        print(f"\n📊 EXECUTION SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Errors: {error_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Routing error pattern analysis
        tests_with_routing_patterns = [r for r in self.results if r.routing_error_indicators]
        tests_with_target_patterns = [
            r for r in self.results 
            if any(p in self.target_patterns for p in r.routing_error_indicators)
        ]
        
        print(f"\n🎯 ROUTING ERROR PATTERN DETECTION:")
        print(f"   Tests with routing patterns: {len(tests_with_routing_patterns)}")
        print(f"   Tests with TARGET patterns: {len(tests_with_target_patterns)}")
        
        if tests_with_target_patterns:
            print(f"\n🏆 SUCCESS: TARGET ROUTING ERROR PATTERNS DETECTED!")
            for test in tests_with_target_patterns:
                print(f"   ✅ {test.test_name}: {test.routing_error_indicators}")
        
        # Middleware conflict analysis
        tests_with_conflicts = [r for r in self.results if r.middleware_conflicts]
        print(f"\n🔧 MIDDLEWARE CONFLICT ANALYSIS:")
        print(f"   Tests with middleware conflicts: {len(tests_with_conflicts)}")
        
        # Most common patterns
        all_patterns = []
        for result in self.results:
            all_patterns.extend(result.routing_error_indicators)
        
        if all_patterns:
            from collections import Counter
            pattern_counts = Counter(all_patterns)
            print(f"\n📈 MOST COMMON ERROR PATTERNS:")
            for pattern, count in pattern_counts.most_common(5):
                print(f"   {count}x: {pattern}")
        
        # Test timing analysis
        avg_duration = sum(r.duration for r in self.results) / len(self.results)
        longest_test = max(self.results, key=lambda r: r.duration)
        
        print(f"\n⏱️ PERFORMANCE ANALYSIS:")
        print(f"   Average test duration: {avg_duration:.2f}s")
        print(f"   Longest test: {longest_test.test_name} ({longest_test.duration:.2f}s)")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if tests_with_target_patterns:
            print("   🎯 SUCCESS: Target routing error reproduced!")
            print("   → Focus on the tests that detected target patterns")
            print("   → Analyze middleware configurations from successful reproductions")
            print("   → Implement fixes based on identified root causes")
        elif tests_with_routing_patterns:
            print("   ⚠️ PARTIAL SUCCESS: Related routing errors detected")
            print("   → Investigate high-correlation patterns for clues") 
            print("   → Consider environment differences from production")
            print("   → Try increasing test stress levels or timing variations")
        else:
            print("   ❌ No routing errors reproduced in current test run")
            print("   → Verify production environment configuration matches test setup")
            print("   → Consider external dependencies not captured in tests")
            print("   → Review production logs for additional error context")
        
        if tests_with_conflicts:
            print("   🔧 Middleware conflicts detected - investigate ordering issues")
        
        # Save detailed results
        self._save_results_to_file()
    
    def _save_results_to_file(self):
        """Save detailed results to JSON file for further analysis."""
        results_file = self.test_directory / "routing_error_test_results.json"
        
        results_data = {
            "execution_timestamp": time.time(),
            "environment": dict(os.environ),
            "test_results": [asdict(result) for result in self.results],
            "summary": {
                "total_tests": len(self.results),
                "routing_patterns_detected": len([r for r in self.results if r.routing_error_indicators]),
                "middleware_conflicts_detected": len([r for r in self.results if r.middleware_conflicts])
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"   💾 Detailed results saved to: {results_file}")
    
    def run_full_test_suite(self):
        """Execute the complete test suite following the strategic approach."""
        print("🚀 STARTING COMPREHENSIVE STARLETTE ROUTING ERROR REPRODUCTION")
        print("="*80)
        
        if not self.environment_setup:
            self.setup_environment()
        
        try:
            # Phase 1: Quick wins
            print("Starting Phase 1: Quick Reproduction Attempts...")
            phase1_results = self.run_quick_reproduction_phase()
            
            # Check if we got immediate success
            phase1_successes = [r for r in phase1_results if r.routing_error_indicators]
            if phase1_successes:
                print(f"\n🎉 PHASE 1 SUCCESS: {len(phase1_successes)} tests detected routing patterns!")
                print("Proceeding with comprehensive testing to gather more evidence...")
            
            # Phase 2: Comprehensive testing
            print("\nStarting Phase 2: Comprehensive Pattern Testing...")
            phase2_results = self.run_comprehensive_pattern_testing()
            
            # Phase 3: Stress testing (only if we haven't found clear successes)
            total_successes = len([r for r in self.results if r.routing_error_indicators])
            if total_successes < 3:  # If we don't have strong evidence yet
                print("\nStarting Phase 3: Stress Testing & Edge Cases...")
                phase3_results = self.run_stress_testing_phase()
            
            # Generate final report
            self.generate_comprehensive_report()
            
        except KeyboardInterrupt:
            print("\n⚠️ Test execution interrupted by user")
            if self.results:
                print("Generating partial report from completed tests...")
                self.generate_comprehensive_report()
        except Exception as e:
            print(f"\n❌ Test execution failed: {e}")
            if self.results:
                print("Generating partial report from completed tests...")
                self.generate_comprehensive_report()
            raise


def main():
    """Main entry point for the test runner."""
    print("Starlette Routing Error Reproduction Test Suite")
    print("Automated execution following comprehensive test strategy")
    print()
    
    runner = StarletteRoutingErrorTestRunner()
    
    # Check if specific test requested
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            runner.setup_environment()
            runner.run_quick_reproduction_phase()
            runner.generate_comprehensive_report()
        elif sys.argv[1] == "--comprehensive":  
            runner.setup_environment()
            runner.run_comprehensive_pattern_testing()
            runner.generate_comprehensive_report()
        elif sys.argv[1] == "--stress":
            runner.setup_environment()
            runner.run_stress_testing_phase() 
            runner.generate_comprehensive_report()
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Available options: --quick, --comprehensive, --stress")
            sys.exit(1)
    else:
        # Run full suite
        runner.run_full_test_suite()


if __name__ == "__main__":
    main()