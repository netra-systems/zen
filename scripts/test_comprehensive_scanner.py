#!/usr/bin/env python3
"""Comprehensive test scanner to find all failures."""

import json
import subprocess
import sys
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import re
from shared.isolated_environment import IsolatedEnvironment


class ComprehensiveTestScanner:
    """Scan all test categories and identify failures."""
    
    def __init__(self):
        self.report_dir = Path("test_failures")
        self.report_dir.mkdir(exist_ok=True)
        self.all_failures = []
        self.session_start = datetime.now()
        
    def extract_test_results_from_json(self, report_path: str) -> List[Dict]:
        """Extract test results from JSON report if available."""
        failures = []
        try:
            with open(report_path, 'r') as f:
                data = json.load(f)
                
            for category, info in data.get('categories', {}).items():
                if not info.get('success', True):
                    output = info.get('output', '')
                    
                    # Parse pytest output for failures
                    if 'FAILED' in output or 'ERROR' in output:
                        lines = output.split('\n')
                        for line in lines:
                            if 'FAILED' in line and '::' in line:
                                # Extract test path
                                match = re.search(r'([\w/\\\.]+::\S+)\s+FAILED', line)
                                if match:
                                    failures.append({
                                        'test': match.group(1),
                                        'type': 'FAILED',
                                        'category': category
                                    })
                            elif 'ERROR' in line and '::' in line:
                                match = re.search(r'([\w/\\\.]+::\S+)\s+ERROR', line)
                                if match:
                                    failures.append({
                                        'test': match.group(1),
                                        'type': 'ERROR',
                                        'category': category
                                    })
        except Exception as e:
            print(f"Error parsing JSON report: {e}")
            
        return failures
    
    def run_single_test(self, test_path: str) -> bool:
        """Run a single test to verify if it passes."""
        print(f"  Verifying: {test_path}")
        
        cmd = ["python", "-m", "pytest", test_path, "-xvs", "--tb=short"]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path.cwd()
            )
            success = result.returncode == 0
            print(f"    Result: {'PASS' if success else 'FAIL'}")
            return success
            
        except subprocess.TimeoutExpired:
            print(f"    Result: TIMEOUT")
            return False
        except Exception as e:
            print(f"    Result: ERROR - {e}")
            return False
    
    def scan_recent_reports(self) -> List[Dict]:
        """Scan recent test reports for failures."""
        failures = []
        report_files = list(Path("test_reports").glob("test_report_*.json"))
        
        # Get reports from last hour
        one_hour_ago = time.time() - 3600
        recent_reports = [f for f in report_files if f.stat().st_mtime > one_hour_ago]
        
        print(f"Found {len(recent_reports)} recent test reports")
        
        for report_file in recent_reports[-5:]:  # Last 5 reports
            print(f"  Scanning: {report_file.name}")
            report_failures = self.extract_test_results_from_json(report_file)
            failures.extend(report_failures)
        
        # Deduplicate
        unique_failures = {}
        for failure in failures:
            key = failure['test']
            if key not in unique_failures:
                unique_failures[key] = failure
        
        return list(unique_failures.values())
    
    def run_targeted_categories(self) -> Dict:
        """Run specific categories that are known to have issues."""
        categories_to_test = [
            "database",
            "clickhouse", 
            "integration",
            "api",
            "core"
        ]
        
        results = {}
        
        for category in categories_to_test:
            print(f"\nTesting category: {category}")
            
            cmd = ["python", "unified_test_runner.py", 
                   "--category", category,
                   "--no-coverage",
                   "--fast-fail"]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=45
                )
                
                # Check the most recent report
                report_files = sorted(Path("test_reports").glob("test_report_*.json"))
                if report_files:
                    latest_report = report_files[-1]
                    failures = self.extract_test_results_from_json(latest_report)
                    results[category] = {
                        'success': result.returncode == 0,
                        'failures': failures
                    }
                    
                    if failures:
                        print(f"  Found {len(failures)} failures")
                        
            except subprocess.TimeoutExpired:
                print(f"  Timeout for category: {category}")
                results[category] = {
                    'success': False,
                    'failures': []
                }
            except Exception as e:
                print(f"  Error testing category {category}: {e}")
                results[category] = {
                    'success': False,
                    'failures': []
                }
        
        return results
    
    def generate_comprehensive_report(self):
        """Generate comprehensive failure report."""
        print("\n" + "="*60)
        print("COMPREHENSIVE TEST SCAN COMPLETE")
        print("="*60)
        
        # Scan recent reports
        print("\nScanning recent test reports...")
        recent_failures = self.scan_recent_reports()
        
        # Run targeted tests
        print("\nRunning targeted category tests...")
        category_results = self.run_targeted_categories()
        
        # Combine all failures
        all_failures = recent_failures.copy()
        for category, info in category_results.items():
            all_failures.extend(info['failures'])
        
        # Deduplicate
        unique_failures = {}
        for failure in all_failures:
            key = failure['test']
            if key not in unique_failures:
                unique_failures[key] = failure
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'scan_duration': (datetime.now() - self.session_start).total_seconds(),
            'total_failures': len(unique_failures),
            'failures': list(unique_failures.values()),
            'category_results': category_results
        }
        
        report_file = self.report_dir / f"comprehensive_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\nTotal unique failures found: {len(unique_failures)}")
        
        if unique_failures:
            print("\nFailures by category:")
            by_category = {}
            for failure in unique_failures.values():
                cat = failure.get('category', 'unknown')
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(failure)
            
            for cat, failures in by_category.items():
                print(f"  {cat}: {len(failures)} failures")
                for f in failures[:3]:  # Show first 3
                    print(f"    - {f['type']}: {f['test']}")
                if len(failures) > 3:
                    print(f"    ... and {len(failures) - 3} more")
        
        print(f"\nReport saved to: {report_file}")
        
        # Verify some failures
        if unique_failures and len(unique_failures) <= 5:
            print("\nVerifying failures...")
            for failure in list(unique_failures.values())[:3]:
                self.run_single_test(failure['test'])
        
        return unique_failures


def main():
    """Main entry point."""
    scanner = ComprehensiveTestScanner()
    failures = scanner.generate_comprehensive_report()
    
    if failures:
        # Create tasks for Process B
        tasks_file = Path("test_failures/process_b_tasks.json")
        with open(tasks_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_tasks': len(failures),
                'tasks': list(failures.values())
            }, f, indent=2)
        
        print(f"\nProcess B tasks created: {tasks_file}")
        print(f"Total failures to fix: {len(failures)}")
        
        return 1
    else:
        print("\nNo failures found!")
        return 0


if __name__ == "__main__":
    sys.exit(main())