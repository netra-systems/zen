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
from typing import Any, Dict, List, Optional

import pytest


class MicroserviceIsolationValidator:
    """Validates microservice independence using AST parsing and static analysis"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.backend_services = {
            "main_backend": self.project_root / "app",
            "auth_service": self.project_root / "auth_service"
        }
        self.excluded_services = {"frontend": self.project_root / "frontend"}
    
    def get_python_files(self, service_path: Path) -> List[Path]:
        """Get all Python files in a service directory"""
        if not service_path.exists():
            return []
        return [f for f in service_path.rglob("*.py") 
                if not any(skip in str(f) for skip in ["test_", "__pycache__", ".pyc"])]
    
    def extract_imports_from_file(self, file_path: Path) -> List[str]:
        """Extract all import statements from a Python file using AST"""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
        except (SyntaxError, UnicodeDecodeError, OSError):
            pass
        return imports
    
    def validate_import_isolation(self) -> Dict[str, Any]:
        """Validate that services don't import from each other"""
        violations = []
        forbidden_imports = {
            "auth_service": "app.",
            "main_backend": "auth_service."
        }
        
        for service_name, service_path in self.backend_services.items():
            for file_path in self.get_python_files(service_path):
                imports = self.extract_imports_from_file(file_path)
                forbidden_prefix = forbidden_imports.get(service_name)
                
                if forbidden_prefix:
                    for import_stmt in imports:
                        if import_stmt.startswith(forbidden_prefix):
                            violations.append({
                                "service": service_name,
                                "file": str(file_path.relative_to(self.project_root)),
                                "violation": f"Forbidden import: {import_stmt}",
                                "rule": "MS-ARC-002"
                            })
        
        return {"violations": violations, "total_violations": len(violations), "isolated": len(violations) == 0}
    
    def validate_service_independence(self) -> Dict[str, Any]:
        """Validate service directory structure independence"""
        violations = []
        
        for service_name, service_path in self.backend_services.items():
            if not service_path.exists():
                violations.append(f"{service_name}: Service directory does not exist")
                continue
            
            if service_name == "auth_service" and (service_path / "app").exists():
                violations.append(f"{service_name}: Contains forbidden 'app' directory (MS-ARC-001)")
            
            if not (service_path / "main.py").exists():
                violations.append(f"{service_name}: Missing main.py entry point")
        
        return {"violations": violations, "total_violations": len(violations), "independent": len(violations) == 0}
    
    def validate_code_boundaries(self) -> Dict[str, Any]:
        """Validate no shared code violations between services"""
        violations = []
        module_map: Dict[str, List[str]] = {}
        
        for service_name, service_path in self.backend_services.items():
            for file_path in self.get_python_files(service_path):
                rel_path = file_path.relative_to(service_path)
                module_name = str(rel_path).replace(os.sep, '.').replace('.py', '')
                module_map.setdefault(module_name, []).append(service_name)
        
        for module_name, services in module_map.items():
            if len(services) > 1 and module_name != "__init__":
                violations.append(f"Module namespace conflict: {module_name} in {services}")
        
        return {"violations": violations, "total_violations": len(violations), "boundaries_clean": len(violations) == 0}
    
    def validate_configuration_isolation(self) -> Dict[str, Any]:
        """Validate separate configuration files for each service"""
        violations = []
        
        for service_name, service_path in self.backend_services.items():
            required_files = ["requirements.txt", "Dockerfile"]
            for file_name in required_files:
                if not (service_path / file_name).exists():
                    violations.append(f"{service_name}: Missing {file_name}")
            
            config_files = [
                service_path / "config.py",
                service_path / "config.yaml",
                service_path / f"{service_name.split('_')[0]}_core" / "config.py"
            ]
            
            if not any(f.exists() for f in config_files):
                violations.append(f"{service_name}: Missing service-specific configuration")
        
        return {"violations": violations, "total_violations": len(violations), "isolated_config": len(violations) == 0}
    
    def validate_communication_protocols(self) -> Dict[str, Any]:
        """Validate only API-based inter-service communication"""
        violations = []
        forbidden_patterns = [r'from\s+app\.db\.', r'from\s+auth_service\..*\.services\.', r'from\s+app\.services\.']
        
        for service_name, service_path in self.backend_services.items():
            for file_path in self.get_python_files(service_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for pattern in forbidden_patterns:
                        for match in re.findall(pattern, content):
                            # Skip same-service access
                            if (service_name == "main_backend" and "app." in match) or \
                               (service_name == "auth_service" and "auth_service." in match):
                                continue
                            
                            violations.append({
                                "service": service_name,
                                "file": str(file_path.relative_to(self.project_root)),
                                "violation": f"Direct cross-service access: {match}"
                            })
                except (UnicodeDecodeError, OSError):
                    pass
        
        return {"violations": violations, "total_violations": len(violations), "api_only_communication": len(violations) == 0}
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run all microservice isolation validations"""
        return {
            "import_isolation": self.validate_import_isolation(),
            "service_independence": self.validate_service_independence(),
            "code_boundaries": self.validate_code_boundaries(),
            "configuration_isolation": self.validate_configuration_isolation(),
            "communication_protocols": self.validate_communication_protocols()
        }


@pytest.mark.e2e
class TestMicroserviceIsolationValidation:
    """Test suite for microservice isolation validation"""
    
    @pytest.fixture(scope="class")
    def validator(self):
        return MicroserviceIsolationValidator()
    
    @pytest.fixture(scope="class")
    def validation_results(self, validator):
        return validator.run_full_validation()
    
    @pytest.mark.e2e
    def test_import_isolation_enforced(self, validation_results):
        """Test that services have no forbidden cross-service imports"""
        results = validation_results["import_isolation"]
        if not results["isolated"]:
            violations = "\n".join([f"FAIL {v['service']}: {v['violation']} in {v['file']}" for v in results["violations"]])
            pytest.fail(f"\nIMPORT ISOLATION VIOLATIONS:\n{violations}\n\nCRITICAL: Services must be 100% import-isolated per SPEC/independent_services.xml")
    
    @pytest.mark.e2e
    def test_service_independence_maintained(self, validation_results):
        """Test that services maintain structural independence"""
        results = validation_results["service_independence"]
        if not results["independent"]:
            violations = "\n".join([f"  - {v}" for v in results["violations"]])
            pytest.fail(f"\nSERVICE INDEPENDENCE VIOLATIONS:\n{violations}\n\nServices must maintain independent directory structures.")
    
    @pytest.mark.e2e
    def test_code_boundaries_clean(self, validation_results):
        """Test that code boundaries are properly enforced"""
        results = validation_results["code_boundaries"]
        if not results["boundaries_clean"]:
            violations = "\n".join([f"  - {v}" for v in results["violations"]])
            pytest.fail(f"\nCODE BOUNDARY VIOLATIONS:\n{violations}\n\nServices must not share module namespaces.")
    
    @pytest.mark.e2e
    def test_configuration_isolation_complete(self, validation_results):
        """Test that each service has isolated configuration"""
        results = validation_results["configuration_isolation"]
        if not results["isolated_config"]:
            violations = "\n".join([f"  - {v}" for v in results["violations"]])
            pytest.fail(f"\nCONFIGURATION ISOLATION VIOLATIONS:\n{violations}\n\nEach service must have independent configuration files.")
    
    @pytest.mark.e2e
    def test_api_only_communication(self, validation_results):
        """Test that inter-service communication uses only APIs"""
        results = validation_results["communication_protocols"]
        if not results["api_only_communication"]:
            violations = "\n".join([f"FAIL {v['service']}: {v['violation']} in {v['file']}" for v in results["violations"]])
            pytest.fail(f"\nCOMMUNICATION PROTOCOL VIOLATIONS:\n{violations}\n\nServices must communicate only via APIs, not direct code calls.")
    
    @pytest.mark.e2e
    def test_backend_services_only_scope(self, validator):
        """Test that validation correctly scopes to backend services only"""
        assert "frontend" not in validator.backend_services
        assert "frontend" in validator.excluded_services
        assert set(validator.backend_services.keys()) == {"main_backend", "auth_service"}
    
    @pytest.mark.e2e
    def test_comprehensive_isolation_report(self, validation_results):
        """Generate comprehensive isolation validation report"""
        categories = [("Import Isolation", "import_isolation"), ("Service Independence", "service_independence"),
                     ("Code Boundaries", "code_boundaries"), ("Configuration Isolation", "configuration_isolation"),
                     ("Communication Protocols", "communication_protocols")]
        
        print("\n" + "=" * 25 + " MICROSERVICE ISOLATION REPORT " + "=" * 25)
        total_violations = 0
        all_passed = True
        
        for name, key in categories:
            violations = validation_results[key]["total_violations"]
            total_violations += violations
            status = "PASS" if violations == 0 else f"FAIL ({violations} violations)"
            if violations > 0:
                all_passed = False
            print(f"{name:25}: {status}")
        
        print("-" * 80)
        print(f"Total Violations: {total_violations}")
        
        if all_passed:
            print("ALL MICROSERVICE ISOLATION TESTS PASSED\nArchitecture integrity maintained - services are 100% independent")
        else:
            print("MICROSERVICE ISOLATION VIOLATIONS DETECTED\nFix isolation violations to maintain system stability")
        
        print("=" * 80)
        assert True, "Microservice isolation validation report generated"


# Standalone execution support
def run_microservice_isolation_validation():
    """Run microservice isolation validation directly"""
    validator = MicroserviceIsolationValidator()
    results = validator.run_full_validation()
    total_violations = sum(category["total_violations"] for category in results.values())
    print(f"\nMicroservice Isolation Validation: {total_violations} total violations")
    return total_violations == 0


if __name__ == "__main__":
    sys.exit(0 if run_microservice_isolation_validation() else 1)