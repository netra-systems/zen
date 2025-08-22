#!/usr/bin/env python3
"""
Autonomous Test Review System - Main Reviewer
Main autonomous test reviewer class for orchestrating analysis and improvements
"""

import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from scripts.autonomous_review.report_generator import ReportGenerator
from scripts.autonomous_review.test_generator import TestGenerator
from scripts.autonomous_review.types import ReviewMode, TestAnalysis, TestMetadata
from scripts.autonomous_review.ultra_thinking_analyzer import UltraThinkingAnalyzer


class AutonomousTestReviewer:
    """Main autonomous test review system"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.spec_path = self.project_root / "SPEC" / "test_update_spec.xml"
        self.reports_dir = self.project_root / "reports"
        self.scripts_dir = self.project_root / "scripts"
        self.ultra_analyzer = UltraThinkingAnalyzer()
        self.test_generator = TestGenerator()
        self.report_generator = ReportGenerator()
        self.coverage_goal = 97.0
        self.test_metadata_cache = {}
        
    async def run_review(self, mode: ReviewMode = ReviewMode.AUTO) -> TestAnalysis:
        """Run autonomous test review based on mode"""
        print(f"\n[REVIEW] Running Autonomous Test Review in {mode.value} mode")
        print("=" * 60)
        
        analysis = TestAnalysis()
        
        # Step 1: Ultra-thinking analysis
        if mode in [ReviewMode.ULTRA_THINK, ReviewMode.FULL_ANALYSIS, ReviewMode.AUTO]:
            print("\n[ULTRA-THINK] Performing deep semantic analysis...")
            await self._perform_ultra_analysis(analysis)
        
        # Step 2: Coverage analysis
        print("\n[COVERAGE] Analyzing test coverage...")
        await self._analyze_coverage(analysis)
        
        # Step 3: Test quality assessment
        print("\n[QUALITY] Assessing test quality...")
        await self._assess_test_quality(analysis)
        
        # Step 4: Identify test gaps
        print("\n[GAPS] Identifying test gaps...")
        await self._identify_test_gaps(analysis)
        
        # Step 5: Generate recommendations
        print("\n[RECOMMEND] Generating improvement recommendations...")
        await self._generate_recommendations(analysis)
        
        # Step 6: Auto-fix issues (if in auto mode)
        if mode in [ReviewMode.AUTO, ReviewMode.SMART_GENERATE]:
            print("\n[AUTO-FIX] Applying automatic improvements...")
            await self._apply_auto_fixes(analysis)
        
        # Step 7: Generate report
        await self.report_generator.generate_report(analysis, self.reports_dir)
        
        return analysis
    
    async def _perform_ultra_analysis(self, analysis: TestAnalysis) -> None:
        """Perform ultra-thinking deep analysis"""
        # Analyze all Python files
        py_files = list(self.project_root.rglob("*.py"))
        py_files = [f for f in py_files if "test" not in f.name and "__pycache__" not in str(f)]
        
        critical_untested = []
        
        for file_path in py_files[:50]:  # Analyze top 50 files
            semantics = await self.ultra_analyzer.analyze_code_semantics(file_path)
            
            if semantics:
                # Check if file has corresponding test
                test_file = self._find_test_file(file_path)
                if not test_file or not test_file.exists():
                    # Calculate criticality score
                    criticality = sum([
                        len(semantics.get("critical_paths", [])) * 3,
                        len(semantics.get("error_handlers", [])) * 2,
                        len(semantics.get("data_validators", [])) * 2,
                        semantics.get("complexity", 0) // 5
                    ])
                    
                    if criticality > 0:
                        critical_untested.append({
                            "file": str(file_path.relative_to(self.project_root)),
                            "criticality": criticality,
                            "functions": len(semantics.get("functions", [])),
                            "classes": len(semantics.get("classes", []))
                        })
        
        # Sort by criticality and add to analysis
        critical_untested.sort(key=lambda x: x["criticality"], reverse=True)
        analysis.critical_gaps = [f["file"] for f in critical_untested[:10]]
        analysis.missing_tests.extend([f["file"] for f in critical_untested[:20]])
    
    async def _analyze_coverage(self, analysis: TestAnalysis) -> None:
        """Analyze current test coverage"""
        # Try to get actual coverage
        try:
            # Backend coverage
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov=app", "--cov-report=json", "--quiet"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60
            )
            
            if result.returncode == 0 and (self.project_root / "coverage.json").exists():
                with open(self.project_root / "coverage.json", 'r') as f:
                    coverage_data = json.load(f)
                    analysis.coverage_percentage = coverage_data.get("totals", {}).get("percent_covered", 70.0)
            else:
                analysis.coverage_percentage = 70.0  # Fallback to baseline
                
        except (subprocess.TimeoutExpired, Exception):
            analysis.coverage_percentage = 70.0  # Fallback to baseline
        
        # Calculate coverage gap
        coverage_gap = self.coverage_goal - analysis.coverage_percentage
        if coverage_gap > 0:
            analysis.recommendations.append(
                f"Need to increase coverage by {coverage_gap:.1f}% to reach {self.coverage_goal}% goal"
            )
    
    async def _assess_test_quality(self, analysis: TestAnalysis) -> None:
        """Assess quality of existing tests"""
        test_files = list(self.project_root.rglob("test_*.py"))
        test_files.extend(list(self.project_root.rglob("*_test.py")))
        test_files.extend(list(self.project_root.rglob("*.test.ts*")))
        
        quality_issues = defaultdict(list)
        
        for test_file in test_files[:100]:  # Analyze first 100 test files
            content = test_file.read_text(encoding='utf-8', errors='replace')
            
            # Check for quality issues using test generator
            issues = self.test_generator.analyze_test_quality(test_file, content)
            
            if issues:
                self.test_metadata_cache[str(test_file)] = TestMetadata(
                    file_path=test_file,
                    test_name=test_file.stem,
                    quality_issues=issues
                )
                
                # Categorize issues
                for issue in issues:
                    if "deprecated" in issue.lower():
                        quality_issues["legacy_framework"].append(str(test_file))
                    elif "assertion" in issue.lower():
                        quality_issues["missing_assertion"].append(str(test_file))
                    elif "sleep" in issue.lower():
                        quality_issues["hardcoded_wait"].append(str(test_file))
                    elif "skip" in issue.lower():
                        quality_issues["skipped_tests"].append(str(test_file))
        
        # Update analysis
        analysis.legacy_tests = quality_issues.get("legacy_framework", [])[:10]
        analysis.quality_score = max(0, 100 - len(quality_issues) * 5)
        analysis.test_debt = sum(len(files) for files in quality_issues.values())
        
        # Add specific recommendations
        if quality_issues["missing_assertion"]:
            analysis.recommendations.append(
                f"Add assertions to {len(quality_issues['missing_assertion'])} tests without validation"
            )
        if quality_issues["hardcoded_wait"]:
            analysis.recommendations.append(
                f"Replace hardcoded sleeps in {len(quality_issues['hardcoded_wait'])} test files"
            )
    
    async def _identify_test_gaps(self, analysis: TestAnalysis) -> None:
        """Identify gaps in test coverage"""
        # Find untested modules
        app_modules = list((self.project_root / "app").rglob("*.py"))
        frontend_modules = list((self.project_root / "frontend").rglob("*.tsx"))
        
        untested_backend = []
        untested_frontend = []
        
        for module in app_modules:
            if "__pycache__" in str(module) or "test" in module.name:
                continue
                
            test_file = self._find_test_file(module)
            if not test_file or not test_file.exists():
                untested_backend.append(str(module.relative_to(self.project_root)))
        
        for module in frontend_modules:
            if "node_modules" in str(module) or ".test." in module.name or "__tests__" in str(module):
                continue
                
            test_file = module.parent / "__tests__" / f"{module.stem}.test.tsx"
            if not test_file.exists():
                test_file = module.parent / f"{module.stem}.test.tsx"
                if not test_file.exists():
                    untested_frontend.append(str(module.relative_to(self.project_root)))
        
        # Identify test categories that are missing
        test_categories = {
            "unit": False,
            "integration": False,
            "e2e": False,
            "performance": False,
            "security": False
        }
        
        # Check for test categories
        for test_file in self.project_root.rglob("test_*.py"):
            content = test_file.read_text(encoding='utf-8', errors='replace').lower()
            if "unit" in content or "unittest" in content:
                test_categories["unit"] = True
            if "integration" in content or "api" in content:
                test_categories["integration"] = True
            if "e2e" in content or "end_to_end" in content:
                test_categories["e2e"] = True
            if "performance" in content or "benchmark" in content:
                test_categories["performance"] = True
            if "security" in content or "auth" in content:
                test_categories["security"] = True
        
        # Add gaps to analysis
        analysis.missing_tests.extend(untested_backend[:10])
        analysis.missing_tests.extend(untested_frontend[:10])
        
        for category, exists in test_categories.items():
            if not exists:
                analysis.recommendations.append(f"Add {category} tests to test suite")
    
    async def _generate_recommendations(self, analysis: TestAnalysis) -> None:
        """Generate intelligent recommendations"""
        # Priority-based recommendations
        if analysis.coverage_percentage < 80:
            analysis.recommendations.insert(0, 
                "CRITICAL: Coverage below 80% - focus on unit test generation for core modules"
            )
        
        if analysis.critical_gaps:
            analysis.recommendations.insert(0,
                f"URGENT: Add tests for {len(analysis.critical_gaps)} critical modules with security/data operations"
            )
        
        if analysis.test_debt > 50:
            analysis.recommendations.append(
                f"Schedule tech debt sprint to address {analysis.test_debt} test quality issues"
            )
        
        # Smart test type recommendations
        if len(analysis.missing_tests) > 20:
            analysis.recommendations.append(
                "Enable continuous test generation in CI/CD pipeline"
            )
        
        # Performance recommendations
        if analysis.slow_tests:
            analysis.recommendations.append(
                f"Optimize {len(analysis.slow_tests)} slow tests to improve CI/CD speed"
            )
    
    async def _apply_auto_fixes(self, analysis: TestAnalysis) -> None:
        """Automatically fix identified issues"""
        print("\n[AUTO-FIX] Applying automatic improvements...")
        
        fixes_applied = 0
        
        # Generate tests for critical gaps
        if analysis.critical_gaps:
            print(f"  Generating tests for {len(analysis.critical_gaps[:5])} critical modules...")
            for module_path in analysis.critical_gaps[:5]:
                if await self.test_generator.generate_smart_test(Path(self.project_root / module_path)):
                    fixes_applied += 1
        
        # Fix legacy patterns
        if analysis.legacy_tests:
            print(f"  Modernizing {len(analysis.legacy_tests[:5])} legacy test files...")
            for test_path in analysis.legacy_tests[:5]:
                if await self.test_generator.modernize_test_file(Path(test_path)):
                    fixes_applied += 1
        
        # Remove redundant tests
        if analysis.redundant_tests:
            print(f"  Removing {len(analysis.redundant_tests[:3])} redundant tests...")
            for test_path in analysis.redundant_tests[:3]:
                if await self.test_generator.remove_redundant_test(Path(test_path)):
                    fixes_applied += 1
        
        print(f"\n[SUCCESS] Applied {fixes_applied} automatic fixes")
    
    def _find_test_file(self, source_file: Path) -> Path:
        """Find corresponding test file for a source file"""
        # Backend Python tests
        if source_file.suffix == ".py":
            # Standard test naming patterns
            test_patterns = [
                source_file.parent / f"test_{source_file.stem}.py",
                source_file.parent / f"{source_file.stem}_test.py",
                source_file.parent / "tests" / f"test_{source_file.stem}.py",
                self.project_root / "app" / "tests" / f"test_{source_file.stem}.py",
                self.project_root / "tests" / f"test_{source_file.stem}.py"
            ]
            
            for pattern in test_patterns:
                if pattern.exists():
                    return pattern
        
        # Frontend TypeScript/JavaScript tests
        elif source_file.suffix in [".tsx", ".ts", ".js", ".jsx"]:
            test_patterns = [
                source_file.parent / "__tests__" / f"{source_file.stem}.test.tsx",
                source_file.parent / f"{source_file.stem}.test.tsx",
                source_file.parent / f"{source_file.stem}.test.ts"
            ]
            
            for pattern in test_patterns:
                if pattern.exists():
                    return pattern
        
        return None