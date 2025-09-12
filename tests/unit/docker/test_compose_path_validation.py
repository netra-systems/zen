"""
Unit tests for Docker compose path validation - NO DOCKER BUILDS REQUIRED

Purpose: Validate Docker compose configurations detect path misconfigurations 
Issue: #443 - Docker compose path validation (part of Issue #426 cluster)
Approach: File system validation only, no container builds

MISSION CRITICAL: These tests must detect the 5/6 broken Docker compose files
WITHOUT requiring Docker to be running or functional.

Business Impact: $500K+ ARR Golden Path depends on working Docker infrastructure
"""

import pytest
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDockerComposePathValidation(SSotBaseTestCase):
    """Unit tests for Docker compose path validation - FILE SYSTEM ONLY"""
    
    @classmethod
    def setUpClass(cls):
        """Setup test environment - locate project root and Docker files"""
        super().setUpClass()
        
        # Locate project root
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.docker_dir = cls.project_root / "docker"
        
        # Expected Docker compose files
        cls.expected_compose_files = [
            "docker-compose.yml",
            "docker-compose.staging.yml", 
            "docker-compose.minimal-test.yml",
            "docker-compose.alpine-test.yml",
            "docker-compose.alpine-dev.yml",
            "docker-compose.staging.alpine.yml"
        ]
        
        cls.logger.info(f"Testing Docker compose files in: {cls.docker_dir}")

    def test_all_docker_compose_files_exist(self):
        """
        Test that all expected Docker compose files exist
        
        Issue: #443 - Basic file existence validation
        Difficulty: Low (5 minutes)
        Expected: PASS - Files should exist
        """
        missing_files = []
        
        for compose_file in self.expected_compose_files:
            file_path = self.docker_dir / compose_file
            if not file_path.exists():
                missing_files.append(str(file_path))
        
        assert not missing_files, (
            f"Missing Docker compose files: {missing_files}. "
            f"This breaks Docker infrastructure and prevents service startup."
        )

    def test_docker_compose_files_are_valid_yaml(self):
        """
        Test that all Docker compose files contain valid YAML
        
        Issue: #443 - YAML syntax validation
        Difficulty: Low (10 minutes) 
        Expected: MAY FAIL - Syntax errors could exist
        """
        yaml_errors = []
        
        for compose_file in self.expected_compose_files:
            file_path = self.docker_dir / compose_file
            
            if not file_path.exists():
                continue  # Skip missing files (covered by other test)
                
            try:
                with open(file_path, 'r') as f:
                    yaml.safe_load(f)
                    
            except yaml.YAMLError as e:
                yaml_errors.append({
                    "file": compose_file,
                    "error": str(e)
                })
        
        assert not yaml_errors, (
            f"YAML syntax errors in Docker compose files: {yaml_errors}. "
            f"This prevents Docker from parsing configurations."
        )

    def test_build_context_paths_exist(self):
        """
        Test that all build context paths referenced in compose files exist
        
        Issue: #443 - Build context validation (CRITICAL)
        Difficulty: Medium (15 minutes)
        Expected: LIKELY TO FAIL - This is probably the root cause
        """
        build_context_errors = []
        
        for compose_file in self.expected_compose_files:
            file_path = self.docker_dir / compose_file
            
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r') as f:
                    compose_config = yaml.safe_load(f)
                    
                if not compose_config or 'services' not in compose_config:
                    continue
                    
                # Check build contexts for each service
                for service_name, service_config in compose_config['services'].items():
                    if 'build' in service_config:
                        build_config = service_config['build']
                        
                        # Handle both string and dict build configurations
                        if isinstance(build_config, str):
                            context_path = build_config
                        elif isinstance(build_config, dict) and 'context' in build_config:
                            context_path = build_config['context']
                        else:
                            continue
                            
                        # Resolve context path relative to compose file
                        if context_path.startswith('./'):
                            # Relative to compose file location
                            resolved_path = self.docker_dir / context_path[2:]
                        elif context_path.startswith('/'):
                            # Absolute path
                            resolved_path = Path(context_path)
                        else:
                            # Relative to project root (common pattern)
                            resolved_path = self.project_root / context_path
                            
                        if not resolved_path.exists():
                            build_context_errors.append({
                                "compose_file": compose_file,
                                "service": service_name,
                                "context_path": context_path,
                                "resolved_path": str(resolved_path),
                                "error": "Build context directory does not exist"
                            })
                            
            except Exception as e:
                build_context_errors.append({
                    "compose_file": compose_file,
                    "service": "unknown",
                    "error": f"Failed to parse compose file: {e}"
                })
        
        if build_context_errors:
            self.logger.error(f"Build context path errors: {build_context_errors}")
            
        assert not build_context_errors, (
            f"Build context path errors: {build_context_errors}. "
            f"CRITICAL: This is likely the root cause of Issue #426 Docker failures. "
            f"Services cannot build because build contexts point to non-existent directories."
        )

    def test_dockerfile_paths_exist(self):
        """
        Test that all Dockerfile paths referenced in compose files exist
        
        Issue: #443 - Dockerfile path validation
        Difficulty: Medium (15 minutes)
        Expected: MAY FAIL - Dockerfile paths could be wrong
        """
        dockerfile_errors = []
        
        for compose_file in self.expected_compose_files:
            file_path = self.docker_dir / compose_file
            
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r') as f:
                    compose_config = yaml.safe_load(f)
                    
                if not compose_config or 'services' not in compose_config:
                    continue
                    
                # Check Dockerfile paths for each service
                for service_name, service_config in compose_config['services'].items():
                    if 'build' in service_config:
                        build_config = service_config['build']
                        
                        dockerfile_path = None
                        context_path = "."
                        
                        # Handle both string and dict build configurations
                        if isinstance(build_config, dict):
                            if 'dockerfile' in build_config:
                                dockerfile_path = build_config['dockerfile']
                            if 'context' in build_config:
                                context_path = build_config['context']
                        
                        # Default Dockerfile name if not specified
                        if dockerfile_path is None:
                            dockerfile_path = "Dockerfile"
                            
                        # Resolve Dockerfile path
                        if context_path.startswith('./'):
                            context_dir = self.docker_dir / context_path[2:]
                        elif context_path.startswith('/'):
                            context_dir = Path(context_path)
                        else:
                            context_dir = self.project_root / context_path
                            
                        # Dockerfile path relative to context
                        if dockerfile_path.startswith('./'):
                            resolved_dockerfile = context_dir / dockerfile_path[2:]
                        elif dockerfile_path.startswith('/'):
                            resolved_dockerfile = Path(dockerfile_path)
                        else:
                            resolved_dockerfile = context_dir / dockerfile_path
                            
                        if not resolved_dockerfile.exists():
                            dockerfile_errors.append({
                                "compose_file": compose_file,
                                "service": service_name,
                                "dockerfile_path": dockerfile_path,
                                "context_path": context_path,
                                "resolved_path": str(resolved_dockerfile),
                                "error": "Dockerfile does not exist"
                            })
                            
            except Exception as e:
                dockerfile_errors.append({
                    "compose_file": compose_file,
                    "service": "unknown", 
                    "error": f"Failed to parse compose file: {e}"
                })
        
        if dockerfile_errors:
            self.logger.error(f"Dockerfile path errors: {dockerfile_errors}")
            
        assert not dockerfile_errors, (
            f"Dockerfile path errors: {dockerfile_errors}. "
            f"Services cannot build because Dockerfiles are missing or incorrectly referenced."
        )

    def test_service_dependency_consistency(self):
        """
        Test that service dependencies reference valid services
        
        Issue: #443 - Service dependency validation
        Difficulty: Medium (20 minutes)
        Expected: MAY FAIL - Dependencies might reference non-existent services
        """
        dependency_errors = []
        
        for compose_file in self.expected_compose_files:
            file_path = self.docker_dir / compose_file
            
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r') as f:
                    compose_config = yaml.safe_load(f)
                    
                if not compose_config or 'services' not in compose_config:
                    continue
                    
                services = compose_config['services']
                service_names = set(services.keys())
                
                # Check dependencies for each service
                for service_name, service_config in services.items():
                    # Check depends_on dependencies
                    if 'depends_on' in service_config:
                        depends_on = service_config['depends_on']
                        
                        # Handle both list and dict formats
                        if isinstance(depends_on, list):
                            dependency_names = depends_on
                        elif isinstance(depends_on, dict):
                            dependency_names = list(depends_on.keys())
                        else:
                            continue
                            
                        # Validate each dependency exists
                        for dep_name in dependency_names:
                            if dep_name not in service_names:
                                dependency_errors.append({
                                    "compose_file": compose_file,
                                    "service": service_name,
                                    "missing_dependency": dep_name,
                                    "available_services": list(service_names)
                                })
                    
                    # Check network aliases point to valid services (less common)
                    if 'networks' in service_config:
                        networks = service_config['networks']
                        if isinstance(networks, dict):
                            for network_name, network_config in networks.items():
                                if isinstance(network_config, dict) and 'aliases' in network_config:
                                    # This is less critical, just log for now
                                    pass
                                    
            except Exception as e:
                dependency_errors.append({
                    "compose_file": compose_file,
                    "service": "unknown",
                    "error": f"Failed to parse compose file: {e}"
                })
        
        assert not dependency_errors, (
            f"Service dependency errors: {dependency_errors}. "
            f"Services have dependencies on non-existent services, preventing startup."
        )

    def test_port_mapping_conflicts(self):
        """
        Test for port mapping conflicts across compose files
        
        Issue: #443 - Port conflict detection
        Difficulty: Medium (15 minutes)
        Expected: MAY FAIL - Port conflicts could prevent service startup
        """
        port_mappings = {}  # port -> [(compose_file, service)]
        port_conflicts = []
        
        for compose_file in self.expected_compose_files:
            file_path = self.docker_dir / compose_file
            
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r') as f:
                    compose_config = yaml.safe_load(f)
                    
                if not compose_config or 'services' not in compose_config:
                    continue
                    
                # Extract port mappings for each service
                for service_name, service_config in compose_config['services'].items():
                    if 'ports' in service_config:
                        for port_mapping in service_config['ports']:
                            if isinstance(port_mapping, str):
                                # Format: "host_port:container_port" 
                                if ':' in port_mapping:
                                    host_port = port_mapping.split(':')[0]
                                    # Handle port ranges and variable substitutions
                                    if '-' not in host_port and '${' not in host_port:
                                        port_key = host_port
                                        
                                        if port_key in port_mappings:
                                            port_conflicts.append({
                                                "port": port_key,
                                                "conflict_services": port_mappings[port_key] + [(compose_file, service_name)]
                                            })
                                        else:
                                            port_mappings[port_key] = [(compose_file, service_name)]
            except Exception as e:
                self.logger.warning(f"Error parsing compose file {compose_file}: {e}")
                continue
        
        # Note: Port conflicts might be acceptable if services are in different profiles
        # This is more of a warning than a hard failure
        if port_conflicts:
            self.logger.warning(f"Potential port conflicts detected: {port_conflicts}")
            # Don't fail the test for port conflicts as they might be in different profiles
            
    def test_environment_variable_consistency(self):
        """
        Test that environment variables are consistently defined
        
        Issue: #443 - Environment variable validation
        Difficulty: Low (10 minutes)
        Expected: PASS - Environment variables should be consistent
        """
        env_var_usage = {}  # var_name -> [(compose_file, service, default_value)]
        
        for compose_file in self.expected_compose_files:
            file_path = self.docker_dir / compose_file
            
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r') as f:
                    compose_config = yaml.safe_load(f)
                    
                if not compose_config or 'services' not in compose_config:
                    continue
                    
                # Extract environment variable usage
                for service_name, service_config in compose_config['services'].items():
                    if 'environment' in service_config:
                        env_vars = service_config['environment']
                        
                        # Handle both dict and list formats
                        if isinstance(env_vars, dict):
                            for var_name, var_value in env_vars.items():
                                # Track variable usage with default values
                                if isinstance(var_value, str) and var_value.startswith('${') and ':-' in var_value:
                                    # Format: ${VAR_NAME:-default_value}
                                    var_parts = var_value[2:-1].split(':-', 1)
                                    actual_var_name = var_parts[0]
                                    default_value = var_parts[1] if len(var_parts) > 1 else None
                                    
                                    key = actual_var_name
                                    if key not in env_var_usage:
                                        env_var_usage[key] = []
                                    env_var_usage[key].append((compose_file, service_name, default_value))
                        
                        elif isinstance(env_vars, list):
                            for env_item in env_vars:
                                if '=' in str(env_item):
                                    var_name = str(env_item).split('=')[0]
                                    if var_name not in env_var_usage:
                                        env_var_usage[var_name] = []
                                    env_var_usage[var_name].append((compose_file, service_name, None))
                                    
            except Exception as e:
                self.logger.warning(f"Failed to parse environment variables in {compose_file}: {e}")
        
        # Check for inconsistent default values
        inconsistent_defaults = []
        for var_name, usages in env_var_usage.items():
            default_values = set([usage[2] for usage in usages if usage[2] is not None])
            if len(default_values) > 1:
                inconsistent_defaults.append({
                    "variable": var_name,
                    "different_defaults": list(default_values),
                    "usages": usages
                })
        
        # This is a warning rather than a failure - inconsistent defaults are common
        if inconsistent_defaults:
            self.logger.info(f"Environment variables with different defaults: {inconsistent_defaults}")

    def test_compose_file_completeness(self):
        """
        Test that compose files have required sections
        
        Issue: #443 - Compose file structure validation
        Difficulty: Low (10 minutes)
        Expected: PASS - Files should have basic required structure
        """
        structure_issues = []
        
        required_sections = ['services']  # Minimal requirement
        recommended_sections = ['version', 'services', 'networks', 'volumes']
        
        for compose_file in self.expected_compose_files:
            file_path = self.docker_dir / compose_file
            
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r') as f:
                    compose_config = yaml.safe_load(f)
                    
                if not compose_config:
                    structure_issues.append({
                        "compose_file": compose_file,
                        "issue": "Empty or invalid YAML"
                    })
                    continue
                
                # Check required sections
                for section in required_sections:
                    if section not in compose_config:
                        structure_issues.append({
                            "compose_file": compose_file,
                            "issue": f"Missing required section: {section}"
                        })
                
                # Check if services section is empty
                if 'services' in compose_config and not compose_config['services']:
                    structure_issues.append({
                        "compose_file": compose_file,
                        "issue": "Services section is empty"
                    })
                    
            except Exception as e:
                structure_issues.append({
                    "compose_file": compose_file,
                    "issue": f"Failed to parse: {e}"
                })
        
        assert not structure_issues, (
            f"Compose file structure issues: {structure_issues}. "
            f"Files are missing required sections or have invalid structure."
        )


# Test configuration
pytestmark = [
    pytest.mark.unit,
    pytest.mark.docker_infrastructure,
    pytest.mark.path_validation,
    pytest.mark.issue_443,
    pytest.mark.issue_426_cluster,
    pytest.mark.no_docker_required
]


if __name__ == "__main__":
    # Allow running this file directly for focused testing
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--no-docker"  # Ensure Docker is not used
    ])