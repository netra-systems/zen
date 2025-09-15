"""
Unit tests for Docker Alpine build context validation - NO DOCKER BUILDS REQUIRED

Purpose: Validate Alpine build context issues that cause cache key failures
Issue: #1082 - Docker Alpine build infrastructure failure
Approach: File system validation only, no container builds

MISSION CRITICAL: These tests must detect the specific Alpine build issues
WITHOUT requiring Docker to be running or functional.

Business Impact: $500K+ ARR Golden Path depends on working Docker infrastructure
Critical Error: "failed to compute cache key for /Users/anthony/Desktop/netra-apex/netra_backend"

Test Strategy: These tests are designed to FAIL initially to prove they detect real issues
"""
import pytest
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestAlpineBuildContextValidation(SSotBaseTestCase):
    """Unit tests for Alpine build context validation - FILE SYSTEM ONLY

    These tests validate the build context and source directories that are
    causing cache key computation failures in Alpine Docker builds.
    """

    def setup_method(self, method):
        """Setup test environment - locate project root and Docker files"""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.docker_dir = self.project_root / 'docker'
        self.dockerfiles_dir = self.project_root / 'dockerfiles'
        self.netra_backend_dir = self.project_root / 'netra_backend'
        self.auth_service_dir = self.project_root / 'auth_service'
        self.frontend_dir = self.project_root / 'frontend'

        self.alpine_dockerfiles = [
            'backend.alpine.Dockerfile',
            'auth.alpine.Dockerfile',
            'frontend.alpine.Dockerfile',
            'backend.staging.alpine.Dockerfile',
            'auth.staging.alpine.Dockerfile',
            'frontend.staging.alpine.Dockerfile'
        ]

        self.logger.info(f'Testing Alpine build context in: {self.dockerfiles_dir}')

    def test_netra_backend_source_directory_exists_and_accessible(self):
        """
        Test that netra_backend directory exists and is accessible for COPY operations

        Issue: #1082 - Cache key failure on COPY --chown=netra:netra netra_backend
        Difficulty: Low (5 minutes)
        Expected: FAIL initially - Source directory may have permission/access issues
        """
        # Check if netra_backend directory exists
        assert self.netra_backend_dir.exists(), \
            f"netra_backend source directory does not exist: {self.netra_backend_dir}. " \
            f"This will cause Docker COPY operations to fail with cache key computation errors."

        # Check if directory is readable
        assert os.access(self.netra_backend_dir, os.R_OK), \
            f"netra_backend directory is not readable: {self.netra_backend_dir}. " \
            f"This will cause Docker to fail computing cache keys for COPY operations."

        # Check for critical Python files that Docker needs
        critical_files = ['__init__.py', 'app/__init__.py']
        missing_files = []
        for file_path in critical_files:
            full_path = self.netra_backend_dir / file_path
            if not full_path.exists():
                missing_files.append(str(full_path))

        assert not missing_files, \
            f"Critical Python files missing in netra_backend: {missing_files}. " \
            f"Docker Alpine builds will fail cache key computation without these structural files."

    def test_alpine_dockerfile_copy_paths_are_valid(self):
        """
        Test that all COPY paths in Alpine Dockerfiles point to existing directories

        Issue: #1082 - COPY operations failing in backend.alpine.Dockerfile:69
        Difficulty: Medium (10 minutes)
        Expected: FAIL initially - COPY paths may be incorrect or missing
        """
        copy_failures = []

        for dockerfile_name in self.alpine_dockerfiles:
            dockerfile_path = self.dockerfiles_dir / dockerfile_name

            if not dockerfile_path.exists():
                copy_failures.append(f"Missing Dockerfile: {dockerfile_path}")
                continue

            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()

                # Extract COPY commands and validate paths
                copy_commands = self._extract_copy_commands(dockerfile_content)

                for line_num, copy_cmd in copy_commands:
                    source_path, dest_path = self._parse_copy_command(copy_cmd)

                    if source_path and not source_path.startswith('/'):
                        # Relative path - check if it exists relative to project root
                        full_source_path = self.project_root / source_path

                        if not full_source_path.exists():
                            copy_failures.append(
                                f"{dockerfile_name}:{line_num} - COPY source missing: "
                                f"{source_path} -> {full_source_path}"
                            )
                        elif not os.access(full_source_path, os.R_OK):
                            copy_failures.append(
                                f"{dockerfile_name}:{line_num} - COPY source not readable: "
                                f"{source_path} -> {full_source_path}"
                            )

            except Exception as e:
                copy_failures.append(f"Failed to parse {dockerfile_name}: {str(e)}")

        assert not copy_failures, \
            f"Docker Alpine COPY path validation failures: {json.dumps(copy_failures, indent=2)}. " \
            f"These path issues cause cache key computation failures in Alpine builds."

    def test_build_context_directory_structure(self):
        """
        Test that the build context directory structure matches Alpine Dockerfile expectations

        Issue: #1082 - Build context structure causing cache key failures
        Difficulty: Medium (10 minutes)
        Expected: FAIL initially - Directory structure may not match Alpine expectations
        """
        build_context_issues = []

        # Check expected directory structure for each service
        service_directories = {
            'backend': self.netra_backend_dir,
            'auth': self.auth_service_dir,
            'frontend': self.frontend_dir
        }

        for service_name, service_dir in service_directories.items():
            if not service_dir.exists():
                build_context_issues.append(f"Missing {service_name} service directory: {service_dir}")
                continue

            # Check for __init__.py files that indicate proper Python package structure
            init_files = list(service_dir.rglob('__init__.py'))
            if len(init_files) == 0:
                build_context_issues.append(
                    f"{service_name} service has no __init__.py files - not a valid Python package"
                )

            # Check for excessive file count that might cause build context issues
            all_files = list(service_dir.rglob('*'))
            file_count = len([f for f in all_files if f.is_file()])

            if file_count > 10000:
                build_context_issues.append(
                    f"{service_name} service has excessive files ({file_count}), may cause Alpine build timeouts"
                )

            # Check for large files that could cause cache key computation issues
            large_files = []
            for file_path in all_files:
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        if file_size > 100 * 1024 * 1024:  # 100MB
                            large_files.append(f"{file_path} ({file_size // (1024*1024)}MB)")
                    except (OSError, PermissionError):
                        pass  # Skip files we can't stat

            if large_files:
                build_context_issues.append(
                    f"{service_name} service has large files that may cause Alpine cache issues: {large_files[:5]}"
                )

        assert not build_context_issues, \
            f"Build context directory structure issues: {json.dumps(build_context_issues, indent=2)}. " \
            f"These structural issues cause Alpine Docker builds to fail cache key computation."

    def test_docker_ignore_patterns_prevent_cache_issues(self):
        """
        Test that .dockerignore patterns properly exclude problematic files

        Issue: #1082 - Cache key computation failing due to ignored files being included
        Difficulty: Medium (15 minutes)
        Expected: FAIL initially - .dockerignore may not properly exclude cache-breaking files
        """
        dockerignore_issues = []

        # Check for .dockerignore files
        dockerignore_files = [
            self.docker_dir / '.dockerignore',
            self.dockerfiles_dir / '.dockerignore',
            self.project_root / '.dockerignore'
        ]

        existing_dockerignore = None
        for dockerignore_path in dockerignore_files:
            if dockerignore_path.exists():
                existing_dockerignore = dockerignore_path
                break

        if not existing_dockerignore:
            dockerignore_issues.append("No .dockerignore file found - all files included in build context")
        else:
            try:
                with open(existing_dockerignore, 'r') as f:
                    dockerignore_content = f.read()

                # Check for critical ignore patterns that prevent cache issues
                critical_patterns = [
                    '__pycache__',
                    '*.pyc',
                    '*.pyo',
                    '.git',
                    '.pytest_cache',
                    'node_modules',
                    '.DS_Store',
                    '*.log'
                ]

                missing_patterns = []
                for pattern in critical_patterns:
                    if pattern not in dockerignore_content:
                        missing_patterns.append(pattern)

                if missing_patterns:
                    dockerignore_issues.append(
                        f"Missing critical .dockerignore patterns: {missing_patterns}. "
                        f"These files can cause Alpine cache key computation failures."
                    )

            except Exception as e:
                dockerignore_issues.append(f"Failed to read .dockerignore: {str(e)}")

        # Check if problematic files exist that should be ignored
        problematic_files = []
        for service_dir in [self.netra_backend_dir, self.auth_service_dir, self.frontend_dir]:
            if service_dir.exists():
                # Look for __pycache__ directories
                pycache_dirs = list(service_dir.rglob('__pycache__'))
                if pycache_dirs:
                    problematic_files.extend([str(p) for p in pycache_dirs[:3]])

                # Look for .pyc files
                pyc_files = list(service_dir.rglob('*.pyc'))
                if pyc_files:
                    problematic_files.extend([str(p) for p in pyc_files[:3]])

        if problematic_files:
            dockerignore_issues.append(
                f"Found problematic files that should be .dockerignored: {problematic_files}. "
                f"These can cause Alpine build cache key computation failures."
            )

        assert not dockerignore_issues, \
            f"Docker ignore pattern issues: {json.dumps(dockerignore_issues, indent=2)}. " \
            f"Improper .dockerignore patterns cause cache key failures in Alpine builds."

    def test_alpine_specific_file_permissions(self):
        """
        Test file permissions that could cause Alpine-specific build failures

        Issue: #1082 - Alpine Linux has stricter file permission requirements
        Difficulty: High (20 minutes)
        Expected: FAIL initially - File permissions may not be compatible with Alpine
        """
        permission_issues = []

        # Check source directories for Alpine-incompatible permissions
        for service_name, service_dir in [
            ('backend', self.netra_backend_dir),
            ('auth', self.auth_service_dir),
            ('frontend', self.frontend_dir)
        ]:
            if not service_dir.exists():
                continue

            try:
                # Check directory permissions
                dir_stat = service_dir.stat()
                dir_mode = oct(dir_stat.st_mode)[-3:]

                # Alpine needs readable/executable directories
                if not os.access(service_dir, os.R_OK | os.X_OK):
                    permission_issues.append(
                        f"{service_name} directory not readable/executable: {service_dir} (mode: {dir_mode})"
                    )

                # Check for files with problematic permissions
                problematic_files = []
                for file_path in service_dir.rglob('*'):
                    if file_path.is_file():
                        try:
                            if not os.access(file_path, os.R_OK):
                                file_stat = file_path.stat()
                                file_mode = oct(file_stat.st_mode)[-3:]
                                problematic_files.append(f"{file_path} (mode: {file_mode})")

                                if len(problematic_files) >= 5:
                                    break  # Limit to first 5 issues
                        except (OSError, PermissionError):
                            problematic_files.append(f"{file_path} (permission denied)")

                if problematic_files:
                    permission_issues.append(
                        f"{service_name} has files with problematic permissions: {problematic_files}"
                    )

            except (OSError, PermissionError) as e:
                permission_issues.append(f"Cannot check {service_name} permissions: {str(e)}")

        assert not permission_issues, \
            f"Alpine file permission issues: {json.dumps(permission_issues, indent=2)}. " \
            f"These permission problems cause cache key computation failures in Alpine builds."

    def _extract_copy_commands(self, dockerfile_content: str) -> List[tuple]:
        """Extract COPY commands from Dockerfile content with line numbers"""
        copy_commands = []
        lines = dockerfile_content.split('\n')

        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line.startswith('COPY '):
                copy_commands.append((i, stripped_line))

        return copy_commands

    def _parse_copy_command(self, copy_command: str) -> tuple:
        """Parse a COPY command to extract source and destination paths"""
        try:
            parts = copy_command.split()
            if len(parts) >= 3:
                # Handle COPY --chown=user:group src dest
                if parts[1].startswith('--'):
                    source = parts[2] if len(parts) > 2 else None
                    dest = parts[3] if len(parts) > 3 else None
                else:
                    source = parts[1]
                    dest = parts[2] if len(parts) > 2 else None
                return source, dest
        except (IndexError, AttributeError):
            pass

        return None, None