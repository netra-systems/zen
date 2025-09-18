"""
SSOT Workflow Integration Tests Validation Script

This script validates that the complete SSOT workflow integration tests
meet all requirements from the TEST_CREATION_GUIDE.md and CLAUDE.md standards.

Usage:
    python netra_backend/tests/integration/validate_ssot_workflow_tests.py
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Any


class SSotWorkflowTestValidator:
    """Validates SSOT workflow integration tests against requirements."""
    
    def __init__(self):
        self.test_file_path = Path(__file__).parent / "test_complete_ssot_workflow_integration.py"
        self.requirements = {
            "min_test_methods": 13,
            "min_lines_of_code": 2000,
            "required_markers": ["@pytest.mark.integration", "@pytest.mark.real_services"],
            "required_ssot_classes": [
                "IsolatedEnvironment",
                "UnifiedConfigurationManager", 
                "UnifiedWebSocketManager",
                "UnifiedStateManager",
                "AgentRegistry",
                "BaseAgent"
            ],
            "required_websocket_events": [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ],
            "min_business_value_per_test": 100000,  # $100K minimum
            "required_base_class": "BaseIntegrationTest"
        }
        
    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks."""
        results = {
            "file_exists": self._validate_file_exists(),
            "line_count": self._validate_line_count(),
            "test_methods": self._validate_test_methods(),
            "pytest_markers": self._validate_pytest_markers(),
            "base_class": self._validate_base_class(),
            "ssot_imports": self._validate_ssot_imports(),
            "business_value": self._validate_business_value(),
            "websocket_events": self._validate_websocket_events(),
            "no_mocks_policy": self._validate_no_mocks_policy(),
            "real_services": self._validate_real_services_usage(),
            "multi_user_support": self._validate_multi_user_support()
        }
        
        return results
    
    def _validate_file_exists(self) -> Dict[str, Any]:
        """Validate test file exists."""
        exists = self.test_file_path.exists()
        return {
            "passed": exists,
            "message": f"Test file exists: {self.test_file_path}" if exists else "Test file missing",
            "details": {"path": str(self.test_file_path)}
        }
    
    def _validate_line_count(self) -> Dict[str, Any]:
        """Validate sufficient lines of code."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
            
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            line_count = len(f.readlines())
        
        passed = line_count >= self.requirements["min_lines_of_code"]
        return {
            "passed": passed,
            "message": f"Line count: {line_count} (min: {self.requirements['min_lines_of_code']})",
            "details": {"actual": line_count, "required": self.requirements["min_lines_of_code"]}
        }
    
    def _validate_test_methods(self) -> Dict[str, Any]:
        """Validate number and structure of test methods."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count test methods
        test_methods = re.findall(r'async def (test_\w+)', content)
        method_count = len(test_methods)
        
        passed = method_count >= self.requirements["min_test_methods"]
        
        return {
            "passed": passed,
            "message": f"Test methods: {method_count} (min: {self.requirements['min_test_methods']})",
            "details": {
                "methods": test_methods,
                "count": method_count,
                "required": self.requirements["min_test_methods"]
            }
        }
    
    def _validate_pytest_markers(self) -> Dict[str, Any]:
        """Validate all tests have required pytest markers."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_markers = []
        for marker in self.requirements["required_markers"]:
            marker_count = content.count(marker)
            test_method_count = len(re.findall(r'async def (test_\w+)', content))
            
            if marker_count < test_method_count:
                missing_markers.append(f"{marker} (found {marker_count}, need {test_method_count})")
        
        passed = len(missing_markers) == 0
        
        return {
            "passed": passed,
            "message": "All tests have required markers" if passed else f"Missing markers: {missing_markers}",
            "details": {"missing_markers": missing_markers}
        }
    
    def _validate_base_class(self) -> Dict[str, Any]:
        """Validate test class inherits from BaseIntegrationTest."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        base_class_pattern = rf"class.*\({self.requirements['required_base_class']}\):"
        has_base_class = bool(re.search(base_class_pattern, content))
        
        return {
            "passed": has_base_class,
            "message": f"Inherits from {self.requirements['required_base_class']}" if has_base_class else f"Missing {self.requirements['required_base_class']} inheritance",
            "details": {"required_base_class": self.requirements['required_base_class']}
        }
    
    def _validate_ssot_imports(self) -> Dict[str, Any]:
        """Validate required SSOT classes are imported."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_imports = []
        for ssot_class in self.requirements["required_ssot_classes"]:
            if ssot_class not in content:
                missing_imports.append(ssot_class)
        
        passed = len(missing_imports) == 0
        
        return {
            "passed": passed,
            "message": "All SSOT classes imported" if passed else f"Missing imports: {missing_imports}",
            "details": {"missing_imports": missing_imports, "required": self.requirements["required_ssot_classes"]}
        }
    
    def _validate_business_value(self) -> Dict[str, Any]:
        """Validate each test has business value justification."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract business value amounts
        bvj_pattern = r'Business Value.*?(\$[\d,]+\+?).*?annual value'
        bvj_matches = re.findall(bvj_pattern, content, re.IGNORECASE | re.DOTALL)
        
        test_count = len(re.findall(r'async def (test_\w+)', content))
        bvj_count = len(bvj_matches)
        
        passed = bvj_count >= test_count
        
        return {
            "passed": passed,
            "message": f"BVJ statements: {bvj_count}/{test_count} tests" if passed else f"Missing BVJ in {test_count - bvj_count} tests",
            "details": {
                "bvj_found": bvj_count,
                "tests_count": test_count,
                "bvj_values": bvj_matches
            }
        }
    
    def _validate_websocket_events(self) -> Dict[str, Any]:
        """Validate critical WebSocket events are tested."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_events = []
        for event in self.requirements["required_websocket_events"]:
            if event not in content:
                missing_events.append(event)
        
        passed = len(missing_events) == 0
        
        return {
            "passed": passed,
            "message": "All WebSocket events validated" if passed else f"Missing events: {missing_events}",
            "details": {"missing_events": missing_events, "required": self.requirements["required_websocket_events"]}
        }
    
    def _validate_no_mocks_policy(self) -> Dict[str, Any]:
        """Validate no inappropriate mocks are used."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for inappropriate mocks (mocking SSOT classes or core functionality)
        inappropriate_mocks = []
        
        # Check for mocking of SSOT classes
        for ssot_class in self.requirements["required_ssot_classes"]:
            if f"Mock({ssot_class})" in content or f"mock_{ssot_class.lower()}" in content:
                inappropriate_mocks.append(f"Mocked {ssot_class}")
        
        # AsyncMock for WebSocket is acceptable, but not for core SSOT classes
        # We allow mock_websocket since that's the WebSocket connection, not the manager
        
        passed = len(inappropriate_mocks) == 0
        
        return {
            "passed": passed,
            "message": "No inappropriate mocks found" if passed else f"Inappropriate mocks: {inappropriate_mocks}",
            "details": {"inappropriate_mocks": inappropriate_mocks}
        }
    
    def _validate_real_services_usage(self) -> Dict[str, Any]:
        """Validate tests use real services fixture."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        real_services_imports = content.count("real_services_fixture")
        test_methods_with_fixture = content.count("real_services_fixture)")
        test_method_count = len(re.findall(r'async def (test_\w+)', content))
        
        passed = test_methods_with_fixture >= test_method_count
        
        return {
            "passed": passed,
            "message": f"Real services usage: {test_methods_with_fixture}/{test_method_count} tests",
            "details": {
                "methods_with_fixture": test_methods_with_fixture,
                "total_methods": test_method_count
            }
        }
    
    def _validate_multi_user_support(self) -> Dict[str, Any]:
        """Validate tests support multi-user scenarios."""
        if not self.test_file_path.exists():
            return {"passed": False, "message": "File not found", "details": {}}
        
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for multi-user test patterns
        multi_user_indicators = [
            "test_users",
            "user_id",
            "concurrent",
            "isolation",
            "multi_user"
        ]
        
        found_indicators = []
        for indicator in multi_user_indicators:
            if indicator in content:
                found_indicators.append(indicator)
        
        passed = len(found_indicators) >= 3  # Need at least 3 indicators
        
        return {
            "passed": passed,
            "message": f"Multi-user support indicators: {len(found_indicators)}/5",
            "details": {"found_indicators": found_indicators, "all_indicators": multi_user_indicators}
        }
    
    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        results = self.validate_all()
        
        report = []
        report.append("=" * 80)
        report.append("SSOT WORKFLOW INTEGRATION TESTS VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        total_checks = len(results)
        passed_checks = sum(1 for result in results.values() if result.get("passed", False))
        
        report.append(f"Overall Status: {passed_checks}/{total_checks} checks passed")
        report.append("")
        
        for check_name, result in results.items():
            status = "[PASS]" if result.get("passed", False) else "[FAIL]"
            report.append(f"{status} {check_name.upper().replace('_', ' ')}")
            report.append(f"    {result.get('message', 'No message')}")
            
            if not result.get("passed", False) and "details" in result:
                details = result["details"]
                for key, value in details.items():
                    if isinstance(value, list) and len(value) < 10:  # Don't spam long lists
                        report.append(f"    {key}: {value}")
                    elif not isinstance(value, list):
                        report.append(f"    {key}: {value}")
            report.append("")
        
        if passed_checks == total_checks:
            report.append("SUCCESS: ALL CHECKS PASSED! Tests meet all requirements.")
        else:
            report.append(f"WARNING: {total_checks - passed_checks} checks failed. Review and fix issues above.")
        
        report.append("")
        report.append("Test File: " + str(self.test_file_path))
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Run validation and display results."""
    validator = SSotWorkflowTestValidator()
    report = validator.generate_report()
    print(report)
    
    # Exit with error code if validation fails
    results = validator.validate_all()
    failed_checks = sum(1 for result in results.values() if not result.get("passed", False))
    
    if failed_checks > 0:
        print(f"\nValidation failed with {failed_checks} issues.")
        sys.exit(1)
    else:
        print("\nValidation successful! All requirements met.")
        sys.exit(0)


if __name__ == "__main__":
    main()