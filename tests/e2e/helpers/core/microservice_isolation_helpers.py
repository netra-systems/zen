"""
Microservice Isolation Validation Test Suite

BVJ: Segment: Enterprise | Goal: Compliance | Impact: $100K+ MRR (SOC2 + Scalability)
SPEC: SPEC/independent_services.xml
BUSINESS IMPACT: Critical for SOC2 compliance, independent scaling, and enterprise sales

This test ensures 100% microservice independence preventing cascading failures worth $100K+ MRR.

Critical Requirements:
1. Zero cross-service imports (auth_service has NO app.* imports)  
2. Backend has NO auth_service.* imports
3. Frontend has NO direct backend module imports
4. Unique module namespaces (auth_core/ not app/)
5. Dockerfile independence validation
6. Service startup independence simulation

Prevents: Cascading failures, deployment coupling, enterprise compliance violations
"""

import ast
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent

# Test configuration - Fast static analysis focused
TEST_TIMEOUT = 15  # seconds - Static analysis should be fast
AST_PARSE_TIMEOUT = 5  # seconds - Fast AST parsing
DOCKERFILE_SCAN_TIMEOUT = 3  # seconds - Quick file scanning


@dataclass
class MicroserviceSpec:
    """Specification for microservice isolation requirements."""
    name: str
    path: Path
    module_namespace: str
    forbidden_imports: List[str]
    forbidden_patterns: List[str]
    required_independence_files: List[str]
    dockerfile_name: Optional[str]


