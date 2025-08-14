#!/usr/bin/env python
"""
Test Orchestrator - Simplified orchestration of test suite execution
Coordinates test discovery, execution, and reporting
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from .test_profile_models import TestProfile, TestSuite, TestProfileManager, TestPriority
from .test_discovery import TestDiscovery
from .test_execution_engine import TestExecutionEngine
from .failure_patterns import FailurePatternAnalyzer
from .test_insights import TestInsightGenerator


class TestOrchestrator:
    """
    Simplified orchestrator that coordinates test discovery, execution, and analysis
    """
    
    def __init__(self, project_root: Path, config_path: Optional[Path] = None):
        self.project_root = project_root
        self.config_path = config_path or project_root / "test_framework" / "test_config.json"
        
        # Initialize components
        self.discovery = TestDiscovery(project_root)
        self.execution_engine = TestExecutionEngine(project_root)
        self.failure_analyzer = FailurePatternAnalyzer()
        self.insight_generator = TestInsightGenerator()
        
        # Profile management
        profiles_path = project_root / "test_framework" / "test_profiles.json"
        self.profile_manager = TestProfileManager(profiles_path)
        self.test_profiles = self.profile_manager.load_profiles()
        
        # Test suites
        self.suites: Dict[str, TestSuite] = self._initialize_suites()
        
        # Load configuration
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load test configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        
        # Default configuration
        return {
            "max_parallel": 8,
            "timeout_multiplier": 1.5,
            "retry_flaky": True,
            "fail_fast": False,
            "coverage_threshold": 80,
            "performance_regression_threshold": 1.2,
            "test_categories": {
                "unit": {"priority": 2, "parallel": True, "timeout": 60},
                "integration": {"priority": 3, "parallel": True, "timeout": 120},
                "e2e": {"priority": 4, "parallel": False, "timeout": 300},
                "smoke": {"priority": 1, "parallel": True, "timeout": 30},
                "performance": {"priority": 5, "parallel": False, "timeout": 600}
            }
        }
    
    def _initialize_suites(self) -> Dict[str, TestSuite]:
        """Initialize test suites based on discovered tests"""
        discovered_tests = self.discovery.discover_tests()
        suites = {}
        
        for category, test_paths in discovered_tests.items():
            # Create test profiles for new tests
            tests = []
            for test_path in test_paths:
                test_name = Path(test_path).stem
                
                # Get or create profile
                profile = self.test_profiles.get(test_name)
                if not profile:
                    profile = TestProfile(
                        path=test_path,
                        name=test_name,
                        category=category
                    )
                    self.test_profiles[test_name] = profile
                
                tests.append(profile)
            
            # Create test suite
            suite = TestSuite(
                name=category,
                tests=tests,
                priority=TestPriority.MEDIUM,
                parallel_safe=True,
                max_parallel=4,
                timeout=300
            )
            
            suites[category] = suite
        
        return suites
    
    async def execute_suite(
        self,
        suite_name: str,
        parallel: bool = True,
        fail_fast: bool = False,
        retry_failed: bool = True
    ) -> Dict[str, Any]:
        """Execute a test suite with intelligent scheduling"""
        if suite_name not in self.suites:
            raise ValueError(f"Suite {suite_name} not found")
        
        suite = self.suites[suite_name]
        results = {
            "suite": suite_name,
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
        
        # Get execution order
        tests = suite.get_execution_order()
        
        # Execute tests
        if parallel and suite.parallel_safe:
            results["tests"] = await self.execution_engine.execute_parallel(
                tests, suite.max_parallel, fail_fast
            )
        else:
            results["tests"] = await self.execution_engine.execute_sequential(
                tests, fail_fast
            )
        
        # Retry failed tests if configured
        if retry_failed:
            failed_tests = [t for t in results["tests"] if t["status"] in ["failed", "error"]]
            if failed_tests:
                retry_results = await self.execution_engine.retry_failed_tests(
                    failed_tests, self.test_profiles, suite.retry_count
                )
                # Update results with retry outcomes
                for retry in retry_results:
                    for i, test in enumerate(results["tests"]):
                        if test["name"] == retry["name"]:
                            results["tests"][i] = retry
                            break
        
        # Generate summary
        results["end_time"] = datetime.now().isoformat()
        results["summary"] = self.execution_engine.generate_execution_summary(results["tests"])
        
        # Save results and update profiles
        self._save_results(results)
        
        return results
    
    def _save_results(self, results: Dict):
        """Save test results and update profiles"""
        # Update test profiles based on results
        for test_result in results["tests"]:
            test_name = test_result["name"]
            if test_name in self.test_profiles:
                # Profile was already updated during execution
                pass
            else:
                # Create new profile
                self.test_profiles[test_name] = TestProfile(
                    path=test_result["path"],
                    name=test_name,
                    category=results["suite"]
                )
        
        # Save updated profiles
        self.profile_manager.save_profiles(self.test_profiles)
    
    def get_available_suites(self) -> List[str]:
        """Get list of available test suites"""
        return list(self.suites.keys())
    
    def get_suite_info(self, suite_name: str) -> Dict:
        """Get information about a specific test suite"""
        if suite_name not in self.suites:
            return {}
        
        suite = self.suites[suite_name]
        return {
            "name": suite.name,
            "test_count": len(suite.tests),
            "priority": suite.priority.name,
            "parallel_safe": suite.parallel_safe,
            "max_parallel": suite.max_parallel,
            "timeout": suite.timeout,
            "categories": list(set(t.category for t in suite.tests))
        }
    
    def analyze_test_health(self) -> Dict[str, Any]:
        """Analyze overall test suite health"""
        return self.insight_generator.generate_insights(self.test_profiles)
    
    def get_failing_tests(self) -> List[Dict]:
        """Get currently failing tests"""
        failing = []
        for profile in self.test_profiles.values():
            if profile.consecutive_failures > 0:
                failing.append({
                    "name": profile.name,
                    "category": profile.category,
                    "consecutive_failures": profile.consecutive_failures,
                    "failure_rate": profile.failure_rate,
                    "last_status": profile.last_status.value
                })
        
        return sorted(failing, key=lambda x: x["consecutive_failures"], reverse=True)
    
    def get_flaky_tests(self, threshold: float = 0.3) -> List[Dict]:
        """Get flaky tests above threshold"""
        flaky = []
        for profile in self.test_profiles.values():
            if profile.flaky_score > threshold:
                flaky.append({
                    "name": profile.name,
                    "category": profile.category,
                    "flaky_score": profile.flaky_score,
                    "failure_rate": profile.failure_rate,
                    "total_runs": profile.total_runs
                })
        
        return sorted(flaky, key=lambda x: x["flaky_score"], reverse=True)
    
    def discover_tests(self) -> Dict[str, List[str]]:
        """Discover all tests in the project"""
        return self.discovery.discover_tests()
    
    def refresh_suites(self):
        """Refresh test suites after discovering new tests"""
        self.suites = self._initialize_suites()
        self.profile_manager.save_profiles(self.test_profiles)