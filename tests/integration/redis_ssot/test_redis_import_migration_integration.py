"""
Redis Import Migration Validation Integration Test - CRITICAL for GitHub Issue #190

This test validates that all 76 files importing Redis managers use the single SSOT,
preventing the chaos of competing Redis managers that block user chat functionality.

BUSINESS IMPACT: CRITICAL - $500K+ ARR at risk
- Chat functionality failures from Redis connection instability
- 76 files importing different Redis managers creating import chaos
- WebSocket 1011 errors from Redis connection race conditions
- Memory leaks and connection pool conflicts

CRITICAL MISSION: Validate import migration from 4 managers  ->  1 SSOT manager
- Primary SSOT: netra_backend.app.redis_manager.RedisManager
- This test should FAIL until all 76 files migrate to SSOT imports
- Validates NO files import from violation locations
- Ensures import consistency across entire codebase

VIOLATION DETECTION:
- Scan all Python files for Redis manager imports
- Detect imports to duplicate managers (db/redis_manager, cache/redis_cache_manager, etc.)
- Validate imports point ONLY to primary SSOT
- This test is designed to FAIL until migration is complete
"""

import ast
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestContext, CategoryType
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class RedisImportMigrationIntegrationTest(SSotBaseTestCase):
    """
    Critical integration test validating Redis import migration to single SSOT.
    
    This test scans the entire codebase to ensure ALL files import Redis
    functionality from the single SSOT location, not from duplicate managers.
    
    DEPLOYMENT BLOCKER: This test will FAIL until import migration is complete.
    """
    
    def setUp(self):
        """Set up test context for Redis import migration validation."""
        super().setUp()
        self.context = SsotTestContext(
            test_id=f"redis_import_migration_{int(time.time())}",
            test_name="Redis Import Migration Integration Test",
            test_category=CategoryType.MISSION_CRITICAL,
            metadata={
                "github_issue": "#190",
                "business_impact": "CRITICAL",
                "deployment_blocker": True,
                "ssot_category": "redis_import_migration",
                "files_to_migrate": 76,
                "arr_at_risk": "$500K+"
            }
        )
        self.metrics.start_timing()
        
        # SSOT import location (ONLY valid import)
        self.ssot_import_patterns = [
            "from netra_backend.app.redis_manager import",
            "import netra_backend.app.redis_manager",
            "from netra_backend.app.redis_manager import RedisManager"
        ]
        
        # VIOLATION import patterns (should NOT exist)
        self.violation_import_patterns = [
            "from netra_backend.app.db.redis_manager import",
            "import netra_backend.app.db.redis_manager",
            "from netra_backend.app.cache.redis_cache_manager import", 
            "import netra_backend.app.cache.redis_cache_manager",
            "from auth_service.redis_manager import",
            "import auth_service.redis_manager"
        ]
        
        # Directories to scan for imports
        self.scan_directories = [
            "netra_backend",
            "auth_service", 
            "analytics_service",
            "frontend",
            "test_framework",
            "tests",
            "scripts"
        ]
        
    def test_scan_all_redis_imports(self):
        """
        CRITICAL: Scan all Python files for Redis manager imports.
        
        This test scans the entire codebase to catalog ALL Redis manager
        imports and identify which ones need migration to SSOT.
        """
        logger.info(" SEARCH:  SCANNING: All Redis manager imports in codebase")
        
        project_root = Path(__file__).parent.parent.parent.parent
        all_imports = self._scan_redis_imports_comprehensive(project_root)
        
        total_files_with_redis = len(all_imports)
        ssot_imports = sum(1 for imports in all_imports.values() if imports["uses_ssot"])
        violation_imports = sum(1 for imports in all_imports.values() if imports["has_violations"])
        
        self.metrics.record_custom("total_files_with_redis", total_files_with_redis)
        self.metrics.record_custom("ssot_imports", ssot_imports)
        self.metrics.record_custom("violation_imports", violation_imports)
        self.metrics.record_custom("import_details", all_imports)
        
        logger.info(f" CHART:  Redis Import Scan Results:")
        logger.info(f"   - Total files with Redis imports: {total_files_with_redis}")
        logger.info(f"   - Files using SSOT: {ssot_imports}")
        logger.info(f"   - Files with violations: {violation_imports}")
        
        # Store scan results for other tests
        self.scan_results = all_imports
    
    def test_no_violation_imports_exist(self):
        """
        DEPLOYMENT BLOCKER: Test that NO files import from violation locations.
        
        This test MUST FAIL until all files migrate from duplicate Redis
        managers to the single SSOT manager.
        """
        logger.info(" ALERT:  TESTING: No violation imports exist (Expected to FAIL)")
        
        if not hasattr(self, 'scan_results'):
            self.test_scan_all_redis_imports()  # Run scan if not already done
        
        violation_files = []
        violation_details = {}
        
        for file_path, import_info in self.scan_results.items():
            if import_info["has_violations"]:
                violation_files.append(file_path)
                violation_details[file_path] = import_info["violation_imports"]
                
                logger.warning(f"VIOLATION: {file_path} imports from: {import_info['violation_imports']}")
        
        self.metrics.record_custom("violation_files", violation_files)
        self.metrics.record_custom("violation_details", violation_details)
        
        # This should FAIL until migration is complete
        assert len(violation_files) == 0, (
            f" ALERT:  IMPORT MIGRATION INCOMPLETE: {len(violation_files)} files still import "
            f"from duplicate Redis managers instead of SSOT. "
            f"Violation files: {violation_files[:10]}{'...' if len(violation_files) > 10 else ''}"
        )
        
        logger.error(f"EXPECTED FAILURE: {len(violation_files)} files need import migration")
    
    def test_all_files_use_ssot_imports(self):
        """
        Test that ALL files with Redis imports use SSOT import patterns.
        
        Validates files that need Redis functionality import ONLY from
        the primary SSOT manager location.
        """
        logger.info(" SEARCH:  TESTING: All files use SSOT Redis imports")
        
        if not hasattr(self, 'scan_results'):
            self.test_scan_all_redis_imports()  # Run scan if not already done
        
        files_needing_ssot = []
        files_using_ssot = []
        
        for file_path, import_info in self.scan_results.items():
            if import_info["needs_redis"]:  # File needs Redis functionality
                if import_info["uses_ssot"]:
                    files_using_ssot.append(file_path)
                else:
                    files_needing_ssot.append(file_path)
        
        ssot_adoption_rate = len(files_using_ssot) / max(len(files_using_ssot) + len(files_needing_ssot), 1)
        
        self.metrics.record_custom("files_using_ssot", len(files_using_ssot))
        self.metrics.record_custom("files_needing_ssot", len(files_needing_ssot))
        self.metrics.record_custom("ssot_adoption_rate", ssot_adoption_rate)
        
        # Should approach 100% adoption (will fail during migration)
        assert ssot_adoption_rate >= 0.95, (
            f" ALERT:  LOW SSOT ADOPTION: Only {ssot_adoption_rate:.1%} of files use SSOT imports. "
            f"Expected >95% adoption. Files needing migration: {len(files_needing_ssot)}"
        )
        
        logger.info(f" PASS:  SSOT adoption rate: {ssot_adoption_rate:.1%} "
                   f"({len(files_using_ssot)} SSOT / {len(files_needing_ssot)} need migration)")
    
    def test_import_consistency_across_services(self):
        """
        Test that import patterns are consistent across all services.
        
        Validates that different services (backend, auth, analytics) all use
        the same SSOT import pattern for Redis functionality.
        """
        logger.info(" SEARCH:  TESTING: Import consistency across services")
        
        if not hasattr(self, 'scan_results'):
            self.test_scan_all_redis_imports()  # Run scan if not already done
        
        service_consistency = self._analyze_import_consistency_by_service()
        
        self.metrics.record_custom("service_consistency", service_consistency)
        
        inconsistent_services = [
            service for service, info in service_consistency.items()
            if info["consistency_score"] < 0.8
        ]
        
        assert len(inconsistent_services) == 0, (
            f" ALERT:  INCONSISTENT IMPORTS: {len(inconsistent_services)} services have inconsistent "
            f"Redis import patterns: {inconsistent_services}. "
            f"All services must use SSOT imports consistently."
        )
        
        logger.info(f" PASS:  Import consistency validated across {len(service_consistency)} services")
    
    def test_no_duplicate_redis_instantiations(self):
        """
        Test that files don't instantiate multiple Redis managers.
        
        Validates that files using Redis create instances through proper
        factory patterns, not direct instantiation of multiple managers.
        """
        logger.info(" SEARCH:  TESTING: No duplicate Redis instantiations")
        
        if not hasattr(self, 'scan_results'):
            self.test_scan_all_redis_imports()  # Run scan if not already done
        
        instantiation_violations = self._scan_redis_instantiation_patterns()
        
        self.metrics.record_custom("instantiation_violations", len(instantiation_violations))
        self.metrics.record_custom("violation_patterns", instantiation_violations)
        
        assert len(instantiation_violations) == 0, (
            f" ALERT:  DUPLICATE INSTANTIATIONS: Found {len(instantiation_violations)} files with "
            f"duplicate Redis manager instantiations. Files must use single SSOT manager. "
            f"Violations: {list(instantiation_violations.keys())[:5]}"
        )
        
        logger.info(" PASS:  No duplicate Redis instantiations found")
    
    def test_expected_import_volume_realistic(self):
        """
        Test that import migration scope matches expected 76 files.
        
        Validates the scope of import migration matches business expectations
        from GitHub issue analysis.
        """
        logger.info(" SEARCH:  TESTING: Expected import volume matches reality")
        
        if not hasattr(self, 'scan_results'):
            self.test_scan_all_redis_imports()  # Run scan if not already done
        
        total_redis_files = len(self.scan_results)
        expected_files = self.context.metadata["files_to_migrate"]
        
        self.metrics.record_custom("actual_files", total_redis_files)
        self.metrics.record_custom("expected_files", expected_files)
        
        # Allow some variance in file count (business estimate may not be exact)
        variance_threshold = 0.3  # 30% variance allowed
        min_expected = int(expected_files * (1 - variance_threshold))
        max_expected = int(expected_files * (1 + variance_threshold))
        
        assert min_expected <= total_redis_files <= max_expected, (
            f" ALERT:  SCOPE MISMATCH: Found {total_redis_files} files with Redis imports, "
            f"expected ~{expected_files} files ( +/- {variance_threshold:.0%}). "
            f"Import migration scope may be different than estimated."
        )
        
        logger.info(f" PASS:  Import volume realistic: {total_redis_files} files "
                   f"(expected ~{expected_files})")
    
    def _scan_redis_imports_comprehensive(self, project_root: Path) -> Dict[str, Dict[str, Any]]:
        """
        Comprehensively scan all Python files for Redis imports.
        
        Returns:
            Dictionary mapping file paths to import analysis details
        """
        all_imports = {}
        
        for directory in self.scan_directories:
            dir_path = project_root / directory
            if not dir_path.exists():
                continue
                
            logger.info(f"Scanning directory: {directory}")
            
            for py_file in dir_path.rglob("*.py"):
                # Skip __pycache__ and other non-source files
                if "__pycache__" in str(py_file) or py_file.name.startswith("."):
                    continue
                
                try:
                    import_info = self._analyze_file_redis_imports(py_file, project_root)
                    if import_info["has_redis_imports"]:
                        relative_path = str(py_file.relative_to(project_root))
                        all_imports[relative_path] = import_info
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze {py_file}: {e}")
        
        return all_imports
    
    def _analyze_file_redis_imports(self, file_path: Path, project_root: Path) -> Dict[str, Any]:
        """Analyze Redis imports in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return {"has_redis_imports": False}
        
        import_info = {
            "has_redis_imports": False,
            "uses_ssot": False,
            "has_violations": False,
            "needs_redis": False,
            "ssot_imports": [],
            "violation_imports": [],
            "redis_usage_patterns": []
        }
        
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Check for SSOT import patterns
            for pattern in self.ssot_import_patterns:
                if pattern in line_stripped:
                    import_info["has_redis_imports"] = True
                    import_info["uses_ssot"] = True
                    import_info["ssot_imports"].append({
                        "line": line_num,
                        "content": line_stripped,
                        "pattern": pattern
                    })
            
            # Check for violation import patterns
            for pattern in self.violation_import_patterns:
                if pattern in line_stripped:
                    import_info["has_redis_imports"] = True
                    import_info["has_violations"] = True
                    import_info["violation_imports"].append({
                        "line": line_num,
                        "content": line_stripped,
                        "pattern": pattern
                    })
            
            # Check if file needs Redis functionality (uses Redis operations)
            redis_usage_indicators = [
                ".get(", ".set(", ".delete(", ".ping()", 
                "redis", "Redis", "cache", "session"
            ]
            if any(indicator in line_stripped.lower() for indicator in redis_usage_indicators):
                import_info["needs_redis"] = True
                import_info["redis_usage_patterns"].append({
                    "line": line_num,
                    "usage": line_stripped
                })
        
        return import_info
    
    def _analyze_import_consistency_by_service(self) -> Dict[str, Dict[str, Any]]:
        """Analyze import consistency within each service."""
        service_consistency = {}
        
        for file_path, import_info in self.scan_results.items():
            # Determine service from file path
            service = self._determine_service_from_path(file_path)
            
            if service not in service_consistency:
                service_consistency[service] = {
                    "total_files": 0,
                    "ssot_files": 0,
                    "violation_files": 0,
                    "consistency_score": 0.0
                }
            
            service_consistency[service]["total_files"] += 1
            
            if import_info["uses_ssot"]:
                service_consistency[service]["ssot_files"] += 1
            
            if import_info["has_violations"]:
                service_consistency[service]["violation_files"] += 1
        
        # Calculate consistency scores
        for service, info in service_consistency.items():
            if info["total_files"] > 0:
                info["consistency_score"] = info["ssot_files"] / info["total_files"]
        
        return service_consistency
    
    def _determine_service_from_path(self, file_path: str) -> str:
        """Determine service name from file path."""
        if file_path.startswith("netra_backend/"):
            return "backend"
        elif file_path.startswith("auth_service/"):
            return "auth"
        elif file_path.startswith("analytics_service/"):
            return "analytics"
        elif file_path.startswith("frontend/"):
            return "frontend"
        elif file_path.startswith("tests/"):
            return "tests"
        elif file_path.startswith("test_framework/"):
            return "test_framework"
        elif file_path.startswith("scripts/"):
            return "scripts"
        else:
            return "unknown"
    
    def _scan_redis_instantiation_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Scan for files with multiple Redis manager instantiations."""
        violations = {}
        
        for file_path, import_info in self.scan_results.items():
            instantiation_patterns = []
            
            # Check usage patterns for multiple instantiations
            for usage in import_info.get("redis_usage_patterns", []):
                usage_content = usage["usage"].lower()
                
                # Look for instantiation patterns
                if any(pattern in usage_content for pattern in [
                    "redismanager(", "redis_manager(", "redis.redis(",
                    "= redis", "= Redis"
                ]):
                    instantiation_patterns.append(usage)
            
            # If multiple instantiation patterns found, it's a violation
            if len(instantiation_patterns) > 1:
                violations[file_path] = instantiation_patterns
        
        return violations
    
    def tearDown(self):
        """Clean up test and record final metrics."""
        self.metrics.end_timing()
        
        total_files = self.metrics.get_custom("total_files_with_redis", 0)
        violations = self.metrics.get_custom("violation_imports", 0)
        ssot_adoption = self.metrics.get_custom("ssot_adoption_rate", 0.0)
        
        logger.info(f" ALERT:  Redis Import Migration Test Complete:")
        logger.info(f"   - Total files with Redis: {total_files}")
        logger.info(f"   - Files with violations: {violations}")
        logger.info(f"   - SSOT adoption rate: {ssot_adoption:.1%}")
        
        if violations > 0:
            logger.error(f"DEPLOYMENT BLOCKER: {violations} files need import migration. "
                        f"GitHub Issue #190 import migration incomplete.")
        else:
            logger.info(" PASS:  Redis import migration appears complete")
        
        super().tearDown()


if __name__ == "__main__":
    # Run as standalone test
    pytest.main([__file__, "-v", "--tb=short"])