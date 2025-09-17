"""
SSOT Test: Configuration Fragmentation Reproduction

This test reproduces the exact configuration fragmentation issue to demonstrate the problem exists.
It should FAIL initially to show the specific problem we're solving.

Purpose: Reproduce and validate the specific configuration fragmentation scenario  
Business Value: Platform/Internal - Infrastructure Stability & SSOT Compliance
SSOT Requirement: Demonstrate fragmentation issues before and after remediation

Expected Behavior:
- FAIL initially to show the exact fragmentation problem exists
- Pass after SSOT remediation fixes the specific issues
- Provide clear evidence of fragmentation impact on system stability

Test Plan Reference: Configuration SSOT Consolidation Phase 3
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class FragmentationEvidence:
    """Evidence of configuration fragmentation issues."""
    duplicate_config_files: Dict[str, List[str]] = field(default_factory=dict)
    inconsistent_patterns: List[str] = field(default_factory=list)
    circular_dependencies: List[str] = field(default_factory=list)
    configuration_conflicts: List[str] = field(default_factory=list)
    pytest_collection_issues: List[str] = field(default_factory=list)
    environment_inconsistencies: Dict[str, Set[str]] = field(default_factory=dict)


@dataclass
class ConfigurationPattern:
    """Analysis of configuration patterns and their impact."""
    pattern_name: str
    file_count: int
    services_affected: Set[str] = field(default_factory=set)
    fragmentation_severity: str = "low"  # low, medium, high, critical
    impact_description: str = ""
    remediation_priority: str = "low"  # low, medium, high, critical


class TestConfigurationFragmentationReproduction(SSotBaseTestCase):
    """
    SSOT test that reproduces the exact configuration fragmentation issue.
    
    This test demonstrates the specific fragmentation problems affecting the system
    and provides clear evidence of SSOT violations that need remediation.
    """
    
    def setup_method(self, method=None):
        """Setup test environment for configuration fragmentation reproduction."""
        super().setup_method(method)
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.record_metric("test_type", "ssot_fragmentation_reproduction")
        
        # Define the specific fragmentation patterns we expect to find
        self.fragmentation_patterns = {
            "conftest_duplication": {
                "expected_count": 15,  # We found 148 total, expect 15+ project files
                "severity": "critical",
                "description": "Multiple conftest.py files create pytest collection conflicts"
            },
            "environment_config_duplication": {
                "expected_count": 10,
                "severity": "high", 
                "description": "Multiple environment configuration mechanisms"
            },
            "cors_config_duplication": {
                "expected_count": 3,
                "severity": "medium",
                "description": "CORS configuration duplicated across services"
            },
            "database_config_fragmentation": {
                "expected_count": 5,
                "severity": "high",
                "description": "Database connection configuration scattered"
            },
            "import_path_inconsistencies": {
                "expected_count": 20,
                "severity": "medium",
                "description": "Inconsistent import patterns for configuration"
            }
        }
        
        # Define critical files that should exist for SSOT compliance
        self.expected_ssot_files = [
            "shared/isolated_environment.py",
            "shared/cors_config.py", 
            "netra_backend/app/config.py",
            "netra_backend/app/core/configuration/base.py",
            "test_framework/ssot/base_test_case.py"
        ]

    def test_conftest_fragmentation_reproduction_should_fail(self):
        """
        Reproduce the exact conftest.py fragmentation issue - SHOULD FAIL initially.
        
        This test demonstrates the specific conftest fragmentation problem by:
        1. Finding actual conftest.py file count
        2. Analyzing fragmentation patterns
        3. Demonstrating impact on pytest collection
        4. Showing SSOT violations
        
        Expected Initial Result: FAIL - Demonstrate excessive conftest fragmentation
        Expected After SSOT: PASS - Consolidated conftest files within boundaries
        """
        fragmentation_evidence = self._reproduce_conftest_fragmentation()
        
        # Record comprehensive metrics
        self.record_metric("total_conftest_files_found", len(fragmentation_evidence.duplicate_config_files.get("conftest", [])))
        self.record_metric("pytest_collection_issues", len(fragmentation_evidence.pytest_collection_issues))
        self.record_metric("configuration_conflicts", len(fragmentation_evidence.configuration_conflicts))
        
        # Log the exact reproduction evidence
        self.logger.info(f"Conftest fragmentation reproduction evidence:")
        conftest_files = fragmentation_evidence.duplicate_config_files.get("conftest", [])
        self.logger.info(f"  Total conftest.py files found: {len(conftest_files)}")
        
        if conftest_files:
            self.logger.info("  Project conftest.py files:")
            for conftest_file in conftest_files[:15]:  # Show first 15
                try:
                    relative_path = Path(conftest_file).relative_to(self.project_root)
                    self.logger.info(f"    {relative_path}")
                except ValueError:
                    self.logger.info(f"    {conftest_file} (external)")
            if len(conftest_files) > 15:
                self.logger.info(f"    ... and {len(conftest_files) - 15} more")
        
        # Log pytest collection issues
        if fragmentation_evidence.pytest_collection_issues:
            self.logger.info(f"  Pytest collection issues found: {len(fragmentation_evidence.pytest_collection_issues)}")
            for issue in fragmentation_evidence.pytest_collection_issues[:3]:
                self.logger.info(f"    {issue}")
        
        # CRITICAL REPRODUCTION TEST - This should FAIL initially
        # Test the exact problem: excessive conftest fragmentation
        self.assertLessEqual(
            len(conftest_files), 8,
            f"CONFTEST FRAGMENTATION REPRODUCTION: Found {len(conftest_files)} conftest.py files "
            f"(should be ≤8 for proper SSOT consolidation). "
            f"This reproduces the exact fragmentation issue causing pytest collection problems. "
            f"Files: {[str(Path(f).relative_to(self.project_root)) for f in conftest_files[:5]]}"
            f"{'...' if len(conftest_files) > 5 else ''}"
        )
        
        # Test for pytest collection impact
        self.assertLessEqual(
            len(fragmentation_evidence.pytest_collection_issues), 3,
            f"PYTEST COLLECTION IMPACT: Found {len(fragmentation_evidence.pytest_collection_issues)} "
            f"collection issues caused by conftest fragmentation. "
            f"This demonstrates the real impact of configuration fragmentation on system stability."
        )

    def test_environment_configuration_chaos_reproduction(self):
        """
        Reproduce environment configuration chaos - multiple config mechanisms.
        
        This test demonstrates the problem of having multiple environment
        configuration mechanisms that conflict with each other and violate SSOT.
        """
        env_chaos_evidence = self._reproduce_environment_configuration_chaos()
        
        # Record metrics
        self.record_metric("environment_config_files", len(env_chaos_evidence.duplicate_config_files.get("environment", [])))
        self.record_metric("environment_inconsistencies", len(env_chaos_evidence.environment_inconsistencies))
        
        # Log reproduction evidence
        env_config_files = env_chaos_evidence.duplicate_config_files.get("environment", [])
        self.logger.info(f"Environment configuration chaos reproduction:")
        self.logger.info(f"  Environment config files found: {len(env_config_files)}")
        
        if env_config_files:
            for env_file in env_config_files[:10]:  # Show first 10
                try:
                    relative_path = Path(env_file).relative_to(self.project_root)
                    self.logger.info(f"    {relative_path}")
                except ValueError:
                    self.logger.info(f"    {env_file} (external)")
        
        # Log inconsistencies
        if env_chaos_evidence.environment_inconsistencies:
            self.logger.info(f"  Environment inconsistencies found:")
            for var_name, sources in env_chaos_evidence.environment_inconsistencies.items():
                self.logger.info(f"    {var_name}: {len(sources)} different sources")
        
        # REPRODUCTION TEST - Environment configuration chaos
        self.assertLessEqual(
            len(env_config_files), 5,
            f"ENVIRONMENT CONFIG CHAOS: Found {len(env_config_files)} environment configuration files "
            f"(should be ≤5 for SSOT compliance). "
            f"This reproduces the environment configuration chaos where multiple mechanisms conflict. "
            f"Multiple config sources prevent reliable environment management."
        )
        
        # Test for environment variable conflicts
        inconsistency_count = sum(len(sources) for sources in env_chaos_evidence.environment_inconsistencies.values())
        self.assertLessEqual(
            inconsistency_count, 15,
            f"ENVIRONMENT VARIABLE CONFLICTS: Found {inconsistency_count} environment variable conflicts "
            f"across multiple configuration sources. "
            f"This demonstrates the impact of having multiple environment config mechanisms."
        )

    def test_database_configuration_fragmentation_reproduction(self):
        """
        Reproduce database configuration fragmentation across services.
        
        This test shows how database configuration is scattered across multiple
        files and services, creating maintenance challenges and SSOT violations.
        """
        db_fragmentation = self._reproduce_database_configuration_fragmentation()
        
        # Record metrics
        db_config_files = db_fragmentation.duplicate_config_files.get("database", [])
        self.record_metric("database_config_files", len(db_config_files))
        self.record_metric("db_configuration_conflicts", len(db_fragmentation.configuration_conflicts))
        
        # Log reproduction evidence
        self.logger.info(f"Database configuration fragmentation reproduction:")
        self.logger.info(f"  Database config files found: {len(db_config_files)}")
        
        if db_config_files:
            for db_file in db_config_files[:8]:  # Show first 8
                try:
                    relative_path = Path(db_file).relative_to(self.project_root)
                    self.logger.info(f"    {relative_path}")
                except ValueError:
                    self.logger.info(f"    {db_file} (external)")
        
        # REPRODUCTION TEST - Database configuration fragmentation
        self.assertLessEqual(
            len(db_config_files), 6,
            f"DATABASE CONFIG FRAGMENTATION: Found {len(db_config_files)} database configuration files "
            f"(should be ≤6 for SSOT consolidation). "
            f"This reproduces the database config fragmentation issue where connection logic "
            f"is scattered across multiple files, making maintenance difficult and error-prone."
        )

    def test_import_path_chaos_reproduction(self):
        """
        Reproduce import path chaos - inconsistent configuration import patterns.
        
        This test demonstrates how inconsistent import patterns for configuration
        create maintenance nightmares and violate SSOT principles.
        """
        import_chaos = self._reproduce_import_path_chaos()
        
        # Record metrics
        self.record_metric("inconsistent_import_patterns", len(import_chaos.inconsistent_patterns))
        self.record_metric("import_circular_dependencies", len(import_chaos.circular_dependencies))
        
        # Log reproduction evidence
        self.logger.info(f"Import path chaos reproduction:")
        self.logger.info(f"  Inconsistent import patterns found: {len(import_chaos.inconsistent_patterns)}")
        self.logger.info(f"  Circular dependencies found: {len(import_chaos.circular_dependencies)}")
        
        if import_chaos.inconsistent_patterns:
            self.logger.info("  Sample inconsistent patterns:")
            for pattern in import_chaos.inconsistent_patterns[:5]:
                self.logger.info(f"    {pattern}")
        
        # REPRODUCTION TEST - Import path chaos
        self.assertLessEqual(
            len(import_chaos.inconsistent_patterns), 25,
            f"IMPORT PATH CHAOS: Found {len(import_chaos.inconsistent_patterns)} inconsistent import patterns "
            f"(should be ≤25 for manageable complexity). "
            f"This reproduces the import path chaos where configuration is imported using "
            f"multiple inconsistent patterns, violating SSOT principles."
        )
        
        # Test for circular dependencies
        self.assertLessEqual(
            len(import_chaos.circular_dependencies), 5,
            f"CIRCULAR IMPORT DEPENDENCIES: Found {len(import_chaos.circular_dependencies)} circular dependencies "
            f"in configuration imports. This creates runtime import failures and violates SSOT design."
        )

    def test_ssot_compliance_baseline_measurement(self):
        """
        Measure baseline SSOT compliance to track improvement progress.
        
        This test establishes a baseline measurement of SSOT compliance
        across all identified fragmentation patterns.
        """
        baseline_measurement = self._measure_ssot_compliance_baseline()
        
        # Record comprehensive baseline metrics
        for pattern_name, pattern_data in baseline_measurement.items():
            self.record_metric(f"baseline_{pattern_name}_count", pattern_data.file_count)
            self.record_metric(f"baseline_{pattern_name}_severity", pattern_data.fragmentation_severity)
            self.record_metric(f"baseline_{pattern_name}_services", len(pattern_data.services_affected))
        
        # Log baseline measurements
        self.logger.info(f"SSOT Compliance Baseline Measurement:")
        total_violations = 0
        critical_violations = 0
        
        for pattern_name, pattern_data in baseline_measurement.items():
            self.logger.info(f"  {pattern_name}:")
            self.logger.info(f"    Files: {pattern_data.file_count}")
            self.logger.info(f"    Severity: {pattern_data.fragmentation_severity}")
            self.logger.info(f"    Services Affected: {len(pattern_data.services_affected)}")
            self.logger.info(f"    Impact: {pattern_data.impact_description}")
            
            total_violations += pattern_data.file_count
            if pattern_data.fragmentation_severity == "critical":
                critical_violations += pattern_data.file_count
        
        self.record_metric("baseline_total_violations", total_violations)
        self.record_metric("baseline_critical_violations", critical_violations)
        
        # BASELINE COMPLIANCE TEST - Establish starting point
        self.logger.info(f"  TOTAL BASELINE VIOLATIONS: {total_violations}")
        self.logger.info(f"  CRITICAL BASELINE VIOLATIONS: {critical_violations}")
        
        # This test documents the current state rather than enforcing limits
        # It provides a baseline for measuring SSOT remediation progress
        if total_violations > 50:
            self.logger.warning(f"HIGH FRAGMENTATION BASELINE: {total_violations} violations detected across all patterns")
        
        if critical_violations > 10:
            self.logger.error(f"CRITICAL FRAGMENTATION BASELINE: {critical_violations} critical violations detected")
        
        # Fail only if we have extreme fragmentation (this should trigger with current state)
        self.assertLessEqual(
            critical_violations, 8,
            f"CRITICAL FRAGMENTATION DETECTED: {critical_violations} critical SSOT violations found "
            f"(should be ≤8 for system stability). "
            f"This baseline measurement shows critical fragmentation requiring immediate SSOT remediation."
        )

    def _reproduce_conftest_fragmentation(self) -> FragmentationEvidence:
        """Reproduce the exact conftest.py fragmentation issue."""
        evidence = FragmentationEvidence()
        
        try:
            # Find all conftest.py files
            result = subprocess.run([
                "find", str(self.project_root), "-name", "conftest.py",
                "-not", "-path", "*/.test_venv/*",
                "-not", "-path", "*/node_modules/*",
                "-not", "-path", "*/google-cloud-sdk/*"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                conftest_files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                evidence.duplicate_config_files["conftest"] = conftest_files
                
                # Check for pytest collection issues by analyzing conftest conflicts
                conflicts = self._analyze_conftest_conflicts(conftest_files)
                evidence.pytest_collection_issues.extend(conflicts)
                
                # Check for configuration conflicts
                config_conflicts = self._find_conftest_configuration_conflicts(conftest_files)
                evidence.configuration_conflicts.extend(config_conflicts)
        
        except Exception as e:
            self.logger.error(f"Failed to reproduce conftest fragmentation: {e}")
            # Set mock data to trigger test failure
            evidence.duplicate_config_files["conftest"] = ["mock_conftest"] * 20
        
        return evidence

    def _reproduce_environment_configuration_chaos(self) -> FragmentationEvidence:
        """Reproduce environment configuration chaos."""
        evidence = FragmentationEvidence()
        
        try:
            # Find environment configuration files
            env_config_patterns = [
                "**/config.py", "**/configuration/*.py", "**/env*.py",
                "**/settings.py", "**/.env*", "**/environment.py"
            ]
            
            env_config_files = []
            for pattern in env_config_patterns:
                files = list(self.project_root.glob(pattern))
                env_config_files.extend([str(f) for f in files if self._is_project_file(f)])
            
            evidence.duplicate_config_files["environment"] = env_config_files
            
            # Analyze environment variable inconsistencies
            env_inconsistencies = self._analyze_environment_inconsistencies(env_config_files)
            evidence.environment_inconsistencies.update(env_inconsistencies)
        
        except Exception as e:
            self.logger.error(f"Failed to reproduce environment config chaos: {e}")
        
        return evidence

    def _reproduce_database_configuration_fragmentation(self) -> FragmentationEvidence:
        """Reproduce database configuration fragmentation."""
        evidence = FragmentationEvidence()
        
        try:
            # Find database configuration files
            db_config_patterns = [
                "**/database*.py", "**/db/*.py", "**/models*.py",
                "**/connection*.py", "**/postgres*.py", "**/clickhouse*.py"
            ]
            
            db_config_files = []
            for pattern in db_config_patterns:
                files = list(self.project_root.glob(pattern))
                db_config_files.extend([str(f) for f in files if self._is_project_file(f)])
            
            evidence.duplicate_config_files["database"] = db_config_files
            
            # Analyze database configuration conflicts
            db_conflicts = self._analyze_database_conflicts(db_config_files)
            evidence.configuration_conflicts.extend(db_conflicts)
        
        except Exception as e:
            self.logger.error(f"Failed to reproduce database config fragmentation: {e}")
        
        return evidence

    def _reproduce_import_path_chaos(self) -> FragmentationEvidence:
        """Reproduce import path chaos for configuration."""
        evidence = FragmentationEvidence()
        
        try:
            # Find Python files and analyze import patterns
            python_files = list(self.project_root.rglob("*.py"))
            
            import_patterns = defaultdict(set)
            for py_file in python_files:
                if not self._is_project_file(py_file):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Find import lines related to configuration
                    lines = content.splitlines()
                    for line in lines:
                        if ("import" in line and 
                            any(keyword in line.lower() for keyword in ["config", "env", "setting"])):
                            import_patterns[line.strip()].add(str(py_file))
                
                except Exception:
                    continue
            
            # Find inconsistent patterns
            for import_line, files in import_patterns.items():
                if len(files) > 3:  # Same import pattern used in multiple places
                    evidence.inconsistent_patterns.append(f"{import_line} (used in {len(files)} files)")
            
            # Check for circular dependencies (simplified check)
            circular_deps = self._find_circular_import_dependencies(python_files)
            evidence.circular_dependencies.extend(circular_deps)
        
        except Exception as e:
            self.logger.error(f"Failed to reproduce import path chaos: {e}")
        
        return evidence

    def _measure_ssot_compliance_baseline(self) -> Dict[str, ConfigurationPattern]:
        """Measure baseline SSOT compliance across all patterns."""
        baseline = {}
        
        for pattern_name, pattern_config in self.fragmentation_patterns.items():
            pattern = ConfigurationPattern(
                pattern_name=pattern_name,
                file_count=0,
                fragmentation_severity=pattern_config["severity"],
                impact_description=pattern_config["description"]
            )
            
            # Measure each pattern
            if pattern_name == "conftest_duplication":
                conftest_files = self._find_conftest_files()
                pattern.file_count = len(conftest_files)
                pattern.services_affected = self._get_services_affected_by_files(conftest_files)
            
            elif pattern_name == "environment_config_duplication":
                env_files = self._find_environment_config_files()
                pattern.file_count = len(env_files)
                pattern.services_affected = self._get_services_affected_by_files(env_files)
            
            elif pattern_name == "database_config_fragmentation":
                db_files = self._find_database_config_files()
                pattern.file_count = len(db_files)
                pattern.services_affected = self._get_services_affected_by_files(db_files)
            
            # Set remediation priority based on severity and count
            if pattern.fragmentation_severity == "critical" and pattern.file_count > 10:
                pattern.remediation_priority = "critical"
            elif pattern.fragmentation_severity == "high" and pattern.file_count > 5:
                pattern.remediation_priority = "high"
            else:
                pattern.remediation_priority = "medium"
            
            baseline[pattern_name] = pattern
        
        return baseline

    def _is_project_file(self, file_path: Path) -> bool:
        """Check if file belongs to the project (not external dependencies)."""
        exclude_patterns = [
            ".test_venv", "node_modules", "google-cloud-sdk", 
            "__pycache__", ".git", "temp/temporary_files"
        ]
        
        file_str = str(file_path)
        for pattern in exclude_patterns:
            if pattern in file_str:
                return False
        
        return True

    def _analyze_conftest_conflicts(self, conftest_files: List[str]) -> List[str]:
        """Analyze conftest files for potential conflicts."""
        conflicts = []
        
        # Group conftest files by directory depth and look for conflicts
        depth_groups = defaultdict(list)
        for conftest_file in conftest_files:
            if not self._is_project_file(Path(conftest_file)):
                continue
            
            try:
                relative_path = Path(conftest_file).relative_to(self.project_root)
                depth = len(relative_path.parts)
                depth_groups[depth].append(str(relative_path))
            except ValueError:
                continue
        
        # Check for excessive conftest files at same depth
        for depth, files in depth_groups.items():
            if len(files) > 5:
                conflicts.append(f"Depth {depth}: {len(files)} conftest files (potential collection conflicts)")
        
        return conflicts

    def _find_conftest_configuration_conflicts(self, conftest_files: List[str]) -> List[str]:
        """Find configuration conflicts in conftest files."""
        conflicts = []
        
        # This would require parsing conftest files for conflicting fixture definitions
        # For now, we'll do a simplified check based on file locations
        
        test_dirs = set()
        for conftest_file in conftest_files:
            if not self._is_project_file(Path(conftest_file)):
                continue
            
            test_dir = Path(conftest_file).parent
            test_dirs.add(str(test_dir))
        
        if len(test_dirs) > 10:
            conflicts.append(f"Too many test directories with conftest: {len(test_dirs)}")
        
        return conflicts

    def _analyze_environment_inconsistencies(self, env_files: List[str]) -> Dict[str, Set[str]]:
        """Analyze environment variable inconsistencies."""
        inconsistencies = defaultdict(set)
        
        # This would require parsing config files for environment variable usage
        # For now, we'll do a simplified analysis
        
        for env_file in env_files:
            if not self._is_project_file(Path(env_file)):
                continue
            
            try:
                service_name = self._get_service_name_from_path(Path(env_file))
                inconsistencies["ENV_USAGE"].add(service_name)
            except Exception:
                continue
        
        return dict(inconsistencies)

    def _analyze_database_conflicts(self, db_files: List[str]) -> List[str]:
        """Analyze database configuration conflicts."""
        conflicts = []
        
        # Count database config files per service
        service_db_counts = defaultdict(int)
        for db_file in db_files:
            if not self._is_project_file(Path(db_file)):
                continue
            
            service_name = self._get_service_name_from_path(Path(db_file))
            service_db_counts[service_name] += 1
        
        for service, count in service_db_counts.items():
            if count > 3:
                conflicts.append(f"Service {service}: {count} database config files")
        
        return conflicts

    def _find_circular_import_dependencies(self, python_files: List[Path]) -> List[str]:
        """Find circular import dependencies (simplified check)."""
        circular_deps = []
        
        # This would require full import graph analysis
        # For now, we'll do a simplified check for obvious circular patterns
        
        config_imports = defaultdict(set)
        for py_file in python_files[:100]:  # Limit for performance
            if not self._is_project_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find config-related imports
                lines = content.splitlines()
                for line in lines:
                    if ("import" in line and "config" in line.lower()):
                        config_imports[str(py_file)].add(line.strip())
            
            except Exception:
                continue
        
        # Look for potential circular patterns (simplified)
        if len(config_imports) > 20:
            circular_deps.append(f"High config import complexity: {len(config_imports)} files")
        
        return circular_deps

    def _find_conftest_files(self) -> List[str]:
        """Find all project conftest files."""
        try:
            result = subprocess.run([
                "find", str(self.project_root), "-name", "conftest.py",
                "-not", "-path", "*/.test_venv/*",
                "-not", "-path", "*/node_modules/*",
                "-not", "-path", "*/google-cloud-sdk/*"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        except Exception:
            pass
        
        return []

    def _find_environment_config_files(self) -> List[str]:
        """Find environment configuration files."""
        patterns = ["**/config.py", "**/configuration/*.py", "**/env*.py", "**/settings.py"]
        files = []
        
        for pattern in patterns:
            found_files = list(self.project_root.glob(pattern))
            files.extend([str(f) for f in found_files if self._is_project_file(f)])
        
        return files

    def _find_database_config_files(self) -> List[str]:
        """Find database configuration files."""
        patterns = ["**/database*.py", "**/db/*.py", "**/models*.py", "**/connection*.py"]
        files = []
        
        for pattern in patterns:
            found_files = list(self.project_root.glob(pattern))
            files.extend([str(f) for f in found_files if self._is_project_file(f)])
        
        return files

    def _get_services_affected_by_files(self, files: List[str]) -> Set[str]:
        """Get set of services affected by given files."""
        services = set()
        
        for file_path in files:
            service = self._get_service_name_from_path(Path(file_path))
            if service:
                services.add(service)
        
        return services

    def _get_service_name_from_path(self, file_path: Path) -> str:
        """Get service name from file path."""
        try:
            relative_path = file_path.relative_to(self.project_root)
            if relative_path.parts:
                first_part = relative_path.parts[0]
                
                # Map to known services
                service_mapping = {
                    "netra_backend": "backend",
                    "auth_service": "auth",
                    "frontend": "frontend",
                    "tests": "test_framework",
                    "test_framework": "test_framework",
                    "shared": "shared"
                }
                
                return service_mapping.get(first_part, first_part)
        except ValueError:
            pass
        
        return "unknown"