class MicroserviceIsolationValidator:
    """
    BVJ: Enterprise | SOC2 Compliance | $100K+ MRR Impact
    
    Comprehensive static analysis validator for microservice isolation.
    Prevents coupling that causes cascading failures in enterprise deployments.
    """
    
    def __init__(self):
        self.project_root = project_root
        self.scan_stats = {
            "total_files_scanned": 0,
            "total_ast_parsed": 0,
            "total_violations": 0,
            "scan_time": 0
        }
        
        # Define microservice specifications
        self.microservices = {
            "auth_service": MicroserviceSpec(
                name="auth_service",
                path=self.project_root / "auth_service",
                module_namespace="auth_core",
                forbidden_imports=[
                    "from netra_backend.app.",
                    "import app.",
                    "from app ",
                    "import app "
                ],
                forbidden_patterns=[
                    r"from\s+app\.",
                    r"import\s+app\.",
                    r"from\s+app\s",
                    r"import\s+app\s"
                ],
                required_independence_files=[
                    "main.py",
                    "requirements.txt", 
                    "auth_core/__init__.py"
                ],
                dockerfile_name="deployment/docker/auth.gcp.Dockerfile"
            ),
            "main_backend": MicroserviceSpec(
                name="main_backend",
                path=self.project_root / "app",
                module_namespace="app",
                forbidden_imports=[
                    "from auth_service.",
                    "import auth_service.",
                    "from auth_service ",
                    "import auth_service "
                ],
                forbidden_patterns=[
                    r"from\s+auth_service\.",
                    r"import\s+auth_service\.",
                    r"from\s+auth_service\s",
                    r"import\s+auth_service\s"
                ],
                required_independence_files=[
                    "main.py",
                    "core/__init__.py"
                ],
                dockerfile_name="deployment/docker/backend.gcp.Dockerfile"
            ),
            "frontend": MicroserviceSpec(
                name="frontend",
                path=self.project_root / "frontend",
                module_namespace="frontend",
                forbidden_imports=[
                    "from netra_backend./app/",
                    "from netra_backend./auth_service/",
                    "import('../app",
                    "import('../auth_service",
                    "require('../app",
                    "require('../auth_service"
                ],
                forbidden_patterns=[
                    r"from\s+\.\./app/",
                    r"from\s+\.\./auth_service/",
                    r"import\(['\"]\.\.\/app",
                    r"import\(['\"]\.\.\/auth_service",
                    r"require\(['\"]\.\.\/app",
                    r"require\(['\"]\.\.\/auth_service"
                ],
                required_independence_files=[
                    "package.json",
                    "next.config.ts"
                ],
                dockerfile_name="deployment/docker/frontend.gcp.Dockerfile"
            )
        }

    @pytest.mark.critical
    async def test_microservice_isolation_comprehensive(self) -> Dict[str, Any]:
        """
        BVJ: Enterprise | SOC2 Compliance | $100K+ MRR Impact
        Comprehensive microservice isolation validation.
        
        Validates:
        1. Zero cross-service imports
        2. Namespace isolation
        3. Independent startup capability
        4. Dockerfile independence
        """
        results = {
            "success": False,
            "isolation_tests": {},
            "total_violations": 0,
            "execution_time": 0,
            "scan_statistics": {}
        }
        
        start_time = time.time()
        
        try:
            # Phase 1: Cross-Service Import Validation (Critical)
            print("Phase 1: Validating cross-service import isolation...")
            import_results = await self._validate_cross_service_imports()
            results["isolation_tests"]["cross_service_imports"] = import_results
            results["total_violations"] += import_results.get("total_violations", 0)
            
            # Phase 2: Module Namespace Validation
            print("Phase 2: Validating module namespace isolation...")
            namespace_results = await self._validate_namespace_isolation()
            results["isolation_tests"]["namespace_isolation"] = namespace_results
            
            # Phase 3: Dockerfile Independence
            print("Phase 3: Validating Dockerfile independence...")
            dockerfile_results = await self._validate_dockerfile_independence()
            results["isolation_tests"]["dockerfile_independence"] = dockerfile_results
            
            # Phase 4: Service Startup Independence
            print("Phase 4: Validating service startup independence...")
            startup_results = await self._validate_startup_independence()
            results["isolation_tests"]["startup_independence"] = startup_results
            
            # Phase 5: Static File Structure Validation
            print("Phase 5: Validating file structure independence...")
            structure_results = await self._validate_file_structure_independence()
            results["isolation_tests"]["file_structure"] = structure_results
            
            # Overall success determination
            critical_tests_passed = all([
                import_results.get("passed", False),
                namespace_results.get("passed", False),
                dockerfile_results.get("passed", False)
            ])
            
            results["success"] = critical_tests_passed and results["total_violations"] == 0
            results["execution_time"] = round(time.time() - start_time, 2)
            results["scan_statistics"] = self.scan_stats
            
            # Enforce timeout
            if results["execution_time"] >= TEST_TIMEOUT:
                results["success"] = False
                results["timeout_exceeded"] = True
            
        except Exception as e:
            results["error"] = str(e)
            results["success"] = False
            results["execution_time"] = round(time.time() - start_time, 2)
            
        return results

    async def _validate_cross_service_imports(self) -> Dict[str, Any]:
        """Validate zero cross-service imports using AST parsing."""
        results = {
            "passed": False,
            "total_violations": 0,
            "service_results": {},
            "critical_violations": []
        }
        
        start_time = time.time()
        
        try:
            for service_name, service_spec in self.microservices.items():
                print(f"  Scanning {service_name} for forbidden imports...")
                service_result = await self._scan_service_imports_ast(service_spec)
                results["service_results"][service_name] = service_result
                
                violations = service_result.get("violations", [])
                results["total_violations"] += len(violations)
                
                # Track critical violations
                for violation in violations:
                    if self._is_critical_violation(violation, service_spec):
                        results["critical_violations"].append({
                            "service": service_name,
                            "violation": violation
                        })
            
            # Pass only if zero violations found
            results["passed"] = results["total_violations"] == 0
            results["scan_time"] = round(time.time() - start_time, 2)
            
        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False
            
        return results

    async def _scan_service_imports_ast(self, service_spec: MicroserviceSpec) -> Dict[str, Any]:
        """Scan service imports using AST parsing for accuracy."""
        result = {
            "violations": [],
            "files_scanned": 0,
            "imports_analyzed": 0
        }
        
        if not service_spec.path.exists():
            result["violations"].append({
                "type": "SERVICE_MISSING",
                "file": str(service_spec.path),
                "message": f"Service directory {service_spec.path} does not exist"
            })
            return result
        
        # Determine file patterns based on service
        if service_spec.name == "frontend":
            file_patterns = ["*.ts", "*.tsx", "*.js", "*.jsx"]
        else:
            file_patterns = ["*.py"]
        
        # Scan files with AST parsing
        for pattern in file_patterns:
            for file_path in service_spec.path.rglob(pattern):
                # Skip irrelevant directories
                if self._should_skip_file(file_path):
                    continue
                
                result["files_scanned"] += 1
                self.scan_stats["total_files_scanned"] += 1
                
                violations = await self._analyze_file_imports(file_path, service_spec)
                result["violations"].extend(violations)
                result["imports_analyzed"] += len(violations)
        
        return result

    async def _analyze_file_imports(self, file_path: Path, service_spec: MicroserviceSpec) -> List[Dict[str, Any]]:
        """Analyze file imports using AST parsing for Python or regex for JS/TS."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if file_path.suffix == '.py':
                violations = await self._analyze_python_imports_ast(file_path, content, service_spec)
            else:
                violations = await self._analyze_js_imports_regex(file_path, content, service_spec)
                
        except Exception as e:
            violations.append({
                "type": "FILE_READ_ERROR",
                "file": str(file_path.relative_to(self.project_root)),
                "message": f"Could not analyze file: {str(e)}"
            })
        
        return violations

    async def _analyze_python_imports_ast(self, file_path: Path, content: str, service_spec: MicroserviceSpec) -> List[Dict[str, Any]]:
        """Analyze Python imports using AST parsing."""
        violations = []
        
        try:
            tree = ast.parse(content)
            self.scan_stats["total_ast_parsed"] += 1
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_info = self._extract_import_info(node)
                    
                    if self._is_forbidden_import(import_info, service_spec):
                        # Allow exceptions for specific cases
                        if self._is_allowed_exception(file_path, import_info, service_spec):
                            continue
                            
                        violations.append({
                            "type": "FORBIDDEN_IMPORT",
                            "file": str(file_path.relative_to(self.project_root)),
                            "line": getattr(node, 'lineno', 0),
                            "import": import_info,
                            "violation_pattern": self._get_matching_pattern(import_info, service_spec)
                        })
                        
        except SyntaxError:
            # File might not be valid Python, skip AST parsing
            pass
        except Exception as e:
            violations.append({
                "type": "AST_PARSE_ERROR",
                "file": str(file_path.relative_to(self.project_root)),
                "message": f"AST parsing failed: {str(e)}"
            })
        
        return violations

    async def _analyze_js_imports_regex(self, file_path: Path, content: str, service_spec: MicroserviceSpec) -> List[Dict[str, Any]]:
        """Analyze JavaScript/TypeScript imports using regex patterns."""
        violations = []
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line_clean = line.strip()
            
            # Skip comments and empty lines
            if not line_clean or line_clean.startswith('//') or line_clean.startswith('/*'):
                continue
            
            # Check each forbidden pattern
            for pattern in service_spec.forbidden_patterns:
                if re.search(pattern, line_clean):
                    # Allow exceptions for test files
                    if self._is_allowed_exception(file_path, line_clean, service_spec):
                        continue
                        
                    violations.append({
                        "type": "FORBIDDEN_IMPORT",
                        "file": str(file_path.relative_to(self.project_root)),
                        "line": line_num,
                        "import": line_clean[:100],  # Truncate long lines
                        "violation_pattern": pattern
                    })
        
        return violations

    def _extract_import_info(self, node: ast.AST) -> str:
        """Extract import information from AST node."""
        if isinstance(node, ast.Import):
            return ", ".join([alias.name for alias in node.names])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ", ".join([alias.name for alias in node.names])
            return f"from {module} import {names}"
        return ""

    def _is_forbidden_import(self, import_info: str, service_spec: MicroserviceSpec) -> bool:
        """Check if import matches forbidden patterns."""
        for forbidden in service_spec.forbidden_imports:
            if forbidden in import_info:
                return True
        return False

    def _get_matching_pattern(self, import_info: str, service_spec: MicroserviceSpec) -> str:
        """Get the specific forbidden pattern that matched."""
        for forbidden in service_spec.forbidden_imports:
            if forbidden in import_info:
                return forbidden
        return "unknown"

    def _is_critical_violation(self, violation: Dict[str, Any], service_spec: MicroserviceSpec) -> bool:
        """Determine if violation is critical for business compliance."""
        violation_types = ["FORBIDDEN_IMPORT", "NAMESPACE_COLLISION"]
        return violation.get("type") in violation_types

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped during scanning."""
        skip_dirs = [
            "node_modules", ".git", "__pycache__", ".next", 
            "dist", "build", "coverage", ".pytest_cache"
        ]
        
        return any(skip_dir in str(file_path) for skip_dir in skip_dirs)

    def _is_allowed_exception(self, file_path: Path, import_line: str, service_spec: MicroserviceSpec) -> bool:
        """Check if import violation is an allowed exception."""
        file_path_str = str(file_path)
        
        # Allow test files to import for testing purposes
        test_indicators = [
            "test_", "_test.py", "conftest.py", "test_helpers",
            "/tests/", "\\tests\\", "__tests__", ".test.", ".spec."
        ]
        
        if any(indicator in file_path_str for indicator in test_indicators):
            return True
        
        # Allow specific documented sync imports
        if "main_db_sync.py" in file_path_str and "from netra_backend.app.db.models_postgres" in import_line:
            return True
        
        # Allow mock files
        if any(word in file_path.name.lower() for word in ["mock", "fixture", "stub"]):
            return True
            
        return False

    async def _validate_namespace_isolation(self) -> Dict[str, Any]:
        """Validate unique module namespaces."""
        results = {
            "passed": False,
            "namespace_violations": [],
            "namespace_analysis": {}
        }
        
        try:
            for service_name, service_spec in self.microservices.items():
                namespace_info = {
                    "expected_namespace": service_spec.module_namespace,
                    "has_correct_namespace": False,
                    "namespace_violations": []
                }
                
                # Check if service has correct namespace directory
                namespace_path = service_spec.path / service_spec.module_namespace
                if namespace_path.exists() and namespace_path.is_dir():
                    namespace_info["has_correct_namespace"] = True
                
                # Check for forbidden 'app' directory in auth_service
                if service_name == "auth_service":
                    forbidden_app_path = service_spec.path / "app"
                    if forbidden_app_path.exists():
                        namespace_info["namespace_violations"].append({
                            "type": "FORBIDDEN_APP_DIRECTORY",
                            "path": str(forbidden_app_path.relative_to(self.project_root)),
                            "message": "Auth service must not have 'app' directory"
                        })
                
                results["namespace_analysis"][service_name] = namespace_info
            
            # Collect all violations
            all_violations = []
            all_have_correct_namespace = True
            
            for service_name, analysis in results["namespace_analysis"].items():
                all_violations.extend(analysis.get("namespace_violations", []))
                if not analysis.get("has_correct_namespace", False):
                    all_have_correct_namespace = False
                    all_violations.append({
                        "type": "MISSING_NAMESPACE",
                        "service": service_name,
                        "message": f"Service {service_name} missing correct namespace directory"
                    })
            
            results["namespace_violations"] = all_violations
            results["passed"] = len(all_violations) == 0 and all_have_correct_namespace
            
        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False
            
        return results

    async def _validate_dockerfile_independence(self) -> Dict[str, Any]:
        """Validate Dockerfile independence for each service."""
        results = {
            "passed": False,
            "dockerfile_analysis": {},
            "independence_score": 0
        }
        
        try:
            services_with_dockerfiles = 0
            independent_dockerfiles = 0
            
            for service_name, service_spec in self.microservices.items():
                dockerfile_info = {
                    "has_dockerfile": False,
                    "dockerfile_path": None,
                    "independence_violations": [],
                    "dockerfile_independent": False
                }
                
                # Check for service-specific Dockerfile
                if service_spec.dockerfile_name:
                    dockerfile_path = self.project_root / service_spec.dockerfile_name
                    if dockerfile_path.exists():
                        dockerfile_info["has_dockerfile"] = True
                        dockerfile_info["dockerfile_path"] = str(dockerfile_path.relative_to(self.project_root))
                        
                        # Analyze Dockerfile for independence
                        independence_analysis = await self._analyze_dockerfile_independence(
                            dockerfile_path, service_spec
                        )
                        dockerfile_info.update(independence_analysis)
                        
                        if dockerfile_info["dockerfile_independent"]:
                            independent_dockerfiles += 1
                        services_with_dockerfiles += 1
                
                results["dockerfile_analysis"][service_name] = dockerfile_info
            
            # Calculate independence score
            if services_with_dockerfiles > 0:
                results["independence_score"] = (independent_dockerfiles / services_with_dockerfiles) * 100
                results["passed"] = results["independence_score"] >= 80  # 80% threshold
            else:
                results["passed"] = False
                results["independence_score"] = 0
                
        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False
            
        return results

    async def _analyze_dockerfile_independence(self, dockerfile_path: Path, service_spec: MicroserviceSpec) -> Dict[str, Any]:
        """Analyze Dockerfile for independence violations."""
        analysis = {
            "dockerfile_independent": False,
            "independence_violations": [],
            "independence_features": []
        }
        
        try:
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Check for independence indicators
            service_specific_copy = False
            multi_stage_build = False
            service_only_dependencies = True
            
            for line in lines:
                line_clean = line.strip().upper()
                
                # Check for service-specific COPY commands
                if line_clean.startswith('COPY') and service_spec.name in line.lower():
                    service_specific_copy = True
                    analysis["independence_features"].append("Service-specific COPY found")
                
                # Check for multi-stage build
                if 'FROM' in line_clean and 'AS' in line_clean:
                    multi_stage_build = True
                    analysis["independence_features"].append("Multi-stage build detected")
                
                # Check for cross-service dependencies
                if line_clean.startswith('COPY'):
                    for other_service in self.microservices.keys():
                        if other_service != service_spec.name and other_service in line.lower():
                            service_only_dependencies = False
                            analysis["independence_violations"].append({
                                "type": "CROSS_SERVICE_DEPENDENCY",
                                "line": line.strip(),
                                "message": f"Dockerfile copies from other service: {other_service}"
                            })
            
            # Determine overall independence
            independence_checks = [service_specific_copy, service_only_dependencies]
            analysis["dockerfile_independent"] = all(independence_checks)
            
            if multi_stage_build:
                analysis["independence_features"].append("Optimized multi-stage build")
                
        except Exception as e:
            analysis["independence_violations"].append({
                "type": "DOCKERFILE_READ_ERROR",
                "message": f"Could not read Dockerfile: {str(e)}"
            })
        
        return analysis

    async def _validate_startup_independence(self) -> Dict[str, Any]:
        """Validate services can start independently."""
        results = {
            "passed": False,
            "startup_tests": {},
            "independence_summary": {}
        }
        
        try:
            independent_services = 0
            total_services = 0
            
            for service_name, service_spec in self.microservices.items():
                startup_test = await self._test_service_startup_independence(service_spec)
                results["startup_tests"][service_name] = startup_test
                
                total_services += 1
                if startup_test.get("can_start_independently", False):
                    independent_services += 1
            
            # Calculate independence metrics
            independence_ratio = independent_services / total_services if total_services > 0 else 0
            results["independence_summary"] = {
                "independent_services": independent_services,
                "total_services": total_services,
                "independence_ratio": independence_ratio,
                "independence_percentage": round(independence_ratio * 100, 2)
            }
            
            # Pass if at least 66% of services can start independently
            results["passed"] = independence_ratio >= 0.66
            
        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False
            
        return results

    async def _test_service_startup_independence(self, service_spec: MicroserviceSpec) -> Dict[str, Any]:
        """Test if service can start independently by checking dependencies."""
        test_result = {
            "can_start_independently": False,
            "independence_factors": [],
            "dependency_issues": []
        }
        
        try:
            # Check if required files exist
            all_required_files_exist = True
            for required_file in service_spec.required_independence_files:
                file_path = service_spec.path / required_file
                if not file_path.exists():
                    all_required_files_exist = False
                    test_result["dependency_issues"].append({
                        "type": "MISSING_REQUIRED_FILE",
                        "file": required_file,
                        "message": f"Required file {required_file} not found"
                    })
                else:
                    test_result["independence_factors"].append(f"Required file {required_file} exists")
            
            # Check for dependency files
            has_dependency_file = False
            if service_spec.name == "frontend":
                dependency_files = ["package.json"]
            else:
                dependency_files = ["requirements.txt"]
            
            for dep_file in dependency_files:
                dep_path = service_spec.path / dep_file
                if dep_path.exists():
                    has_dependency_file = True
                    test_result["independence_factors"].append(f"Dependency file {dep_file} exists")
                    break
            
            if not has_dependency_file:
                test_result["dependency_issues"].append({
                    "type": "MISSING_DEPENDENCY_FILE",
                    "message": "No dependency management file found"
                })
            
            # Determine independence
            test_result["can_start_independently"] = (
                all_required_files_exist and 
                has_dependency_file and 
                len(test_result["dependency_issues"]) == 0
            )
            
        except Exception as e:
            test_result["dependency_issues"].append({
                "type": "STARTUP_TEST_ERROR",
                "message": f"Error testing startup independence: {str(e)}"
            })
        
        return test_result

    async def _validate_file_structure_independence(self) -> Dict[str, Any]:
        """Validate file structure shows proper service separation."""
        results = {
            "passed": False,
            "structure_analysis": {},
            "separation_score": 0
        }
        
        try:
            total_separation_score = 0
            services_analyzed = 0
            
            for service_name, service_spec in self.microservices.items():
                structure_info = {
                    "has_own_directory": service_spec.path.exists(),
                    "directory_isolation": True,
                    "structure_violations": []
                }
                
                if structure_info["has_own_directory"]:
                    # Check for proper isolation (no cross-references in file structure)
                    for other_service_name, other_service_spec in self.microservices.items():
                        if other_service_name != service_name:
                            # Check if this service has directories named after other services
                            other_service_dir = service_spec.path / other_service_name
                            if other_service_dir.exists():
                                structure_info["structure_violations"].append({
                                    "type": "CROSS_SERVICE_DIRECTORY",
                                    "path": str(other_service_dir.relative_to(self.project_root)),
                                    "message": f"Service contains directory named after other service: {other_service_name}"
                                })
                                structure_info["directory_isolation"] = False
                
                # Calculate service separation score
                service_score = 100
                if not structure_info["has_own_directory"]:
                    service_score -= 50
                service_score -= len(structure_info["structure_violations"]) * 25
                service_score = max(0, service_score)
                
                structure_info["separation_score"] = service_score
                total_separation_score += service_score
                services_analyzed += 1
                
                results["structure_analysis"][service_name] = structure_info
            
            # Calculate overall separation score
            if services_analyzed > 0:
                results["separation_score"] = total_separation_score / services_analyzed
                results["passed"] = results["separation_score"] >= 75  # 75% threshold
            else:
                results["passed"] = False
                
        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False
            
        return results


