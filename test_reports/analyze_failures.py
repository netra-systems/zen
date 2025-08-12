#!/usr/bin/env python
"""
Test Failure Analysis Script
Analyzes test failures and categorizes them for systematic fixing
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class TestFailureAnalyzer:
    """Analyzes test failures and categorizes them for systematic fixing"""
    
    def __init__(self):
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.analysis_dir = self.reports_dir / "analysis"
        self.analysis_dir.mkdir(exist_ok=True)
        
        self.failures = {
            "backend": [],
            "frontend": [],
            "summary": {
                "total_failures": 0,
                "by_category": {},
                "by_error_type": {},
                "by_file": {}
            }
        }
        
    def run_backend_discovery(self) -> List[Dict]:
        """Discover all backend tests and their status"""
        print("Discovering backend tests...")
        failures = []
        
        try:
            # Run pytest with collect-only to get all tests
            cmd = [sys.executable, "-m", "pytest", "--co", "-q", "--tb=no"]
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT / "app",
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Now run actual tests with minimal output
            cmd = [sys.executable, "-m", "pytest", "--tb=short", "-q", "--no-header"]
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT / "app",
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse failures
            lines = result.stdout.split('\n')
            for line in lines:
                if 'FAILED' in line or 'ERROR' in line:
                    match = re.match(r'(FAILED|ERROR)\s+([^:]+)::([^\s\[]+)(?:\[([^\]]+)\])?\s*-\s*(.+)', line)
                    if match:
                        status, test_file, test_name, params, error = match.groups()
                        
                        # Categorize the error
                        category = self._categorize_error(error, test_file)
                        
                        failures.append({
                            "file": test_file,
                            "test": test_name,
                            "params": params,
                            "error": error,
                            "category": category,
                            "error_type": self._extract_error_type(error),
                            "status": status
                        })
            
            print(f"Found {len(failures)} backend test failures")
            
        except subprocess.TimeoutExpired:
            print("Backend test discovery timed out")
        except Exception as e:
            print(f"Error during backend discovery: {e}")
            
        return failures
    
    def run_frontend_discovery(self) -> List[Dict]:
        """Discover all frontend tests and their status"""
        print("Discovering frontend tests...")
        failures = []
        
        try:
            # Run Jest tests with json reporter
            cmd = ["npm", "test", "--", "--listTests", "--json"]
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT / "frontend",
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Run actual tests
            cmd = ["npm", "test", "--", "--no-coverage", "--json", "--outputFile=test-results.json"]
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT / "frontend",
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse test results if json file exists
            results_file = PROJECT_ROOT / "frontend" / "test-results.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    test_results = json.load(f)
                    
                for test_suite in test_results.get("testResults", []):
                    for assertion in test_suite.get("assertionResults", []):
                        if assertion["status"] == "failed":
                            test_file = Path(test_suite["name"]).relative_to(PROJECT_ROOT / "frontend")
                            
                            failures.append({
                                "file": str(test_file),
                                "test": assertion["title"],
                                "ancestor": assertion.get("ancestorTitles", []),
                                "error": assertion.get("failureMessages", ["Unknown error"])[0][:500],
                                "category": self._categorize_frontend_test(str(test_file), assertion["title"]),
                                "error_type": self._extract_frontend_error_type(assertion.get("failureMessages", [""])[0]),
                                "status": "FAILED"
                            })
                
                # Clean up
                results_file.unlink()
            
            print(f"Found {len(failures)} frontend test failures")
            
        except subprocess.TimeoutExpired:
            print("Frontend test discovery timed out")
        except Exception as e:
            print(f"Error during frontend discovery: {e}")
            
        return failures
    
    def _categorize_error(self, error: str, test_file: str) -> str:
        """Categorize error based on error message and test file"""
        error_lower = error.lower()
        file_lower = test_file.lower()
        
        # Import errors
        if "import" in error_lower or "modulenotfound" in error_lower:
            return "import_error"
        
        # Database/Model errors
        if "database" in file_lower or "repository" in file_lower or "model" in file_lower:
            return "database"
        
        # WebSocket errors
        if "websocket" in file_lower or "ws_" in file_lower:
            return "websocket"
        
        # Agent errors
        if "agent" in file_lower:
            return "agent"
        
        # LLM errors
        if "llm" in file_lower:
            return "llm"
        
        # API/Route errors
        if "route" in file_lower or "api" in file_lower:
            return "api"
        
        # Service errors
        if "service" in file_lower:
            return "service"
        
        # Auth errors
        if "auth" in file_lower or "security" in file_lower:
            return "auth"
        
        # Validation errors
        if "validation" in error_lower or "pydantic" in error_lower:
            return "validation"
        
        # Type errors
        if "typeerror" in error_lower or "attributeerror" in error_lower:
            return "type_error"
        
        # Timeout errors
        if "timeout" in error_lower:
            return "timeout"
        
        return "other"
    
    def _categorize_frontend_test(self, test_file: str, test_name: str) -> str:
        """Categorize frontend test based on file and name"""
        file_lower = test_file.lower()
        name_lower = test_name.lower()
        
        if "component" in file_lower:
            return "component"
        elif "hook" in file_lower:
            return "hook"
        elif "service" in file_lower or "api" in file_lower:
            return "service"
        elif "store" in file_lower:
            return "store"
        elif "auth" in file_lower:
            return "auth"
        elif "websocket" in name_lower or "ws" in file_lower:
            return "websocket"
        elif "util" in file_lower:
            return "utility"
        else:
            return "other"
    
    def _extract_error_type(self, error: str) -> str:
        """Extract error type from error message"""
        # Common Python error types
        error_types = [
            "AssertionError", "AttributeError", "ImportError", "ModuleNotFoundError",
            "TypeError", "ValueError", "KeyError", "IndexError", "NameError",
            "ValidationError", "TimeoutError", "ConnectionError", "RuntimeError"
        ]
        
        for error_type in error_types:
            if error_type in error:
                return error_type
        
        return "UnknownError"
    
    def _extract_frontend_error_type(self, error: str) -> str:
        """Extract error type from frontend error message"""
        if "expect(" in error:
            return "AssertionError"
        elif "Cannot read" in error or "undefined" in error:
            return "TypeError"
        elif "not found" in error.lower():
            return "NotFoundError"
        elif "timeout" in error.lower():
            return "TimeoutError"
        else:
            return "TestError"
    
    def analyze_failures(self):
        """Analyze all test failures"""
        print("\n" + "="*60)
        print("ANALYZING TEST FAILURES")
        print("="*60)
        
        # Discover backend failures
        backend_failures = self.run_backend_discovery()
        self.failures["backend"] = backend_failures
        
        # Discover frontend failures
        frontend_failures = self.run_frontend_discovery()
        self.failures["frontend"] = frontend_failures
        
        # Calculate summary statistics
        total_failures = len(backend_failures) + len(frontend_failures)
        self.failures["summary"]["total_failures"] = total_failures
        
        # Count by category
        category_counts = defaultdict(int)
        for failure in backend_failures + frontend_failures:
            category_counts[failure["category"]] += 1
        self.failures["summary"]["by_category"] = dict(category_counts)
        
        # Count by error type
        error_type_counts = defaultdict(int)
        for failure in backend_failures + frontend_failures:
            error_type_counts[failure["error_type"]] += 1
        self.failures["summary"]["by_error_type"] = dict(error_type_counts)
        
        # Count by file
        file_counts = defaultdict(int)
        for failure in backend_failures + frontend_failures:
            file_counts[failure["file"]] += 1
        
        # Get top 10 files with most failures
        top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        self.failures["summary"]["by_file"] = dict(top_files)
        
        # Print summary
        print(f"\nTotal Failures: {total_failures}")
        print(f"  Backend: {len(backend_failures)}")
        print(f"  Frontend: {len(frontend_failures)}")
        
        print("\nFailures by Category:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")
        
        print("\nFailures by Error Type:")
        for error_type, count in sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {error_type}: {count}")
        
        print("\nTop Files with Failures:")
        for file, count in top_files:
            print(f"  {file}: {count}")
    
    def prioritize_failures(self) -> List[Dict]:
        """Prioritize failures for fixing based on impact and dependencies"""
        all_failures = []
        
        # Add priority score to each failure
        for failure in self.failures["backend"]:
            failure["component"] = "backend"
            failure["priority"] = self._calculate_priority(failure)
            all_failures.append(failure)
        
        for failure in self.failures["frontend"]:
            failure["component"] = "frontend"
            failure["priority"] = self._calculate_priority(failure)
            all_failures.append(failure)
        
        # Sort by priority (higher is more important)
        all_failures.sort(key=lambda x: x["priority"], reverse=True)
        
        return all_failures
    
    def _calculate_priority(self, failure: Dict) -> int:
        """Calculate priority score for a failure"""
        priority = 0
        
        # Import errors are highest priority
        if failure["category"] == "import_error":
            priority += 100
        
        # Type errors and validation errors are high priority
        elif failure["category"] in ["type_error", "validation"]:
            priority += 80
        
        # Database and service errors are medium-high priority
        elif failure["category"] in ["database", "service"]:
            priority += 60
        
        # API and auth errors are medium priority
        elif failure["category"] in ["api", "auth"]:
            priority += 40
        
        # Component and hook errors are lower priority
        elif failure["category"] in ["component", "hook"]:
            priority += 20
        
        # Boost priority for certain error types
        if failure["error_type"] in ["ImportError", "ModuleNotFoundError"]:
            priority += 50
        elif failure["error_type"] in ["TypeError", "AttributeError"]:
            priority += 30
        
        # Boost priority for tests in critical paths
        if "auth" in failure["file"].lower() or "security" in failure["file"].lower():
            priority += 25
        elif "database" in failure["file"].lower() or "repository" in failure["file"].lower():
            priority += 20
        
        return priority
    
    def save_analysis(self):
        """Save analysis results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full analysis
        analysis_file = self.analysis_dir / f"failure_analysis_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(self.failures, f, indent=2)
        print(f"\nAnalysis saved to: {analysis_file}")
        
        # Save prioritized list
        prioritized = self.prioritize_failures()
        priority_file = self.analysis_dir / f"prioritized_failures_{timestamp}.json"
        with open(priority_file, 'w') as f:
            json.dump(prioritized[:200], f, indent=2)  # Top 200 failures
        print(f"Prioritized list saved to: {priority_file}")
        
        # Save markdown report
        self.generate_markdown_report(prioritized[:200], timestamp)
    
    def generate_markdown_report(self, prioritized: List[Dict], timestamp: str):
        """Generate markdown report of failures"""
        report_file = self.analysis_dir / f"failure_report_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Test Failure Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Failures:** {self.failures['summary']['total_failures']}\n")
            f.write(f"- **Backend Failures:** {len(self.failures['backend'])}\n")
            f.write(f"- **Frontend Failures:** {len(self.failures['frontend'])}\n\n")
            
            f.write("## Failures by Category\n\n")
            for category, count in sorted(self.failures['summary']['by_category'].items(), 
                                         key=lambda x: x[1], reverse=True):
                f.write(f"- **{category}:** {count}\n")
            
            f.write("\n## Failures by Error Type\n\n")
            for error_type, count in sorted(self.failures['summary']['by_error_type'].items(),
                                           key=lambda x: x[1], reverse=True)[:10]:
                f.write(f"- **{error_type}:** {count}\n")
            
            f.write("\n## Top 200 Prioritized Failures\n\n")
            
            current_category = None
            for i, failure in enumerate(prioritized, 1):
                if failure["category"] != current_category:
                    current_category = failure["category"]
                    f.write(f"\n### {current_category.replace('_', ' ').title()}\n\n")
                
                f.write(f"{i}. **{failure['component']}/{failure['file']}**\n")
                f.write(f"   - Test: `{failure['test']}`\n")
                f.write(f"   - Error: {failure['error_type']} - {failure['error'][:100]}...\n")
                f.write(f"   - Priority: {failure['priority']}\n\n")
        
        print(f"Markdown report saved to: {report_file}")

def main():
    analyzer = TestFailureAnalyzer()
    analyzer.analyze_failures()
    analyzer.save_analysis()

if __name__ == "__main__":
    main()