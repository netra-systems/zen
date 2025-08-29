#!/usr/bin/env python3
"""
Docker File Organization Compliance Checker

Validates that Docker files are properly organized according to SPEC/docker_file_organization.xml
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import yaml
import re

class DockerFileChecker:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors = []
        self.warnings = []
        
    def check_forbidden_locations(self) -> None:
        """Check that Docker files don't exist in forbidden locations"""
        forbidden_paths = [
            self.project_root / "netra_backend" / "Dockerfile",
            self.project_root / "auth_service" / "Dockerfile", 
            self.project_root / "frontend" / "Dockerfile"
        ]
        
        for path in forbidden_paths:
            if path.exists():
                self.errors.append(f"Dockerfile found in forbidden location: {path.relative_to(self.project_root)}")
                
    def check_expected_docker_files(self) -> None:
        """Check that expected Docker files exist"""
        expected_files = {
            "docker/backend.Dockerfile": "Production backend",
            "docker/backend.development.Dockerfile": "Development backend",
            "docker/auth.Dockerfile": "Production auth",
            "docker/auth.development.Dockerfile": "Development auth",
            "docker/auth.test.Dockerfile": "Test auth",
            "docker/frontend.Dockerfile": "Production frontend",
            "docker/frontend.development.Dockerfile": "Development frontend",
            "docker/frontend.test.Dockerfile": "Test frontend",
            "deployment/docker/backend.gcp.Dockerfile": "GCP backend",
            "deployment/docker/auth.gcp.Dockerfile": "GCP auth",
            "deployment/docker/frontend.gcp.Dockerfile": "GCP frontend"
        }
        
        for file_path, description in expected_files.items():
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.warnings.append(f"Missing expected Docker file: {file_path} ({description})")
                
    def check_docker_compose_references(self) -> None:
        """Check that docker-compose files reference existing Docker files"""
        compose_files = [
            "docker-compose.yml",
            "docker-compose.dev.yml", 
            "docker-compose.test.yml",
            "docker-compose.all.yml"
        ]
        
        for compose_file in compose_files:
            compose_path = self.project_root / compose_file
            if not compose_path.exists():
                continue
                
            with open(compose_path, 'r') as f:
                try:
                    compose_data = yaml.safe_load(f)
                    if not compose_data or 'services' not in compose_data:
                        continue
                        
                    for service_name, service_config in compose_data['services'].items():
                        if 'build' in service_config:
                            build_config = service_config['build']
                            if isinstance(build_config, dict) and 'dockerfile' in build_config:
                                dockerfile = build_config['dockerfile']
                                context = build_config.get('context', '.')
                                
                                # Resolve the dockerfile path relative to the context
                                if context == '.':
                                    dockerfile_path = self.project_root / dockerfile
                                else:
                                    dockerfile_path = self.project_root / context / dockerfile
                                    
                                if not dockerfile_path.exists():
                                    self.errors.append(
                                        f"{compose_file}: Service '{service_name}' references "
                                        f"non-existent Dockerfile: {dockerfile}"
                                    )
                except yaml.YAMLError as e:
                    self.warnings.append(f"Failed to parse {compose_file}: {e}")
                    
    def check_production_docker_files(self) -> None:
        """Check that production Docker files follow best practices"""
        production_files = [
            "docker/backend.Dockerfile",
            "docker/auth.Dockerfile",
            "docker/frontend.Dockerfile",
            "deployment/docker/backend.gcp.Dockerfile",
            "deployment/docker/auth.gcp.Dockerfile",
            "deployment/docker/frontend.gcp.Dockerfile",
            "deployment/docker/frontend.prod.Dockerfile"
        ]
        
        for file_path in production_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            with open(full_path, 'r') as f:
                content = f.read()
                
                # Check for multi-stage build
                if content.count('FROM ') < 2 and 'AS builder' not in content:
                    self.warnings.append(
                        f"{file_path}: Production Dockerfile should use multi-stage build"
                    )
                    
                # Check for non-root user
                if not re.search(r'USER\s+(?!root)', content):
                    self.warnings.append(
                        f"{file_path}: Production Dockerfile should run as non-root user"
                    )
                    
                # Check for health check
                if 'HEALTHCHECK' not in content:
                    self.warnings.append(
                        f"{file_path}: Dockerfile should include HEALTHCHECK"
                    )
                    
    def run_checks(self) -> Tuple[List[str], List[str]]:
        """Run all checks and return errors and warnings"""
        self.check_forbidden_locations()
        self.check_expected_docker_files()
        self.check_docker_compose_references()
        self.check_production_docker_files()
        
        return self.errors, self.warnings
        
def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent
    
    checker = DockerFileChecker(project_root)
    errors, warnings = checker.run_checks()
    
    print("Docker File Organization Compliance Check")
    print("=" * 50)
    
    if errors:
        print(f"\n[ERROR] Found {len(errors)} ERROR(S):")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n[OK] No errors found")
        
    if warnings:
        print(f"\n[WARNING] Found {len(warnings)} WARNING(S):")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("[OK] No warnings found")
        
    print("\n" + "=" * 50)
    
    if errors:
        print("[FAILED] Fix errors before proceeding")
        sys.exit(1)
    else:
        print("[PASSED] Docker files are properly organized")
        sys.exit(0)
        
if __name__ == "__main__":
    main()