# Pytest test implementations

@pytest.mark.critical
@pytest.mark.asyncio
async def test_microservice_isolation_comprehensive():
    """
    BVJ: Enterprise | SOC2 Compliance | $100K+ MRR Impact
    Comprehensive microservice isolation validation preventing cascading failures.
    """
    validator = MicroserviceIsolationValidator()
    
    results = await validator.test_microservice_isolation_comprehensive()
    
    # Assert critical success criteria
    assert results["success"], f"Microservice isolation validation failed: {results.get('error', 'Unknown error')}"
    
    # Assert zero violations (critical for compliance)
    assert results["total_violations"] == 0, (
        f"Found {results['total_violations']} isolation violations. "
        f"Critical for SOC2 compliance and enterprise scalability."
    )
    
    # Assert performance requirement
    assert results["execution_time"] < TEST_TIMEOUT, (
        f"Test exceeded time limit: {results['execution_time']}s > {TEST_TIMEOUT}s"
    )
    
    # Validate critical isolation tests passed
    isolation_tests = results["isolation_tests"]
    
    # Cross-service imports must be zero
    import_test = isolation_tests.get("cross_service_imports", {})
    assert import_test.get("passed", False), (
        f"Cross-service import validation failed: {import_test.get('total_violations', 0)} violations found"
    )
    
    # Namespace isolation must pass
    namespace_test = isolation_tests.get("namespace_isolation", {})
    assert namespace_test.get("passed", False), (
        f"Namespace isolation failed: {len(namespace_test.get('namespace_violations', []))} violations"
    )
    
    # Dockerfile independence must pass
    dockerfile_test = isolation_tests.get("dockerfile_independence", {})
    assert dockerfile_test.get("passed", False), (
        f"Dockerfile independence failed: {dockerfile_test.get('independence_score', 0)}% score"
    )
    
    # Print success summary
    print(f"[SUCCESS] Microservice Isolation Validation")
    print(f"   Execution time: {results['execution_time']}s")
    print(f"   Files scanned: {results['scan_statistics']['total_files_scanned']}")
    print(f"   AST parsed: {results['scan_statistics']['total_ast_parsed']}")
    print(f"   Total violations: {results['total_violations']}")
    
    for test_name, test_result in isolation_tests.items():
        status = "PASS" if test_result.get("passed", False) else "FAIL"
        print(f"   [{status}] {test_name}")


