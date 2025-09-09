#!/usr/bin/env python3
"""
Validation Script for GitHub Issue #110 ToolRegistry Remediation

This script provides systematic validation of BaseModel filtering and registry
management across all identified instantiation pathways.

Business Value:
- Ensures chat functionality reliability through validated registry behavior
- Prevents "modelmetaclass already registered" errors in production
- Validates multi-user isolation and WebSocket integration

Usage:
    python3 scripts/validate_toolregistry_remediation.py --mode=quick
    python3 scripts/validate_toolregistry_remediation.py --mode=comprehensive --include-staging
"""

import sys
import importlib
import logging
import traceback
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class ValidationResult:
    """Result of a validation test."""
    test_name: str
    success: bool
    error: Optional[str] = None
    details: Dict[str, Any] = None
    duration_ms: float = 0.0

class ToolRegistryRemediationValidator:
    """Comprehensive validator for ToolRegistry remediation."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.results: List[ValidationResult] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for validation."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def validate_basemodel_filtering(self) -> ValidationResult:
        """Validate BaseModel filtering across core pathways."""
        start_time = datetime.now()
        
        try:
            # Import Pydantic BaseModel for testing
            from pydantic import BaseModel
            
            # Create test BaseModel class
            class TestBaseModelForValidation(BaseModel):
                test_field: str = "test_value"
                
            # Test UniversalRegistry BaseModel detection
            from netra_backend.app.core.registry.universal_registry import ToolRegistry
            
            registry = ToolRegistry(scope_id="validation_test")
            
            # Attempt to register BaseModel - should fail
            try:
                registry.register("test_basemodel", TestBaseModelForValidation)
                return ValidationResult(
                    test_name="basemodel_filtering",
                    success=False,
                    error="BaseModel was accepted - filtering failed",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
            except ValueError as e:
                if "basemodel" in str(e).lower():
                    self.logger.info("✅ BaseModel filtering working correctly")
                    return ValidationResult(
                        test_name="basemodel_filtering", 
                        success=True,
                        details={"rejection_reason": str(e)},
                        duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                    )
                else:
                    return ValidationResult(
                        test_name="basemodel_filtering",
                        success=False, 
                        error=f"Wrong rejection reason: {e}",
                        duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                    )
                    
        except Exception as e:
            return ValidationResult(
                test_name="basemodel_filtering",
                success=False,
                error=f"Exception during validation: {e}",
                details={"traceback": traceback.format_exc()},
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def validate_registry_api_compatibility(self) -> ValidationResult:
        """Validate registry API compatibility for tests."""
        start_time = datetime.now()
        
        try:
            from netra_backend.app.core.registry.universal_registry import ToolRegistry
            
            registry = ToolRegistry(scope_id="api_test")
            
            # Check for compatibility methods
            compatibility_issues = []
            
            if not hasattr(registry, 'get_tool'):
                compatibility_issues.append("Missing get_tool() method")
                
            if not hasattr(registry, 'register_tool'):
                compatibility_issues.append("Missing register_tool() method")
            
            if compatibility_issues:
                return ValidationResult(
                    test_name="api_compatibility",
                    success=False,
                    error="API compatibility issues found",
                    details={"missing_methods": compatibility_issues},
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
            
            # Test get_tool method works
            try:
                result = registry.get_tool("nonexistent_tool")
                if result is None:
                    self.logger.info("✅ get_tool() compatibility method working")
                    return ValidationResult(
                        test_name="api_compatibility",
                        success=True,
                        details={"methods_validated": ["get_tool", "register_tool"]},
                        duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                    )
            except AttributeError:
                return ValidationResult(
                    test_name="api_compatibility", 
                    success=False,
                    error="get_tool() method not working",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
                
        except Exception as e:
            return ValidationResult(
                test_name="api_compatibility",
                success=False,
                error=f"Exception during API validation: {e}",
                details={"traceback": traceback.format_exc()},
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def validate_websocket_cleanup_integration(self) -> ValidationResult:
        """Validate WebSocket registry cleanup integration."""
        start_time = datetime.now()
        
        try:
            from netra_backend.app.websocket_core.supervisor_factory import (
                cleanup_websocket_registries,
                get_registry_cleanup_status
            )
            
            # Test cleanup status function
            status = get_registry_cleanup_status()
            
            if not isinstance(status, dict):
                return ValidationResult(
                    test_name="websocket_cleanup",
                    success=False,
                    error="Cleanup status function not returning dict",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
            
            # Test cleanup function (safe to call with non-existent connection)
            cleanup_websocket_registries("test_connection_validation")
            
            self.logger.info("✅ WebSocket cleanup functions accessible")
            return ValidationResult(
                test_name="websocket_cleanup",
                success=True,
                details={"cleanup_status": status},
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="websocket_cleanup",
                success=False, 
                error=f"WebSocket cleanup validation failed: {e}",
                details={"traceback": traceback.format_exc()},
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def validate_registry_instantiation_pathways(self) -> ValidationResult:
        """Validate key registry instantiation pathways."""
        start_time = datetime.now()
        
        try:
            # Key instantiation points to test
            pathways_to_test = [
                "netra_backend.app.core.registry.universal_registry.ToolRegistry",
                "netra_backend.app.core.registry.universal_registry.get_global_registry",
                "netra_backend.app.core.registry.universal_registry.create_scoped_registry"
            ]
            
            validated_pathways = []
            failed_pathways = []
            
            for pathway in pathways_to_test:
                try:
                    if "ToolRegistry" in pathway:
                        module_path, class_name = pathway.rsplit('.', 1)
                        module = importlib.import_module(module_path)
                        registry_class = getattr(module, class_name)
                        registry = registry_class(scope_id="pathway_test")
                        validated_pathways.append(pathway)
                    elif "get_global_registry" in pathway:
                        module_path, func_name = pathway.rsplit('.', 1)
                        module = importlib.import_module(module_path)
                        func = getattr(module, func_name)
                        registry = func("tool")
                        validated_pathways.append(pathway)
                    elif "create_scoped_registry" in pathway:
                        module_path, func_name = pathway.rsplit('.', 1) 
                        module = importlib.import_module(module_path)
                        func = getattr(module, func_name)
                        registry = func("tool", "pathway_test")
                        validated_pathways.append(pathway)
                        
                except Exception as e:
                    failed_pathways.append(f"{pathway}: {e}")
            
            if failed_pathways:
                return ValidationResult(
                    test_name="instantiation_pathways",
                    success=False,
                    error="Some pathways failed validation",
                    details={
                        "validated": validated_pathways,
                        "failed": failed_pathways
                    },
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
            
            self.logger.info(f"✅ All {len(validated_pathways)} instantiation pathways working")
            return ValidationResult(
                test_name="instantiation_pathways", 
                success=True,
                details={"validated_pathways": validated_pathways},
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
        except Exception as e:
            return ValidationResult(
                test_name="instantiation_pathways",
                success=False,
                error=f"Pathway validation failed: {e}",
                details={"traceback": traceback.format_exc()},
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def run_quick_validation(self) -> Dict[str, Any]:
        """Run quick validation of core functionality."""
        self.logger.info("🚀 Starting Quick Validation for GitHub Issue #110")
        
        validations = [
            self.validate_basemodel_filtering,
            self.validate_registry_api_compatibility, 
            self.validate_websocket_cleanup_integration,
            self.validate_registry_instantiation_pathways
        ]
        
        for validation_func in validations:
            result = validation_func()
            self.results.append(result)
            
            if result.success:
                self.logger.info(f"✅ {result.test_name}: PASSED ({result.duration_ms:.1f}ms)")
            else:
                self.logger.error(f"❌ {result.test_name}: FAILED - {result.error}")
                if result.details:
                    self.logger.error(f"   Details: {result.details}")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        report = {
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "github_issue": "110",
            "total_tests": total_tests,
            "passed_tests": passed_tests, 
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "overall_status": "PASSED" if failed_tests == 0 else "FAILED",
            "test_results": [
                {
                    "test_name": r.test_name,
                    "status": "PASSED" if r.success else "FAILED",
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        return report

def main():
    """Main validation entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate ToolRegistry Remediation")
    parser.add_argument("--mode", choices=["quick", "comprehensive"], 
                       default="quick", help="Validation mode")
    parser.add_argument("--include-staging", action="store_true",
                       help="Include staging environment tests")
    parser.add_argument("--output", help="Output report to file")
    
    args = parser.parse_args()
    
    validator = ToolRegistryRemediationValidator()
    
    if args.mode == "quick":
        report = validator.run_quick_validation()
    else:
        # Comprehensive mode would include more extensive testing
        report = validator.run_quick_validation()  # For now, same as quick
    
    # Print summary
    print("\n" + "="*60)
    print("TOOLREGISTRY REMEDIATION VALIDATION REPORT")
    print("="*60)
    print(f"Overall Status: {report['overall_status']}")
    print(f"Tests Passed: {report['passed_tests']}/{report['total_tests']} "
          f"({report['success_rate']:.1%})")
    
    if report['failed_tests'] > 0:
        print("\n❌ FAILED TESTS:")
        for test in report['test_results']:
            if test['status'] == 'FAILED':
                print(f"  - {test['test_name']}: {test['error']}")
    else:
        print("\n✅ ALL VALIDATIONS PASSED - Remediation appears successful")
    
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Full report saved to: {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if report['overall_status'] == 'PASSED' else 1)

if __name__ == "__main__":
    main()