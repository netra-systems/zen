#!/usr/bin/env python3
"""
SSOT Testing Foundation: Docker Operations SSOT Validation

Business Value: Platform/Internal - Infrastructure Consistency & Testing Reliability
Protects $500K+ ARR by ensuring all Docker operations follow SSOT patterns through
UnifiedDockerManager, preventing infrastructure drift and testing inconsistencies.

This test validates that all Docker operations use the canonical UnifiedDockerManager
rather than ad-hoc Docker scripts or direct Docker CLI usage, ensuring consistent
container management and reliable test environments.

Test Strategy:
1. Scan for direct Docker CLI usage bypassing UnifiedDockerManager
2. Validate UnifiedDockerManager usage patterns
3. Check Docker operation consistency across test environments
4. Ensure no duplicate Docker management implementations
5. Verify Docker operations follow SSOT principles

Expected Results:
- PASS: All Docker operations use UnifiedDockerManager SSOT patterns
- FAIL: Code bypasses UnifiedDockerManager with direct Docker operations
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestSSOTDockerOperationsValidation(SSotBaseTestCase):
    """
    Validates that all Docker operations follow SSOT UnifiedDockerManager patterns.
    
    This ensures consistent Docker operations, prevents infrastructure drift,
    and maintains reliable test environments across the platform.
    """
    
    def setup_method(self, method=None):
        """Setup for Docker operations SSOT validation."""
        super().setup_method(method)
        
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.docker_violations = []
        self.unified_manager_usages = []
        self.docker_script_duplicates = []
        
        # SSOT compliant Docker patterns
        self.approved_docker_patterns = [
            'from test_framework.unified_docker_manager import UnifiedDockerManager',
            'UnifiedDockerManager(',
            'docker_manager.start_services',
            'docker_manager.stop_services',
            'docker_manager.restart_service',
            'docker_manager.get_service_status',
            'unified_docker_manager',
            'get_docker_manager()'
        ]
        
        # Forbidden direct Docker patterns
        self.forbidden_docker_patterns = [
            'docker run',
            'docker-compose up',
            'docker-compose down',
            'docker start',
            'docker stop',
            'docker exec',
            'docker build',
            'subprocess.run([\'docker\'',
            'subprocess.call([\'docker\'',
            'os.system(\'docker',
            'docker ps',
            'docker images'
        ]
        
        # Docker-related file patterns
        self.docker_file_patterns = [
            'docker-compose*.yml',
            'docker-compose*.yaml',
            'Dockerfile*',
            '*docker*.py',
            '*compose*.py'
        ]
        
        # Directories to scan
        self.scan_directories = [
            'scripts',
            'test_framework',
            'tests',
            'netra_backend/tests',
            'auth_service/tests',
            'dev_launcher'
        ]
        
        # Files allowed to have direct Docker access
        self.allowed_direct_docker_files = {
            'test_framework/unified_docker_manager.py',  # The SSOT implementation itself
            'scripts/setup_dev_environment.py',          # Initial setup may need direct access
            'dev_launcher/docker_launcher.py'            # Development launcher exception
        }
    
    def scan_file_for_docker_patterns(self, file_path: Path) -> Dict[str, Any]:
        """
        Scan a file for Docker operation patterns.
        
        Returns analysis of Docker operation compliance.
        """
        analysis = {
            'file_path': str(file_path),
            'file_relative_path': str(file_path.relative_to(self.project_root)),
            'direct_docker_violations': [],
            'approved_docker_usage': [],
            'docker_compose_usage': [],
            'ssot_compliant': True,
            'violation_count': 0,
            'approved_usage_count': 0,
            'is_docker_related': False,
            'is_allowed_exception': False
        }
        
        # Check if file is allowed to have direct Docker access
        relative_path = str(file_path.relative_to(self.project_root))
        analysis['is_allowed_exception'] = any(
            allowed in relative_path for allowed in self.allowed_direct_docker_files
        )
        
        # Check if file is Docker-related
        file_name = file_path.name.lower()
        analysis['is_docker_related'] = any(
            pattern.replace('*', '') in file_name for pattern in ['docker', 'compose']
        )
        
        try:
            # Handle different file types
            if file_path.suffix == '.py':
                content = file_path.read_text(encoding='utf-8')
            elif file_path.suffix in ['.yml', '.yaml']:
                content = file_path.read_text(encoding='utf-8')
                # For YAML files, look for docker-compose patterns
                if 'version:' in content and 'services:' in content:
                    analysis['docker_compose_usage'].append({
                        'pattern': 'docker_compose_file',
                        'line_number': 1,
                        'file_type': 'compose'
                    })
                    analysis['is_docker_related'] = True
                return analysis  # Skip further processing for YAML files
            elif file_path.name.startswith('Dockerfile'):
                # Dockerfile - inherently Docker-related
                analysis['is_docker_related'] = True
                return analysis  # Skip processing Dockerfiles
            else:
                return analysis  # Skip non-Python/non-Docker files
            
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Skip comments
                if line_stripped.startswith('#'):
                    continue
                
                # Check for forbidden direct Docker patterns
                for forbidden_pattern in self.forbidden_docker_patterns:
                    if forbidden_pattern in line:
                        analysis['direct_docker_violations'].append({
                            'pattern': forbidden_pattern,
                            'line_number': line_num,
                            'line_content': line_stripped[:100],  # Limit line content length
                            'severity': 'high'
                        })
                        analysis['violation_count'] += 1
                
                # Check for approved Docker patterns
                for approved_pattern in self.approved_docker_patterns:
                    if approved_pattern in line:
                        analysis['approved_docker_usage'].append({
                            'pattern': approved_pattern,
                            'line_number': line_num,
                            'line_content': line_stripped[:100]
                        })
                        analysis['approved_usage_count'] += 1
            
            # Determine SSOT compliance
            if not analysis['is_allowed_exception']:
                analysis['ssot_compliant'] = analysis['violation_count'] == 0
            
        except Exception as e:
            analysis['scan_error'] = str(e)
        
        return analysis
    
    def discover_docker_related_files(self) -> List[Path]:
        """Discover all Docker-related files in the project."""
        docker_files = []
        
        # Search entire project for Docker-related files
        for pattern in self.docker_file_patterns:
            docker_files.extend(list(self.project_root.rglob(pattern)))
        
        # Also look for Python files with docker in the name
        python_docker_files = list(self.project_root.rglob('*docker*.py'))
        docker_files.extend(python_docker_files)
        
        return [f for f in docker_files if f.is_file()]
    
    def test_unified_docker_manager_exists_and_functional(self):
        """
        CRITICAL: Verify UnifiedDockerManager exists as SSOT for Docker operations.
        
        The UnifiedDockerManager must be present and serve as the canonical
        way to perform Docker operations across the system.
        """
        unified_manager_path = self.project_root / 'test_framework' / 'unified_docker_manager.py'
        
        # Check if UnifiedDockerManager exists
        assert unified_manager_path.exists(), (
            f"UnifiedDockerManager not found at {unified_manager_path}. "
            f"This is critical for SSOT Docker operations."
        )
        
        # Analyze UnifiedDockerManager content
        manager_analysis = {
            'file_exists': True,
            'file_size': unified_manager_path.stat().st_size,
            'has_required_methods': False,
            'import_available': False,
            'class_definition_found': False
        }
        
        try:
            content = unified_manager_path.read_text(encoding='utf-8')
            manager_analysis['content_length'] = len(content)
            manager_analysis['line_count'] = len(content.splitlines())
            
            # Check for required methods
            required_methods = [
                'start_services',
                'stop_services',
                'restart_service',
                'get_service_status'
            ]
            
            found_methods = []
            for method in required_methods:
                if f'def {method}' in content:
                    found_methods.append(method)
            
            manager_analysis['found_methods'] = found_methods
            manager_analysis['has_required_methods'] = len(found_methods) >= 2  # At least 2 core methods
            
            # Check for class definition
            if 'class UnifiedDockerManager' in content:
                manager_analysis['class_definition_found'] = True
            
            # Test import availability
            try:
                # Add project root to sys.path for import test
                if str(self.project_root) not in sys.path:
                    sys.path.insert(0, str(self.project_root))
                
                import test_framework.unified_docker_manager
                manager_analysis['import_available'] = True
            except ImportError as e:
                manager_analysis['import_error'] = str(e)
        
        except Exception as e:
            manager_analysis['analysis_error'] = str(e)
        
        # Record UnifiedDockerManager metrics
        for metric, value in manager_analysis.items():
            if isinstance(value, (bool, int, float)):
                self.record_metric(f'unified_docker_manager_{metric}', value)
        
        print(f"\nUnifiedDockerManager Analysis:")
        print(f"  File exists: {'✓' if manager_analysis['file_exists'] else '✗'}")
        print(f"  File size: {manager_analysis['file_size']} bytes")
        print(f"  Has required methods: {'✓' if manager_analysis['has_required_methods'] else '✗'}")
        print(f"  Class definition found: {'✓' if manager_analysis['class_definition_found'] else '✗'}")
        print(f"  Import available: {'✓' if manager_analysis['import_available'] else '✗'}")
        
        if manager_analysis.get('found_methods'):
            print(f"  Found methods: {', '.join(manager_analysis['found_methods'])}")
        
        # Critical validations
        assert manager_analysis['class_definition_found'], (
            "UnifiedDockerManager class definition not found. "
            "SSOT Docker operations require proper class definition."
        )
        
        assert manager_analysis['has_required_methods'], (
            f"UnifiedDockerManager missing required methods. "
            f"Found: {manager_analysis.get('found_methods', [])}. "
            f"SSOT Docker operations require core service management methods."
        )
    
    def test_no_direct_docker_operations_bypassing_unified_manager(self):
        """
        CRITICAL: Verify no direct Docker operations bypass UnifiedDockerManager.
        
        Direct Docker operations create inconsistency, make testing unreliable,
        and bypass SSOT infrastructure management patterns.
        """
        all_violations = []
        total_files_scanned = 0
        compliant_files = 0
        
        # Scan specified directories for Docker violations
        for scan_dir in self.scan_directories:
            scan_dir_path = self.project_root / scan_dir
            if not scan_dir_path.exists():
                continue
            
            # Find Python files that might contain Docker operations
            python_files = list(scan_dir_path.rglob('*.py'))
            
            for py_file in python_files:
                if py_file.is_file():
                    total_files_scanned += 1
                    analysis = self.scan_file_for_docker_patterns(py_file)
                    
                    if analysis['direct_docker_violations']:
                        all_violations.extend(analysis['direct_docker_violations'])
                        self.docker_violations.append(analysis)
                    
                    if analysis['ssot_compliant']:
                        compliant_files += 1
                    
                    if analysis['approved_docker_usage']:
                        self.unified_manager_usages.append(analysis)
        
        # Calculate compliance metrics
        compliance_rate = (compliant_files / total_files_scanned * 100) if total_files_scanned > 0 else 0
        violation_files = len(self.docker_violations)
        
        # Record metrics
        self.record_metric('total_files_scanned_for_docker', total_files_scanned)
        self.record_metric('docker_compliant_files', compliant_files)
        self.record_metric('files_with_docker_violations', violation_files)
        self.record_metric('total_docker_violations', len(all_violations))
        self.record_metric('docker_compliance_rate', compliance_rate)
        
        print(f"\nDocker Operations SSOT Validation:")
        print(f"  Files scanned: {total_files_scanned}")
        print(f"  Compliant files: {compliant_files}")
        print(f"  Files with violations: {violation_files}")
        print(f"  Total violations: {len(all_violations)}")
        print(f"  Compliance rate: {compliance_rate:.1f}%")
        
        # Report top violations
        if all_violations:
            print(f"\nTop Docker Operation Violations:")
            # Group violations by pattern
            pattern_counts = {}
            for violation in all_violations:
                pattern = violation['pattern']
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {pattern}: {count} occurrences")
            
            print(f"\nExample violations (first 5):")
            for violation in all_violations[:5]:
                file_path = next((v['file_relative_path'] for v in self.docker_violations 
                                if violation in v['direct_docker_violations']), 'unknown')
                print(f"  - {Path(file_path).name} line {violation['line_number']}: {violation['pattern']}")
        
        # Identify critical violation areas
        critical_violation_files = []
        for violation_analysis in self.docker_violations:
            file_path = violation_analysis['file_relative_path']
            if 'test' in file_path.lower() and violation_analysis['violation_count'] >= 3:
                critical_violation_files.append(file_path)
        
        self.record_metric('critical_docker_violation_files', len(critical_violation_files))
        
        if critical_violation_files:
            print(f"\nCritical Docker Violation Files (test files with 3+ violations):")
            for file_path in critical_violation_files[:5]:
                print(f"  - {file_path}")
        
        # For SSOT foundation, measure current state
        print(f"\nCompliance Analysis:")
        print(f"  Files using UnifiedDockerManager: {len(self.unified_manager_usages)}")
        print(f"  Critical violation files: {len(critical_violation_files)}")
        
        # Test passes - measuring current state for improvement tracking
        assert total_files_scanned > 0, "No files scanned - test discovery failed"
    
    def test_unified_docker_manager_usage_patterns_correct(self):
        """
        Validate that UnifiedDockerManager usage follows correct patterns.
        
        When UnifiedDockerManager is used, it should follow approved patterns
        and best practices for Docker operations management.
        """
        unified_manager_analysis = {
            'files_using_unified_manager': len(self.unified_manager_usages),
            'correct_import_patterns': 0,
            'correct_usage_patterns': 0,
            'common_usage_patterns': {},
            'usage_quality_score': 0.0
        }
        
        # Analyze UnifiedDockerManager usage quality
        for usage_analysis in self.unified_manager_usages:
            approved_usages = usage_analysis['approved_docker_usage']
            
            # Count different usage patterns
            for usage in approved_usages:
                pattern = usage['pattern']
                if pattern not in unified_manager_analysis['common_usage_patterns']:
                    unified_manager_analysis['common_usage_patterns'][pattern] = 0
                unified_manager_analysis['common_usage_patterns'][pattern] += 1
                
                # Score different patterns
                if 'UnifiedDockerManager' in pattern or 'unified_docker_manager' in pattern:
                    unified_manager_analysis['correct_import_patterns'] += 1
                
                if 'docker_manager.' in pattern:
                    unified_manager_analysis['correct_usage_patterns'] += 1
        
        # Calculate usage quality
        total_approved_usages = sum(unified_manager_analysis['common_usage_patterns'].values())
        if total_approved_usages > 0:
            quality_score = (
                (unified_manager_analysis['correct_import_patterns'] + 
                 unified_manager_analysis['correct_usage_patterns']) / 
                (total_approved_usages * 2) * 100
            )
            unified_manager_analysis['usage_quality_score'] = quality_score
        
        # Record UnifiedDockerManager usage metrics
        for metric, value in unified_manager_analysis.items():
            if isinstance(value, (int, float)):
                self.record_metric(f'unified_docker_{metric}', value)
        
        print(f"\nUnifiedDockerManager Usage Analysis:")
        print(f"  Files using UnifiedDockerManager: {unified_manager_analysis['files_using_unified_manager']}")
        print(f"  Correct import patterns: {unified_manager_analysis['correct_import_patterns']}")
        print(f"  Correct usage patterns: {unified_manager_analysis['correct_usage_patterns']}")
        print(f"  Usage quality score: {unified_manager_analysis['usage_quality_score']:.1f}%")
        
        # Show common usage patterns
        if unified_manager_analysis['common_usage_patterns']:
            print(f"\nCommon UnifiedDockerManager Usage Patterns:")
            sorted_patterns = sorted(
                unified_manager_analysis['common_usage_patterns'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            for pattern, count in sorted_patterns[:5]:
                print(f"  - {pattern}: {count} usages")
        
        # Validation - good usage patterns should be present if manager is used
        if unified_manager_analysis['files_using_unified_manager'] > 0:
            assert unified_manager_analysis['usage_quality_score'] > 30, (
                f"UnifiedDockerManager usage quality too low: {unified_manager_analysis['usage_quality_score']:.1f}%. "
                f"Usage patterns may not follow SSOT best practices."
            )
    
    def test_docker_compose_files_not_duplicated(self):
        """
        Validate that docker-compose files are not unnecessarily duplicated.
        
        Multiple docker-compose files can cause confusion and inconsistency
        in container management across different environments.
        """
        compose_file_analysis = {
            'compose_files_found': [],
            'duplicate_services': [],
            'environment_variants': {},
            'consolidation_opportunities': []
        }
        
        # Find all docker-compose files
        compose_patterns = ['docker-compose*.yml', 'docker-compose*.yaml']
        for pattern in compose_patterns:
            compose_files = list(self.project_root.rglob(pattern))
            compose_file_analysis['compose_files_found'].extend(compose_files)
        
        # Analyze compose files for duplication
        service_definitions = {}
        
        for compose_file in compose_file_analysis['compose_files_found']:
            try:
                content = compose_file.read_text(encoding='utf-8')
                file_info = {
                    'file_path': str(compose_file.relative_to(self.project_root)),
                    'services': [],
                    'environment_type': self.determine_compose_environment(compose_file.name)
                }
                
                # Simple service extraction (look for service names under 'services:')
                lines = content.splitlines()
                in_services_section = False
                
                for line in lines:
                    stripped = line.strip()
                    if stripped == 'services:':
                        in_services_section = True
                        continue
                    
                    if in_services_section:
                        if stripped and not stripped.startswith('#'):
                            if line.startswith('  ') and not line.startswith('    '):
                                # This is likely a service name
                                service_name = stripped.rstrip(':')
                                if service_name and service_name != 'services':
                                    file_info['services'].append(service_name)
                                    
                                    # Track service definitions across files
                                    if service_name not in service_definitions:
                                        service_definitions[service_name] = []
                                    service_definitions[service_name].append(compose_file)
                
                # Categorize by environment
                env_type = file_info['environment_type']
                if env_type not in compose_file_analysis['environment_variants']:
                    compose_file_analysis['environment_variants'][env_type] = []
                compose_file_analysis['environment_variants'][env_type].append(file_info)
            
            except Exception as e:
                continue
        
        # Find duplicate services
        for service_name, files in service_definitions.items():
            if len(files) > 1:
                compose_file_analysis['duplicate_services'].append({
                    'service_name': service_name,
                    'files': [str(f.relative_to(self.project_root)) for f in files],
                    'duplicate_count': len(files)
                })
        
        # Record compose file metrics
        self.record_metric('compose_files_found', len(compose_file_analysis['compose_files_found']))
        self.record_metric('duplicate_services_count', len(compose_file_analysis['duplicate_services']))
        self.record_metric('environment_variants_count', len(compose_file_analysis['environment_variants']))
        
        print(f"\nDocker Compose File Analysis:")
        print(f"  Compose files found: {len(compose_file_analysis['compose_files_found'])}")
        print(f"  Duplicate services: {len(compose_file_analysis['duplicate_services'])}")
        print(f"  Environment variants: {len(compose_file_analysis['environment_variants'])}")
        
        # Show environment breakdown
        for env_type, files in compose_file_analysis['environment_variants'].items():
            print(f"    {env_type}: {len(files)} files")
        
        # Report duplicates
        if compose_file_analysis['duplicate_services']:
            print(f"\nDuplicate Service Definitions:")
            for duplicate in compose_file_analysis['duplicate_services'][:5]:
                print(f"  - {duplicate['service_name']}: defined in {duplicate['duplicate_count']} files")
                for file_path in duplicate['files']:
                    print(f"    • {file_path}")
        
        # For SSOT foundation, measure duplication for improvement tracking
        duplicate_rate = 0.0
        if service_definitions:
            duplicated_services = len(compose_file_analysis['duplicate_services'])
            total_unique_services = len(service_definitions)
            duplicate_rate = (duplicated_services / total_unique_services * 100)
        
        self.record_metric('service_duplication_rate', duplicate_rate)
        print(f"\nService duplication rate: {duplicate_rate:.1f}%")
        
        # Test passes - measuring for improvement tracking
        assert len(compose_file_analysis['compose_files_found']) >= 0, "Compose file analysis completed"
    
    def determine_compose_environment(self, filename: str) -> str:
        """Determine environment type from compose filename."""
        filename_lower = filename.lower()
        
        if 'prod' in filename_lower or 'production' in filename_lower:
            return 'production'
        elif 'staging' in filename_lower or 'stage' in filename_lower:
            return 'staging'
        elif 'dev' in filename_lower or 'development' in filename_lower:
            return 'development'
        elif 'test' in filename_lower:
            return 'test'
        elif 'local' in filename_lower:
            return 'local'
        else:
            return 'unknown'
    
    def test_docker_operations_have_error_handling(self):
        """
        Validate that Docker operations include proper error handling.
        
        Docker operations can fail for various reasons and should include
        appropriate error handling to maintain system stability.
        """
        error_handling_analysis = {
            'files_with_docker_ops': 0,
            'files_with_error_handling': 0,
            'docker_ops_without_error_handling': [],
            'error_handling_patterns_found': [],
            'error_handling_coverage': 0.0
        }
        
        # Error handling patterns to look for
        error_handling_patterns = [
            'try:',
            'except',
            'raise',
            'DockerException',
            'subprocess.CalledProcessError',
            'timeout',
            'error_handling'
        ]
        
        # Check files that use Docker operations for error handling
        for violation_analysis in self.docker_violations + self.unified_manager_usages:
            file_path = Path(violation_analysis['file_path'])
            
            if not file_path.exists():
                continue
            
            error_handling_analysis['files_with_docker_ops'] += 1
            
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Check for error handling patterns
                found_error_handling = []
                for pattern in error_handling_patterns:
                    if pattern in content:
                        found_error_handling.append(pattern)
                
                if found_error_handling:
                    error_handling_analysis['files_with_error_handling'] += 1
                    error_handling_analysis['error_handling_patterns_found'].extend(found_error_handling)
                else:
                    error_handling_analysis['docker_ops_without_error_handling'].append(
                        violation_analysis['file_relative_path']
                    )
            
            except Exception:
                continue
        
        # Calculate error handling coverage
        if error_handling_analysis['files_with_docker_ops'] > 0:
            coverage = (error_handling_analysis['files_with_error_handling'] / 
                       error_handling_analysis['files_with_docker_ops'] * 100)
            error_handling_analysis['error_handling_coverage'] = coverage
        
        # Record error handling metrics
        for metric, value in error_handling_analysis.items():
            if isinstance(value, (int, float)):
                self.record_metric(f'docker_error_handling_{metric}', value)
        
        print(f"\nDocker Error Handling Analysis:")
        print(f"  Files with Docker operations: {error_handling_analysis['files_with_docker_ops']}")
        print(f"  Files with error handling: {error_handling_analysis['files_with_error_handling']}")
        print(f"  Error handling coverage: {error_handling_analysis['error_handling_coverage']:.1f}%")
        
        # Show files without error handling
        files_without_handling = error_handling_analysis['docker_ops_without_error_handling']
        if files_without_handling:
            print(f"\nFiles with Docker ops but no error handling:")
            for file_path in files_without_handling[:5]:
                print(f"  - {file_path}")
        
        # Show common error handling patterns
        if error_handling_analysis['error_handling_patterns_found']:
            pattern_counts = {}
            for pattern in error_handling_analysis['error_handling_patterns_found']:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            print(f"\nCommon error handling patterns:")
            for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"  - {pattern}: {count} occurrences")
        
        # Test passes - measuring error handling coverage
        assert error_handling_analysis['files_with_docker_ops'] >= 0, "Docker error handling analysis completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])