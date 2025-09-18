"""
SSOT Test: Configuration Fragmentation - Conftest Consolidation Detection

This test validates SSOT compliance by detecting fragmented conftest.py files across the project.
It should FAIL initially to demonstrate the configuration fragmentation problem exists.

Purpose: Identify conftest.py file duplication that violates SSOT principles
Business Value: Platform/Internal - Test Infrastructure Stability & Maintainability
SSOT Requirement: Single authoritative conftest.py configuration per service boundary

Expected Behavior: 
- FAIL initially by finding 15+ conftest files showing fragmentation
- Pass after SSOT consolidation reduces conftest files to service boundaries
- Validate proper configuration inheritance patterns

Test Plan Reference: Configuration SSOT Consolidation Phase 1
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class ConftestAnalysis:
    """Analysis results for conftest.py file fragmentation."""
    total_conftest_files: int = 0
    project_conftest_files: List[str] = field(default_factory=list)
    service_boundaries: Dict[str, List[str]] = field(default_factory=dict)
    fragmentation_violations: List[str] = field(default_factory=list)
    consolidation_opportunities: List[str] = field(default_factory=list)
    external_files_excluded: int = 0


class TestSsotConftestConsolidation(SSotBaseTestCase):
    """
    SSOT validation test for conftest.py file consolidation.
    
    This test enforces SSOT principles by detecting configuration fragmentation
    in conftest.py files and validating proper service boundary isolation.
    """
    
    def setup_method(self, method=None):
        """Setup test environment for SSOT conftest validation."""
        super().setup_method(method)
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.record_metric("test_type", "ssot_configuration_validation")
        
        # Define service boundaries for SSOT compliance
        self.service_boundaries = {
            "main_backend": ["netra_backend"],
            "auth_service": ["auth_service"],
            "frontend": ["frontend"],
            "test_framework": ["test_framework", "tests"],
            "shared_utilities": ["shared"]
        }
        
        # Define allowed conftest patterns for SSOT compliance
        self.allowed_conftest_patterns = [
            "tests/conftest.py",  # Main test configuration
            "netra_backend/conftest.py",  # Backend service boundary
            "auth_service/conftest.py",  # Auth service boundary (if exists)
            "frontend/tests/conftest.py",  # Frontend service boundary
            "test_framework/conftest.py"  # Test framework boundary (if needed)
        ]

    def test_conftest_fragmentation_detection_should_fail_initially(self):
        """
        Detect conftest.py fragmentation violations - SHOULD FAIL to demonstrate problem.
        
        This test is designed to FAIL initially by finding too many conftest.py files,
        demonstrating the configuration fragmentation issue that needs SSOT consolidation.
        
        Expected Initial Result: FAIL - Find 15+ conftest files showing fragmentation
        Expected After SSOT: PASS - Reduced to service boundary conftest files only
        """
        analysis = self._analyze_conftest_fragmentation()
        
        # Record metrics for monitoring SSOT progress
        self.record_metric("total_conftest_files", analysis.total_conftest_files)
        self.record_metric("project_conftest_files", len(analysis.project_conftest_files))
        self.record_metric("fragmentation_violations", len(analysis.fragmentation_violations))
        self.record_metric("external_files_excluded", analysis.external_files_excluded)
        
        # Log detailed analysis for debugging
        self.logger.info(f"Conftest fragmentation analysis:")
        self.logger.info(f"  Total conftest files found: {analysis.total_conftest_files}")
        self.logger.info(f"  Project conftest files: {len(analysis.project_conftest_files)}")
        self.logger.info(f"  External files excluded: {analysis.external_files_excluded}")
        self.logger.info(f"  Fragmentation violations: {len(analysis.fragmentation_violations)}")
        
        if analysis.project_conftest_files:
            self.logger.info("Project conftest files found:")
            for conftest_file in analysis.project_conftest_files[:10]:  # Show first 10
                relative_path = Path(conftest_file).relative_to(self.project_root)
                self.logger.info(f"    {relative_path}")
            if len(analysis.project_conftest_files) > 10:
                self.logger.info(f"    ... and {len(analysis.project_conftest_files) - 10} more")
        
        # CRITICAL SSOT VIOLATION DETECTION
        # This assertion is designed to FAIL initially, demonstrating the fragmentation problem
        self.assertTrue(
            len(analysis.project_conftest_files) <= 5,
            f"SSOT VIOLATION: Found {len(analysis.project_conftest_files)} conftest.py files "
            f"in project (should be ≤5 for proper service boundaries). "
            f"This indicates configuration fragmentation that violates SSOT principles. "
            f"Files found: {[str(Path(f).relative_to(self.project_root)) for f in analysis.project_conftest_files[:10]]}"
            f"{'...' if len(analysis.project_conftest_files) > 10 else ''}"
        )
        
        # Additional SSOT validation - check for unauthorized conftest files
        unauthorized_conftest = self._find_unauthorized_conftest_files(analysis.project_conftest_files)
        self.assertEqual(
            len(unauthorized_conftest), 0,
            f"SSOT VIOLATION: Found {len(unauthorized_conftest)} unauthorized conftest.py files "
            f"that violate service boundary isolation: {unauthorized_conftest[:5]}"
            f"{'...' if len(unauthorized_conftest) > 5 else ''}"
        )

    def test_service_boundary_isolation_validation(self):
        """
        Validate that conftest files respect service boundary isolation.
        
        Each service should have its own conftest.py file at the service root only,
        not scattered throughout subdirectories within the service.
        """
        analysis = self._analyze_conftest_fragmentation()
        
        # Group conftest files by service boundary
        service_conftest_mapping = self._group_conftest_by_service(analysis.project_conftest_files)
        
        self.record_metric("services_with_conftest", len(service_conftest_mapping))
        
        for service_name, conftest_files in service_conftest_mapping.items():
            self.logger.info(f"Service '{service_name}' conftest files: {len(conftest_files)}")
            
            # Each service should have minimal conftest files (ideally 1-2 max)
            if len(conftest_files) > 2:
                self.logger.warning(f"Service '{service_name}' has {len(conftest_files)} conftest files:")
                for conftest_file in conftest_files:
                    relative_path = Path(conftest_file).relative_to(self.project_root)
                    self.logger.warning(f"    {relative_path}")
            
            # SSOT requirement: Each service should have minimal conftest fragmentation
            self.assertLessEqual(
                len(conftest_files), 3,
                f"SSOT VIOLATION: Service '{service_name}' has {len(conftest_files)} conftest files "
                f"(should be ≤3 for proper isolation). Files: "
                f"{[str(Path(f).relative_to(self.project_root)) for f in conftest_files]}"
            )

    def test_configuration_inheritance_patterns(self):
        """
        Validate that conftest files follow proper inheritance patterns.
        
        Conftest files should follow a clear hierarchy:
        1. Root conftest.py (main configuration)
        2. Service conftest.py (service-specific configuration)
        3. Minimal subdirectory conftest.py (only if absolutely necessary)
        """
        analysis = self._analyze_conftest_fragmentation()
        
        # Analyze inheritance patterns
        inheritance_violations = []
        deep_nesting_violations = []
        
        for conftest_file in analysis.project_conftest_files:
            relative_path = Path(conftest_file).relative_to(self.project_root)
            path_parts = relative_path.parts
            
            # Check for deep nesting (more than 3 levels deep)
            if len(path_parts) > 4:  # e.g., tests/category/subcategory/conftest.py = 4 parts
                deep_nesting_violations.append(str(relative_path))
            
            # Check for conftest files in unexpected locations
            if not self._is_conftest_location_authorized(relative_path):
                inheritance_violations.append(str(relative_path))
        
        self.record_metric("deep_nesting_violations", len(deep_nesting_violations))
        self.record_metric("inheritance_violations", len(inheritance_violations))
        
        if deep_nesting_violations:
            self.logger.warning(f"Deep nesting violations found: {deep_nesting_violations}")
        
        if inheritance_violations:
            self.logger.warning(f"Inheritance pattern violations found: {inheritance_violations}")
        
        # SSOT requirements for proper configuration inheritance
        self.assertEqual(
            len(deep_nesting_violations), 0,
            f"SSOT VIOLATION: Found {len(deep_nesting_violations)} conftest files with excessive nesting "
            f"(>4 levels deep): {deep_nesting_violations}. This violates SSOT configuration hierarchy."
        )
        
        # Allow some inheritance violations initially, but track them for improvement
        if len(inheritance_violations) > 10:
            self.fail(
                f"SSOT VIOLATION: Found {len(inheritance_violations)} conftest files in "
                f"unauthorized locations: {inheritance_violations[:5]}... "
                f"This severely violates SSOT configuration patterns."
            )

    def _analyze_conftest_fragmentation(self) -> ConftestAnalysis:
        """Analyze conftest.py file fragmentation across the project."""
        analysis = ConftestAnalysis()
        
        try:
            # Find all conftest.py files in project
            result = subprocess.run([
                "find", str(self.project_root), "-name", "conftest.py",
                "-not", "-path", "*/.test_venv/*",
                "-not", "-path", "*/node_modules/*", 
                "-not", "-path", "*/google-cloud-sdk/*",
                "-not", "-path", "*/__pycache__/*"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                all_conftest_files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                analysis.total_conftest_files = len(all_conftest_files)
                
                # Filter to project files only (exclude external dependencies)
                for conftest_file in all_conftest_files:
                    if self._is_project_conftest_file(conftest_file):
                        analysis.project_conftest_files.append(conftest_file)
                    else:
                        analysis.external_files_excluded += 1
                
                # Analyze fragmentation patterns
                analysis.fragmentation_violations = self._identify_fragmentation_violations(
                    analysis.project_conftest_files
                )
                analysis.consolidation_opportunities = self._identify_consolidation_opportunities(
                    analysis.project_conftest_files
                )
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            self.logger.error(f"Failed to analyze conftest fragmentation: {e}")
            # Set minimal data to avoid test failure due to analysis issues
            analysis.total_conftest_files = 999  # High number to trigger SSOT violation
            analysis.project_conftest_files = ["analysis_failed"] * 20  # Trigger violation
        
        return analysis

    def _is_project_conftest_file(self, conftest_file: str) -> bool:
        """Check if conftest file belongs to project (not external dependencies)."""
        excluded_patterns = [
            "/.test_venv/", "/node_modules/", "/google-cloud-sdk/", 
            "/__pycache__/", "/temp/temporary_files/"
        ]
        
        for pattern in excluded_patterns:
            if pattern in conftest_file:
                return False
        
        return True

    def _find_unauthorized_conftest_files(self, project_conftest_files: List[str]) -> List[str]:
        """Find conftest files that don't follow authorized patterns."""
        unauthorized = []
        
        for conftest_file in project_conftest_files:
            relative_path = Path(conftest_file).relative_to(self.project_root)
            
            # Check against allowed patterns
            is_authorized = False
            for allowed_pattern in self.allowed_conftest_patterns:
                if str(relative_path) == allowed_pattern or str(relative_path).endswith("/" + allowed_pattern):
                    is_authorized = True
                    break
            
            # Also allow conftest files in direct test subdirectories (limited depth)
            if not is_authorized and self._is_reasonable_test_conftest(relative_path):
                is_authorized = True
            
            if not is_authorized:
                unauthorized.append(str(relative_path))
        
        return unauthorized

    def _is_reasonable_test_conftest(self, relative_path: Path) -> bool:
        """Check if conftest file is in a reasonable test subdirectory location."""
        path_str = str(relative_path)
        
        # Allow conftest in direct test subdirectories with reasonable naming
        reasonable_patterns = [
            "/tests/", "/test/", "tests/", "test/"
        ]
        
        # Allow reasonable depth for test organization
        path_parts = relative_path.parts
        if len(path_parts) <= 4:  # e.g., tests/integration/conftest.py = 3 parts
            for pattern in reasonable_patterns:
                if pattern in path_str:
                    return True
        
        return False

    def _group_conftest_by_service(self, project_conftest_files: List[str]) -> Dict[str, List[str]]:
        """Group conftest files by service boundary."""
        service_mapping = {}
        
        for conftest_file in project_conftest_files:
            relative_path = Path(conftest_file).relative_to(self.project_root)
            service_name = self._determine_service_boundary(relative_path)
            
            if service_name not in service_mapping:
                service_mapping[service_name] = []
            service_mapping[service_name].append(conftest_file)
        
        return service_mapping

    def _determine_service_boundary(self, relative_path: Path) -> str:
        """Determine which service boundary a conftest file belongs to."""
        path_parts = relative_path.parts
        
        if not path_parts:
            return "unknown"
        
        # Check service boundaries
        first_part = path_parts[0]
        for service_name, service_dirs in self.service_boundaries.items():
            if first_part in service_dirs:
                return service_name
        
        # Default categorization
        if "test" in first_part.lower():
            return "test_framework"
        else:
            return f"service_{first_part}"

    def _identify_fragmentation_violations(self, project_conftest_files: List[str]) -> List[str]:
        """Identify specific fragmentation violations."""
        violations = []
        
        # Look for excessive conftest files in single directories
        dir_conftest_count = {}
        for conftest_file in project_conftest_files:
            dir_path = Path(conftest_file).parent
            dir_conftest_count[str(dir_path)] = dir_conftest_count.get(str(dir_path), 0) + 1
        
        for dir_path, count in dir_conftest_count.items():
            if count > 1:
                violations.append(f"Multiple conftest files in {dir_path}: {count}")
        
        return violations

    def _identify_consolidation_opportunities(self, project_conftest_files: List[str]) -> List[str]:
        """Identify opportunities for conftest consolidation."""
        opportunities = []
        
        # Group by parent directories to find consolidation opportunities
        parent_dirs = {}
        for conftest_file in project_conftest_files:
            parent_dir = Path(conftest_file).parent.parent  # Go up one level
            parent_key = str(parent_dir)
            
            if parent_key not in parent_dirs:
                parent_dirs[parent_key] = []
            parent_dirs[parent_key].append(conftest_file)
        
        for parent_dir, conftest_files in parent_dirs.items():
            if len(conftest_files) > 2:
                opportunities.append(
                    f"Consolidate {len(conftest_files)} conftest files under {parent_dir}"
                )
        
        return opportunities

    def _is_conftest_location_authorized(self, relative_path: Path) -> bool:
        """Check if conftest location follows authorized patterns."""
        path_str = str(relative_path)
        
        # Define authorized location patterns
        authorized_patterns = [
            "tests/conftest.py",
            "netra_backend/conftest.py", 
            "auth_service/conftest.py",
            "frontend/tests/conftest.py",
            "test_framework/conftest.py"
        ]
        
        # Check exact matches
        for pattern in authorized_patterns:
            if path_str == pattern:
                return True
        
        # Allow reasonable test subdirectory patterns
        if ("tests/" in path_str or "test/" in path_str) and len(relative_path.parts) <= 4:
            return True
        
        return False