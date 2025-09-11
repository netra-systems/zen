#!/usr/bin/env python3
"""
WebSocket Test Plan Validation Script

Business Value Justification:
- Segment: Platform/Internal - Test Infrastructure Validation
- Business Goal: Ensure WebSocket handshake test plan is executable and comprehensive
- Value Impact: Validates test infrastructure before critical handshake fixes
- Strategic Impact: Prevents test failures that could delay $500K+ ARR fixes

USAGE:
This script validates that the WebSocket handshake test plan is properly configured
and can be executed. It performs syntax validation, import checking, and basic
test discovery to ensure the test plan will work when needed.
"""

import sys
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketTestPlanValidator:
    """
    Validator for WebSocket handshake test plan infrastructure.
    
    This validator ensures the test plan is properly structured and executable
    before we need it for critical handshake fixes.
    """
    
    def __init__(self):
        self.project_root = project_root
        self.test_plan_path = self.project_root / "test_plans" / "websocket_auth_handshake_comprehensive_test_plan.py"
        self.utilities_path = self.project_root / "test_framework" / "websocket_handshake_test_utilities.py"
        self.test_runner_path = self.project_root / "scripts" / "run_websocket_handshake_tests.py"
        
    def validate_test_plan(self) -> Dict[str, Any]:
        """
        Validate the complete WebSocket handshake test plan.
        
        Returns:
            Comprehensive validation results
        """
        logger.info("🔍 Validating WebSocket Handshake Test Plan")
        logger.info("=" * 50)
        
        results = {
            "overall_valid": False,
            "file_checks": {},
            "syntax_checks": {},
            "import_checks": {},
            "test_discovery": {},
            "business_value_validation": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Step 1: File existence validation
            results["file_checks"] = self._validate_file_structure()
            
            # Step 2: Syntax validation
            results["syntax_checks"] = self._validate_syntax()
            
            # Step 3: Import validation
            results["import_checks"] = self._validate_imports()
            
            # Step 4: Test discovery validation
            results["test_discovery"] = self._validate_test_discovery()
            
            # Step 5: Business value validation
            results["business_value_validation"] = self._validate_business_value_coverage()
            
            # Calculate overall validity
            results["overall_valid"] = self._calculate_overall_validity(results)
            
        except Exception as e:
            results["errors"].append(f"Validation failed with exception: {str(e)}")
            logger.error(f"Test plan validation failed: {e}")
        
        return results
    
    def _validate_file_structure(self) -> Dict[str, Any]:
        """Validate that all required files exist and are accessible."""
        logger.info("📁 Validating file structure...")
        
        files_to_check = {
            "test_plan": self.test_plan_path,
            "utilities": self.utilities_path,
            "test_runner": self.test_runner_path,
            "readme": self.project_root / "test_plans" / "README_WebSocket_Handshake_Testing.md"
        }
        
        results = {
            "all_files_exist": True,
            "file_status": {},
            "missing_files": []
        }
        
        for file_type, file_path in files_to_check.items():
            if file_path.exists():
                results["file_status"][file_type] = {
                    "exists": True,
                    "size": file_path.stat().st_size,
                    "readable": file_path.is_file()
                }
                logger.debug(f"✅ {file_type}: {file_path.name} ({file_path.stat().st_size} bytes)")
            else:
                results["all_files_exist"] = False
                results["missing_files"].append(str(file_path))
                results["file_status"][file_type] = {"exists": False}
                logger.error(f"❌ Missing {file_type}: {file_path}")
        
        return results
    
    def _validate_syntax(self) -> Dict[str, Any]:
        """Validate Python syntax of all test files."""
        logger.info("🐍 Validating Python syntax...")
        
        files_to_check = [
            self.test_plan_path,
            self.utilities_path,
            self.test_runner_path
        ]
        
        results = {
            "all_syntax_valid": True,
            "file_syntax": {},
            "syntax_errors": []
        }
        
        for file_path in files_to_check:
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                # Parse the AST to check syntax
                ast.parse(source_code, filename=str(file_path))
                
                results["file_syntax"][file_path.name] = {
                    "valid": True,
                    "lines": len(source_code.splitlines())
                }
                logger.debug(f"✅ Syntax valid: {file_path.name}")
                
            except SyntaxError as e:
                results["all_syntax_valid"] = False
                error_msg = f"{file_path.name}:{e.lineno}: {e.msg}"
                results["syntax_errors"].append(error_msg)
                results["file_syntax"][file_path.name] = {
                    "valid": False,
                    "error": str(e)
                }
                logger.error(f"❌ Syntax error in {file_path.name}: {e}")
            except Exception as e:
                results["all_syntax_valid"] = False
                error_msg = f"{file_path.name}: {str(e)}"
                results["syntax_errors"].append(error_msg)
                results["file_syntax"][file_path.name] = {
                    "valid": False,
                    "error": str(e)
                }
                logger.error(f"❌ Error reading {file_path.name}: {e}")
        
        return results
    
    def _validate_imports(self) -> Dict[str, Any]:
        """Validate that critical imports are available."""
        logger.info("📦 Validating imports...")
        
        critical_imports = [
            # Core testing framework
            "pytest",
            "asyncio",
            "unittest.mock",
            
            # FastAPI WebSocket
            "fastapi",
            "fastapi.websockets",
            
            # Project imports (check if they exist)
            "test_framework.base_integration_test",
            "netra_backend.app.websocket_core.unified_jwt_protocol_handler",
            "netra_backend.app.websocket_core.unified_websocket_auth",
        ]
        
        results = {
            "all_imports_available": True,
            "import_status": {},
            "missing_imports": []
        }
        
        for import_name in critical_imports:
            try:
                # Try to import the module
                if "." in import_name:
                    # Handle dotted imports
                    module_name = import_name.split(".")[0]
                    __import__(import_name)
                else:
                    __import__(import_name)
                
                results["import_status"][import_name] = {"available": True}
                logger.debug(f"✅ Import available: {import_name}")
                
            except ImportError as e:
                results["all_imports_available"] = False
                results["missing_imports"].append(import_name)
                results["import_status"][import_name] = {
                    "available": False,
                    "error": str(e)
                }
                logger.warning(f"⚠️ Import unavailable: {import_name} ({e})")
            except Exception as e:
                results["import_status"][import_name] = {
                    "available": False,
                    "error": str(e)
                }
                logger.warning(f"⚠️ Import error: {import_name} ({e})")
        
        return results
    
    def _validate_test_discovery(self) -> Dict[str, Any]:
        """Validate that tests can be discovered by pytest."""
        logger.info("🔍 Validating test discovery...")
        
        results = {
            "tests_discoverable": False,
            "test_classes_found": [],
            "test_methods_found": [],
            "total_tests": 0
        }
        
        try:
            if not self.test_plan_path.exists():
                results["error"] = "Test plan file not found"
                return results
            
            with open(self.test_plan_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse AST to find test classes and methods
            tree = ast.parse(source_code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    if class_name.startswith("Test"):
                        results["test_classes_found"].append(class_name)
                        
                        # Find test methods in this class
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                                method_name = f"{class_name}.{item.name}"
                                results["test_methods_found"].append(method_name)
                                results["total_tests"] += 1
                
                elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    # Standalone test function
                    results["test_methods_found"].append(node.name)
                    results["total_tests"] += 1
            
            results["tests_discoverable"] = results["total_tests"] > 0
            
            logger.info(f"📊 Discovered {len(results['test_classes_found'])} test classes")
            logger.info(f"📊 Discovered {results['total_tests']} test methods")
            
            for class_name in results["test_classes_found"]:
                logger.debug(f"  📋 Test class: {class_name}")
            
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Test discovery failed: {e}")
        
        return results
    
    def _validate_business_value_coverage(self) -> Dict[str, Any]:
        """Validate that tests cover critical business value scenarios."""
        logger.info("💰 Validating business value coverage...")
        
        required_scenarios = [
            # Core business flows
            "golden_path", "chat_functionality", "agent_response",
            
            # Critical technical scenarios  
            "rfc6455", "handshake", "authentication", "subprotocol",
            
            # Error scenarios
            "1011_error", "malformed", "graceful_degradation",
            
            # Performance scenarios
            "performance", "regression",
            
            # Revenue protection
            "business_value", "revenue", "arr"
        ]
        
        results = {
            "business_value_covered": False,
            "scenario_coverage": {},
            "missing_scenarios": [],
            "coverage_score": 0
        }
        
        try:
            if not self.test_plan_path.exists():
                results["error"] = "Test plan file not found"
                return results
            
            with open(self.test_plan_path, 'r', encoding='utf-8') as f:
                source_code = f.read().lower()
            
            # Check for each required scenario
            covered_scenarios = 0
            
            for scenario in required_scenarios:
                if scenario in source_code:
                    results["scenario_coverage"][scenario] = True
                    covered_scenarios += 1
                    logger.debug(f"✅ Scenario covered: {scenario}")
                else:
                    results["scenario_coverage"][scenario] = False
                    results["missing_scenarios"].append(scenario)
                    logger.warning(f"⚠️ Scenario missing: {scenario}")
            
            # Calculate coverage score
            results["coverage_score"] = (covered_scenarios / len(required_scenarios)) * 100
            results["business_value_covered"] = results["coverage_score"] >= 80  # 80% threshold
            
            logger.info(f"📊 Business value coverage: {results['coverage_score']:.1f}%")
            
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Business value validation failed: {e}")
        
        return results
    
    def _calculate_overall_validity(self, results: Dict[str, Any]) -> bool:
        """Calculate overall validity based on all validation results."""
        validity_checks = [
            results["file_checks"].get("all_files_exist", False),
            results["syntax_checks"].get("all_syntax_valid", False),
            results["test_discovery"].get("tests_discoverable", False),
            results["business_value_validation"].get("business_value_covered", False)
        ]
        
        # Import checks are optional (may fail in CI without real services)
        import_score = len([k for k, v in results["import_checks"].get("import_status", {}).items() if v.get("available", False)])
        total_imports = len(results["import_checks"].get("import_status", {}))
        import_threshold_met = import_score >= (total_imports * 0.7) if total_imports > 0 else True  # 70% threshold
        
        validity_checks.append(import_threshold_met)
        
        return all(validity_checks)
    
    def print_validation_report(self, results: Dict[str, Any]):
        """Print a comprehensive validation report."""
        logger.info("\n🎯 VALIDATION REPORT")
        logger.info("=" * 50)
        
        overall_status = "✅ VALID" if results["overall_valid"] else "❌ INVALID"
        logger.info(f"Overall Status: {overall_status}")
        
        # File structure
        file_checks = results.get("file_checks", {})
        logger.info(f"📁 File Structure: {'✅ PASS' if file_checks.get('all_files_exist') else '❌ FAIL'}")
        
        # Syntax validation
        syntax_checks = results.get("syntax_checks", {})
        logger.info(f"🐍 Python Syntax: {'✅ PASS' if syntax_checks.get('all_syntax_valid') else '❌ FAIL'}")
        
        # Import validation
        import_checks = results.get("import_checks", {})
        import_count = len([v for v in import_checks.get("import_status", {}).values() if v.get("available")])
        total_imports = len(import_checks.get("import_status", {}))
        logger.info(f"📦 Import Availability: {import_count}/{total_imports} imports available")
        
        # Test discovery
        test_discovery = results.get("test_discovery", {})
        test_count = test_discovery.get("total_tests", 0)
        logger.info(f"🔍 Test Discovery: {test_count} tests discovered")
        
        # Business value coverage
        bv_validation = results.get("business_value_validation", {})
        coverage_score = bv_validation.get("coverage_score", 0)
        logger.info(f"💰 Business Value Coverage: {coverage_score:.1f}%")
        
        # Errors and warnings
        if results.get("errors"):
            logger.info(f"\n❌ ERRORS:")
            for error in results["errors"]:
                logger.info(f"  - {error}")
        
        if results.get("warnings"):
            logger.info(f"\n⚠️ WARNINGS:")
            for warning in results["warnings"]:
                logger.info(f"  - {warning}")
        
        # Recommendations
        logger.info(f"\n📋 RECOMMENDATIONS:")
        if results["overall_valid"]:
            logger.info("  ✅ Test plan is ready for execution")
            logger.info("  ✅ All critical components are in place")
            logger.info("  ✅ Business value scenarios are covered")
            logger.info("  🚀 Ready to validate WebSocket handshake fixes")
        else:
            logger.info("  🔧 Fix file structure issues before testing")
            logger.info("  🔧 Resolve syntax errors in Python files")
            logger.info("  🔧 Ensure all critical imports are available") 
            logger.info("  🔧 Add missing business value test scenarios")


def main():
    """Main validation function."""
    validator = WebSocketTestPlanValidator()
    
    try:
        # Run comprehensive validation
        results = validator.validate_test_plan()
        
        # Print detailed report
        validator.print_validation_report(results)
        
        # Exit with appropriate code
        if results["overall_valid"]:
            logger.info("\n✅ WebSocket handshake test plan validation successful!")
            logger.info("🚀 Ready to execute comprehensive handshake testing")
            sys.exit(0)
        else:
            logger.error("\n❌ WebSocket handshake test plan validation failed!")
            logger.error("🔧 Fix validation issues before executing tests")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()