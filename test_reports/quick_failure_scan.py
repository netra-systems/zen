#!/usr/bin/env python
"""
Quick Failure Scanner - Get actual failing tests from the codebase
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class QuickFailureScanner:
    """Quick scanner to identify failing tests"""
    
    def __init__(self):
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        self.backend_failures = []
        self.frontend_failures = []
        
    def scan_backend_tests(self) -> List[Dict]:
        """Quick scan of backend test failures"""
        print("Scanning backend tests...")
        failures = []
        
        try:
            # Run pytest with minimal output to get failures quickly
            cmd = [
                sys.executable, "-m", "pytest", 
                "--tb=no",  # No traceback
                "-q",       # Quiet
                "--no-header",
                "-x",       # Stop on first failure
                "--maxfail=200"  # Stop after 200 failures
            ]
            
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT / "app",
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8',
                errors='replace'
            )
            
            # Extract failure information
            lines = result.stdout.split('\n') + result.stderr.split('\n')
            
            for line in lines:
                if 'FAILED' in line:
                    # Parse failure line
                    match = re.match(r'FAILED\s+([^\s]+)::([^\s\[]+)(?:\[([^\]]+)\])?\s*-\s*(.+)', line)
                    if match:
                        test_file, test_name, params, error = match.groups()
                        failures.append({
                            "file": test_file,
                            "test": test_name,
                            "params": params,
                            "error": error[:200],  # Limit error message length
                            "full_path": f"{test_file}::{test_name}"
                        })
                elif 'ERROR' in line and '::' in line:
                    match = re.match(r'ERROR\s+([^\s]+)(?:::([^\s]+))?\s*-\s*(.+)', line)
                    if match:
                        test_file, test_name, error = match.groups()
                        failures.append({
                            "file": test_file,
                            "test": test_name or "setup/teardown",
                            "params": None,
                            "error": error[:200],
                            "full_path": f"{test_file}::{test_name or 'setup'}"
                        })
            
            # Also check summary line
            summary_match = re.search(r'(\d+) failed', result.stdout)
            if summary_match:
                print(f"  Found {summary_match.group(1)} failed backend tests")
            
        except subprocess.TimeoutExpired:
            print("  Backend scan timed out")
        except Exception as e:
            print(f"  Error scanning backend: {e}")
        
        return failures[:200]  # Limit to 200 failures
    
    def scan_frontend_tests(self) -> List[Dict]:
        """Quick scan of frontend test failures"""
        print("Scanning frontend tests...")
        failures = []
        
        try:
            # Run Jest with minimal reporter
            cmd = [
                "npm", "test", "--",
                "--no-coverage",
                "--silent",
                "--json",
                "--outputFile=quick-test-results.json"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT / "frontend",
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse JSON results
            results_file = PROJECT_ROOT / "frontend" / "quick-test-results.json"
            if results_file.exists():
                try:
                    with open(results_file, 'r', encoding='utf-8') as f:
                        test_results = json.load(f)
                    
                    for suite in test_results.get("testResults", []):
                        suite_name = Path(suite["name"]).relative_to(PROJECT_ROOT / "frontend")
                        
                        for assertion in suite.get("assertionResults", []):
                            if assertion["status"] == "failed":
                                failures.append({
                                    "file": str(suite_name),
                                    "test": assertion["title"],
                                    "ancestors": " > ".join(assertion.get("ancestorTitles", [])),
                                    "error": (assertion.get("failureMessages", ["Unknown error"])[0])[:200],
                                    "full_path": f"{suite_name}::{assertion['title']}"
                                })
                    
                    # Clean up
                    results_file.unlink()
                    
                    print(f"  Found {len(failures)} failed frontend tests")
                    
                except Exception as e:
                    print(f"  Error parsing frontend results: {e}")
            
        except subprocess.TimeoutExpired:
            print("  Frontend scan timed out")
        except FileNotFoundError:
            print("  npm not found - skipping frontend tests")
        except Exception as e:
            print(f"  Error scanning frontend: {e}")
        
        return failures[:200]  # Limit to 200 failures
    
    def categorize_failure(self, failure: Dict, component: str) -> str:
        """Categorize a failure based on file and error"""
        file_lower = failure["file"].lower()
        error_lower = failure["error"].lower()
        
        # Import/Module errors - highest priority
        if "import" in error_lower or "modulenotfound" in error_lower or "no module named" in error_lower:
            return "import_error"
        
        # Type/Attribute errors - high priority
        if "typeerror" in error_lower or "attributeerror" in error_lower:
            return "type_error"
        
        # Validation errors
        if "validation" in error_lower or "pydantic" in error_lower:
            return "validation"
        
        # Based on file path
        if "database" in file_lower or "repository" in file_lower:
            return "database"
        elif "agent" in file_lower:
            return "agent"
        elif "websocket" in file_lower or "ws_" in file_lower:
            return "websocket"
        elif "auth" in file_lower or "security" in file_lower:
            return "auth"
        elif "service" in file_lower:
            return "service"
        elif "route" in file_lower or "api" in file_lower:
            return "api"
        elif "llm" in file_lower:
            return "llm"
        elif component == "frontend":
            if "component" in file_lower:
                return "component"
            elif "hook" in file_lower:
                return "hook"
            elif "store" in file_lower:
                return "store"
        
        return "other"
    
    def prioritize_failures(self, failures: List[Dict], component: str) -> List[Dict]:
        """Prioritize failures for fixing"""
        for failure in failures:
            failure["component"] = component
            failure["category"] = self.categorize_failure(failure, component)
            
            # Assign priority score
            priority = 0
            
            # Category-based priority
            category_priority = {
                "import_error": 100,
                "type_error": 80,
                "validation": 70,
                "database": 60,
                "auth": 60,
                "service": 50,
                "api": 40,
                "agent": 40,
                "websocket": 30,
                "llm": 30,
                "component": 20,
                "hook": 20,
                "store": 20,
                "other": 10
            }
            priority += category_priority.get(failure["category"], 10)
            
            # Boost for certain error types
            if "cannot import" in failure["error"].lower():
                priority += 50
            elif "fixture" in failure["error"].lower():
                priority += 30
            elif "not found" in failure["error"].lower():
                priority += 20
            
            failure["priority"] = priority
        
        # Sort by priority
        failures.sort(key=lambda x: x["priority"], reverse=True)
        return failures
    
    def scan_all_tests(self):
        """Scan all tests and generate report"""
        print("\n" + "="*60)
        print("QUICK FAILURE SCAN")
        print("="*60)
        
        # Scan backend
        self.backend_failures = self.scan_backend_tests()
        
        # Scan frontend
        self.frontend_failures = self.scan_frontend_tests()
        
        # Prioritize failures
        self.backend_failures = self.prioritize_failures(self.backend_failures, "backend")
        self.frontend_failures = self.prioritize_failures(self.frontend_failures, "frontend")
        
        # Combine and get top 200
        all_failures = self.backend_failures + self.frontend_failures
        all_failures.sort(key=lambda x: x["priority"], reverse=True)
        top_200 = all_failures[:200]
        
        # Print summary
        print("\n" + "="*60)
        print("SCAN RESULTS")
        print("="*60)
        print(f"Backend failures: {len(self.backend_failures)}")
        print(f"Frontend failures: {len(self.frontend_failures)}")
        print(f"Total failures: {len(all_failures)}")
        
        # Count by category
        category_counts = {}
        for failure in all_failures:
            cat = failure["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        print("\nFailures by category:")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}")
        
        # Save results
        self.save_results(top_200)
        
        return top_200
    
    def save_results(self, top_failures: List[Dict]):
        """Save scan results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_file = self.reports_dir / f"quick_scan_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "backend_failures": len(self.backend_failures),
                "frontend_failures": len(self.frontend_failures),
                "top_200_failures": top_failures
            }, f, indent=2)
        print(f"\nResults saved to: {json_file}")
        
        # Save markdown report
        md_file = self.reports_dir / f"quick_scan_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# Quick Test Failure Scan\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"- Backend failures: {len(self.backend_failures)}\n")
            f.write(f"- Frontend failures: {len(self.frontend_failures)}\n")
            f.write(f"- Total: {len(self.backend_failures) + len(self.frontend_failures)}\n\n")
            
            f.write("## Top 200 Failures (Prioritized)\n\n")
            
            current_category = None
            for i, failure in enumerate(top_failures, 1):
                if failure["category"] != current_category:
                    current_category = failure["category"]
                    f.write(f"\n### {current_category.replace('_', ' ').title()}\n\n")
                
                f.write(f"{i}. **[{failure['component']}]** `{failure['file']}`\n")
                f.write(f"   - Test: `{failure['test']}`\n")
                f.write(f"   - Error: {failure['error']}\n")
                f.write(f"   - Priority: {failure['priority']}\n\n")
        
        print(f"Markdown report saved to: {md_file}")

def main():
    scanner = QuickFailureScanner()
    top_failures = scanner.scan_all_tests()
    
    # Save for batch processing
    with open(PROJECT_ROOT / "test_reports" / "failures_to_fix.json", 'w', encoding='utf-8') as f:
        json.dump(top_failures, f, indent=2)
    
    print(f"\nTop {len(top_failures)} failures saved for processing")

if __name__ == "__main__":
    main()