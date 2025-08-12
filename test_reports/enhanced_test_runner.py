#!/usr/bin/env python
"""
Enhanced Test Runner with Advanced Failure Analysis and Batch Processing
Designed for systematic test fixing and parallel execution optimization
"""

import os
import sys
import json
import time
import re
import asyncio
import subprocess
import multiprocessing
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import threading
import queue

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Determine optimal parallelization based on test type
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = {
    "unit": min(CPU_COUNT - 1, 6),
    "integration": min(CPU_COUNT // 2, 4),
    "e2e": 2,  # E2E tests need more resources
    "smoke": CPU_COUNT,  # Smoke tests are light
    "comprehensive": min(CPU_COUNT - 2, 8)
}

@dataclass
class TestFailure:
    """Represents a single test failure with metadata"""
    test_name: str
    test_path: str
    error_type: str
    error_message: str
    category: str
    priority: int  # 1-5, 1 being highest
    component: str  # backend/frontend
    fix_strategy: str = ""
    dependencies: List[str] = field(default_factory=list)
    estimated_fix_time: int = 15  # minutes
    
@dataclass
class TestBatch:
    """Represents a batch of tests to be fixed together"""
    batch_id: int
    failures: List[TestFailure]
    total_tests: int
    category: str
    estimated_time: int  # minutes
    parallel_safe: bool = True

class EnhancedTestRunner:
    """Advanced test runner with failure analysis and batch processing"""
    
    def __init__(self):
        self.cpu_count = CPU_COUNT
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Failure tracking
        self.all_failures: List[TestFailure] = []
        self.failure_patterns: Dict[str, int] = Counter()
        self.fixed_tests: Set[str] = set()
        self.regression_tests: Set[str] = set()
        
        # Test organization
        self.test_categories = {
            "backend": {
                "unit": [],
                "integration": [],
                "agent": [],
                "websocket": [],
                "auth": [],
                "database": [],
                "service": [],
                "route": [],
                "llm": [],
                "core": []
            },
            "frontend": {
                "component": [],
                "integration": [],
                "e2e": [],
                "service": [],
                "store": [],
                "auth": [],
                "websocket": [],
                "import": [],
                "hook": []
            }
        }
        
        # Test runner state
        self.current_batch: Optional[TestBatch] = None
        self.batch_history: List[TestBatch] = []
        self.total_batches_processed = 0
        
    def categorize_test(self, test_path: str, test_name: str = "") -> Tuple[str, str]:
        """Categorize test based on path and name"""
        path_lower = test_path.lower()
        name_lower = test_name.lower()
        
        # Determine component
        component = "backend" if "app/" in path_lower or "backend" in path_lower else "frontend"
        
        # Determine category
        if component == "backend":
            if "agent" in path_lower:
                return component, "agent"
            elif "websocket" in path_lower or "ws_" in path_lower:
                return component, "websocket"
            elif "auth" in path_lower or "security" in path_lower:
                return component, "auth"
            elif "database" in path_lower or "repository" in path_lower:
                return component, "database"
            elif "service" in path_lower:
                return component, "service"
            elif "route" in path_lower or "api" in path_lower:
                return component, "route"
            elif "llm" in path_lower:
                return component, "llm"
            elif "core" in path_lower:
                return component, "core"
            elif "integration" in path_lower:
                return component, "integration"
            else:
                return component, "unit"
        else:  # frontend
            if "import" in name_lower or "import" in path_lower:
                return component, "import"
            elif "e2e" in path_lower or "cypress" in path_lower:
                return component, "e2e"
            elif "integration" in path_lower:
                return component, "integration"
            elif "component" in path_lower:
                return component, "component"
            elif "hook" in path_lower:
                return component, "hook"
            elif "service" in path_lower:
                return component, "service"
            elif "store" in path_lower:
                return component, "store"
            elif "auth" in path_lower:
                return component, "auth"
            elif "websocket" in path_lower or "ws" in path_lower:
                return component, "websocket"
            else:
                return component, "component"
    
    def parse_test_output(self, output: str, component: str = "backend") -> List[TestFailure]:
        """Parse test output to extract failures with detailed information"""
        failures = []
        
        if component == "backend":
            # Parse pytest output
            failure_pattern = r"FAILED (.*?)::(.*?) - (.*?)$"
            for match in re.finditer(failure_pattern, output, re.MULTILINE):
                test_path = match.group(1)
                test_name = match.group(2)
                error_msg = match.group(3)
                
                # Extract error type
                error_type = "Unknown"
                if "AssertionError" in error_msg:
                    error_type = "AssertionError"
                elif "AttributeError" in error_msg:
                    error_type = "AttributeError"
                elif "TypeError" in error_msg:
                    error_type = "TypeError"
                elif "ImportError" in error_msg or "ModuleNotFoundError" in error_msg:
                    error_type = "ImportError"
                elif "TimeoutError" in error_msg or "timeout" in error_msg.lower():
                    error_type = "TimeoutError"
                
                # Determine priority
                priority = self.calculate_priority(test_path, test_name, error_type)
                
                # Determine category
                _, category = self.categorize_test(test_path, test_name)
                
                # Suggest fix strategy
                fix_strategy = self.suggest_fix_strategy(error_type, error_msg, test_path)
                
                failure = TestFailure(
                    test_name=test_name,
                    test_path=test_path,
                    error_type=error_type,
                    error_message=error_msg[:500],  # Truncate long messages
                    category=category,
                    priority=priority,
                    component=component,
                    fix_strategy=fix_strategy
                )
                failures.append(failure)
                
        else:  # frontend
            # Parse Jest/React test output
            failure_pattern = r"● (.*?)$"
            current_file = None
            
            for line in output.split('\n'):
                # Track current test file
                if "FAIL" in line:
                    match = re.search(r"FAIL\s+(.*?)$", line)
                    if match:
                        current_file = match.group(1)
                
                # Extract test failures
                match = re.match(failure_pattern, line)
                if match and current_file:
                    test_name = match.group(1)
                    
                    # Look for error details in next lines
                    error_type = "TestFailure"
                    error_msg = test_name
                    
                    # Common frontend error patterns
                    if "Cannot find module" in output:
                        error_type = "ImportError"
                    elif "useRouter" in output or "navigation" in output.lower():
                        error_type = "RouterError"
                    elif "WebSocket" in output:
                        error_type = "WebSocketError"
                    elif "Provider" in output:
                        error_type = "ContextError"
                    
                    _, category = self.categorize_test(current_file, test_name)
                    priority = self.calculate_priority(current_file, test_name, error_type)
                    fix_strategy = self.suggest_fix_strategy(error_type, error_msg, current_file)
                    
                    failure = TestFailure(
                        test_name=test_name,
                        test_path=current_file or "unknown",
                        error_type=error_type,
                        error_message=error_msg[:500],
                        category=category,
                        priority=priority,
                        component=component,
                        fix_strategy=fix_strategy
                    )
                    failures.append(failure)
        
        return failures
    
    def calculate_priority(self, test_path: str, test_name: str, error_type: str) -> int:
        """Calculate priority of fixing a test (1=highest, 5=lowest)"""
        priority = 3  # Default medium priority
        
        # Critical path tests
        if "critical" in test_path.lower() or "critical" in test_name.lower():
            priority = 1
        elif "core" in test_path.lower() or "auth" in test_path.lower():
            priority = 1
        # Import/setup failures block other tests
        elif error_type in ["ImportError", "ModuleNotFoundError"]:
            priority = 1
        # Integration tests
        elif "integration" in test_path.lower():
            priority = 2
        # Agent tests (business logic)
        elif "agent" in test_path.lower():
            priority = 2
        # WebSocket tests (real-time features)
        elif "websocket" in test_path.lower():
            priority = 2
        # Timeout issues (might be environment-specific)
        elif error_type == "TimeoutError":
            priority = 4
        # E2E tests (can be flaky)
        elif "e2e" in test_path.lower():
            priority = 4
        
        return priority
    
    def suggest_fix_strategy(self, error_type: str, error_msg: str, test_path: str) -> str:
        """Suggest a fix strategy based on error type and context"""
        strategies = {
            "ImportError": "Check import paths and module exports. Verify dependencies are installed.",
            "AttributeError": "Check if class/object has the expected attribute. May need to update mocks.",
            "AssertionError": "Review assertion logic. Check if implementation changed or test expectations are outdated.",
            "TypeError": "Check function signatures and argument types. Verify mock return values.",
            "RouterError": "Add proper router mocking. Wrap component with Router context.",
            "WebSocketError": "Add WebSocket provider wrapper. Mock WebSocket connection properly.",
            "ContextError": "Wrap component with required context providers.",
            "TimeoutError": "Increase timeout or optimize async operations. Check for hanging promises."
        }
        
        # Specific patterns
        if "mock" in error_msg.lower():
            return "Update mock configuration to match actual implementation."
        elif "fixture" in error_msg.lower():
            return "Check fixture setup and dependencies."
        elif "database" in error_msg.lower():
            return "Ensure test database is properly configured and seeded."
        
        return strategies.get(error_type, "Analyze error and update test or implementation as needed.")
    
    def create_test_batches(self, failures: List[TestFailure], batch_size: int = 50) -> List[TestBatch]:
        """Create batches of tests grouped by similarity for efficient fixing"""
        batches = []
        
        # Group by component and category first
        grouped = defaultdict(list)
        for failure in failures:
            key = f"{failure.component}_{failure.category}_{failure.error_type}"
            grouped[key].append(failure)
        
        # Sort groups by priority
        sorted_groups = sorted(grouped.items(), key=lambda x: min(f.priority for f in x[1]))
        
        # Create batches
        batch_id = 1
        current_batch_failures = []
        
        for group_key, group_failures in sorted_groups:
            # Sort failures within group by priority
            group_failures.sort(key=lambda x: x.priority)
            
            for failure in group_failures:
                current_batch_failures.append(failure)
                
                if len(current_batch_failures) >= batch_size:
                    # Create batch
                    batch = TestBatch(
                        batch_id=batch_id,
                        failures=current_batch_failures[:],
                        total_tests=len(current_batch_failures),
                        category=group_key,
                        estimated_time=sum(f.estimated_fix_time for f in current_batch_failures),
                        parallel_safe=self.is_parallel_safe(current_batch_failures)
                    )
                    batches.append(batch)
                    batch_id += 1
                    current_batch_failures = []
        
        # Add remaining failures as final batch
        if current_batch_failures:
            batch = TestBatch(
                batch_id=batch_id,
                failures=current_batch_failures,
                total_tests=len(current_batch_failures),
                category="mixed",
                estimated_time=sum(f.estimated_fix_time for f in current_batch_failures),
                parallel_safe=self.is_parallel_safe(current_batch_failures)
            )
            batches.append(batch)
        
        return batches
    
    def is_parallel_safe(self, failures: List[TestFailure]) -> bool:
        """Determine if a batch of tests can be run in parallel"""
        # Don't parallelize if there are database or auth tests
        categories = {f.category for f in failures}
        unsafe_categories = {"database", "auth", "integration", "e2e"}
        
        return not bool(categories & unsafe_categories)
    
    def run_test_suite(self, level: str = "comprehensive", 
                      component: Optional[str] = None,
                      category: Optional[str] = None,
                      parallel: Optional[int] = None,
                      timeout: int = 600) -> Tuple[int, str, List[TestFailure]]:
        """Run test suite with specified parameters"""
        
        cmd = [sys.executable, "test_runner.py", "--level", level]
        
        if component:
            cmd.extend(["--component", component])
        if category:
            cmd.extend(["--category", category])
        if parallel:
            cmd.extend(["--parallel", str(parallel)])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            # Parse failures
            failures = self.parse_test_output(result.stdout + result.stderr, component or "backend")
            
            return result.returncode, result.stdout + result.stderr, failures
            
        except subprocess.TimeoutExpired:
            return -1, f"Tests timed out after {timeout}s", []
    
    def analyze_failure_patterns(self, failures: List[TestFailure]) -> Dict[str, any]:
        """Analyze patterns in test failures"""
        analysis = {
            "total_failures": len(failures),
            "by_component": Counter(f.component for f in failures),
            "by_category": Counter(f.category for f in failures),
            "by_error_type": Counter(f.error_type for f in failures),
            "by_priority": Counter(f.priority for f in failures),
            "common_patterns": [],
            "recommended_fixes": []
        }
        
        # Find common error patterns
        error_patterns = Counter(f.error_type for f in failures)
        for error_type, count in error_patterns.most_common(5):
            if count > 3:
                analysis["common_patterns"].append({
                    "pattern": error_type,
                    "count": count,
                    "percentage": f"{(count/len(failures)*100):.1f}%"
                })
        
        # Recommend batch fixes for common issues
        if error_patterns.get("ImportError", 0) > 5:
            analysis["recommended_fixes"].append(
                "Multiple import errors detected. Review module exports and update import statements."
            )
        if error_patterns.get("RouterError", 0) > 3:
            analysis["recommended_fixes"].append(
                "Router/navigation issues in frontend. Create standard router mock fixture."
            )
        if error_patterns.get("WebSocketError", 0) > 3:
            analysis["recommended_fixes"].append(
                "WebSocket issues detected. Create WebSocket test wrapper component."
            )
        
        return analysis
    
    def generate_batch_report(self, batch: TestBatch, fixed_count: int, output_path: Optional[Path] = None) -> str:
        """Generate report for a batch of test fixes"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# Test Batch Report - Batch #{batch.batch_id}
**Generated:** {timestamp}
**Category:** {batch.category}
**Total Tests:** {batch.total_tests}
**Fixed:** {fixed_count}
**Success Rate:** {(fixed_count/batch.total_tests*100):.1f}%
**Estimated Time:** {batch.estimated_time} minutes
**Parallel Safe:** {batch.parallel_safe}

## Test Failures in Batch

| Test Name | Path | Error Type | Priority | Fix Strategy |
|-----------|------|------------|----------|--------------|
"""
        
        for failure in batch.failures[:10]:  # Show first 10
            report += f"| {failure.test_name[:50]} | {failure.test_path.split('/')[-1]} | {failure.error_type} | P{failure.priority} | {failure.fix_strategy[:60]}... |\n"
        
        if len(batch.failures) > 10:
            report += f"\n*... and {len(batch.failures) - 10} more tests*\n"
        
        report += f"\n## Summary\n"
        report += f"- Batch processed successfully\n"
        report += f"- {fixed_count} tests fixed\n"
        report += f"- {batch.total_tests - fixed_count} tests still failing\n"
        
        if output_path:
            output_path.write_text(report)
        
        return report
    
    def run_continuous_fixing(self, max_batches: int = 10, batch_size: int = 50):
        """Run continuous test fixing process"""
        print(f"\n{'='*80}")
        print("STARTING CONTINUOUS TEST FIXING PROCESS")
        print(f"{'='*80}\n")
        
        # Step 1: Run comprehensive test to get all failures
        print("Step 1: Running comprehensive test suite to identify all failures...")
        exit_code, output, failures = self.run_test_suite("comprehensive", timeout=900)
        
        if not failures:
            print("No test failures found! All tests passing.")
            return
        
        print(f"Found {len(failures)} test failures")
        
        # Step 2: Analyze failure patterns
        print("\nStep 2: Analyzing failure patterns...")
        analysis = self.analyze_failure_patterns(failures)
        
        print(f"  - Backend failures: {analysis['by_component']['backend']}")
        print(f"  - Frontend failures: {analysis['by_component']['frontend']}")
        print(f"  - Priority 1 (Critical): {analysis['by_priority'][1]}")
        print(f"  - Priority 2 (High): {analysis['by_priority'][2]}")
        
        # Step 3: Create test batches
        print(f"\nStep 3: Creating test batches (size={batch_size})...")
        batches = self.create_test_batches(failures, batch_size)
        print(f"Created {len(batches)} batches")
        
        # Step 4: Process batches
        print(f"\nStep 4: Processing batches (max={max_batches})...")
        
        for i, batch in enumerate(batches[:max_batches]):
            print(f"\n{'='*60}")
            print(f"PROCESSING BATCH #{batch.batch_id} ({i+1}/{min(len(batches), max_batches)})")
            print(f"{'='*60}")
            print(f"  - Tests: {batch.total_tests}")
            print(f"  - Category: {batch.category}")
            print(f"  - Estimated time: {batch.estimated_time} minutes")
            
            # This is where actual fixing would happen
            # For now, we'll generate a report
            self.current_batch = batch
            self.total_batches_processed += 1
            
            # Generate batch report
            report_path = self.reports_dir / f"batch_{batch.batch_id}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            report = self.generate_batch_report(batch, 0, report_path)
            
            print(f"  - Report saved to: {report_path}")
            
            # Add to history
            self.batch_history.append(batch)
            
            # Run tests for this batch's component/category
            component = batch.failures[0].component if batch.failures else "backend"
            category = batch.failures[0].category if batch.failures else None
            
            print(f"\n  Running tests for {component}/{category}...")
            exit_code, output, new_failures = self.run_test_suite(
                "unit",
                component=component,
                category=category,
                parallel=4 if batch.parallel_safe else 1,
                timeout=300
            )
            
            if exit_code == 0:
                print(f"  ✓ All tests in batch passing!")
            else:
                print(f"  ✗ {len(new_failures)} tests still failing")
        
        # Step 5: Generate final report
        print(f"\n{'='*80}")
        print("GENERATING FINAL REPORT")
        print(f"{'='*80}")
        
        self.generate_final_report()

    def generate_final_report(self):
        """Generate comprehensive final report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"continuous_fix_report_{timestamp}.md"
        
        report = f"""# Continuous Test Fixing Report
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Batches Processed:** {self.total_batches_processed}
**Total Failures Analyzed:** {len(self.all_failures)}

## Summary by Component
- Backend: {sum(1 for f in self.all_failures if f.component == 'backend')}
- Frontend: {sum(1 for f in self.all_failures if f.component == 'frontend')}

## Common Failure Patterns
"""
        
        for pattern, count in self.failure_patterns.most_common(10):
            report += f"- {pattern}: {count} occurrences\n"
        
        report += f"\n## Batch Processing History\n"
        for batch in self.batch_history[:10]:
            report += f"- Batch #{batch.batch_id}: {batch.total_tests} tests, {batch.category}\n"
        
        report_path.write_text(report)
        print(f"Final report saved to: {report_path}")
        
        return report


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Test Runner with Batch Processing")
    parser.add_argument("--max-batches", type=int, default=10, help="Maximum number of batches to process")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of tests per batch")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze failures, don't fix")
    
    args = parser.parse_args()
    
    runner = EnhancedTestRunner()
    
    if args.analyze_only:
        # Just analyze current failures
        print("Running analysis only...")
        exit_code, output, failures = runner.run_test_suite("comprehensive", timeout=900)
        analysis = runner.analyze_failure_patterns(failures)
        
        print(f"\nAnalysis Results:")
        print(f"  Total failures: {analysis['total_failures']}")
        print(f"  By component: {dict(analysis['by_component'])}")
        print(f"  By category: {dict(analysis['by_category'])}")
        print(f"  By error type: {dict(analysis['by_error_type'])}")
        
        if analysis['recommended_fixes']:
            print(f"\nRecommended Fixes:")
            for fix in analysis['recommended_fixes']:
                print(f"  - {fix}")
    else:
        # Run continuous fixing
        runner.run_continuous_fixing(
            max_batches=args.max_batches,
            batch_size=args.batch_size
        )


if __name__ == "__main__":
    main()