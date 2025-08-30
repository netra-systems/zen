#!/usr/bin/env python3
"""
Test Collection Audit and Improvement Tool
Analyzes and optimizes test collection across the Netra Apex platform
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dev_launcher.isolated_environment import get_env

@dataclass
class TestCollectionMetrics:
    """Metrics for test collection analysis"""
    total_tests: int = 0
    total_collection_time: float = 0.0
    collection_errors: List[str] = None
    duplicate_tests: List[str] = None
    missing_markers: List[str] = None
    orphaned_tests: List[str] = None
    test_distribution: Dict[str, int] = None
    marker_distribution: Dict[str, int] = None
    
    def __post_init__(self):
        if self.collection_errors is None:
            self.collection_errors = []
        if self.duplicate_tests is None:
            self.duplicate_tests = []
        if self.missing_markers is None:
            self.missing_markers = []
        if self.orphaned_tests is None:
            self.orphaned_tests = []
        if self.test_distribution is None:
            self.test_distribution = {}
        if self.marker_distribution is None:
            self.marker_distribution = {}


class TestCollectionAuditor:
    """Audits and improves test collection across all services"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_path = project_root / "netra_backend"
        self.auth_path = project_root / "auth_service"
        self.frontend_path = project_root / "frontend"
        self.test_paths = {
            "backend": self.backend_path / "tests",
            "auth": self.auth_path / "tests",
            "frontend": self.frontend_path / "__tests__",
            "e2e": project_root / "tests",
            "cypress": project_root / "cypress" / "e2e"
        }
        
    def audit_all_services(self) -> Dict[str, TestCollectionMetrics]:
        """Audit test collection for all services"""
        results = {}
        
        print("\n[AUDIT] Starting Test Collection Audit...")
        print("=" * 60)
        
        # Audit Python test collections
        for service in ["backend", "auth"]:
            print(f"\n[SERVICE] Auditing {service.upper()} service...")
            results[service] = self._audit_python_tests(service)
            
        # Audit frontend tests
        print("\n[SERVICE] Auditing FRONTEND service...")
        results["frontend"] = self._audit_frontend_tests()
        
        # Audit E2E tests
        print("\n[SERVICE] Auditing E2E tests...")
        results["e2e"] = self._audit_e2e_tests()
        
        return results
    
    def _audit_python_tests(self, service: str) -> TestCollectionMetrics:
        """Audit Python test collection for a service"""
        metrics = TestCollectionMetrics()
        
        if service == "backend":
            test_path = self.backend_path
            module_path = "netra_backend"
        else:
            test_path = self.auth_path
            module_path = "auth_service"
            
        # Collect tests and measure time
        start_time = time.time()
        
        try:
            # Run pytest collection
            result = subprocess.run(
                ["python", "-m", "pytest", f"{module_path}/tests", "--collect-only", "--quiet"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60
            )
            
            metrics.total_collection_time = time.time() - start_time
            
            # Parse collection output
            lines = result.stdout.strip().split('\n')
            test_items = [line for line in lines if '::test_' in line or '::Test' in line]
            metrics.total_tests = len(test_items)
            
            # Check for collection errors
            if result.returncode != 0:
                metrics.collection_errors.append(result.stderr)
                
            # Analyze test distribution
            metrics.test_distribution = self._analyze_test_distribution(test_items)
            
            # Find duplicate test names
            metrics.duplicate_tests = self._find_duplicate_tests(test_items)
            
            # Check for missing markers
            metrics.missing_markers = self._check_missing_markers(test_path / "tests")
            
            # Find orphaned test files
            metrics.orphaned_tests = self._find_orphaned_tests(test_path / "tests")
            
            # Analyze marker distribution
            metrics.marker_distribution = self._analyze_marker_distribution(test_path / "tests")
            
        except subprocess.TimeoutExpired:
            metrics.collection_errors.append("Test collection timed out after 60 seconds")
        except Exception as e:
            metrics.collection_errors.append(f"Collection failed: {str(e)}")
            
        return metrics
    
    def _audit_frontend_tests(self) -> TestCollectionMetrics:
        """Audit frontend test collection"""
        metrics = TestCollectionMetrics()
        
        # Check Jest test collection
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["npm", "test", "--", "--listTests", "--json"],
                capture_output=True,
                text=True,
                cwd=self.frontend_path,
                timeout=30
            )
            
            metrics.total_collection_time = time.time() - start_time
            
            if result.returncode == 0:
                try:
                    test_files = json.loads(result.stdout)
                    metrics.total_tests = len(test_files)
                    
                    # Analyze test distribution
                    for test_file in test_files:
                        category = self._categorize_frontend_test(test_file)
                        metrics.test_distribution[category] = metrics.test_distribution.get(category, 0) + 1
                        
                except json.JSONDecodeError:
                    metrics.collection_errors.append("Failed to parse Jest test list")
                    
        except subprocess.TimeoutExpired:
            metrics.collection_errors.append("Frontend test collection timed out")
        except Exception as e:
            metrics.collection_errors.append(f"Frontend collection failed: {str(e)}")
            
        # Check Cypress tests
        cypress_path = self.project_root / "cypress" / "e2e"
        if cypress_path.exists():
            cypress_tests = list(cypress_path.glob("**/*.cy.ts"))
            metrics.test_distribution["cypress"] = len(cypress_tests)
            
        return metrics
    
    def _audit_e2e_tests(self) -> TestCollectionMetrics:
        """Audit E2E test collection"""
        metrics = TestCollectionMetrics()
        
        e2e_path = self.project_root / "tests"
        if not e2e_path.exists():
            return metrics
            
        # Count E2E test files
        for test_file in e2e_path.rglob("test_*.py"):
            category = test_file.parent.name if test_file.parent != e2e_path else "root"
            metrics.test_distribution[category] = metrics.test_distribution.get(category, 0) + 1
            metrics.total_tests += 1
            
        return metrics
    
    def _analyze_test_distribution(self, test_items: List[str]) -> Dict[str, int]:
        """Analyze distribution of tests across modules"""
        distribution = defaultdict(int)
        
        for item in test_items:
            # Extract module from test path
            parts = item.split("::")
            if len(parts) >= 1:
                module = parts[0].split("/")[-2] if "/" in parts[0] else "root"
                distribution[module] += 1
                
        return dict(distribution)
    
    def _find_duplicate_tests(self, test_items: List[str]) -> List[str]:
        """Find duplicate test names"""
        test_names = defaultdict(list)
        
        for item in test_items:
            # Extract test name
            if "::" in item:
                test_name = item.split("::")[-1]
                test_names[test_name].append(item)
                
        duplicates = []
        for name, items in test_names.items():
            if len(items) > 1:
                duplicates.append(f"{name}: {', '.join(items)}")
                
        return duplicates
    
    def _check_missing_markers(self, test_path: Path) -> List[str]:
        """Check for tests missing important markers"""
        missing = []
        
        if not test_path.exists():
            return missing
            
        for test_file in test_path.rglob("test_*.py"):
            content = test_file.read_text()
            
            # Check if file has any pytest markers
            if "pytest.mark" not in content and "@pytest.mark" not in content:
                relative_path = test_file.relative_to(self.project_root)
                missing.append(str(relative_path))
                
        return missing
    
    def _find_orphaned_tests(self, test_path: Path) -> List[str]:
        """Find test files that don't correspond to any source modules"""
        orphaned = []
        
        if not test_path.exists():
            return orphaned
            
        for test_file in test_path.rglob("test_*.py"):
            # Skip special test files
            if test_file.stem in ["test_imports", "test_fixtures", "test_utils"]:
                continue
                
            # Check if corresponding source module exists
            module_name = test_file.stem.replace("test_", "")
            possible_paths = [
                test_file.parent.parent / f"{module_name}.py",
                test_file.parent.parent / module_name / "__init__.py",
                test_file.parent.parent.parent / "app" / f"{module_name}.py"
            ]
            
            if not any(p.exists() for p in possible_paths):
                relative_path = test_file.relative_to(self.project_root)
                orphaned.append(str(relative_path))
                
        return orphaned
    
    def _analyze_marker_distribution(self, test_path: Path) -> Dict[str, int]:
        """Analyze distribution of pytest markers"""
        markers = defaultdict(int)
        
        if not test_path.exists():
            return dict(markers)
            
        for test_file in test_path.rglob("test_*.py"):
            content = test_file.read_text()
            
            # Find all pytest markers in file
            import re
            marker_pattern = r'@pytest\.mark\.(\w+)'
            found_markers = re.findall(marker_pattern, content)
            
            for marker in found_markers:
                markers[marker] += 1
                
        return dict(markers)
    
    def _categorize_frontend_test(self, test_file: str) -> str:
        """Categorize frontend test based on file path"""
        if "unit" in test_file:
            return "unit"
        elif "integration" in test_file:
            return "integration"
        elif "component" in test_file:
            return "component"
        elif "e2e" in test_file:
            return "e2e"
        else:
            return "other"
    
    def generate_report(self, results: Dict[str, TestCollectionMetrics]) -> str:
        """Generate detailed audit report"""
        report = []
        report.append("\n" + "=" * 70)
        report.append("TEST COLLECTION AUDIT REPORT")
        report.append("=" * 70)
        
        total_tests = 0
        total_errors = 0
        total_duplicates = 0
        total_orphaned = 0
        
        for service, metrics in results.items():
            report.append(f"\n[{service.upper()}] Service")
            report.append("-" * 40)
            
            report.append(f"  Total Tests: {metrics.total_tests}")
            report.append(f"  Collection Time: {metrics.total_collection_time:.2f}s")
            
            if metrics.test_distribution:
                report.append("\n  Test Distribution:")
                for category, count in sorted(metrics.test_distribution.items()):
                    report.append(f"    - {category}: {count}")
                    
            if metrics.marker_distribution:
                report.append("\n  Marker Usage:")
                for marker, count in sorted(metrics.marker_distribution.items(), key=lambda x: -x[1])[:10]:
                    report.append(f"    - @pytest.mark.{marker}: {count}")
                    
            if metrics.collection_errors:
                report.append(f"\n  [WARNING] Collection Errors: {len(metrics.collection_errors)}")
                for error in metrics.collection_errors[:3]:
                    report.append(f"    - {error[:100]}...")
                    
            if metrics.duplicate_tests:
                report.append(f"\n  [WARNING] Duplicate Tests: {len(metrics.duplicate_tests)}")
                for dup in metrics.duplicate_tests[:5]:
                    report.append(f"    - {dup[:100]}...")
                    
            if metrics.missing_markers:
                report.append(f"\n  [WARNING] Tests Missing Markers: {len(metrics.missing_markers)}")
                for missing in metrics.missing_markers[:5]:
                    report.append(f"    - {missing}")
                    
            if metrics.orphaned_tests:
                report.append(f"\n  [WARNING] Orphaned Tests: {len(metrics.orphaned_tests)}")
                for orphaned in metrics.orphaned_tests[:5]:
                    report.append(f"    - {orphaned}")
                    
            total_tests += metrics.total_tests
            total_errors += len(metrics.collection_errors)
            total_duplicates += len(metrics.duplicate_tests)
            total_orphaned += len(metrics.orphaned_tests)
            
        # Summary
        report.append("\n" + "=" * 70)
        report.append("SUMMARY")
        report.append("=" * 70)
        report.append(f"Total Tests Collected: {total_tests}")
        report.append(f"Total Collection Errors: {total_errors}")
        report.append(f"Total Duplicate Tests: {total_duplicates}")
        report.append(f"Total Orphaned Tests: {total_orphaned}")
        
        # Recommendations
        report.append("\n" + "=" * 70)
        report.append("RECOMMENDATIONS")
        report.append("=" * 70)
        
        if total_errors > 0:
            report.append("1. Fix collection errors to ensure all tests are discoverable")
            
        if total_duplicates > 0:
            report.append("2. Rename duplicate tests to have unique names")
            
        if total_orphaned > 0:
            report.append("3. Review orphaned tests - remove or link to source modules")
            
        if any(m.total_collection_time > 10 for m in results.values()):
            report.append("4. Optimize test collection time - consider parallel collection")
            
        report.append("5. Add appropriate markers to all tests for better categorization")
        report.append("6. Consider using test discovery caching for faster collection")
        
        return "\n".join(report)
    
    def write_metrics_json(self, results: Dict[str, TestCollectionMetrics], output_path: Path):
        """Write metrics to JSON file for tracking"""
        data = {
            "timestamp": time.time(),
            "services": {}
        }
        
        for service, metrics in results.items():
            data["services"][service] = {
                "total_tests": metrics.total_tests,
                "collection_time": metrics.total_collection_time,
                "errors": len(metrics.collection_errors),
                "duplicates": len(metrics.duplicate_tests),
                "missing_markers": len(metrics.missing_markers),
                "orphaned": len(metrics.orphaned_tests),
                "test_distribution": metrics.test_distribution,
                "marker_distribution": metrics.marker_distribution
            }
            
        output_path.write_text(json.dumps(data, indent=2))
        

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Audit and improve test collection across Netra Apex platform"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("test_collection_metrics.json"),
        help="Output file for metrics JSON"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix identified issues"
    )
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent.absolute()
    
    # Create auditor
    auditor = TestCollectionAuditor(project_root)
    
    # Run audit
    results = auditor.audit_all_services()
    
    # Generate report
    report = auditor.generate_report(results)
    print(report)
    
    # Write metrics
    auditor.write_metrics_json(results, args.output)
    print(f"\n[SUCCESS] Metrics written to {args.output}")
    
    # Return non-zero if issues found
    total_issues = sum(
        len(m.collection_errors) + len(m.duplicate_tests) + len(m.orphaned_tests)
        for m in results.values()
    )
    
    if total_issues > 0:
        print(f"\n[WARNING] Found {total_issues} issues requiring attention")
        return 1
    else:
        print("\n[SUCCESS] No critical issues found")
        return 0


if __name__ == "__main__":
    sys.exit(main())