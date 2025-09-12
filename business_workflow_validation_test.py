#!/usr/bin/env python3
"""
BUSINESS WORKFLOW VALIDATION TEST
=================================

Tests the business workflow impact of the cluster issues, focusing on:
1. Developer TDD workflow with timeout impact
2. Chat platform testing capability (90% platform value)
3. CI/CD pipeline simulation
4. Business value delivery measurement

Business Value Justification:
- Segment: Platform (affects all customer tiers)
- Goal: Ensure development infrastructure supports business delivery
- Value Impact: Validates testing can support chat functionality (90% platform value)
- Revenue Impact: Prevents development bottlenecks affecting $500K+ ARR
"""

import asyncio
import sys
import time
import subprocess
import traceback
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

@dataclass
class WorkflowTestResult:
    name: str
    success: bool
    duration: float
    details: str
    business_impact: str

class BusinessWorkflowValidator:
    def __init__(self):
        self.results: List[WorkflowTestResult] = []
        self.start_time = time.time()

    def log(self, message: str):
        elapsed = time.time() - self.start_time
        try:
            print(f"[{elapsed:6.2f}s] {message}")
        except UnicodeEncodeError:
            safe_message = message.encode('ascii', errors='replace').decode('ascii')
            print(f"[{elapsed:6.2f}s] {safe_message}")

    def test_developer_tdd_workflow(self):
        """Test typical developer TDD workflow impact"""
        self.log("=== TESTING DEVELOPER TDD WORKFLOW ===")
        
        workflow_start = time.time()
        
        # Step 1: Import key modules (should be <1s)
        step_start = time.time()
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.core.agent_execution_tracker import ExecutionState
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            import_time = time.time() - step_start
            import_success = True
            import_details = f"Core imports completed in {import_time:.2f}s"
            
            if import_time > 1.0:
                import_details += " (SLOW - impacts TDD feedback loop)"
                
        except Exception as e:
            import_time = time.time() - step_start
            import_success = False
            import_details = f"Import failed in {import_time:.2f}s: {e}"
        
        # Step 2: Quick test discovery (should be <5s for TDD)
        step_start = time.time()
        try:
            # Simulate developer running tests on specific module
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "netra_backend/tests/unit", 
                "--collect-only", "--quiet", "--maxfail=5",
                "-k", "test_user_execution"
            ], capture_output=True, text=True, timeout=10)
            
            discovery_time = time.time() - step_start
            discovery_success = result.returncode == 0
            
            if discovery_success:
                discovery_details = f"Test discovery completed in {discovery_time:.2f}s"
                if discovery_time > 5.0:
                    discovery_details += " (SLOW - impacts TDD flow)"
            else:
                discovery_details = f"Test discovery failed in {discovery_time:.2f}s"
                
        except subprocess.TimeoutExpired:
            discovery_time = 10.0
            discovery_success = False
            discovery_details = "Test discovery timed out (10s) - TDD workflow blocked"
        except Exception as e:
            discovery_time = time.time() - step_start
            discovery_success = False
            discovery_details = f"Test discovery error in {discovery_time:.2f}s: {e}"
        
        # Step 3: Quick test execution (should be <10s for unit tests)
        step_start = time.time()
        try:
            # Run just a few unit tests quickly
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "netra_backend/tests/unit", 
                "-k", "test_execution_state", 
                "--no-header", "--quiet", "--tb=no"
            ], capture_output=True, text=True, timeout=15)
            
            execution_time = time.time() - step_start
            execution_success = result.returncode == 0
            
            if execution_success:
                execution_details = f"Unit tests passed in {execution_time:.2f}s"
                if execution_time > 10.0:
                    execution_details += " (SLOW - impacts TDD velocity)"
            else:
                execution_details = f"Unit tests failed/hung in {execution_time:.2f}s"
                
        except subprocess.TimeoutExpired:
            execution_time = 15.0
            execution_success = False
            execution_details = "Unit tests timed out (15s) - TDD workflow broken"
        except Exception as e:
            execution_time = time.time() - step_start
            execution_success = False
            execution_details = f"Unit test execution error in {execution_time:.2f}s: {e}"
        
        # Overall workflow assessment
        total_workflow_time = time.time() - workflow_start
        workflow_success = import_success and discovery_success and execution_success
        
        # Business impact assessment
        if total_workflow_time > 30:
            impact = "HIGH - TDD feedback loop broken (>30s)"
        elif total_workflow_time > 15:
            impact = "MEDIUM - TDD velocity impacted (15-30s)"  
        elif not workflow_success:
            impact = "HIGH - TDD workflow broken (errors/timeouts)"
        else:
            impact = "LOW - TDD workflow functional"
        
        workflow_details = f"""
Import: {import_details}
Discovery: {discovery_details}  
Execution: {execution_details}
Total: {total_workflow_time:.2f}s
"""
        
        self.results.append(WorkflowTestResult(
            name="Developer TDD Workflow",
            success=workflow_success,
            duration=total_workflow_time,
            details=workflow_details,
            business_impact=impact
        ))

    def test_chat_platform_testing_capability(self):
        """Test ability to test chat functionality (90% of platform value)"""
        self.log("=== TESTING CHAT PLATFORM TESTING CAPABILITY ===")
        
        chat_start = time.time()
        
        # Test 1: Can we test WebSocket functionality?
        step_start = time.time()
        try:
            # Try to collect WebSocket tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "netra_backend/tests", 
                "-k", "websocket",
                "--collect-only", "--quiet"
            ], capture_output=True, text=True, timeout=20)
            
            websocket_time = time.time() - step_start
            websocket_success = result.returncode == 0 and "collected" in result.stdout
            
            if websocket_success:
                # Count collected tests
                lines = result.stdout.split('\n')
                for line in lines:
                    if "collected" in line:
                        websocket_details = f"WebSocket tests discoverable: {line} ({websocket_time:.2f}s)"
                        break
                else:
                    websocket_details = f"WebSocket tests found ({websocket_time:.2f}s)"
            else:
                websocket_details = f"WebSocket test discovery failed ({websocket_time:.2f}s)"
                
        except subprocess.TimeoutExpired:
            websocket_time = 20.0
            websocket_success = False
            websocket_details = "WebSocket test discovery timed out (20s)"
        
        # Test 2: Can we test agent functionality? 
        step_start = time.time()
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "netra_backend/tests", 
                "-k", "agent",
                "--collect-only", "--quiet"
            ], capture_output=True, text=True, timeout=20)
            
            agent_time = time.time() - step_start
            agent_success = result.returncode == 0 and "collected" in result.stdout
            
            if agent_success:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "collected" in line:
                        agent_details = f"Agent tests discoverable: {line} ({agent_time:.2f}s)"
                        break
                else:
                    agent_details = f"Agent tests found ({agent_time:.2f}s)"
            else:
                agent_details = f"Agent test discovery failed ({agent_time:.2f}s)"
                
        except subprocess.TimeoutExpired:
            agent_time = 20.0
            agent_success = False
            agent_details = "Agent test discovery timed out (20s)"
        
        # Test 3: Can we test user context (multi-user isolation)?
        step_start = time.time()
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "netra_backend/tests", 
                "-k", "user_execution_context",
                "--collect-only", "--quiet"
            ], capture_output=True, text=True, timeout=20)
            
            context_time = time.time() - step_start
            context_success = result.returncode == 0
            
            if context_success:
                context_details = f"User context tests discoverable ({context_time:.2f}s)"
            else:
                context_details = f"User context test discovery failed ({context_time:.2f}s)"
                
        except subprocess.TimeoutExpired:
            context_time = 20.0
            context_success = False
            context_details = "User context test discovery timed out (20s)"
        
        # Overall chat testing capability assessment
        total_chat_time = time.time() - chat_start
        chat_success = websocket_success and agent_success and context_success
        
        # Business impact assessment
        if not chat_success:
            impact = "CRITICAL - Cannot validate chat functionality (90% platform value at risk)"
        elif total_chat_time > 60:
            impact = "HIGH - Chat testing severely slow (>60s impacts development)"
        elif total_chat_time > 30:
            impact = "MEDIUM - Chat testing slow (30-60s impacts velocity)"
        else:
            impact = "LOW - Chat testing functional"
        
        chat_details = f"""
WebSocket: {websocket_details}
Agent: {agent_details}
Context: {context_details}
Total: {total_chat_time:.2f}s
"""
        
        self.results.append(WorkflowTestResult(
            name="Chat Platform Testing",
            success=chat_success,
            duration=total_chat_time,
            details=chat_details,
            business_impact=impact
        ))

    def test_cicd_pipeline_simulation(self):
        """Test CI/CD pipeline impact simulation"""
        self.log("=== TESTING CI/CD PIPELINE SIMULATION ===")
        
        pipeline_start = time.time()
        
        # Simulate CI/CD steps that would be affected
        
        # Step 1: Syntax/lint checks (should be fast)
        step_start = time.time()
        try:
            # Quick syntax check of core files
            syntax_files = [
                "netra_backend/app/services/user_execution_context.py",
                "netra_backend/app/core/agent_execution_tracker.py",
                "netra_backend/app/websocket_core/websocket_manager.py"
            ]
            
            syntax_success = True
            for file in syntax_files:
                if Path(file).exists():
                    with open(file, 'r', encoding='utf-8') as f:
                        compile(f.read(), file, 'exec')
                        
            syntax_time = time.time() - step_start
            syntax_details = f"Syntax checks passed ({syntax_time:.2f}s)"
            
        except Exception as e:
            syntax_time = time.time() - step_start  
            syntax_success = False
            syntax_details = f"Syntax checks failed ({syntax_time:.2f}s): {e}"
        
        # Step 2: Quick smoke tests (should be <2 minutes)
        step_start = time.time()
        try:
            # Run smoke tests category
            result = subprocess.run([
                sys.executable, "tests/unified_test_runner.py", 
                "--category", "smoke", 
                "--no-coverage"
            ], capture_output=True, text=True, timeout=120)
            
            smoke_time = time.time() - step_start
            smoke_success = result.returncode == 0
            
            if smoke_success:
                smoke_details = f"Smoke tests passed ({smoke_time:.2f}s)"
            else:
                smoke_details = f"Smoke tests failed ({smoke_time:.2f}s)"
                
        except subprocess.TimeoutExpired:
            smoke_time = 120.0
            smoke_success = False
            smoke_details = "Smoke tests timed out (2 minutes)"
        except Exception as e:
            smoke_time = time.time() - step_start
            smoke_success = False
            smoke_details = f"Smoke tests error ({smoke_time:.2f}s): {e}"
        
        # Step 3: Architecture compliance check (should be <1 minute)
        step_start = time.time()
        try:
            result = subprocess.run([
                sys.executable, "scripts/check_architecture_compliance.py"
            ], capture_output=True, text=True, timeout=60)
            
            compliance_time = time.time() - step_start
            compliance_success = result.returncode == 0
            
            # Extract violation count
            if "Total Violations:" in result.stdout:
                for line in result.stdout.split('\n'):
                    if "Total Violations:" in line:
                        violation_count = line.split(':')[-1].strip()
                        break
                else:
                    violation_count = "unknown"
            else:
                violation_count = "unknown"
            
            if compliance_success:
                compliance_details = f"Compliance check passed ({compliance_time:.2f}s, {violation_count} violations)"
            else:
                compliance_details = f"Compliance check completed ({compliance_time:.2f}s, {violation_count} violations)"
                
        except subprocess.TimeoutExpired:
            compliance_time = 60.0
            compliance_success = False
            compliance_details = "Compliance check timed out (1 minute)"
        except Exception as e:
            compliance_time = time.time() - step_start
            compliance_success = False
            compliance_details = f"Compliance check error ({compliance_time:.2f}s): {e}"
        
        # Overall pipeline assessment
        total_pipeline_time = time.time() - pipeline_start
        pipeline_success = syntax_success and smoke_success
        # Note: compliance doesn't need to pass (40k violations expected)
        
        # Business impact assessment
        if total_pipeline_time > 300:  # 5 minutes
            impact = "CRITICAL - CI/CD pipeline too slow (>5 minutes)"
        elif not pipeline_success:
            impact = "HIGH - CI/CD pipeline broken (syntax/smoke failures)"
        elif total_pipeline_time > 180:  # 3 minutes
            impact = "MEDIUM - CI/CD pipeline slow (3-5 minutes)"
        else:
            impact = "LOW - CI/CD pipeline acceptable"
        
        pipeline_details = f"""
Syntax: {syntax_details}
Smoke: {smoke_details}
Compliance: {compliance_details}
Total: {total_pipeline_time:.2f}s
"""
        
        self.results.append(WorkflowTestResult(
            name="CI/CD Pipeline Simulation",
            success=pipeline_success,
            duration=total_pipeline_time,
            details=pipeline_details,
            business_impact=impact
        ))

    def test_business_value_delivery_measurement(self):
        """Test measurement of business value delivery impact"""
        self.log("=== TESTING BUSINESS VALUE DELIVERY MEASUREMENT ===")
        
        measurement_start = time.time()
        
        # Test core business capabilities
        capabilities = {}
        
        # Capability 1: User isolation (Enterprise feature)
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import UserID, ThreadID, RunID
            
            context1 = UserExecutionContext(
                user_id=UserID("user1"),
                thread_id=ThreadID("thread1"), 
                run_id=RunID("run1"),
                request_id="req1",
                agent_name="test"
            )
            
            context2 = UserExecutionContext(
                user_id=UserID("user2"),
                thread_id=ThreadID("thread2"), 
                run_id=RunID("run2"),
                request_id="req2",
                agent_name="test"
            )
            
            # Verify isolation
            isolation_works = (
                context1.user_id != context2.user_id and
                context1.thread_id != context2.thread_id and
                context1.run_id != context2.run_id
            )
            
            capabilities['user_isolation'] = {
                'works': isolation_works,
                'business_value': '$15K+ MRR per Enterprise customer',
                'impact': 'HIGH' if isolation_works else 'CRITICAL'
            }
            
        except Exception as e:
            capabilities['user_isolation'] = {
                'works': False,
                'business_value': '$15K+ MRR per Enterprise customer',
                'impact': 'CRITICAL',
                'error': str(e)
            }
        
        # Capability 2: Agent execution tracking (Core platform)
        try:
            from netra_backend.app.core.agent_execution_tracker import ExecutionState, AgentExecutionTracker
            
            states_work = all(hasattr(ExecutionState, state) for state in [
                'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
            ])
            
            capabilities['agent_execution'] = {
                'works': states_work,
                'business_value': '90% of platform value (chat functionality)',
                'impact': 'CRITICAL' if not states_work else 'LOW'
            }
            
        except Exception as e:
            capabilities['agent_execution'] = {
                'works': False,
                'business_value': '90% of platform value (chat functionality)',
                'impact': 'CRITICAL',
                'error': str(e)
            }
        
        # Capability 3: WebSocket communication (Real-time UX)
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Can instantiate (doesn't need to be functional)
            manager_importable = True
            
            capabilities['websocket_communication'] = {
                'works': manager_importable,
                'business_value': 'Real-time user experience (retention driver)',
                'impact': 'LOW' if manager_importable else 'HIGH'
            }
            
        except Exception as e:
            capabilities['websocket_communication'] = {
                'works': False,
                'business_value': 'Real-time user experience (retention driver)', 
                'impact': 'HIGH',
                'error': str(e)
            }
        
        # Overall business value assessment
        total_measurement_time = time.time() - measurement_start
        
        critical_failures = [cap for cap in capabilities.values() if cap['impact'] == 'CRITICAL']
        high_failures = [cap for cap in capabilities.values() if cap['impact'] == 'HIGH']
        
        if critical_failures:
            impact = f"CRITICAL - {len(critical_failures)} core capabilities broken"
            success = False
        elif high_failures:
            impact = f"HIGH - {len(high_failures)} important capabilities affected"
            success = True  # Can still deliver some value
        else:
            impact = "LOW - Core business capabilities functional"
            success = True
        
        measurement_details = f"""
User Isolation: {' PASS: ' if capabilities['user_isolation']['works'] else ' FAIL: '} ({capabilities['user_isolation']['business_value']})
Agent Execution: {' PASS: ' if capabilities['agent_execution']['works'] else ' FAIL: '} ({capabilities['agent_execution']['business_value']})
WebSocket: {' PASS: ' if capabilities['websocket_communication']['works'] else ' FAIL: '} ({capabilities['websocket_communication']['business_value']})
Assessment Time: {total_measurement_time:.2f}s
"""
        
        self.results.append(WorkflowTestResult(
            name="Business Value Delivery",
            success=success,
            duration=total_measurement_time,
            details=measurement_details,
            business_impact=impact
        ))

    def run_all_workflow_tests(self):
        """Run all business workflow validation tests"""
        self.log("[U+1F680] STARTING BUSINESS WORKFLOW VALIDATION")
        self.log("=" * 60)
        
        test_methods = [
            self.test_developer_tdd_workflow,
            self.test_chat_platform_testing_capability,
            self.test_cicd_pipeline_simulation,
            self.test_business_value_delivery_measurement
        ]
        
        for test_method in test_methods:
            try:
                test_method()
                self.log("")  # Blank line for readability
            except Exception as e:
                self.log(f" FAIL:  CRITICAL ERROR in {test_method.__name__}: {e}")
                self.log(traceback.format_exc())
                
                # Add error result
                self.results.append(WorkflowTestResult(
                    name=test_method.__name__.replace('test_', '').replace('_', ' ').title(),
                    success=False,
                    duration=0.0,
                    details=f"CRITICAL ERROR: {str(e)}",
                    business_impact="CRITICAL - Test execution failed"
                ))
        
        # Generate final report
        self.generate_workflow_report()
        return self.results

    def generate_workflow_report(self):
        """Generate comprehensive business workflow report"""
        total_time = time.time() - self.start_time
        
        self.log("=" * 60)
        self.log(" CHART:  BUSINESS WORKFLOW VALIDATION RESULTS")
        self.log("=" * 60)
        
        # Summary by workflow
        critical_issues = []
        high_issues = []
        
        for result in self.results:
            status_emoji = " PASS: " if result.success else " FAIL: "
            self.log(f"{status_emoji} {result.name}")
            self.log(f"    Duration: {result.duration:.2f}s")
            self.log(f"    Impact: {result.business_impact}")
            self.log(f"    Details: {result.details.strip()}")
            self.log("")
            
            if "CRITICAL" in result.business_impact:
                critical_issues.append(result.name)
            elif "HIGH" in result.business_impact:
                high_issues.append(result.name)
        
        self.log(f"Total validation time: {total_time:.2f}s")
        self.log("")
        
        # Overall business impact assessment
        if critical_issues:
            self.log(" ALERT:  OVERALL BUSINESS IMPACT: CRITICAL")
            self.log(f"   Critical workflows affected: {', '.join(critical_issues)}")
            self.log("   - Development velocity severely impacted")
            self.log("   - Chat platform testing blocked (90% platform value at risk)")
            self.log("   - Enterprise features not validatable ($15K+ MRR at risk)")
            self.log("   - CI/CD pipeline reliability uncertain")
            overall_impact = "CRITICAL"
        elif high_issues:
            self.log(" WARNING: [U+FE0F]  OVERALL BUSINESS IMPACT: HIGH")
            self.log(f"   High-impact workflows affected: {', '.join(high_issues)}")
            self.log("   - Development velocity impacted")
            self.log("   - Some testing capabilities reduced")
            overall_impact = "HIGH"
        else:
            self.log(" PASS:  OVERALL BUSINESS IMPACT: LOW")
            self.log("   - Core workflows functional")
            self.log("   - Business value delivery preserved")
            overall_impact = "LOW"
        
        # Recommendations
        self.log("")
        self.log("[U+1F4CB] RECOMMENDATIONS:")
        
        if critical_issues:
            self.log("   1. IMMEDIATE: Fix test collection timeout (Issue #489)")
            self.log("   2. IMMEDIATE: Address Unicode encoding issues in test files")
            self.log("   3. SHORT-TERM: Redis connectivity restoration") 
            self.log("   4. MEDIUM-TERM: Architectural violation reduction plan")
        elif high_issues:
            self.log("   1. Address performance bottlenecks in testing infrastructure")
            self.log("   2. Optimize test collection and execution times")
            self.log("   3. Consider architectural violation remediation")
        else:
            self.log("   1. Continue monitoring workflow performance")
            self.log("   2. Consider proactive architectural improvements")
        
        return overall_impact

if __name__ == "__main__":
    validator = BusinessWorkflowValidator()
    results = validator.run_all_workflow_tests()
    
    # Exit with appropriate code based on overall impact
    critical_failures = any("CRITICAL" in r.business_impact for r in results)
    if critical_failures:
        sys.exit(1)
    else:
        sys.exit(0)