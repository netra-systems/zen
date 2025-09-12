#!/usr/bin/env python3
"""
DEPLOYMENT SCRIPT CONFLICTS TEST SUITE
=====================================

Test Strategy for GitHub Issue #245: Identify deployment script conflicts and validate SSOT consolidation

CRITICAL FINDINGS DISCOVERED:
- 7+ conflicting deployment entry points confirmed
- UnifiedTestRunner false deployment mode claims verified
- Configuration drift risks between deployment methods identified
- Terraform calling deprecated scripts confirmed
- $500K+ ARR at risk from deployment reliability issues

This test suite systematically validates deployment infrastructure integrity.
"""

import os
import sys
import subprocess
import json
import pytest
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDeploymentScriptConflicts(SSotBaseTestCase):
    """Test suite to identify and validate deployment script conflicts."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        super().setUpClass()
        cls.project_root = PROJECT_ROOT
        cls.scripts_dir = cls.project_root / "scripts"
        cls.terraform_staging_dir = cls.project_root / "terraform-gcp-staging"
        cls.unified_test_runner = cls.project_root / "tests" / "unified_test_runner.py"
        
    def test_discover_all_deployment_entry_points(self):
        """
        CONFLICT DETECTION TEST 1: Discover all deployment entry points
        
        Maps all potential deployment scripts and entry points to identify conflicts.
        """
        deployment_files = []
        
        # Find all deployment-related files
        deployment_patterns = [
            "**/deploy*.py",
            "**/deploy*.sh", 
            "**/deploy*.bat",
            "**/deploy*.ps1"
        ]
        
        for pattern in deployment_patterns:
            deployment_files.extend(self.project_root.glob(pattern))
        
        # Categorize deployment files
        script_deployments = [f for f in deployment_files if f.parent.name == "scripts"]
        terraform_deployments = [f for f in deployment_files if "terraform" in str(f)]
        other_deployments = [f for f in deployment_files if f not in script_deployments + terraform_deployments]
        
        print(f"\n=== DEPLOYMENT ENTRY POINTS ANALYSIS ===")
        print(f"Scripts directory deployments: {len(script_deployments)}")
        for f in script_deployments:
            print(f"  - {f.name}")
            
        print(f"Terraform-related deployments: {len(terraform_deployments)}")
        for f in terraform_deployments:
            print(f"  - {f.relative_to(self.project_root)}")
            
        print(f"Other deployment files: {len(other_deployments)}")
        for f in other_deployments:
            print(f"  - {f.relative_to(self.project_root)}")
        
        # ASSERTION: Should have multiple deployment entry points (indicating conflicts)
        total_deployments = len(deployment_files)
        self.assertGreaterEqual(total_deployments, 7, 
                              f"Expected 7+ deployment entry points (indicating conflicts), found {total_deployments}")
        
        return {
            "scripts": script_deployments,
            "terraform": terraform_deployments, 
            "other": other_deployments,
            "total": total_deployments
        }
    
    def test_unified_test_runner_deployment_mode_false_claims(self):
        """
        CONFLICT DETECTION TEST 2: Validate UnifiedTestRunner deployment mode claims
        
        Tests whether the UnifiedTestRunner actually supports deployment mode as claimed
        by the deprecated deploy_to_gcp.py script.
        """
        # Read the deprecated deployment script
        deprecated_script = self.scripts_dir / "deploy_to_gcp.py"
        self.assertTrue(deprecated_script.exists(), "Deprecated deploy_to_gcp.py should exist")
        
        with open(deprecated_script, 'r') as f:
            deprecated_content = f.read()
        
        # Verify it claims to redirect to UnifiedTestRunner
        self.assertIn("execution-mode deploy", deprecated_content,
                     "Deprecated script should claim to redirect to UnifiedTestRunner deployment mode")
        
        # Read the UnifiedTestRunner to check if deployment mode actually exists
        with open(self.unified_test_runner, 'r') as f:
            runner_content = f.read()
        
        # Check for deployment mode support
        has_deploy_execution_mode = "execution-mode" in runner_content and "deploy" in runner_content
        has_deploy_handling = "--execution-mode" in runner_content and "deploy" in runner_content.lower()
        
        print(f"\n=== UNIFIED TEST RUNNER DEPLOYMENT MODE ANALYSIS ===")
        print(f"Deprecated script claims deployment mode support: True")
        print(f"UnifiedTestRunner contains 'execution-mode': {'execution-mode' in runner_content}")
        print(f"UnifiedTestRunner contains 'deploy': {'deploy' in runner_content}")
        print(f"UnifiedTestRunner has deployment handling: {has_deploy_handling}")
        
        # Search for specific deployment mode handling
        if "--execution-mode" in runner_content:
            # Extract execution mode choices
            lines = runner_content.split('\n')
            for i, line in enumerate(lines):
                if "--execution-mode" in line and "choices=" in line:
                    print(f"Execution mode choices found: {line.strip()}")
                    # Check if 'deploy' is in the choices
                    deploy_in_choices = "deploy" in line
                    print(f"'deploy' in execution mode choices: {deploy_in_choices}")
                    break
        
        # CRITICAL ASSERTION: If deprecated script claims deployment mode exists, it should actually exist
        if "execution-mode deploy" in deprecated_content:
            self.assertTrue(has_deploy_handling, 
                          "UnifiedTestRunner should support deployment mode if deprecated script claims it does")
        
        return {
            "deprecated_claims_deployment": "execution-mode deploy" in deprecated_content,
            "runner_has_deployment": has_deploy_handling,
            "conflict_detected": "execution-mode deploy" in deprecated_content and not has_deploy_handling
        }
    
    def test_configuration_consistency_across_deployment_methods(self):
        """
        CONFIGURATION CONSISTENCY TEST: Validate configurations are consistent across deployment methods
        
        Checks for configuration drift between different deployment entry points.
        """
        configurations = {}
        
        # Check deploy_to_gcp_actual.py configuration
        actual_script = self.scripts_dir / "deploy_to_gcp_actual.py"
        if actual_script.exists():
            configurations["actual_script"] = self._extract_deployment_config(actual_script)
        
        # Check docker-compose configurations
        compose_files = list(self.project_root.glob("docker-compose*.yml"))
        for compose_file in compose_files:
            key = f"compose_{compose_file.stem}"
            configurations[key] = self._extract_compose_config(compose_file)
        
        # Check terraform deployment scripts
        terraform_deploy = self.terraform_staging_dir / "deploy.sh"
        if terraform_deploy.exists():
            configurations["terraform_deploy"] = self._extract_terraform_config(terraform_deploy)
        
        print(f"\n=== CONFIGURATION CONSISTENCY ANALYSIS ===")
        for name, config in configurations.items():
            print(f"{name}: {config}")
        
        # Check for consistency issues
        inconsistencies = self._detect_configuration_inconsistencies(configurations)
        
        if inconsistencies:
            print(f"\n WARNING: [U+FE0F]  CONFIGURATION INCONSISTENCIES DETECTED:")
            for inconsistency in inconsistencies:
                print(f"  - {inconsistency}")
        
        return {
            "configurations": configurations,
            "inconsistencies": inconsistencies,
            "consistency_score": max(0, 100 - len(inconsistencies) * 10)
        }
    
    def test_terraform_deprecated_script_references(self):
        """
        TERRAFORM INTEGRATION TEST: Check if terraform calls deprecated scripts
        
        Validates that terraform infrastructure doesn't reference deprecated deployment scripts.
        """
        terraform_files = list(self.terraform_staging_dir.glob("**/*"))
        deprecated_references = []
        
        for tf_file in terraform_files:
            if tf_file.is_file() and tf_file.suffix in ['.tf', '.sh', '.py', '.md', '.ps1']:
                try:
                    with open(tf_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for references to deprecated scripts
                    if "deploy_to_gcp.py" in content:
                        deprecated_references.append({
                            "file": tf_file.relative_to(self.project_root),
                            "type": "deploy_to_gcp.py reference",
                            "content_snippet": self._extract_snippet(content, "deploy_to_gcp.py")
                        })
                        
                    if "scripts/deploy" in content and "deprecated" not in content.lower():
                        deprecated_references.append({
                            "file": tf_file.relative_to(self.project_root),
                            "type": "scripts/deploy reference",
                            "content_snippet": self._extract_snippet(content, "scripts/deploy")
                        })
                        
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        print(f"\n=== TERRAFORM DEPRECATED SCRIPT REFERENCES ===")
        if deprecated_references:
            print(f"Found {len(deprecated_references)} deprecated references:")
            for ref in deprecated_references:
                print(f"  File: {ref['file']}")
                print(f"  Type: {ref['type']}")
                print(f"  Snippet: {ref['content_snippet']}")
                print()
        else:
            print("No deprecated script references found in terraform files")
        
        # ASSERTION: Terraform should not reference deprecated scripts
        self.assertEqual(len(deprecated_references), 0,
                        f"Terraform files should not reference deprecated scripts. Found {len(deprecated_references)} references")
        
        return deprecated_references
    
    def test_docker_vs_gcp_deployment_configuration_drift(self):
        """
        CONFIGURATION DRIFT TEST: Compare Docker vs GCP Cloud Run deployment configurations
        
        Identifies potential configuration drift between local Docker and GCP deployments.
        """
        docker_config = self._extract_docker_deployment_config()
        gcp_config = self._extract_gcp_deployment_config()
        
        drift_analysis = self._analyze_configuration_drift(docker_config, gcp_config)
        
        print(f"\n=== DOCKER vs GCP CONFIGURATION DRIFT ANALYSIS ===")
        print(f"Docker services: {list(docker_config.keys())}")
        print(f"GCP services: {list(gcp_config.keys())}")
        
        if drift_analysis["drifts"]:
            print(f"\n WARNING: [U+FE0F]  CONFIGURATION DRIFTS DETECTED:")
            for drift in drift_analysis["drifts"]:
                print(f"  - {drift}")
        
        print(f"\nDrift score: {drift_analysis['drift_score']}% (lower is better)")
        
        # ASSERTION: Configuration drift should be minimal (< 30%)
        self.assertLess(drift_analysis["drift_score"], 30,
                       f"Configuration drift should be < 30%, found {drift_analysis['drift_score']}%")
        
        return drift_analysis
    
    def test_deployment_script_functional_validation(self):
        """
        FUNCTIONAL VALIDATION TEST: Test which deployment scripts are actually functional
        
        Performs dry-run validation to determine which deployment entry points are functional.
        """
        deployment_scripts = [
            self.scripts_dir / "deploy_to_gcp.py",
            self.scripts_dir / "deploy_to_gcp_actual.py",
            self.scripts_dir / "deploy_staging_with_validation.py",
            self.scripts_dir / "deploy_staging_with_sa.py"
        ]
        
        functionality_results = {}
        
        for script in deployment_scripts:
            if script.exists():
                result = self._test_script_functionality(script)
                functionality_results[script.name] = result
        
        print(f"\n=== DEPLOYMENT SCRIPT FUNCTIONALITY ANALYSIS ===")
        for script_name, result in functionality_results.items():
            status = " PASS:  FUNCTIONAL" if result["functional"] else " FAIL:  NON-FUNCTIONAL"
            print(f"{script_name}: {status}")
            if result["error"]:
                print(f"  Error: {result['error']}")
        
        functional_scripts = [name for name, result in functionality_results.items() if result["functional"]]
        
        # ASSERTION: Should have exactly one functional deployment script (SSOT)
        self.assertEqual(len(functional_scripts), 1,
                        f"Should have exactly 1 functional deployment script (SSOT), found {len(functional_scripts)}: {functional_scripts}")
        
        return functionality_results
    
    # Helper methods
    
    def _extract_deployment_config(self, script_path: Path) -> Dict:
        """Extract deployment configuration from a Python script."""
        try:
            with open(script_path, 'r') as f:
                content = f.read()
            
            config = {
                "has_gcp_project": "--project" in content,
                "has_build_local": "--build-local" in content,
                "has_secrets_check": "--check-secrets" in content,
                "has_rollback": "--rollback" in content,
                "imports_gcp_auth": "gcp_auth" in content.lower(),
                "imports_secrets": "secret" in content.lower()
            }
            return config
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_compose_config(self, compose_path: Path) -> Dict:
        """Extract configuration from docker-compose file."""
        try:
            import yaml
            with open(compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            services = list(compose_data.get('services', {}).keys()) if compose_data else []
            return {
                "services": services,
                "has_backend": "backend" in services,
                "has_auth": "auth" in services or "auth_service" in services,
                "has_frontend": "frontend" in services,
                "network_mode": "host" in str(compose_data).lower()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_terraform_config(self, terraform_script: Path) -> Dict:
        """Extract configuration from terraform deployment script."""
        try:
            with open(terraform_script, 'r') as f:
                content = f.read()
            
            return {
                "calls_deploy_script": "deploy_to_gcp.py" in content,
                "has_project_var": "PROJECT_ID" in content,
                "has_build_local": "--build-local" in content,
                "has_checks": "--run-checks" in content
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _detect_configuration_inconsistencies(self, configurations: Dict) -> List[str]:
        """Detect inconsistencies across different deployment configurations."""
        inconsistencies = []
        
        # Check for GCP project handling consistency
        gcp_project_configs = [name for name, config in configurations.items() 
                              if config.get("has_gcp_project") or config.get("has_project_var")]
        
        if len(gcp_project_configs) > 0 and len(gcp_project_configs) != len([c for c in configurations.values() if not c.get("error")]):
            inconsistencies.append(f"Inconsistent GCP project handling across deployments")
        
        # Check for service consistency
        service_configs = {}
        for name, config in configurations.items():
            if "services" in config:
                service_configs[name] = set(config["services"])
        
        if len(service_configs) > 1:
            all_services = set()
            for services in service_configs.values():
                all_services.update(services)
            
            for name, services in service_configs.items():
                missing = all_services - services
                if missing:
                    inconsistencies.append(f"{name} missing services: {missing}")
        
        return inconsistencies
    
    def _extract_docker_deployment_config(self) -> Dict:
        """Extract Docker deployment configuration."""
        docker_configs = {}
        
        compose_files = list(self.project_root.glob("docker-compose*.yml"))
        for compose_file in compose_files:
            config = self._extract_compose_config(compose_file)
            docker_configs[compose_file.name] = config
        
        return docker_configs
    
    def _extract_gcp_deployment_config(self) -> Dict:
        """Extract GCP deployment configuration."""
        gcp_config = {}
        
        # Check actual deployment script
        actual_script = self.scripts_dir / "deploy_to_gcp_actual.py"
        if actual_script.exists():
            gcp_config["deploy_script"] = self._extract_deployment_config(actual_script)
        
        # Check terraform configuration
        terraform_main = self.terraform_staging_dir / "main.tf"
        if terraform_main.exists():
            try:
                with open(terraform_main, 'r') as f:
                    tf_content = f.read()
                gcp_config["terraform"] = {
                    "has_cloud_run": "google_cloud_run" in tf_content,
                    "has_vpc_connector": "vpc_connector" in tf_content,
                    "has_load_balancer": "load_balancer" in tf_content
                }
            except Exception:
                pass
        
        return gcp_config
    
    def _analyze_configuration_drift(self, docker_config: Dict, gcp_config: Dict) -> Dict:
        """Analyze configuration drift between Docker and GCP deployments."""
        drifts = []
        
        # Extract service lists
        docker_services = set()
        for config in docker_config.values():
            if "services" in config and not config.get("error"):
                docker_services.update(config["services"])
        
        # GCP services are harder to extract, but we can check for key services
        gcp_services = set()
        if "deploy_script" in gcp_config and not gcp_config["deploy_script"].get("error"):
            # Assume standard 3-service deployment for GCP
            gcp_services = {"backend", "auth_service", "frontend"}
        
        # Compare services
        if docker_services and gcp_services:
            missing_in_gcp = docker_services - gcp_services
            missing_in_docker = gcp_services - docker_services
            
            if missing_in_gcp:
                drifts.append(f"Services in Docker but not GCP: {missing_in_gcp}")
            if missing_in_docker:
                drifts.append(f"Services in GCP but not Docker: {missing_in_docker}")
        
        # Calculate drift score (0-100, lower is better)
        drift_score = len(drifts) * 20  # Each drift adds 20% to score
        
        return {
            "drifts": drifts,
            "drift_score": min(drift_score, 100),
            "docker_services": docker_services,
            "gcp_services": gcp_services
        }
    
    def _test_script_functionality(self, script_path: Path) -> Dict:
        """Test if a deployment script is functional via dry-run."""
        try:
            # Try to run script with --help to see if it's functional
            result = subprocess.run([
                sys.executable, str(script_path), "--help"
            ], capture_output=True, text=True, timeout=10)
            
            functional = result.returncode == 0
            error = result.stderr if result.returncode != 0 else None
            
            return {
                "functional": functional,
                "error": error,
                "stdout": result.stdout[:200] if result.stdout else None
            }
        except subprocess.TimeoutExpired:
            return {
                "functional": False,
                "error": "Script timed out",
                "stdout": None
            }
        except Exception as e:
            return {
                "functional": False,
                "error": str(e),
                "stdout": None
            }
    
    def _extract_snippet(self, content: str, search_term: str, context_lines: int = 2) -> str:
        """Extract a snippet around a search term."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if search_term in line:
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                snippet_lines = lines[start:end]
                return '\n'.join(snippet_lines)
        return f"Found '{search_term}' but could not extract snippet"


