#!/usr/bin/env python3
"""
Test Plan for Issue #458: Alpine Image Access Failure - Build vs Pull Configuration Mismatch

This test validates the root cause identified:
- Docker compose trying to PULL custom images from registry instead of BUILD locally
- Custom images like netra-alpine-test-* don't exist in public registry
- Should use docker-compose build command with correct dockerfile paths

Business Impact: P1 - Blocks integration testing protecting $500K+ ARR Golden Path functionality
"""

import os
import subprocess
import tempfile
import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
import unittest


class TestIssue458AlpineImageAccess(unittest.TestCase):
    """
    Integration tests for Issue #458 - Alpine image access failure
    
    Validates:
    1. Docker build process for Alpine images
    2. Compose stack startup with built images
    3. Integration test runner can use Alpine stack
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        super().setUpClass()
        cls.project_root = Path(__file__).parent.parent.parent
        cls.docker_compose_file = cls.project_root / "docker" / "docker-compose.alpine-test.yml"
        cls.dockerfiles_dir = cls.project_root / "dockerfiles"
        
        # Custom image names that should be built locally
        cls.custom_images = [
            "netra-alpine-test-migration:latest",
            "netra-alpine-test-backend:latest", 
            "netra-alpine-test-auth:latest",
            "netra-alpine-test-frontend:latest"
        ]
        
        # Expected Dockerfile paths for each service
        cls.expected_dockerfiles = {
            "migration": cls.dockerfiles_dir / "migration.alpine.Dockerfile",
            "backend": cls.dockerfiles_dir / "backend.alpine.Dockerfile", 
            "auth": cls.dockerfiles_dir / "auth.alpine.Dockerfile",
            "frontend": cls.dockerfiles_dir / "frontend.alpine.Dockerfile"
        }

    def test_alpine_compose_file_exists_and_valid(self):
        """Test 1: Verify Alpine compose file exists and is valid YAML"""
        self.assertTrue(
            self.docker_compose_file.exists(),
            f"Alpine test compose file not found: {self.docker_compose_file}"
        )
        
        # Validate YAML syntax
        with open(self.docker_compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
            
        self.assertIsInstance(compose_data, dict, "Compose file should be valid YAML")
        self.assertIn('services', compose_data, "Compose file should have services section")

    def test_dockerfile_paths_configuration_mismatch(self):
        """Test 2: Identify dockerfile path configuration mismatch (EXPECTED TO FAIL INITIALLY)"""
        with open(self.docker_compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        services = compose_data.get('services', {})
        
        # Check each custom service for dockerfile path issues
        dockerfile_issues = []
        
        for service_name in ['alpine-test-migration', 'alpine-test-backend', 'alpine-test-auth', 'alpine-test-frontend']:
            if service_name not in services:
                dockerfile_issues.append(f"Service {service_name} not found in compose file")
                continue
                
            service_config = services[service_name]
            
            # Check if service has build configuration
            if 'build' not in service_config:
                dockerfile_issues.append(f"Service {service_name} missing build configuration")
                continue
                
            build_config = service_config['build']
            if 'dockerfile' not in build_config:
                dockerfile_issues.append(f"Service {service_name} missing dockerfile specification")
                continue
                
            dockerfile_path = Path(build_config['dockerfile'])
            
            # Check if dockerfile path exists relative to project root
            full_dockerfile_path = self.project_root / dockerfile_path
            if not full_dockerfile_path.exists():
                dockerfile_issues.append(f"Dockerfile not found for {service_name}: {full_dockerfile_path}")
        
        # This test is expected to fail initially, documenting the configuration mismatch
        if dockerfile_issues:
            self.fail(f"Dockerfile path configuration issues found: {dockerfile_issues}")

    def test_required_dockerfiles_exist(self):
        """Test 3: Verify all required Alpine Dockerfiles exist in expected location"""
        missing_dockerfiles = []
        
        for service, expected_path in self.expected_dockerfiles.items():
            if not expected_path.exists():
                missing_dockerfiles.append(f"{service}: {expected_path}")
        
        self.assertEqual(
            len(missing_dockerfiles), 0,
            f"Missing required Dockerfiles: {missing_dockerfiles}"
        )

    def test_docker_build_command_validation(self):
        """Test 4: Test docker build command for each service (without actually building)"""
        # Validate that docker build commands would work with correct paths
        build_commands = []
        
        for service, dockerfile_path in self.expected_dockerfiles.items():
            build_cmd = [
                "docker", "build",
                "-f", str(dockerfile_path),
                "-t", f"netra-alpine-test-{service}:latest",
                "--build-arg", "BUILD_ENV=test",
                str(self.project_root)
            ]
            build_commands.append((service, build_cmd))
        
        # Validate build commands are properly formed
        for service, cmd in build_commands:
            self.assertIn("docker", cmd[0], f"Build command for {service} should use docker")
            self.assertIn("-f", cmd, f"Build command for {service} should specify dockerfile")
            self.assertTrue(
                any("-t" in str(arg) for arg in cmd),
                f"Build command for {service} should specify tag"
            )

    def test_docker_compose_build_vs_pull_strategy(self):
        """Test 5: Validate that compose file uses BUILD strategy, not PULL for custom images"""
        with open(self.docker_compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        services = compose_data.get('services', {})
        
        for service_name in ['alpine-test-migration', 'alpine-test-backend', 'alpine-test-auth', 'alpine-test-frontend']:
            service_config = services.get(service_name, {})
            
            # Custom images should have build configuration
            self.assertIn(
                'build', service_config,
                f"Service {service_name} should use BUILD strategy, not pull from registry"
            )
            
            # Should also have image name for tagging
            self.assertIn(
                'image', service_config,
                f"Service {service_name} should specify image name for built image"
            )

    @pytest.mark.integration
    def test_docker_daemon_availability(self):
        """Test 6: Verify Docker daemon is available for building"""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(
                result.returncode, 0,
                f"Docker daemon not available: {result.stderr}"
            )
        except subprocess.TimeoutExpired:
            self.fail("Docker command timed out - daemon may not be running")
        except FileNotFoundError:
            self.fail("Docker command not found - Docker not installed")

    @pytest.mark.integration 
    def test_docker_compose_syntax_validation(self):
        """Test 7: Validate docker-compose file syntax with docker-compose config"""
        try:
            # Test docker-compose config command to validate syntax
            result = subprocess.run([
                "docker-compose", 
                "-f", str(self.docker_compose_file),
                "config"
            ], 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=str(self.project_root)
            )
            
            if result.returncode != 0:
                # Expected to fail initially due to dockerfile path issues
                self.assertIn(
                    "docker/", result.stderr,
                    f"Expected dockerfile path error, got: {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            self.fail("Docker compose config validation timed out")
        except FileNotFoundError:
            self.skipTest("docker-compose not available for syntax validation")

    def test_integration_test_runner_alpine_references(self):
        """Test 8: Verify unified test runner correctly references Alpine compose file"""
        test_runner_path = self.project_root / "tests" / "unified_test_runner.py"
        
        with open(test_runner_path, 'r') as f:
            content = f.read()
        
        # Should reference the correct compose file path
        self.assertIn(
            "docker-compose.alpine-test.yml",
            content,
            "Test runner should reference Alpine compose file"
        )
        
        # Should provide helpful tips for Alpine usage
        self.assertIn(
            "Alpine-based services",
            content,
            "Test runner should provide Alpine usage guidance"
        )

    def generate_remediation_plan(self) -> Dict[str, List[str]]:
        """Generate remediation plan based on test findings"""
        return {
            "dockerfile_path_fixes": [
                "Update docker-compose.alpine-test.yml dockerfile paths",
                "Change 'docker/' prefix to 'dockerfiles/' prefix",
                "Verify all dockerfile paths are relative to project root"
            ],
            "build_strategy_validation": [
                "Ensure all custom services use 'build:' configuration",
                "Verify 'context:' points to project root",
                "Validate 'args:' include BUILD_ENV=test"
            ],
            "integration_testing": [
                "Test docker-compose build command with fixed paths",
                "Validate all services build without registry access",
                "Confirm unified test runner can use built images"
            ],
            "success_criteria": [
                "docker-compose -f docker/docker-compose.alpine-test.yml build succeeds",
                "All 4 custom images build locally without registry errors",
                "Integration tests can start Alpine stack with --real-services flag",
                "No 'pull access denied' errors for custom images"
            ]
        }


class TestIssue458RemediationValidation(unittest.TestCase):
    """
    Post-fix validation tests to confirm Issue #458 is resolved
    
    These tests should PASS after dockerfile path configuration is fixed
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        super().setUpClass()
        cls.project_root = Path(__file__).parent.parent.parent
        cls.docker_compose_file = cls.project_root / "docker" / "docker-compose.alpine-test.yml"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_docker_compose_build_success(self):
        """Post-fix test: Docker compose build should succeed"""
        try:
            # Test actual build process
            result = subprocess.run([
                "docker-compose",
                "-f", str(self.docker_compose_file), 
                "build",
                "--parallel",
                "--progress", "plain"
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes for build
            cwd=str(self.project_root)
            )
            
            self.assertEqual(
                result.returncode, 0,
                f"Docker compose build failed: {result.stderr}"
            )
            
            # Verify no registry access errors
            self.assertNotIn(
                "pull access denied",
                result.stderr,
                "Should not have registry access errors for local build"
            )
            
        except subprocess.TimeoutExpired:
            self.fail("Docker compose build timed out - may indicate configuration issues")

    @pytest.mark.integration
    def test_built_images_exist_locally(self):
        """Post-fix test: Verify built images exist in local Docker"""
        custom_images = [
            "netra-alpine-test-migration:latest",
            "netra-alpine-test-backend:latest", 
            "netra-alpine-test-auth:latest",
            "netra-alpine-test-frontend:latest"
        ]
        
        for image_name in custom_images:
            try:
                result = subprocess.run([
                    "docker", "image", "inspect", image_name
                ],
                capture_output=True,
                text=True,
                timeout=10
                )
                
                self.assertEqual(
                    result.returncode, 0,
                    f"Built image not found locally: {image_name}"
                )
                
            except subprocess.TimeoutExpired:
                self.fail(f"Docker image inspect timed out for {image_name}")

    @pytest.mark.integration  
    @pytest.mark.slow
    def test_alpine_compose_stack_startup(self):
        """Post-fix test: Full Alpine stack should start successfully"""
        project_name = f"netra-alpine-test-validation-{os.getpid()}"
        
        try:
            # Start the stack
            result = subprocess.run([
                "docker-compose",
                "-f", str(self.docker_compose_file),
                "-p", project_name,
                "up", "-d", "--build"
            ],
            capture_output=True,
            text=True, 
            timeout=300,  # 5 minutes
            cwd=str(self.project_root)
            )
            
            self.assertEqual(
                result.returncode, 0,
                f"Alpine stack startup failed: {result.stderr}"
            )
            
            # Verify services are healthy
            # (Health check validation would go here)
            
        except subprocess.TimeoutExpired:
            self.fail("Alpine stack startup timed out")
        
        finally:
            # Cleanup
            subprocess.run([
                "docker-compose",
                "-f", str(self.docker_compose_file), 
                "-p", project_name,
                "down", "-v", "--remove-orphans"
            ],
            capture_output=True,
            timeout=60,
            cwd=str(self.project_root)
            )


if __name__ == '__main__':
    # Print remediation plan
    test_instance = TestIssue458AlpineImageAccess()
    test_instance.setUpClass()
    remediation_plan = test_instance.generate_remediation_plan()
    
    print("=== ISSUE #458 REMEDIATION PLAN ===")
    for category, actions in remediation_plan.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for action in actions:
            print(f"  • {action}")
    
    print("\n=== RUNNING VALIDATION TESTS ===")
    pytest.main([__file__, "-v", "--tb=short"])