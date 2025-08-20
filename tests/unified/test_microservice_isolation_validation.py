"""
Microservice Isolation Validation Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability  
- Value Impact: Protects system architecture integrity by enforcing microservice independence
- Strategic/Revenue Impact: Prevents cascading failures and maintains system scalability

This test suite validates that all microservices maintain 100% independence per 
SPEC/independent_services.xml. Uses static analysis to enforce architectural boundaries.

Test Categories:
1. Import Isolation - No cross-service imports
2. Service Independence - Services can start independently  
3. Code Boundaries - No shared code violations
4. Configuration Isolation - Separate configs per service
5. Communication Protocols - Only API-based inter-service communication

Performance: Static analysis only, completes in <5 seconds
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import pytest


class MicroserviceIsolationValidator:
    """Validates microservice independence using AST parsing and static analysis"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.violations: Dict[str, List[str]] = {}
        
        # Define microservice directories (excluding frontend per spec)
        self.backend_services = {
            "main_backend": self.project_root / "app",
            "auth_service": self.project_root / "auth_service"
        }
        
        # Frontend is exempt from isolation requirements per spec
        self.excluded_services = {
            "frontend": self.project_root / "frontend"
        }
    
    def get_python_files(self, service_path: Path) -> List[Path]:
        """Get all Python files in a service directory"""
        python_files = []
        if service_path.exists():
            for file_path in service_path.rglob("*.py"):
                # Skip test files and __pycache__
                if not any(skip in str(file_path) for skip in ["test_", "__pycache__", ".pyc"]):
                    python_files.append(file_path)
        return python_files
    
    def extract_imports_from_file(self, file_path: Path) -> List[str]:
        """Extract all import statements from a Python file using AST"""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except (SyntaxError, UnicodeDecodeError, OSError):
            # Skip files that can't be parsed
            pass
        return imports
    
    def validate_import_isolation(self) -> Dict[str, Any]:
        """Validate that services don't import from each other"""
        violations = []
        
        for service_name, service_path in self.backend_services.items():
            python_files = self.get_python_files(service_path)
            
            for file_path in python_files:
                imports = self.extract_imports_from_file(file_path)
                relative_path = file_path.relative_to(self.project_root)
                
                for import_stmt in imports:
                    # Check for forbidden cross-service imports
                    if service_name == "auth_service":
                        # Auth service cannot import from main app
                        if import_stmt.startswith("app."):
                            violations.append({
                                "service": service_name,
                                "file": str(relative_path),
                                "violation": f"Import from main app: {import_stmt}",
                                "rule": "MS-ARC-002"
                            })
                    
                    elif service_name == "main_backend":
                        # Main backend cannot import from auth_service
                        if import_stmt.startswith("auth_service."):
                            violations.append({
                                "service": service_name,
                                "file": str(relative_path),
                                "violation": f"Import from auth_service: {import_stmt}",
                                "rule": "MS-ARC-002"
                            })
        
        return {
            "violations": violations,
            "total_violations": len(violations),
            "isolated": len(violations) == 0
        }
    
    def validate_service_independence(self) -> Dict[str, Any]:
        """Validate service directory structure independence"""
        violations = []
        
        for service_name, service_path in self.backend_services.items():
            if not service_path.exists():
                violations.append(f"{service_name}: Service directory does not exist")
                continue
            
            # Check for forbidden 'app' directory in auth_service (MS-ARC-001)
            if service_name == "auth_service":
                app_dir = service_path / "app"
                if app_dir.exists():
                    violations.append(f"{service_name}: Contains forbidden 'app' directory (MS-ARC-001)")
            
            # Verify each service has its own main.py
            main_file = service_path / "main.py"
            if not main_file.exists():
                violations.append(f"{service_name}: Missing main.py entry point")
        
        return {
            "violations": violations,
            "total_violations": len(violations),
            "independent": len(violations) == 0
        }
    
    def validate_code_boundaries(self) -> Dict[str, Any]:
        """Validate no shared code violations between services"""
        violations = []
        
        # Check for duplicate module names that could cause namespace conflicts
        module_map: Dict[str, List[str]] = {}
        
        for service_name, service_path in self.backend_services.items():
            python_files = self.get_python_files(service_path)
            
            for file_path in python_files:
                # Get module path relative to service root
                relative_to_service = file_path.relative_to(service_path)
                module_name = str(relative_to_service).replace(os.sep, '.').replace('.py', '')
                
                if module_name not in module_map:
                    module_map[module_name] = []
                module_map[module_name].append(service_name)
        
        # Find modules present in multiple services (potential conflicts)
        for module_name, services in module_map.items():
            if len(services) > 1 and module_name != "__init__":
                violations.append(f"Module namespace conflict: {module_name} in {services}")
        
        return {
            "violations": violations,
            "total_violations": len(violations),
            "boundaries_clean": len(violations) == 0
        }
    
    def validate_configuration_isolation(self) -> Dict[str, Any]:
        """Validate separate configuration files for each service"""
        violations = []
        
        for service_name, service_path in self.backend_services.items():
            # Check for independent requirements.txt
            requirements_file = service_path / "requirements.txt"
            if not requirements_file.exists():
                violations.append(f"{service_name}: Missing independent requirements.txt")
            
            # Check for independent Dockerfile
            dockerfile = service_path / "Dockerfile"
            if not dockerfile.exists():
                violations.append(f"{service_name}: Missing independent Dockerfile")
            
            # Check for service-specific config
            config_files = [
                service_path / "config.py",
                service_path / "config.yaml",
                service_path / f"{service_name.split('_')[0]}_core" / "config.py"
            ]
            
            has_config = any(config_file.exists() for config_file in config_files)
            if not has_config:
                violations.append(f"{service_name}: Missing service-specific configuration")
        
        return {
            "violations": violations,
            "total_violations": len(violations),
            "isolated_config": len(violations) == 0
        }
    
    def validate_communication_protocols(self) -> Dict[str, Any]:
        """Validate only API-based inter-service communication"""
        violations = []
        
        # Check for direct database access patterns across services
        forbidden_patterns = [
            # Direct database imports across services
            r'from\s+app\.db\.',
            r'import\s+.*app\.db\.',
            # Direct service calls
            r'from\s+auth_service\..*\.services\.',
            r'from\s+app\.services\.',
        ]
        
        for service_name, service_path in self.backend_services.items():
            python_files = self.get_python_files(service_path)
            
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    relative_path = file_path.relative_to(self.project_root)
                    
                    for pattern in forbidden_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            # Skip if it's within the same service
                            if service_name == "main_backend" and "app." in match:
                                continue
                            if service_name == "auth_service" and "auth_service." in match:
                                continue
                            
                            violations.append({
                                "service": service_name,
                                "file": str(relative_path),
                                "violation": f"Direct cross-service access: {match}",
                                "pattern": pattern
                            })
                
                except (UnicodeDecodeError, OSError):
                    pass
        
        return {
            "violations": violations,
            "total_violations": len(violations),
            "api_only_communication": len(violations) == 0
        }
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run all microservice isolation validations"""
        return {
            "import_isolation": self.validate_import_isolation(),
            "service_independence": self.validate_service_independence(),
            "code_boundaries": self.validate_code_boundaries(),
            "configuration_isolation": self.validate_configuration_isolation(),
            "communication_protocols": self.validate_communication_protocols()
        }


class TestMicroserviceIsolationValidation:
    """Test suite for microservice isolation validation"""
    
    @pytest.fixture(scope="class")
    def validator(self):
        """Create microservice isolation validator"""
        return MicroserviceIsolationValidator()
    
    @pytest.fixture(scope="class")
    def validation_results(self, validator):
        """Run full microservice isolation validation"""
        return validator.run_full_validation()
    
    def test_import_isolation_enforced(self, validation_results):
        """Test that services have no forbidden cross-service imports"""
        import_results = validation_results["import_isolation"]
        
        if not import_results["isolated"]:
            violations = import_results["violations"]
            failure_msg = f"\nIMPORT ISOLATION VIOLATIONS: {len(violations)} violations found\n"
            failure_msg += "=" * 80 + "\n"
            
            for violation in violations:
                failure_msg += f"❌ {violation['service']}\n"
                failure_msg += f"   File: {violation['file']}\n"
                failure_msg += f"   Violation: {violation['violation']}\n"
                failure_msg += f"   Rule: {violation['rule']}\n"
                failure_msg += "-" * 60 + "\n"
            
            failure_msg += "\n🔥 CRITICAL: Services must be 100% import-isolated per SPEC/independent_services.xml"
            pytest.fail(failure_msg)
    
    def test_service_independence_maintained(self, validation_results):
        """Test that services maintain structural independence"""
        independence_results = validation_results["service_independence"]
        
        if not independence_results["independent"]:
            violations = independence_results["violations"]
            failure_msg = f"\nSERVICE INDEPENDENCE VIOLATIONS:\n"
            
            for violation in violations:
                failure_msg += f"  - {violation}\n"
            
            failure_msg += "\nServices must maintain independent directory structures."
            pytest.fail(failure_msg)
    
    def test_code_boundaries_clean(self, validation_results):
        """Test that code boundaries are properly enforced"""
        boundary_results = validation_results["code_boundaries"]
        
        if not boundary_results["boundaries_clean"]:
            violations = boundary_results["violations"]
            failure_msg = f"\nCODE BOUNDARY VIOLATIONS:\n"
            
            for violation in violations:
                failure_msg += f"  - {violation}\n"
            
            failure_msg += "\nServices must not share module namespaces."
            pytest.fail(failure_msg)
    
    def test_configuration_isolation_complete(self, validation_results):
        """Test that each service has isolated configuration"""
        config_results = validation_results["configuration_isolation"]
        
        if not config_results["isolated_config"]:
            violations = config_results["violations"]
            failure_msg = f"\nCONFIGURATION ISOLATION VIOLATIONS:\n"
            
            for violation in violations:
                failure_msg += f"  - {violation}\n"
            
            failure_msg += "\nEach service must have independent configuration files."
            pytest.fail(failure_msg)
    
    def test_api_only_communication(self, validation_results):
        """Test that inter-service communication uses only APIs"""
        comm_results = validation_results["communication_protocols"]
        
        if not comm_results["api_only_communication"]:
            violations = comm_results["violations"]
            failure_msg = f"\nCOMMUNICATION PROTOCOL VIOLATIONS:\n"
            
            for violation in violations:
                failure_msg += f"❌ {violation['service']}\n"
                failure_msg += f"   File: {violation['file']}\n"
                failure_msg += f"   Violation: {violation['violation']}\n"
                failure_msg += "-" * 60 + "\n"
            
            failure_msg += "\nServices must communicate only via APIs, not direct code calls."
            pytest.fail(failure_msg)
    
    def test_backend_services_only_scope(self, validator):
        """Test that validation correctly scopes to backend services only"""
        # Verify frontend is excluded per SPEC/independent_services.xml
        assert "frontend" not in validator.backend_services
        assert "frontend" in validator.excluded_services
        
        # Verify correct backend services are included
        expected_services = {"main_backend", "auth_service"}
        assert set(validator.backend_services.keys()) == expected_services
    
    def test_comprehensive_isolation_report(self, validation_results):
        """Generate comprehensive isolation validation report"""
        print("\n" + "=" * 25 + " MICROSERVICE ISOLATION REPORT " + "=" * 25)
        
        categories = [
            ("Import Isolation", validation_results["import_isolation"]),
            ("Service Independence", validation_results["service_independence"]),
            ("Code Boundaries", validation_results["code_boundaries"]),
            ("Configuration Isolation", validation_results["configuration_isolation"]),
            ("Communication Protocols", validation_results["communication_protocols"])
        ]
        
        total_violations = 0
        all_passed = True
        
        for category_name, results in categories:
            violations = results["total_violations"]
            total_violations += violations
            status = "✅ PASS" if violations == 0 else f"❌ FAIL ({violations} violations)"
            
            if violations > 0:
                all_passed = False
            
            print(f"{category_name:25}: {status}")
        
        print("-" * 80)
        print(f"Total Violations: {total_violations}")
        
        if all_passed:
            print("✅ ALL MICROSERVICE ISOLATION TESTS PASSED")
            print("🏗️  Architecture integrity maintained - services are 100% independent")
        else:
            print("❌ MICROSERVICE ISOLATION VIOLATIONS DETECTED")
            print("🚨 Fix isolation violations to maintain system stability")
        
        print("=" * 80)
        
        # Always pass - this is for reporting only
        assert True, "Microservice isolation validation report generated"


# Standalone execution support
def run_microservice_isolation_validation():
    """Run microservice isolation validation directly"""
    validator = MicroserviceIsolationValidator()
    results = validator.run_full_validation()
    
    total_violations = sum(
        category["total_violations"] 
        for category in results.values()
    )
    
    print(f"\nMicroservice Isolation Validation: {total_violations} total violations")
    return total_violations == 0


if __name__ == "__main__":
    success = run_microservice_isolation_validation()
    sys.exit(0 if success else 1)