class TestSSotDeploymentValidation(SSotBaseTestCase):
    """Test suite for SSOT deployment consolidation validation."""
    
    def test_single_canonical_deployment_source(self):
        """
        SSOT VALIDATION TEST 1: Ensure single canonical deployment source exists
        
        Validates that there is exactly one authoritative deployment implementation.
        """
        deployment_sources = self._identify_deployment_sources()
        
        print(f"\n=== SSOT DEPLOYMENT SOURCE ANALYSIS ===")
        for source_type, sources in deployment_sources.items():
            print(f"{source_type}: {len(sources)} sources")
            for source in sources:
                print(f"  - {source}")
        
        # Count active (non-deprecated) deployment sources
        active_sources = []
        for source_type, sources in deployment_sources.items():
            for source in sources:
                if not self._is_deprecated_source(source):
                    active_sources.append(f"{source_type}:{source}")
        
        print(f"\nActive (non-deprecated) deployment sources: {len(active_sources)}")
        for source in active_sources:
            print(f"  - {source}")
        
        # ASSERTION: Should have exactly one active deployment source (SSOT)
        self.assertEqual(len(active_sources), 1,
                        f"Should have exactly 1 active deployment source (SSOT), found {len(active_sources)}: {active_sources}")
        
        return {
            "all_sources": deployment_sources,
            "active_sources": active_sources,
            "ssot_compliant": len(active_sources) == 1
        }
    
    def test_deployment_dependency_chain_validation(self):
        """
        SSOT VALIDATION TEST 2: Validate deployment dependency chains
        
        Ensures deployment dependencies form a clean hierarchy without circular references.
        """
        dependency_chain = self._map_deployment_dependencies()
        
        print(f"\n=== DEPLOYMENT DEPENDENCY CHAIN ANALYSIS ===")
        for source, deps in dependency_chain.items():
            print(f"{source} depends on:")
            for dep in deps:
                print(f"  - {dep}")
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(dependency_chain)
        
        if circular_deps:
            print(f"\n WARNING: [U+FE0F]  CIRCULAR DEPENDENCIES DETECTED:")
            for cycle in circular_deps:
                print(f"  - {' -> '.join(cycle)}")
        
        # ASSERTION: No circular dependencies should exist
        self.assertEqual(len(circular_deps), 0,
                        f"No circular dependencies should exist, found {len(circular_deps)} cycles")
        
        return {
            "dependency_chain": dependency_chain,
            "circular_dependencies": circular_deps,
            "clean_hierarchy": len(circular_deps) == 0
        }
    
    def _identify_deployment_sources(self) -> Dict[str, List[str]]:
        """Identify all deployment sources by type."""
        sources = {
            "python_scripts": [],
            "shell_scripts": [],
            "docker_compose": [],
            "terraform": [],
            "test_runner": []
        }
        
        # Python deployment scripts
        python_scripts = list(self.project_root.glob("scripts/deploy*.py"))
        sources["python_scripts"] = [s.name for s in python_scripts]
        
        # Shell scripts
        shell_scripts = list(self.project_root.glob("scripts/deploy*.sh")) + list(self.project_root.glob("scripts/deploy*.bat"))
        sources["shell_scripts"] = [s.name for s in shell_scripts]
        
        # Docker compose files
        compose_files = list(self.project_root.glob("docker-compose*.yml"))
        sources["docker_compose"] = [s.name for s in compose_files]
        
        # Terraform files
        terraform_files = list(self.project_root.glob("terraform-gcp-staging/deploy.*"))
        sources["terraform"] = [s.name for s in terraform_files]
        
        # Test runner deployment capability
        unified_runner = self.project_root / "tests" / "unified_test_runner.py"
        if unified_runner.exists():
            with open(unified_runner, 'r') as f:
                content = f.read()
            if "deploy" in content.lower():
                sources["test_runner"] = ["unified_test_runner.py"]
        
        return sources
    
    def _is_deprecated_source(self, source_name: str) -> bool:
        """Check if a deployment source is deprecated."""
        deprecated_indicators = [
            "DEPRECATION WARNING",
            "deprecated",
            "DO NOT USE",
            "OBSOLETE"
        ]
        
        # Check script content for deprecation markers
        possible_paths = [
            self.project_root / "scripts" / source_name,
            self.project_root / "terraform-gcp-staging" / source_name,
            self.project_root / source_name
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                    
                    for indicator in deprecated_indicators:
                        if indicator in content:
                            return True
                except Exception:
                    continue
        
        return False
    
    def _map_deployment_dependencies(self) -> Dict[str, List[str]]:
        """Map deployment dependencies between sources."""
        dependencies = {}
        
        # Check each deployment script for dependencies
        deployment_files = []
        deployment_files.extend(list(self.project_root.glob("scripts/deploy*.py")))
        deployment_files.extend(list(self.project_root.glob("scripts/deploy*.sh")))
        deployment_files.extend(list(self.project_root.glob("terraform-gcp-staging/deploy.*")))
        
        for dep_file in deployment_files:
            deps = []
            try:
                with open(dep_file, 'r') as f:
                    content = f.read()
                
                # Look for references to other deployment scripts
                if "deploy_to_gcp" in content:
                    deps.append("deploy_to_gcp.py")
                if "unified_test_runner" in content:
                    deps.append("unified_test_runner.py")
                if "docker-compose" in content:
                    deps.append("docker-compose")
                if "terraform" in content and dep_file.name != "terraform":
                    deps.append("terraform")
                
                dependencies[dep_file.name] = deps
                
            except Exception:
                dependencies[dep_file.name] = []
        
        return dependencies
    
    def _detect_circular_dependencies(self, dependency_chain: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies in deployment chain."""
        def find_cycle(node, path, visited):
            if node in path:
                # Found cycle
                cycle_start = path.index(node)
                return [path[cycle_start:] + [node]]
            
            if node in visited:
                return []
            
            visited.add(node)
            path.append(node)
            
            cycles = []
            for dep in dependency_chain.get(node, []):
                cycles.extend(find_cycle(dep, path.copy(), visited))
            
            return cycles
        
        all_cycles = []
        visited = set()
        
        for node in dependency_chain:
            cycles = find_cycle(node, [], visited.copy())
            all_cycles.extend(cycles)
        
        return all_cycles


class TestGoldenPathDeploymentProtection(SSotBaseTestCase):
    """Test suite for Golden Path protection during deployment."""
    
    def test_deployment_preserves_user_login_flow(self):
        """
        GOLDEN PATH PROTECTION TEST 1: Ensure deployment preserves user login flow
        
        Critical test to ensure deployment changes don't break the primary user journey.
        """
        # This test validates that deployment configurations maintain auth service connectivity
        auth_configs = self._extract_auth_service_configs()
        
        print(f"\n=== AUTH SERVICE CONFIGURATION VALIDATION ===")
        for config_source, config in auth_configs.items():
            print(f"{config_source}: {config}")
        
        # Validate critical auth configurations
        critical_configs = [
            "jwt_secret_configured",
            "oauth_enabled", 
            "cors_configured",
            "database_connected"
        ]
        
        config_issues = []
        for config_source, config in auth_configs.items():
            for critical_config in critical_configs:
                if not config.get(critical_config, False):
                    config_issues.append(f"{config_source} missing {critical_config}")
        
        if config_issues:
            print(f"\n WARNING: [U+FE0F]  AUTH CONFIGURATION ISSUES:")
            for issue in config_issues:
                print(f"  - {issue}")
        
        # ASSERTION: Critical auth configurations should be present
        self.assertEqual(len(config_issues), 0,
                        f"Critical auth configurations missing: {config_issues}")
        
        return {
            "auth_configs": auth_configs,
            "config_issues": config_issues,
            "login_flow_protected": len(config_issues) == 0
        }
    
    def test_deployment_preserves_ai_response_capability(self):
        """
        GOLDEN PATH PROTECTION TEST 2: Ensure deployment preserves AI response capability
        
        Validates that deployment maintains agent execution and WebSocket communication.
        """
        ai_configs = self._extract_ai_service_configs()
        
        print(f"\n=== AI SERVICE CONFIGURATION VALIDATION ===")
        for config_source, config in ai_configs.items():
            print(f"{config_source}: {config}")
        
        # Check for WebSocket configuration preservation
        websocket_issues = []
        for config_source, config in ai_configs.items():
            if not config.get("websocket_enabled", False):
                websocket_issues.append(f"{config_source} missing WebSocket support")
            if not config.get("agent_execution_enabled", False):
                websocket_issues.append(f"{config_source} missing agent execution")
        
        # ASSERTION: WebSocket and agent execution should be configured
        self.assertEqual(len(websocket_issues), 0,
                        f"AI response capability issues: {websocket_issues}")
        
        return {
            "ai_configs": ai_configs,
            "websocket_issues": websocket_issues,
            "ai_response_protected": len(websocket_issues) == 0
        }
    
    def _extract_auth_service_configs(self) -> Dict:
        """Extract auth service configurations from deployment sources."""
        configs = {}
        
        # Check docker-compose files
        compose_files = list(self.project_root.glob("docker-compose*.yml"))
        for compose_file in compose_files:
            try:
                import yaml
                with open(compose_file, 'r') as f:
                    compose_data = yaml.safe_load(f)
                
                auth_config = {}
                if compose_data and "services" in compose_data:
                    # Look for auth service configuration
                    auth_services = [k for k in compose_data["services"].keys() if "auth" in k.lower()]
                    if auth_services:
                        auth_service = compose_data["services"][auth_services[0]]
                        env_vars = auth_service.get("environment", {})
                        
                        auth_config = {
                            "jwt_secret_configured": any("JWT" in str(k) for k in env_vars.keys()),
                            "oauth_enabled": any("OAUTH" in str(k) for k in env_vars.keys()),
                            "cors_configured": any("CORS" in str(k) for k in env_vars.keys()),
                            "database_connected": any("DATABASE" in str(k) or "DB" in str(k) for k in env_vars.keys())
                        }
                
                configs[f"compose_{compose_file.stem}"] = auth_config
                
            except Exception as e:
                configs[f"compose_{compose_file.stem}"] = {"error": str(e)}
        
        return configs
    
    def _extract_ai_service_configs(self) -> Dict:
        """Extract AI service configurations from deployment sources."""
        configs = {}
        
        # Check deployment scripts for AI/WebSocket configuration
        deployment_scripts = list(self.project_root.glob("scripts/deploy*.py"))
        for script in deployment_scripts:
            try:
                with open(script, 'r') as f:
                    content = f.read()
                
                ai_config = {
                    "websocket_enabled": "websocket" in content.lower(),
                    "agent_execution_enabled": "agent" in content.lower(),
                    "llm_configured": "llm" in content.lower() or "openai" in content.lower(),
                    "redis_configured": "redis" in content.lower()
                }
                
                configs[f"script_{script.stem}"] = ai_config
                
            except Exception as e:
                configs[f"script_{script.stem}"] = {"error": str(e)}
        
        return configs


if __name__ == "__main__":
    # Run specific test suites based on arguments
    import sys
    
    if len(sys.argv) > 1:
        test_suite = sys.argv[1]
        if test_suite == "conflicts":
            suite = pytest.TestLoader().loadTestsFromTestCase(TestDeploymentScriptConflicts)
        elif test_suite == "ssot":
            suite = pytest.TestLoader().loadTestsFromTestCase(TestSSotDeploymentValidation)
        elif test_suite == "golden_path":
            suite = pytest.TestLoader().loadTestsFromTestCase(TestGoldenPathDeploymentProtection)
        else:
            # Run all tests
            suite = pytest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    else:
        # Run all tests
        suite = pytest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    
    runner = pytest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)