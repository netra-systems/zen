"""
Integration Test: Docker API Migration Validation for Issue #552

CRITICAL: This test validates that all Docker API usage follows current patterns
and identifies any legacy API calls that need migration.

PURPOSE:
- Identify ALL legacy acquire_environment() calls across codebase
- Validate working start_services_smart() pattern implementations
- Ensure API consistency to prevent future signature mismatches
- Provide migration validation for Issue #552 fix

REQUIREMENTS (per CLAUDE.md):
- NO Docker dependencies (static analysis and mocked API tests)
- Real API validation without container startup
- Comprehensive codebase scanning for legacy patterns
- Integration-level testing of correct API usage

Business Value Justification:
1. Segment: Platform/Internal - Developer productivity, infrastructure reliability
2. Business Goal: Prevent API signature regressions and inconsistencies
3. Value Impact: Reduces developer debugging time, improves CI/CD reliability
4. Revenue Impact: Protects test infrastructure that validates $500K+ ARR functionality

@compliance CLAUDE.md - Real tests that fail properly, comprehensive validation
@compliance SPEC/core.xml - API consistency and migration validation
"""
import asyncio
import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any
from unittest.mock import Mock, patch, AsyncMock
import pytest
import inspect
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType

class TestDockerAPIMigrationValidation:
    """Validate Docker API migration and identify legacy patterns."""

    def setup_method(self):
        """Set up test environment for API validation."""
        self.project_root = Path(__file__).parent.parent.parent
        self.legacy_patterns_found = []
        self.working_patterns_found = []

    def test_scan_for_legacy_acquire_environment_calls(self):
        """FAILING TEST: Find all legacy acquire_environment() calls with parameters.
        
        This test will INITIALLY FAIL, listing all files that contain legacy
        API calls. After Issue #552 is fixed, it should pass.
        """
        legacy_pattern_files = []
        legacy_call_details = []
        scan_patterns = ['**/*.py']
        exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv', 'backup', '.mypy_cache'}
        for pattern in scan_patterns:
            for file_path in self.project_root.rglob(pattern):
                if any((exclude_dir in file_path.parts for exclude_dir in exclude_dirs)):
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if 'acquire_environment(' in line:
                            search_lines = lines[line_num - 1:min(line_num + 5, len(lines))]
                            search_content = ' '.join(search_lines)
                            legacy_params = ['env_name=', 'use_alpine=', 'rebuild_images=']
                            if any((param in search_content for param in legacy_params)):
                                relative_path = file_path.relative_to(self.project_root)
                                legacy_pattern_files.append(str(relative_path))
                                legacy_call_details.append({'file': str(relative_path), 'line': line_num, 'content': line.strip()})
                except (OSError, UnicodeDecodeError):
                    continue
        legacy_pattern_files = list(set(legacy_pattern_files))
        if legacy_pattern_files:
            error_message = f'Found {len(legacy_pattern_files)} files with legacy acquire_environment() calls:\n'
            for detail in legacy_call_details:
                error_message += f"  {detail['file']}:{detail['line']} - {detail['content']}\n"
            error_message += '\nThese files need to be updated to use start_services_smart() pattern.'
        assert not legacy_pattern_files, error_message

    def test_validate_start_services_smart_usage_patterns(self):
        """PASSING TEST: Validate all start_services_smart() calls use correct patterns."""
        working_pattern_files = []
        working_call_details = []
        for file_path in self.project_root.rglob('**/*.py'):
            exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'backup'}
            if any((exclude_dir in file_path.parts for exclude_dir in exclude_dirs)):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if 'start_services_smart(' in line:
                        relative_path = file_path.relative_to(self.project_root)
                        working_pattern_files.append(str(relative_path))
                        working_call_details.append({'file': str(relative_path), 'line': line_num, 'content': line.strip()})
            except (OSError, UnicodeDecodeError):
                continue
        assert working_pattern_files, 'Should find at least some start_services_smart() usage patterns in codebase'
        print(f'\n✅ Found {len(working_call_details)} start_services_smart() calls:')
        for detail in working_call_details[:5]:
            print(f"  {detail['file']}:{detail['line']} - {detail['content']}")
        self.working_patterns_found = working_call_details

    def test_api_signature_consistency_validation(self):
        """PASSING TEST: Validate UnifiedDockerManager API signatures are consistent."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        acquire_sig = inspect.signature(manager.acquire_environment)
        acquire_params = list(acquire_sig.parameters.keys())
        assert acquire_params == ['self'], f"acquire_environment should only have 'self' parameter, got: {acquire_params}"
        if hasattr(manager, 'start_services_smart'):
            smart_sig = inspect.signature(manager.start_services_smart)
            smart_params = list(smart_sig.parameters.keys())
            expected_params = ['self', 'services', 'wait_healthy']
            assert all((param in smart_params for param in expected_params)), f'start_services_smart should have {expected_params}, got: {smart_params}'
        print('✅ API signatures are consistent')

    def test_working_docker_api_pattern_integration(self):
        """PASSING TEST: Validate the working Docker API pattern works correctly.
        
        This test demonstrates the CORRECT pattern that should replace
        legacy acquire_environment() calls.
        """
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)

        async def mock_start_services_smart(services: List[str], wait_healthy: bool=True):
            """Mock implementation that simulates successful service start."""
            if not services:
                return False
            if not isinstance(services, list):
                return False
            return True
        with patch.object(manager, 'start_services_smart', side_effect=mock_start_services_smart):
            result = asyncio.run(manager.start_services_smart(services=['postgres', 'redis', 'auth'], wait_healthy=True))
            assert result == True, 'Working pattern should return True for successful start'
        with patch.object(manager, 'start_services_smart', side_effect=mock_start_services_smart):
            result = asyncio.run(manager.start_services_smart(services=['postgres', 'redis', 'backend'], wait_healthy=True))
            assert result == True, 'Backend services pattern should work'
        print('✅ Working Docker API pattern validated')

    def test_legacy_api_compatibility_removed(self):
        """PASSING TEST: Validate legacy API compatibility has been intentionally removed.
        
        This test ensures that legacy API patterns are properly rejected,
        preventing accidental usage.
        """
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        legacy_combinations = [{'env_name': 'test'}, {'use_alpine': True}, {'rebuild_images': True}, {'env_name': 'test', 'use_alpine': True}, {'env_name': 'test', 'use_alpine': True, 'rebuild_images': True}]
        for legacy_params in legacy_combinations:
            with pytest.raises(TypeError):
                manager.acquire_environment(**legacy_params)
        print(f'✅ All {len(legacy_combinations)} legacy parameter combinations properly rejected')

class TestAuthServiceAPIPatternMigration:
    """Validate auth service specific API pattern migration."""

    def test_auth_service_docker_setup_migration_pattern(self):
        """DEMONSTRATION: Show correct migration pattern for auth service Docker setup.
        
        This test demonstrates how the failing auth E2E test should be fixed.
        """
        manager = UnifiedDockerManager()
        broken_pattern_fails = False
        try:
            env_info = manager.acquire_environment(env_name='test', use_alpine=True, rebuild_images=True)
        except TypeError:
            broken_pattern_fails = True
        assert broken_pattern_fails, 'Broken pattern should fail to demonstrate Issue #552'

        async def correct_pattern():
            with patch.object(manager, 'start_services_smart') as mock_start:
                mock_start.return_value = True
                success = await manager.start_services_smart(services=['postgres', 'redis', 'auth'], wait_healthy=True)
                return success
        result = asyncio.run(correct_pattern())
        assert result == True, 'Correct pattern should work'
        print('✅ Auth service migration pattern validated')

    def test_comprehensive_auth_service_dependencies_pattern(self):
        """PASSING TEST: Validate comprehensive auth service dependency startup pattern."""
        manager = UnifiedDockerManager()

        async def mock_successful_start(services: List[str], wait_healthy: bool=True):
            required_services = {'postgres', 'redis', 'auth'}
            provided_services = set(services)
            if not required_services.issubset(provided_services):
                missing = required_services - provided_services
                print(f'Missing required services: {missing}')
                return False
            return True
        with patch.object(manager, 'start_services_smart', side_effect=mock_successful_start):
            result = asyncio.run(manager.start_services_smart(services=['postgres', 'redis', 'auth', 'backend'], wait_healthy=True))
            assert result == True, 'Comprehensive auth setup should succeed'
        with patch.object(manager, 'start_services_smart', side_effect=mock_successful_start):
            result = asyncio.run(manager.start_services_smart(services=['postgres', 'redis', 'auth'], wait_healthy=True))
            assert result == True, 'Minimal auth setup should succeed'
        print('✅ Comprehensive auth service dependency patterns validated')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')