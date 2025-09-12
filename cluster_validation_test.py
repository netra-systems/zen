#!/usr/bin/env python3
"""
HOLISTIC CLUSTER VALIDATION TEST
=================================

This test validates the cluster of issues:
- Issue #489: Test collection timeout in unified_test_runner.py
- Issue #460: 40,387 architectural violations
- Dependency #450: Redis cleanup status
- Resolved #485: SSOT imports (verification needed)

Business Value Justification:
- Segment: Platform/Development Infrastructure
- Goal: Stability and Development Velocity
- Value Impact: Ensures testing infrastructure supports 90% chat platform value
- Revenue Impact: Prevents development delays that could impact $500K+ ARR
"""

import asyncio
import sys
import time
import traceback
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

class ClusterValidationTest:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()

    def log(self, message: str):
        elapsed = time.time() - self.start_time
        # Handle Unicode encoding issues on Windows
        try:
            print(f"[{elapsed:6.2f}s] {message}")
        except UnicodeEncodeError:
            safe_message = message.encode('ascii', errors='replace').decode('ascii')
            print(f"[{elapsed:6.2f}s] {safe_message}")

    def test_issue_489_timeout_reproduction(self):
        """Test #489: Reproduce test collection timeout behavior"""
        self.log("=== TESTING ISSUE #489: Test Collection Timeout ===")
        
        try:
            # Test 1: Basic import works
            from tests.unified_test_runner import main
            self.log(" PASS:  unified_test_runner imports successfully")
            
            # Test 2: Can we collect tests without hanging?
            import subprocess
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Test collection timed out")
            
            # Set alarm for 30 seconds
            if hasattr(signal, 'SIGALRM'):  # Unix-like systems
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)
            
            try:
                # Try to collect just a few tests
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    "netra_backend/tests/unit", "--collect-only", "--quiet",
                    "--maxfail=1"
                ], capture_output=True, text=True, timeout=30)
                
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)  # Cancel alarm
                
                if result.returncode == 0:
                    self.log(f" PASS:  Test collection completed in {result}")
                    self.results['issue_489'] = 'PASS'
                else:
                    self.log(f" FAIL:  Test collection failed: {result.stderr[:200]}")
                    self.results['issue_489'] = 'FAIL - Collection error'
                    
            except (subprocess.TimeoutExpired, TimeoutError):
                self.log(" FAIL:  Test collection timed out (reproduced issue #489)")
                self.results['issue_489'] = 'FAIL - Timeout reproduced'
                
        except Exception as e:
            self.log(f" FAIL:  Error testing issue #489: {e}")
            self.results['issue_489'] = f'ERROR: {str(e)}'

    def test_issue_460_architectural_violations(self):
        """Test #460: Validate 40,387+ architectural violations exist"""
        self.log("=== TESTING ISSUE #460: Architectural Violations ===")
        
        try:
            # Test architectural compliance script
            import subprocess
            result = subprocess.run([
                sys.executable, "scripts/check_architecture_compliance.py"
            ], capture_output=True, text=True, timeout=60)
            
            output = result.stdout + result.stderr
            
            # Look for violation count
            if "40387" in output or "40383" in output:
                self.log(" PASS:  Issue #460 confirmed: ~40,387 violations found")
                self.results['issue_460'] = 'CONFIRMED'
            elif "Total Violations:" in output:
                # Extract violation count
                for line in output.split('\n'):
                    if "Total Violations:" in line:
                        count = line.split(':')[-1].strip()
                        self.log(f" PASS:  Violations found: {count}")
                        self.results['issue_460'] = f'CONFIRMED - {count} violations'
                        break
            else:
                self.log(f"[U+2753] Unclear violation count in output: {output[:500]}")
                self.results['issue_460'] = 'UNCLEAR'
                
        except Exception as e:
            self.log(f" FAIL:  Error testing issue #460: {e}")
            self.results['issue_460'] = f'ERROR: {str(e)}'

    def test_dependency_450_redis_cleanup(self):
        """Test dependency #450: Redis cleanup status"""
        self.log("=== TESTING DEPENDENCY #450: Redis Cleanup Status ===")
        
        try:
            # Test Redis connectivity
            from netra_backend.app.services.redis_client import get_redis_client
            
            async def test_redis():
                try:
                    client = await get_redis_client()
                    self.log(" PASS:  Redis client accessible")
                    return True
                except Exception as e:
                    self.log(f" FAIL:  Redis not accessible: {e}")
                    return False
            
            redis_available = asyncio.run(test_redis())
            
            if redis_available:
                self.results['dependency_450'] = 'AVAILABLE'
            else:
                self.results['dependency_450'] = 'NOT_AVAILABLE'
                self.log(" WARNING: [U+FE0F]  Redis dependency issue may impact tests")
                
        except Exception as e:
            self.log(f" FAIL:  Error testing dependency #450: {e}")
            self.results['dependency_450'] = f'ERROR: {str(e)}'

    def test_resolved_485_ssot_imports(self):
        """Test resolved #485: SSOT imports verification"""
        self.log("=== TESTING RESOLVED #485: SSOT Imports ===")
        
        try:
            # Test key SSOT imports
            imports_to_test = [
                ("UserExecutionContext", "netra_backend.app.services.user_execution_context"),
                ("ExecutionState", "netra_backend.app.core.agent_execution_tracker"),
                ("AgentExecutionTracker", "netra_backend.app.core.agent_execution_tracker"),
                ("WebSocketManager", "netra_backend.app.websocket_core.websocket_manager"),
            ]
            
            failed_imports = []
            for name, module in imports_to_test:
                try:
                    __import__(module)
                    mod = sys.modules[module]
                    getattr(mod, name)
                    self.log(f" PASS:  {name} from {module}")
                except Exception as e:
                    self.log(f" FAIL:  {name} from {module}: {e}")
                    failed_imports.append((name, module, str(e)))
            
            if not failed_imports:
                self.log(" PASS:  All SSOT imports working correctly")
                self.results['resolved_485'] = 'VERIFIED'
            else:
                self.log(f" FAIL:  {len(failed_imports)} SSOT imports failing")
                self.results['resolved_485'] = f'PARTIAL - {len(failed_imports)} failures'
                
        except Exception as e:
            self.log(f" FAIL:  Error testing resolved #485: {e}")
            self.results['resolved_485'] = f'ERROR: {str(e)}'

    def test_cluster_interaction_patterns(self):
        """Test how issues interact with each other"""
        self.log("=== TESTING CLUSTER INTERACTION PATTERNS ===")
        
        try:
            # Test 1: Do architectural violations cause test timeouts?
            violations_impact_tests = False
            
            # Test 2: Does Redis unavailability affect test collection?
            redis_impact_tests = False
            
            # Test 3: Do SSOT imports work despite architectural violations?
            ssot_works_despite_violations = (
                self.results.get('resolved_485') == 'VERIFIED' and
                'CONFIRMED' in str(self.results.get('issue_460', ''))
            )
            
            if ssot_works_despite_violations:
                self.log(" PASS:  SSOT imports work despite architectural violations")
            else:
                self.log(" FAIL:  SSOT imports affected by other cluster issues")
            
            # Test 4: Business impact assessment
            chat_platform_impact = any([
                'FAIL' in str(self.results.get('issue_489', '')),
                'NOT_AVAILABLE' in str(self.results.get('dependency_450', '')),
                'ERROR' in str(self.results.get('resolved_485', ''))
            ])
            
            if chat_platform_impact:
                self.log(" ALERT:  BUSINESS IMPACT: Cluster affects chat platform testing (90% platform value)")
                self.results['business_impact'] = 'HIGH - Testing infrastructure compromised'
            else:
                self.log(" PASS:  BUSINESS IMPACT: Limited impact on chat platform core functionality")
                self.results['business_impact'] = 'LOW - Core functionality preserved'
                
            self.results['cluster_interaction'] = {
                'ssot_works_despite_violations': ssot_works_despite_violations,
                'business_impact': chat_platform_impact
            }
            
        except Exception as e:
            self.log(f" FAIL:  Error testing cluster interactions: {e}")
            self.results['cluster_interaction'] = f'ERROR: {str(e)}'

    def test_business_workflow_validation(self):
        """Test developer TDD workflow with timeout impact"""
        self.log("=== TESTING BUSINESS WORKFLOW VALIDATION ===")
        
        try:
            # Simulate developer TDD workflow
            workflow_steps = [
                ("Import core modules", self._test_core_imports),
                ("Basic test collection", self._test_basic_collection),
                ("Architecture validation", self._test_architecture_quick),
                ("Business value delivery", self._test_business_value)
            ]
            
            workflow_results = {}
            total_time = 0
            
            for step_name, step_func in workflow_steps:
                self.log(f"Testing workflow step: {step_name}")
                step_start = time.time()
                
                try:
                    result = step_func()
                    step_time = time.time() - step_start
                    total_time += step_time
                    
                    workflow_results[step_name] = {
                        'result': result,
                        'time': step_time,
                        'status': 'SUCCESS' if result else 'FAILED'
                    }
                    
                    if step_time > 30:  # > 30 seconds is problematic for TDD
                        self.log(f" WARNING: [U+FE0F]  Step '{step_name}' took {step_time:.1f}s (TDD workflow impact)")
                    
                except Exception as e:
                    step_time = time.time() - step_start
                    total_time += step_time
                    workflow_results[step_name] = {
                        'result': False,
                        'time': step_time,
                        'status': 'ERROR',
                        'error': str(e)
                    }
            
            # Assess workflow impact
            if total_time > 120:  # > 2 minutes impacts TDD flow
                self.log(f" ALERT:  TDD WORKFLOW IMPACT: Total validation time {total_time:.1f}s > 2 minutes")
                workflow_impact = 'HIGH'
            elif total_time > 60:
                self.log(f" WARNING: [U+FE0F]  TDD WORKFLOW IMPACT: Total validation time {total_time:.1f}s > 1 minute")
                workflow_impact = 'MEDIUM'
            else:
                self.log(f" PASS:  TDD WORKFLOW: Total validation time {total_time:.1f}s acceptable")
                workflow_impact = 'LOW'
            
            self.results['business_workflow'] = {
                'steps': workflow_results,
                'total_time': total_time,
                'impact_level': workflow_impact
            }
            
        except Exception as e:
            self.log(f" FAIL:  Error testing business workflow: {e}")
            self.results['business_workflow'] = f'ERROR: {str(e)}'

    def _test_core_imports(self):
        """Test core module imports for TDD workflow"""
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.core.agent_execution_tracker import ExecutionState
            return True
        except:
            return False

    def _test_basic_collection(self):
        """Test basic test collection for TDD workflow"""
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "--collect-only", "--quiet", "--maxfail=1",
                "netra_backend/tests/unit/test_*.py"  # Just a few test files
            ], capture_output=True, timeout=20)
            return result.returncode == 0
        except:
            return False

    def _test_architecture_quick(self):
        """Test quick architecture validation for TDD workflow"""
        try:
            # Quick check - just count violations without full report
            import subprocess
            result = subprocess.run([
                sys.executable, "-c", 
                "from scripts.check_architecture_compliance import main; print('OK')"
            ], capture_output=True, timeout=10)
            return "OK" in result.stdout
        except:
            return False

    def _test_business_value(self):
        """Test business value delivery for TDD workflow"""
        try:
            # Can we import and instantiate core chat functionality?
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import UserID, ThreadID, RunID
            
            # Create a test context
            context = UserExecutionContext(
                user_id=UserID("test-user"),
                thread_id=ThreadID("test-thread"), 
                run_id=RunID("test-run"),
                request_id="test-request",
                agent_name="test-agent"
            )
            return context is not None
        except:
            return False

    def run_all_tests(self):
        """Run all cluster validation tests"""
        self.log("[U+1F680] STARTING HOLISTIC CLUSTER VALIDATION")
        self.log("=" * 60)
        
        test_methods = [
            self.test_issue_489_timeout_reproduction,
            self.test_issue_460_architectural_violations,
            self.test_dependency_450_redis_cleanup,
            self.test_resolved_485_ssot_imports,
            self.test_cluster_interaction_patterns,
            self.test_business_workflow_validation
        ]
        
        for test_method in test_methods:
            try:
                test_method()
                self.log("")  # Blank line for readability
            except Exception as e:
                self.log(f" FAIL:  CRITICAL ERROR in {test_method.__name__}: {e}")
                self.log(traceback.format_exc())
                self.results[test_method.__name__] = f'CRITICAL_ERROR: {str(e)}'
        
        # Generate final report
        self.generate_final_report()

    def generate_final_report(self):
        """Generate comprehensive cluster validation report"""
        total_time = time.time() - self.start_time
        
        self.log("=" * 60)
        self.log(" CHART:  HOLISTIC CLUSTER VALIDATION RESULTS")
        self.log("=" * 60)
        
        # Summary by issue
        for issue, result in self.results.items():
            status_emoji = " PASS: " if any(x in str(result) for x in ['PASS', 'CONFIRMED', 'VERIFIED', 'SUCCESS']) else " FAIL: "
            self.log(f"{status_emoji} {issue}: {result}")
        
        self.log("")
        self.log(f"Total execution time: {total_time:.2f}s")
        
        # Business impact summary
        business_impact = self.results.get('business_impact', 'UNKNOWN')
        if 'HIGH' in business_impact:
            self.log(" ALERT:  BUSINESS IMPACT: HIGH - Testing infrastructure significantly compromised")
            self.log("   - Developer TDD workflow disrupted")
            self.log("   - Chat platform validation blocked (90% platform value at risk)")
            self.log("   - CI/CD pipeline reliability uncertain")
        elif 'MEDIUM' in business_impact:
            self.log(" WARNING: [U+FE0F]  BUSINESS IMPACT: MEDIUM - Some testing capabilities affected")
        else:
            self.log(" PASS:  BUSINESS IMPACT: LOW - Core functionality testing preserved")
        
        # Cluster validation summary
        cluster_works = all(
            not any(x in str(result) for x in ['ERROR', 'CRITICAL_ERROR', 'FAIL'])
            for result in self.results.values()
        )
        
        if cluster_works:
            self.log(" PASS:  CLUSTER STATUS: All issues validated, interactions understood")
        else:
            self.log(" FAIL:  CLUSTER STATUS: Critical issues found, immediate action required")
        
        return self.results

if __name__ == "__main__":
    validator = ClusterValidationTest()
    results = validator.run_all_tests()
    
    # Exit with appropriate code
    if any('CRITICAL_ERROR' in str(r) or 'HIGH' in str(r) for r in results.values()):
        sys.exit(1)
    else:
        sys.exit(0)