@pytest.mark.critical
@pytest.mark.asyncio
async def test_zero_cross_service_imports():
    """Test that services have absolutely zero cross-service imports."""
    validator = MicroserviceIsolationValidator()
    
    import_results = await validator._validate_cross_service_imports()
    
    total_violations = import_results.get("total_violations", 0)
    assert total_violations == 0, (
        f"Found {total_violations} cross-service import violations:\n" +
        "\n".join([
            f"  {service}: {len(result.get('violations', []))} violations"
            for service, result in import_results.get("service_results", {}).items()
            if result.get("violations", [])
        ])
    )
    
    # Validate all services were scanned
    service_results = import_results.get("service_results", {})
    assert len(service_results) == 3, f"Expected 3 services, found {len(service_results)}"
    
    print(f"[PASS] Zero Cross-Service Imports: {sum(r.get('files_scanned', 0) for r in service_results.values())} files scanned")


@pytest.mark.critical
@pytest.mark.asyncio
async def test_auth_service_no_app_imports():
    """Critical test: Auth service must have zero imports from app module."""
    validator = MicroserviceIsolationValidator()
    
    auth_spec = validator.microservices["auth_service"]
    auth_result = await validator._scan_service_imports_ast(auth_spec)
    
    app_violations = [
        v for v in auth_result.get("violations", [])
        if any(pattern in v.get("import", "") for pattern in ["from netra_backend.app.", "import app."])
    ]
    
    assert len(app_violations) == 0, (
        f"Auth service has {len(app_violations)} forbidden app imports:\n" +
        "\n".join([f"  {v['file']}:{v.get('line', 0)} - {v.get('import', '')}" for v in app_violations])
    )
    
    print(f"[PASS] Auth Service Independence: {auth_result['files_scanned']} files scanned, 0 app imports")


