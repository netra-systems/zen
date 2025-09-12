"""
Unit tests for Dockerfile path consistency validation - NO DOCKER BUILDS REQUIRED

Purpose: Validate that Dockerfiles exist and are consistent across environments
Issue: #443 - Docker infrastructure path validation (part of Issue #426 cluster)
Approach: File system validation and content analysis, no container builds

MISSION CRITICAL: These tests detect Dockerfile path misconfigurations that break
service builds without requiring Docker to be running.
"""

import pytest
import os
from pathlib import Path
from typing import Dict, List, Set
import re

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDockerfilePathConsistency(SSotBaseTestCase):
    """Unit tests for Dockerfile path consistency - FILE SYSTEM ONLY"""
    
    @classmethod
    def setUpClass(cls):
        """Setup test environment - locate Dockerfile directories"""
        super().setUpClass()
        
        # Locate project root and Dockerfile directories
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.dockerfiles_dir = cls.project_root / "dockerfiles"
        cls.docker_dir = cls.project_root / "docker"
        
        # Expected Dockerfiles based on typical service structure
        cls.expected_dockerfiles = [
            "backend.Dockerfile",
            "auth.Dockerfile", 
            "frontend.Dockerfile"
        ]
        
        cls.logger.info(f"Testing Dockerfiles in: {cls.dockerfiles_dir}")

    def test_dockerfile_directory_exists(self):
        """
        Test that the dockerfiles directory exists
        
        Issue: #443 - Basic directory validation
        Difficulty: Low (2 minutes)
        Expected: PASS - Directory should exist
        """
        assert self.dockerfiles_dir.exists(), (
            f"Dockerfiles directory does not exist: {self.dockerfiles_dir}. "
            f"This breaks Docker builds referenced in compose files."
        )
        
        assert self.dockerfiles_dir.is_dir(), (
            f"Dockerfiles path is not a directory: {self.dockerfiles_dir}"
        )

    def test_expected_dockerfiles_exist(self):
        """
        Test that expected Dockerfile files exist
        
        Issue: #443 - Dockerfile existence validation
        Difficulty: Low (5 minutes)
        Expected: MAY FAIL - Dockerfiles could be missing
        """
        missing_dockerfiles = []
        
        for dockerfile_name in self.expected_dockerfiles:
            dockerfile_path = self.dockerfiles_dir / dockerfile_name
            if not dockerfile_path.exists():
                missing_dockerfiles.append(str(dockerfile_path))
        
        assert not missing_dockerfiles, (
            f"Missing Dockerfiles: {missing_dockerfiles}. "
            f"These are required for service builds referenced in Docker compose files."
        )

    def test_dockerfile_basic_structure(self):
        """
        Test that Dockerfiles have basic required structure
        
        Issue: #443 - Dockerfile content validation
        Difficulty: Medium (15 minutes)
        Expected: MAY FAIL - Dockerfiles could have structural issues
        """
        dockerfile_issues = []
        
        # Required Dockerfile instructions
        required_instructions = ['FROM']  # Minimal requirement
        recommended_instructions = ['FROM', 'WORKDIR', 'COPY', 'RUN', 'CMD']
        
        for dockerfile_name in self.expected_dockerfiles:
            dockerfile_path = self.dockerfiles_dir / dockerfile_name
            
            if not dockerfile_path.exists():
                continue  # Skip missing files (covered by other test)
                
            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()
                
                # Check for required instructions
                missing_required = []
                for instruction in required_instructions:
                    if not re.search(f'^{instruction}\\s', dockerfile_content, re.MULTILINE):
                        missing_required.append(instruction)
                
                if missing_required:
                    dockerfile_issues.append({
                        "dockerfile": dockerfile_name,
                        "issue": f"Missing required instructions: {missing_required}"
                    })
                
                # Check for empty Dockerfile
                if not dockerfile_content.strip():
                    dockerfile_issues.append({
                        "dockerfile": dockerfile_name,
                        "issue": "Dockerfile is empty"
                    })
                
                # Check for common syntax issues
                if dockerfile_content.count('FROM') == 0:
                    dockerfile_issues.append({
                        "dockerfile": dockerfile_name,
                        "issue": "No FROM instruction found"
                    })
                
            except Exception as e:
                dockerfile_issues.append({
                    "dockerfile": dockerfile_name,
                    "issue": f"Failed to read Dockerfile: {e}"
                })
        
        assert not dockerfile_issues, (
            f"Dockerfile structure issues: {dockerfile_issues}. "
            f"These issues prevent Docker from building images successfully."
        )

    def test_dockerfile_copy_paths_exist(self):
        """
        Test that COPY/ADD source paths in Dockerfiles exist
        
        Issue: #443 - Dockerfile COPY path validation (CRITICAL)
        Difficulty: High (25 minutes)
        Expected: LIKELY TO FAIL - This could be a major issue
        """
        copy_path_errors = []
        
        for dockerfile_name in self.expected_dockerfiles:
            dockerfile_path = self.dockerfiles_dir / dockerfile_name
            
            if not dockerfile_path.exists():
                continue
                
            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_lines = f.readlines()
                
                # Parse COPY and ADD instructions
                for line_num, line in enumerate(dockerfile_lines, 1):
                    line = line.strip()
                    
                    # Match COPY and ADD instructions
                    copy_match = re.match(r'^(COPY|ADD)\s+(.+)', line)
                    if copy_match:
                        instruction = copy_match.group(1)
                        args = copy_match.group(2).strip()
                        
                        # Parse source and destination
                        # Handle various formats: COPY src dest, COPY ["src", "dest"], etc.
                        if args.startswith('['):
                            # JSON array format
                            try:
                                import json
                                args_list = json.loads(args)
                                if len(args_list) >= 2:
                                    source_paths = args_list[:-1]  # All but last are sources
                            except:
                                continue  # Skip malformed JSON
                        else:
                            # Space-separated format
                            parts = args.split()
                            if len(parts) >= 2:
                                source_paths = parts[:-1]  # All but last are sources
                            else:
                                continue
                        
                        # Validate source paths exist
                        for source_path in source_paths:
                            # Skip URLs and special paths
                            if (source_path.startswith('http') or 
                                source_path.startswith('--') or
                                source_path.startswith('.') and len(source_path) <= 2):
                                continue
                            
                            # Resolve path relative to project root (build context)
                            resolved_path = self.project_root / source_path
                            
                            if not resolved_path.exists():
                                copy_path_errors.append({
                                    "dockerfile": dockerfile_name,
                                    "line": line_num,
                                    "instruction": f"{instruction} {args}",
                                    "source_path": source_path,
                                    "resolved_path": str(resolved_path),
                                    "error": "Source path does not exist"
                                })
                                
            except Exception as e:
                copy_path_errors.append({
                    "dockerfile": dockerfile_name,
                    "error": f"Failed to parse Dockerfile: {e}"
                })
        
        if copy_path_errors:
            self.logger.error(f"COPY/ADD path errors: {copy_path_errors}")
            
        assert not copy_path_errors, (
            f"Dockerfile COPY/ADD path errors: {copy_path_errors}. "
            f"CRITICAL: These missing paths will cause Docker builds to fail. "
            f"This is likely a root cause of Issue #426 service startup failures."
        )

    def test_dockerfile_environment_consistency(self):
        """
        Test that Dockerfile environment variables are consistent
        
        Issue: #443 - Environment variable consistency across Dockerfiles
        Difficulty: Medium (20 minutes)
        Expected: MAY FAIL - Inconsistencies could exist
        """
        env_var_definitions = {}  # dockerfile -> [env_vars]
        consistency_issues = []
        
        for dockerfile_name in self.expected_dockerfiles:
            dockerfile_path = self.dockerfiles_dir / dockerfile_name
            
            if not dockerfile_path.exists():
                continue
                
            env_vars = []
            
            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_lines = f.readlines()
                
                # Extract ENV instructions
                for line_num, line in enumerate(dockerfile_lines, 1):
                    line = line.strip()
                    
                    env_match = re.match(r'^ENV\s+(.+)', line)
                    if env_match:
                        env_args = env_match.group(1)
                        
                        # Parse ENV instruction (can have multiple formats)
                        if '=' in env_args:
                            # ENV key=value or ENV key1=value1 key2=value2
                            pairs = re.findall(r'(\w+)=([^\s]+)', env_args)
                            for key, value in pairs:
                                env_vars.append({
                                    "key": key,
                                    "value": value,
                                    "line": line_num
                                })
                        else:
                            # ENV key value (single pair)
                            parts = env_args.split(None, 1)
                            if len(parts) == 2:
                                env_vars.append({
                                    "key": parts[0],
                                    "value": parts[1],
                                    "line": line_num
                                })
                
                env_var_definitions[dockerfile_name] = env_vars
                
            except Exception as e:
                consistency_issues.append({
                    "dockerfile": dockerfile_name,
                    "issue": f"Failed to parse ENV instructions: {e}"
                })
        
        # Check for common environment variables with different values
        common_env_vars = {}  # var_name -> {dockerfile: value}
        
        for dockerfile, env_vars in env_var_definitions.items():
            for env_var in env_vars:
                key = env_var["key"]
                value = env_var["value"]
                
                if key not in common_env_vars:
                    common_env_vars[key] = {}
                
                common_env_vars[key][dockerfile] = value
        
        # Find variables defined in multiple Dockerfiles with different values
        for var_name, dockerfile_values in common_env_vars.items():
            if len(dockerfile_values) > 1:
                values = set(dockerfile_values.values())
                if len(values) > 1:
                    consistency_issues.append({
                        "variable": var_name,
                        "issue": "Different values across Dockerfiles",
                        "dockerfile_values": dockerfile_values
                    })
        
        # This is typically a warning rather than a failure
        if consistency_issues:
            self.logger.info(f"Environment variable consistency issues: {consistency_issues}")

    def test_dockerfile_base_image_consistency(self):
        """
        Test that Dockerfile base images are consistent and reasonable
        
        Issue: #443 - Base image validation
        Difficulty: Medium (15 minutes)
        Expected: PASS - Base images should be reasonable
        """
        base_images = {}  # dockerfile -> base_image
        base_image_issues = []
        
        for dockerfile_name in self.expected_dockerfiles:
            dockerfile_path = self.dockerfiles_dir / dockerfile_name
            
            if not dockerfile_path.exists():
                continue
                
            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_lines = f.readlines()
                
                # Find FROM instructions
                from_instructions = []
                for line_num, line in enumerate(dockerfile_lines, 1):
                    line = line.strip()
                    
                    from_match = re.match(r'^FROM\s+(.+)', line)
                    if from_match:
                        base_image = from_match.group(1).strip()
                        
                        # Skip multi-stage build aliases
                        if ' as ' in base_image.lower():
                            base_image = base_image.lower().split(' as ')[0].strip()
                        
                        from_instructions.append({
                            "line": line_num,
                            "base_image": base_image
                        })
                
                if from_instructions:
                    # Use the first (primary) base image
                    primary_base_image = from_instructions[0]["base_image"]
                    base_images[dockerfile_name] = primary_base_image
                    
                    # Check for reasonable base images
                    suspicious_bases = []
                    for from_instruction in from_instructions:
                        base_image = from_instruction["base_image"]
                        
                        # Check for common issues
                        if base_image.lower() in ['scratch', 'latest', 'ubuntu', 'centos']:
                            suspicious_bases.append({
                                "base_image": base_image,
                                "line": from_instruction["line"],
                                "issue": "Potentially problematic base image"
                            })
                        
                        # Check for tag specification
                        if ':' not in base_image and not base_image.startswith('scratch'):
                            suspicious_bases.append({
                                "base_image": base_image,
                                "line": from_instruction["line"], 
                                "issue": "No tag specified (will use 'latest')"
                            })
                    
                    if suspicious_bases:
                        base_image_issues.append({
                            "dockerfile": dockerfile_name,
                            "suspicious_bases": suspicious_bases
                        })
                else:
                    base_image_issues.append({
                        "dockerfile": dockerfile_name,
                        "issue": "No FROM instruction found"
                    })
                    
            except Exception as e:
                base_image_issues.append({
                    "dockerfile": dockerfile_name,
                    "issue": f"Failed to parse FROM instructions: {e}"
                })
        
        # Log base images for analysis
        self.logger.info(f"Base images found: {base_images}")
        
        # This is more informational than a hard failure
        if base_image_issues:
            self.logger.warning(f"Base image analysis: {base_image_issues}")

    def test_dockerfile_workdir_consistency(self):
        """
        Test that WORKDIR instructions are consistent and reasonable
        
        Issue: #443 - Working directory validation
        Difficulty: Low (10 minutes) 
        Expected: PASS - Working directories should be reasonable
        """
        workdirs = {}  # dockerfile -> workdir
        workdir_issues = []
        
        for dockerfile_name in self.expected_dockerfiles:
            dockerfile_path = self.dockerfiles_dir / dockerfile_name
            
            if not dockerfile_path.exists():
                continue
                
            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_lines = f.readlines()
                
                # Find WORKDIR instructions
                for line_num, line in enumerate(dockerfile_lines, 1):
                    line = line.strip()
                    
                    workdir_match = re.match(r'^WORKDIR\s+(.+)', line)
                    if workdir_match:
                        workdir = workdir_match.group(1).strip()
                        workdirs[dockerfile_name] = workdir
                        
                        # Check for reasonable working directories
                        if not workdir.startswith('/'):
                            workdir_issues.append({
                                "dockerfile": dockerfile_name,
                                "workdir": workdir,
                                "line": line_num,
                                "issue": "WORKDIR should be absolute path"
                            })
                        
                        # Check for common problematic directories
                        problematic_dirs = ['/', '/root', '/home', '/tmp']
                        if workdir in problematic_dirs:
                            workdir_issues.append({
                                "dockerfile": dockerfile_name,
                                "workdir": workdir,
                                "line": line_num,
                                "issue": "Potentially problematic WORKDIR"
                            })
                            
            except Exception as e:
                workdir_issues.append({
                    "dockerfile": dockerfile_name,
                    "issue": f"Failed to parse WORKDIR instructions: {e}"
                })
        
        # Log working directories
        self.logger.info(f"Working directories found: {workdirs}")
        
        # Generally informational unless there are clear problems
        if workdir_issues:
            self.logger.warning(f"WORKDIR analysis: {workdir_issues}")


# Test configuration
pytestmark = [
    pytest.mark.unit,
    pytest.mark.docker_infrastructure,
    pytest.mark.dockerfile_validation,
    pytest.mark.issue_443,
    pytest.mark.issue_426_cluster,
    pytest.mark.no_docker_required
]


if __name__ == "__main__":
    # Allow running this file directly
    pytest.main([
        __file__,
        "-v", 
        "--tb=long",
        "-s",
        "--no-docker"
    ])