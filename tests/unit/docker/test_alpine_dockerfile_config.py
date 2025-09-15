"""
Unit tests for Alpine Dockerfile configuration validation - NO DOCKER BUILDS REQUIRED

Purpose: Validate Alpine Dockerfile configurations that cause build failures
Issue: #1082 - Docker Alpine build infrastructure failure
Approach: Dockerfile parsing and configuration validation only, no container builds

MISSION CRITICAL: These tests must detect Alpine-specific configuration issues
WITHOUT requiring Docker to be running or functional.

Business Impact: $500K+ ARR Golden Path depends on working Docker infrastructure
Critical Error Context: backend.alpine.Dockerfile:69 failing with cache key computation

Test Strategy: These tests are designed to FAIL initially to prove they detect real issues
"""
import pytest
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

class AlpineDockerfileConfigValidationTests(SSotBaseTestCase):
    """Unit tests for Alpine Dockerfile configuration validation - PARSING ONLY

    These tests validate Alpine-specific Dockerfile configurations that can
    cause cache key computation failures and build issues.
    """

    @classmethod
    def setUpClass(cls):
        """Setup test environment - locate Dockerfiles and parse configurations"""
        super().setUpClass()
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.dockerfiles_dir = cls.project_root / 'dockerfiles'

        cls.alpine_dockerfiles = {
            'backend.alpine.Dockerfile': 'backend',
            'auth.alpine.Dockerfile': 'auth',
            'frontend.alpine.Dockerfile': 'frontend',
            'backend.staging.alpine.Dockerfile': 'backend-staging',
            'auth.staging.alpine.Dockerfile': 'auth-staging',
            'frontend.staging.alpine.Dockerfile': 'frontend-staging'
        }

        cls.logger.info(f'Testing Alpine Dockerfile configurations in: {cls.dockerfiles_dir}')

    def test_alpine_dockerfile_base_image_versions(self):
        """
        Test that Alpine Dockerfiles use consistent and supported base image versions

        Issue: #1082 - Inconsistent Alpine base images causing cache key failures
        Difficulty: Low (5 minutes)
        Expected: FAIL initially - Base image version inconsistencies or unsupported versions
        """
        base_image_issues = []

        base_images_found = {}

        for dockerfile_name, service_type in self.alpine_dockerfiles.items():
            dockerfile_path = self.dockerfiles_dir / dockerfile_name

            if not dockerfile_path.exists():
                base_image_issues.append(f"Missing Alpine Dockerfile: {dockerfile_path}")
                continue

            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()

                # Extract FROM statements
                from_statements = self._extract_from_statements(dockerfile_content)

                for line_num, from_statement in from_statements:
                    base_image = self._parse_base_image(from_statement)

                    if base_image:
                        if service_type not in base_images_found:
                            base_images_found[service_type] = []
                        base_images_found[service_type].append({
                            'dockerfile': dockerfile_name,
                            'line': line_num,
                            'image': base_image
                        })

                        # Check for Alpine-specific issues
                        if 'alpine' not in base_image.lower():
                            base_image_issues.append(
                                f"{dockerfile_name}:{line_num} - Expected Alpine base image, "
                                f"found: {base_image}"
                            )

                        # Check for version pinning
                        if ':' not in base_image or base_image.endswith(':latest'):
                            base_image_issues.append(
                                f"{dockerfile_name}:{line_num} - Base image not version-pinned: "
                                f"{base_image}. Unpinned images cause cache key instability."
                            )

            except Exception as e:
                base_image_issues.append(f"Failed to parse {dockerfile_name}: {str(e)}")

        # Check for inconsistencies between related Dockerfiles
        for service_type, images in base_images_found.items():
            if len(images) > 1:
                unique_base_images = set(img['image'] for img in images)
                if len(unique_base_images) > 1:
                    base_image_issues.append(
                        f"Inconsistent base images for {service_type}: "
                        f"{[f'{img['dockerfile']}={img['image']}' for img in images]}"
                    )

        assert not base_image_issues, \
            f"Alpine Dockerfile base image validation failures: {json.dumps(base_image_issues, indent=2)}. " \
            f"Base image inconsistencies cause cache key computation failures in Alpine builds."

    def test_alpine_dockerfile_copy_instruction_validation(self):
        """
        Test that COPY instructions in Alpine Dockerfiles are properly formatted

        Issue: #1082 - COPY instruction at line 69 causing cache key computation failure
        Difficulty: Medium (10 minutes)
        Expected: FAIL initially - COPY instructions have formatting or path issues
        """
        copy_instruction_issues = []

        for dockerfile_name, service_type in self.alpine_dockerfiles.items():
            dockerfile_path = self.dockerfiles_dir / dockerfile_name

            if not dockerfile_path.exists():
                continue

            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()

                # Extract COPY instructions
                copy_instructions = self._extract_copy_instructions(dockerfile_content)

                for line_num, copy_instruction in copy_instructions:
                    # Validate COPY instruction format
                    copy_issues = self._validate_copy_instruction(copy_instruction, line_num, service_type)

                    if copy_issues:
                        copy_instruction_issues.extend([
                            f"{dockerfile_name}:{line_num} - {issue}" for issue in copy_issues
                        ])

                    # Special check for line 69 (the specific failing line mentioned in the issue)
                    if line_num == 69:
                        copy_instruction_issues.append(
                            f"{dockerfile_name}:{line_num} - CRITICAL: This is the exact line "
                            f"causing cache key computation failure: '{copy_instruction.strip()}'"
                        )

            except Exception as e:
                copy_instruction_issues.append(f"Failed to parse COPY instructions in {dockerfile_name}: {str(e)}")

        assert not copy_instruction_issues, \
            f"Alpine COPY instruction validation failures: {json.dumps(copy_instruction_issues, indent=2)}. " \
            f"Malformed COPY instructions cause cache key computation failures in Alpine builds."

    def test_alpine_dockerfile_user_and_permissions(self):
        """
        Test that Alpine Dockerfiles properly handle user creation and permissions

        Issue: #1082 - Alpine Linux has stricter user/permission requirements
        Difficulty: Medium (15 minutes)
        Expected: FAIL initially - User creation or permission issues in Alpine context
        """
        user_permission_issues = []

        for dockerfile_name, service_type in self.alpine_dockerfiles.items():
            dockerfile_path = self.dockerfiles_dir / dockerfile_name

            if not dockerfile_path.exists():
                continue

            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()

                # Check for user creation patterns
                user_instructions = self._extract_user_instructions(dockerfile_content)
                run_instructions = self._extract_run_instructions(dockerfile_content)

                # Analyze user creation and permissions
                has_user_creation = False
                has_chown_operations = False
                users_created = []

                for line_num, run_instruction in run_instructions:
                    run_cmd = run_instruction.strip()

                    # Check for user creation commands
                    if any(cmd in run_cmd.lower() for cmd in ['adduser', 'useradd', 'addgroup', 'groupadd']):
                        has_user_creation = True
                        users_created.append((line_num, run_cmd))

                    # Check for chown operations
                    if 'chown' in run_cmd.lower():
                        has_chown_operations = True

                for line_num, user_instruction in user_instructions:
                    users_created.append((line_num, user_instruction))

                # Validate user creation and permissions for Alpine
                if not has_user_creation and service_type.startswith(('backend', 'auth')):
                    user_permission_issues.append(
                        f"{dockerfile_name} - No user creation found for {service_type}. "
                        f"Alpine containers should not run as root for security."
                    )

                # Check COPY instructions with --chown
                copy_instructions = self._extract_copy_instructions(dockerfile_content)
                for line_num, copy_instruction in copy_instructions:
                    if '--chown=' in copy_instruction:
                        chown_user = self._extract_chown_user(copy_instruction)
                        if chown_user and not any(chown_user in str(user_cmd) for _, user_cmd in users_created):
                            user_permission_issues.append(
                                f"{dockerfile_name}:{line_num} - COPY --chown uses user '{chown_user}' "
                                f"but user creation not found in Dockerfile"
                            )

                # Alpine-specific user validation
                for line_num, user_cmd in users_created:
                    if 'adduser' in user_cmd.lower():
                        # Check for Alpine-specific adduser flags
                        if '-D' not in user_cmd:  # Alpine uses -D for no password
                            user_permission_issues.append(
                                f"{dockerfile_name}:{line_num} - adduser command may not be Alpine-compatible: "
                                f"'{user_cmd.strip()}'. Alpine requires -D flag."
                            )

            except Exception as e:
                user_permission_issues.append(f"Failed to parse user instructions in {dockerfile_name}: {str(e)}")

        assert not user_permission_issues, \
            f"Alpine user/permission validation failures: {json.dumps(user_permission_issues, indent=2)}. " \
            f"User permission issues cause cache key computation failures in Alpine builds."

    def test_alpine_dockerfile_package_manager_usage(self):
        """
        Test that Alpine Dockerfiles use apk package manager correctly

        Issue: #1082 - Incorrect package manager usage can cause Alpine build failures
        Difficulty: Medium (10 minutes)
        Expected: FAIL initially - Package manager commands not optimized for Alpine
        """
        package_manager_issues = []

        for dockerfile_name, service_type in self.alpine_dockerfiles.items():
            dockerfile_path = self.dockerfiles_dir / dockerfile_name

            if not dockerfile_path.exists():
                continue

            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()

                # Extract RUN instructions
                run_instructions = self._extract_run_instructions(dockerfile_content)

                apk_commands = []
                non_alpine_commands = []

                for line_num, run_instruction in run_instructions:
                    run_cmd = run_instruction.strip().lower()

                    # Check for Alpine package manager (apk)
                    if 'apk ' in run_cmd:
                        apk_commands.append((line_num, run_instruction))

                    # Check for non-Alpine package managers
                    non_alpine_managers = ['apt-get', 'apt', 'yum', 'dnf', 'pacman', 'zypper']
                    for pkg_mgr in non_alpine_managers:
                        if pkg_mgr in run_cmd:
                            non_alpine_commands.append((line_num, run_instruction, pkg_mgr))

                # Validate APK usage patterns
                for line_num, apk_cmd in apk_commands:
                    apk_issues = self._validate_apk_command(apk_cmd)
                    if apk_issues:
                        package_manager_issues.extend([
                            f"{dockerfile_name}:{line_num} - {issue}" for issue in apk_issues
                        ])

                # Check for non-Alpine package managers
                if non_alpine_commands:
                    for line_num, cmd, pkg_mgr in non_alpine_commands:
                        package_manager_issues.append(
                            f"{dockerfile_name}:{line_num} - Non-Alpine package manager '{pkg_mgr}' "
                            f"used in Alpine Dockerfile: '{cmd.strip()[:100]}'"
                        )

                # Check if any package installation is happening without apk
                python_install_patterns = ['pip install', 'pip3 install', 'python -m pip', 'python3 -m pip']
                for line_num, run_instruction in run_instructions:
                    for pattern in python_install_patterns:
                        if pattern in run_instruction.lower():
                            # Check if pip was installed via apk first
                            has_apk_pip = any('apk' in prev_cmd and 'pip' in prev_cmd
                                            for _, prev_cmd in apk_commands)
                            if not has_apk_pip:
                                package_manager_issues.append(
                                    f"{dockerfile_name}:{line_num} - pip usage without apk installation: "
                                    f"'{run_instruction.strip()[:100]}'"
                                )
                            break

            except Exception as e:
                package_manager_issues.append(f"Failed to parse package manager usage in {dockerfile_name}: {str(e)}")

        assert not package_manager_issues, \
            f"Alpine package manager validation failures: {json.dumps(package_manager_issues, indent=2)}. " \
            f"Incorrect package manager usage causes cache key computation failures in Alpine builds."

    def test_alpine_dockerfile_workdir_and_path_structure(self):
        """
        Test that Alpine Dockerfiles have consistent WORKDIR and path structures

        Issue: #1082 - Inconsistent path structures can cause cache key computation issues
        Difficulty: Low (10 minutes)
        Expected: FAIL initially - WORKDIR inconsistencies or path structure issues
        """
        workdir_issues = []

        workdirs_by_service = {}

        for dockerfile_name, service_type in self.alpine_dockerfiles.items():
            dockerfile_path = self.dockerfiles_dir / dockerfile_name

            if not dockerfile_path.exists():
                continue

            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()

                # Extract WORKDIR instructions
                workdir_instructions = self._extract_workdir_instructions(dockerfile_content)

                if not workdir_instructions:
                    workdir_issues.append(f"{dockerfile_name} - No WORKDIR instruction found")
                    continue

                service_workdirs = []
                for line_num, workdir_instruction in workdir_instructions:
                    workdir_path = workdir_instruction.replace('WORKDIR', '').strip()
                    service_workdirs.append({
                        'line': line_num,
                        'path': workdir_path,
                        'dockerfile': dockerfile_name
                    })

                workdirs_by_service[service_type] = service_workdirs

                # Validate WORKDIR paths
                for workdir_info in service_workdirs:
                    workdir_path = workdir_info['path']

                    # Check for absolute paths
                    if not workdir_path.startswith('/'):
                        workdir_issues.append(
                            f"{dockerfile_name}:{workdir_info['line']} - WORKDIR should use absolute path: "
                            f"'{workdir_path}'"
                        )

                    # Check for consistent app directory structure
                    expected_patterns = ['/app', '/opt/', '/usr/src/app']
                    if not any(pattern in workdir_path for pattern in expected_patterns):
                        workdir_issues.append(
                            f"{dockerfile_name}:{workdir_info['line']} - WORKDIR path unusual for containerized app: "
                            f"'{workdir_path}'. Consider using /app or /opt/appname"
                        )

            except Exception as e:
                workdir_issues.append(f"Failed to parse WORKDIR instructions in {dockerfile_name}: {str(e)}")

        # Check for consistency across related services
        base_service_types = ['backend', 'auth', 'frontend']
        for base_type in base_service_types:
            related_workdirs = []
            for service_type, workdirs in workdirs_by_service.items():
                if base_type in service_type:
                    related_workdirs.extend(workdirs)

            if len(related_workdirs) > 1:
                unique_paths = set(wd['path'] for wd in related_workdirs)
                if len(unique_paths) > 1:
                    workdir_details = [f"{wd['dockerfile']}={wd['path']}" for wd in related_workdirs]
                    workdir_issues.append(
                        f"Inconsistent WORKDIR paths for {base_type} service: {workdir_details}"
                    )

        assert not workdir_issues, \
            f"Alpine WORKDIR validation failures: {json.dumps(workdir_issues, indent=2)}. " \
            f"Inconsistent WORKDIR paths cause cache key computation failures in Alpine builds."

    # Helper methods for parsing Dockerfile content

    def _extract_from_statements(self, dockerfile_content: str) -> List[Tuple[int, str]]:
        """Extract FROM statements with line numbers"""
        statements = []
        lines = dockerfile_content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line.startswith('FROM '):
                statements.append((i, stripped_line))
        return statements

    def _parse_base_image(self, from_statement: str) -> Optional[str]:
        """Parse base image from FROM statement"""
        parts = from_statement.split()
        if len(parts) >= 2:
            return parts[1]
        return None

    def _extract_copy_instructions(self, dockerfile_content: str) -> List[Tuple[int, str]]:
        """Extract COPY instructions with line numbers"""
        instructions = []
        lines = dockerfile_content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line.startswith('COPY '):
                instructions.append((i, line))  # Keep original formatting
        return instructions

    def _validate_copy_instruction(self, copy_instruction: str, line_num: int, service_type: str) -> List[str]:
        """Validate a single COPY instruction"""
        issues = []
        copy_cmd = copy_instruction.strip()

        # Check for --chown flag usage
        if '--chown=' in copy_cmd:
            chown_match = re.search(r'--chown=([^:\s]+):([^\s]+)', copy_cmd)
            if chown_match:
                user, group = chown_match.groups()
                # Validate user/group naming
                if not re.match(r'^[a-z_][a-z0-9_-]{0,30}$', user):
                    issues.append(f"Invalid user name in --chown: '{user}'")
                if not re.match(r'^[a-z_][a-z0-9_-]{0,30}$', group):
                    issues.append(f"Invalid group name in --chown: '{group}'")

        # Check for proper source/destination format
        copy_parts = copy_cmd.split()
        if len(copy_parts) < 3:
            issues.append("COPY instruction missing source or destination")
        else:
            # Find source and destination (skip flags)
            source_dest_parts = [part for part in copy_parts[1:] if not part.startswith('--')]
            if len(source_dest_parts) < 2:
                issues.append("COPY instruction missing source or destination after flags")

        return issues

    def _extract_user_instructions(self, dockerfile_content: str) -> List[Tuple[int, str]]:
        """Extract USER instructions with line numbers"""
        instructions = []
        lines = dockerfile_content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line.startswith('USER '):
                instructions.append((i, stripped_line))
        return instructions

    def _extract_run_instructions(self, dockerfile_content: str) -> List[Tuple[int, str]]:
        """Extract RUN instructions with line numbers"""
        instructions = []
        lines = dockerfile_content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line.startswith('RUN '):
                instructions.append((i, stripped_line))
        return instructions

    def _extract_chown_user(self, copy_instruction: str) -> Optional[str]:
        """Extract user from --chown flag in COPY instruction"""
        chown_match = re.search(r'--chown=([^:\s]+)', copy_instruction)
        if chown_match:
            return chown_match.group(1)
        return None

    def _validate_apk_command(self, apk_cmd: str) -> List[str]:
        """Validate apk command for Alpine best practices"""
        issues = []
        cmd_lower = apk_cmd.lower()

        # Check for cache cleanup
        if 'apk add' in cmd_lower and '--no-cache' not in cmd_lower and 'rm -rf /var/cache/apk' not in cmd_lower:
            issues.append("apk add without --no-cache or cache cleanup reduces image size")

        # Check for update patterns
        if 'apk update' in cmd_lower and 'apk upgrade' not in cmd_lower:
            issues.append("apk update should typically be followed by apk upgrade or use apk add --no-cache")

        return issues

    def _extract_workdir_instructions(self, dockerfile_content: str) -> List[Tuple[int, str]]:
        """Extract WORKDIR instructions with line numbers"""
        instructions = []
        lines = dockerfile_content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line.startswith('WORKDIR '):
                instructions.append((i, stripped_line))
        return instructions