@pytest.mark.critical
@pytest.mark.asyncio
async def test_backend_no_auth_service_imports():
    """Critical test: Backend must have zero imports from auth_service."""
    validator = MicroserviceIsolationValidator()
    
    backend_spec = validator.microservices["main_backend"]
    backend_result = await validator._scan_service_imports_ast(backend_spec)
    
    auth_violations = [
        v for v in backend_result.get("violations", [])
        if any(pattern in v.get("import", "") for pattern in ["from auth_service.", "import auth_service."])
    ]
    
    assert len(auth_violations) == 0, (
        f"Backend has {len(auth_violations)} forbidden auth_service imports:\n" +
        "\n".join([f"  {v['file']}:{v.get('line', 0)} - {v.get('import', '')}" for v in auth_violations])
    )
    
    print(f"[PASS] Backend Independence: {backend_result['files_scanned']} files scanned, 0 auth_service imports")


@pytest.mark.asyncio
async def test_namespace_isolation():
    """Test unique module namespaces prevent collisions."""
    validator = MicroserviceIsolationValidator()
    
    namespace_results = await validator._validate_namespace_isolation()
    
    violations = namespace_results.get("namespace_violations", [])
    assert len(violations) == 0, (
        f"Found {len(violations)} namespace violations:\n" +
        "\n".join([f"  {v.get('type', 'UNKNOWN')}: {v.get('message', '')}" for v in violations])
    )
    
    # Verify auth_service has auth_core namespace (not app)
    auth_analysis = namespace_results.get("namespace_analysis", {}).get("auth_service", {})
    assert auth_analysis.get("has_correct_namespace", False), (
        "Auth service must have auth_core/ namespace directory"
    )
    
    print(f"[PASS] Namespace Isolation: All services have unique namespaces")


