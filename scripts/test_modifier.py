#!/usr/bin/env python3
"""
Test Modifier Module
Orchestrates test generation, legacy pattern updates, and performance optimization
Complies with 300-line limit and 8-line function constraint
"""

from pathlib import Path
from typing import Dict, List, Any

# Import modular components
from test_generator import TestGenerator
from test_optimizer import TestPerformanceOptimizer, LegacyTestUpdater, MetadataManager


class TestModifier:
    """Main test modification orchestrator"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.generator = TestGenerator(project_root)
        self.updater = LegacyTestUpdater(project_root)
        self.optimizer = TestPerformanceOptimizer(project_root)
        self.metadata_manager = MetadataManager(project_root)

    async def generate_tests(self, modules: List[str]) -> int:
        """Generate test files for untested modules"""
        return await self.generator.generate_missing_tests(modules)

    async def update_legacy_tests(self) -> int:
        """Update legacy test patterns to modern standards"""
        return await self.updater.update_legacy_patterns()

    async def optimize_test_performance(self) -> Dict[str, bool]:
        """Optimize test execution performance"""
        return await self.optimizer.optimize_performance()

    def add_metadata_tracking(self, enabled: bool = True) -> None:
        """Add metadata tracking to generated tests"""
        if enabled:
            self.metadata_manager.add_metadata_to_generated_tests()

    async def modify_test_suite(self, modules: List[str], with_metadata: bool = False) -> Dict[str, Any]:
        """Execute comprehensive test suite modifications"""
        results = {
            "generated": await self.generate_tests(modules),
            "updated": await self.update_legacy_tests(),
            "optimizations": await self.optimize_test_performance()
        }
        
        if with_metadata:
            self.add_metadata_tracking(True)
            results["metadata_added"] = True
        
        return results