@pytest.mark.asyncio
async def test_dockerfile_independence():
    """Test Dockerfile independence for deployments."""
    validator = MicroserviceIsolationValidator()
    
    dockerfile_results = await validator._validate_dockerfile_independence()
    
    independence_score = dockerfile_results.get("independence_score", 0)
    assert independence_score >= 80, (
        f"Dockerfile independence score too low: {independence_score}% (minimum 80%)"
    )
    
    # Check for critical violations
    for service, analysis in dockerfile_results.get("dockerfile_analysis", {}).items():
        violations = analysis.get("independence_violations", [])
        cross_service_violations = [
            v for v in violations if v.get("type") == "CROSS_SERVICE_DEPENDENCY"
        ]
        assert len(cross_service_violations) == 0, (
            f"Service {service} has cross-service dependencies in Dockerfile"
        )
    
    print(f"[PASS] Dockerfile Independence: {independence_score}% independence score")


@pytest.mark.asyncio
async def test_startup_independence():
    """Test services can start independently."""
    validator = MicroserviceIsolationValidator()
    
    startup_results = await validator._validate_startup_independence()
    
    independence_ratio = startup_results.get("independence_summary", {}).get("independence_ratio", 0)
    assert independence_ratio >= 0.66, (
        f"Startup independence ratio too low: {independence_ratio:.2%} (minimum 66%)"
    )
    
    # Ensure at least 2 services can start independently
    independent_count = startup_results.get("independence_summary", {}).get("independent_services", 0)
    assert independent_count >= 2, (
        f"Only {independent_count} services can start independently (minimum 2)"
    )
    
    print(f"[PASS] Startup Independence: {independent_count}/3 services can start independently")


if __name__ == "__main__":
    # Run comprehensive validation directly
    async def run_comprehensive_test():
        validator = MicroserviceIsolationValidator()
        results = await validator.test_microservice_isolation_comprehensive()
        
        print("\n" + "="*80)
        print("MICROSERVICE ISOLATION VALIDATION RESULTS")
        print("="*80)
        
        success_indicator = "PASS" if results['success'] else "FAIL"
        print(f"Overall Success: {success_indicator}")
        print(f"Execution Time: {results['execution_time']}s")
        print(f"Total Violations: {results['total_violations']}")
        print(f"Files Scanned: {results['scan_statistics']['total_files_scanned']}")
        
        if results.get("error"):
            print(f"\nError: {results['error']}")
        
        print("\nIsolation Test Results:")
        for test_name, test_result in results["isolation_tests"].items():
            status = "PASS" if test_result.get("passed", False) else "FAIL"
            print(f"  [{status}] {test_name}")
            
            if test_name == "cross_service_imports":
                print(f"    Violations: {test_result.get('total_violations', 0)}")
            elif test_name == "dockerfile_independence":
                print(f"    Independence Score: {test_result.get('independence_score', 0)}%")
    
    asyncio.run(run_comprehensive_test())
