#!/usr/bin/env python3
"""
Factory Contract Validation Script

This script provides automated validation of factory pattern interfaces to prevent
parameter mismatches and breaking changes. It can be run manually or as part of CI/CD.

Usage:
    python scripts/validate_factory_contracts.py --validate-all
    python scripts/validate_factory_contracts.py --check-breaking-changes
    python scripts/validate_factory_contracts.py --save-baselines
    python scripts/validate_factory_contracts.py --validate-user-context
"""

import argparse
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Type, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.lifecycle.contract_validation_framework import (
    get_contract_registry,
    validate_factory_interface,
    check_parameter_compatibility,
    ValidationResult
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class FactoryValidationRunner:
    """Main runner for factory contract validation."""
    
    def __init__(self):
        self.registry = get_contract_registry()
        self.factory_classes = {}
        self.validation_results: List[ValidationResult] = []
        self._discover_factory_classes()
    
    def _discover_factory_classes(self) -> None:
        """Discover all factory classes in the codebase."""
        factory_modules = [
            "netra_backend.app.websocket_core.supervisor_factory",
            "netra_backend.app.websocket_core.websocket_manager_factory", 
            "netra_backend.app.core.supervisor_factory",
            "netra_backend.app.agents.supervisor.execution_engine_factory",
            "netra_backend.app.agents.supervisor.agent_instance_factory",
            "netra_backend.app.core.app_factory",
            "netra_backend.app.llm.client_factory",
            "netra_backend.app.factories.data_access_factory",
            "netra_backend.app.factories.redis_factory",
        ]
        
        for module_name in factory_modules:
            try:
                module = importlib.import_module(module_name)
                
                # Find classes with 'Factory' in the name or factory functions
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 'Factory' in name) or \
                       (inspect.isfunction(obj) and ('create_' in name or 'factory' in name.lower())):
                        
                        # Skip private members
                        if not name.startswith('_'):
                            self.factory_classes[f"{module_name}.{name}"] = obj
                            
            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")
    
    def validate_all_factories(self) -> bool:
        """Validate all discovered factory classes."""
        print("🔍 Validating Factory Contracts...")
        print("=" * 50)
        
        all_valid = True
        
        for factory_name, factory_class in self.factory_classes.items():
            print(f"\nValidating: {factory_name}")
            
            if inspect.isclass(factory_class):
                result = validate_factory_interface(factory_class)
            else:
                # For factory functions, create a mock class for validation
                result = self._validate_factory_function(factory_name, factory_class)
            
            self.validation_results.append(result)
            
            if result.is_valid:
                print(f"✅ VALID: {factory_name}")
            else:
                print(f"❌ INVALID: {factory_name}")
                all_valid = False
                
                for error in result.errors:
                    print(f"   ERROR: {error}")
                
                for warning in result.warnings:
                    print(f"   WARNING: {warning}")
                
                # Print parameter mismatches with details
                for mismatch in result.parameter_mismatches:
                    print(f"   PARAMETER MISMATCH: {mismatch}")
        
        print("\n" + "=" * 50)
        total_factories = len(self.factory_classes)
        valid_factories = sum(1 for r in self.validation_results if r.is_valid)
        invalid_factories = total_factories - valid_factories
        
        print(f"📊 VALIDATION SUMMARY:")
        print(f"   Total Factories: {total_factories}")
        print(f"   Valid: {valid_factories}")
        print(f"   Invalid: {invalid_factories}")
        
        if all_valid:
            print("🎉 ALL FACTORY CONTRACTS ARE VALID!")
        else:
            print("⚠️  FACTORY CONTRACT VIOLATIONS FOUND!")
            
        return all_valid
    
    def _validate_factory_function(self, function_name: str, factory_function: callable) -> ValidationResult:
        """Validate a factory function signature."""
        from shared.lifecycle.contract_validation_framework import SignatureAnalyzer
        
        result = ValidationResult(is_valid=True, interface_name=function_name)
        
        # Extract signature
        try:
            method_contract = SignatureAnalyzer.extract_method_contract(factory_function)
            
            # Check for critical factory function patterns
            param_names = method_contract.get_parameter_names()
            
            # Check for UserExecutionContext parameter
            if 'user_context' in param_names:
                # This should match UserExecutionContext interface
                result.add_warning(f"Factory function {function_name} takes user_context parameter - ensure compatibility")
            
            # Check for websocket parameter naming consistency
            websocket_params = [name for name in param_names if 'websocket' in name.lower()]
            if len(websocket_params) > 1:
                result.add_error(f"Multiple websocket parameters found: {websocket_params} - potential naming inconsistency")
            
            # Check for connection_id vs client_id naming
            connection_params = [name for name in param_names if 'connection' in name.lower() or 'client' in name.lower()]
            if 'websocket_connection_id' in param_names and 'websocket_client_id' in param_names:
                result.add_error("Both websocket_connection_id and websocket_client_id found - this causes the parameter mismatch bug!")
            
        except Exception as e:
            result.add_error(f"Failed to analyze function signature: {e}")
            
        return result
    
    def validate_user_execution_context(self) -> bool:
        """Validate UserExecutionContext against its contract."""
        print("🔍 Validating UserExecutionContext Contract...")
        print("=" * 50)
        
        result = self.registry.validate_user_execution_context(UserExecutionContext)
        
        if result.is_valid:
            print("✅ UserExecutionContext contract is VALID")
        else:
            print("❌ UserExecutionContext contract VIOLATIONS:")
            for error in result.errors:
                print(f"   ERROR: {error}")
            for warning in result.warnings:
                print(f"   WARNING: {warning}")
        
        return result.is_valid
    
    def check_breaking_changes(self) -> bool:
        """Check for breaking changes in factory interfaces."""
        print("🔍 Checking for Breaking Changes...")
        print("=" * 50)
        
        found_breaking_changes = False
        
        # Check UserExecutionContext specifically
        breaking_changes = self.registry.check_for_breaking_changes("UserExecutionContext", UserExecutionContext)
        
        if breaking_changes:
            print("❌ BREAKING CHANGES found in UserExecutionContext:")
            for change in breaking_changes:
                print(f"   {change}")
            found_breaking_changes = True
        else:
            print("✅ No breaking changes in UserExecutionContext")
        
        # Check other factory classes
        for factory_name, factory_class in self.factory_classes.items():
            if inspect.isclass(factory_class):
                changes = self.registry.check_for_breaking_changes(factory_name, factory_class)
                if changes:
                    print(f"❌ BREAKING CHANGES in {factory_name}:")
                    for change in changes:
                        print(f"   {change}")
                    found_breaking_changes = True
        
        if not found_breaking_changes:
            print("🎉 NO BREAKING CHANGES DETECTED!")
            
        return not found_breaking_changes
    
    def save_contract_baselines(self) -> None:
        """Save current contracts as baselines for future comparison."""
        print("💾 Saving Contract Baselines...")
        print("=" * 50)
        
        # Save UserExecutionContext baseline
        implementations = {"UserExecutionContext": UserExecutionContext}
        
        # Add factory classes
        for factory_name, factory_class in self.factory_classes.items():
            if inspect.isclass(factory_class):
                implementations[factory_name] = factory_class
        
        self.registry.save_baseline_contracts(implementations)
        
        print(f"✅ Saved {len(implementations)} contract baselines")
    
    def run_specific_validation_tests(self) -> bool:
        """Run specific tests for the parameter mismatch issue."""
        print("🧪 Running Specific Parameter Mismatch Tests...")
        print("=" * 50)
        
        all_passed = True
        
        # Test 1: Check UserExecutionContext constructor parameters
        print("\nTest 1: UserExecutionContext Constructor Parameters")
        try:
            import inspect
            sig = inspect.signature(UserExecutionContext.__init__)
            param_names = list(sig.parameters.keys())[1:]  # Skip 'self'
            
            print(f"   Parameters: {param_names}")
            
            # Check for the critical parameter
            if 'websocket_client_id' in param_names:
                print("   ✅ websocket_client_id parameter found (correct)")
            else:
                print("   ❌ websocket_client_id parameter missing")
                all_passed = False
                
            if 'websocket_connection_id' in param_names:
                print("   ⚠️  websocket_connection_id parameter found (legacy - should be removed)")
                
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            all_passed = False
        
        # Test 2: Check supervisor factory function calls
        print("\nTest 2: Supervisor Factory Parameter Usage")
        try:
            # Try to import and check supervisor factory
            from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
            from netra_backend.app.core.supervisor_factory import create_supervisor_core
            
            # Check supervisor factory signatures
            supervisor_sig = inspect.signature(get_websocket_scoped_supervisor)
            core_sig = inspect.signature(create_supervisor_core)
            
            print(f"   get_websocket_scoped_supervisor params: {list(supervisor_sig.parameters.keys())}")
            print(f"   create_supervisor_core params: {list(core_sig.parameters.keys())}")
            
            # Check if both use consistent websocket parameter naming
            supervisor_websocket_params = [name for name in supervisor_sig.parameters if 'websocket' in name]
            core_websocket_params = [name for name in core_sig.parameters if 'websocket' in name]
            
            print(f"   WebSocket params in supervisor: {supervisor_websocket_params}")
            print(f"   WebSocket params in core: {core_websocket_params}")
            
            if 'websocket_client_id' in core_websocket_params:
                print("   ✅ Core factory uses websocket_client_id (correct)")
            else:
                print("   ❌ Core factory doesn't use websocket_client_id")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            all_passed = False
        
        # Test 3: Check actual UserExecutionContext creation
        print("\nTest 3: UserExecutionContext Creation Test")
        try:
            # Test creating with the correct parameter name using proper non-placeholder values
            test_context = UserExecutionContext(
                user_id="usr_12345678901234567890",  # Proper length, not placeholder
                thread_id="thrd_12345678901234567890", 
                run_id="run_12345678901234567890",
                websocket_client_id="ws_client_12345678901234567890"  # This should work
            )
            print("   ✅ UserExecutionContext creation with websocket_client_id succeeded")
            
        except TypeError as e:
            print(f"   ❌ UserExecutionContext creation failed: {e}")
            all_passed = False
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            all_passed = False
        
        print(f"\n🧪 Specific Tests Result: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
        return all_passed


def main():
    parser = argparse.ArgumentParser(description="Factory Contract Validation")
    parser.add_argument("--validate-all", action="store_true", help="Validate all factory contracts")
    parser.add_argument("--validate-user-context", action="store_true", help="Validate UserExecutionContext contract")
    parser.add_argument("--check-breaking-changes", action="store_true", help="Check for breaking changes")
    parser.add_argument("--save-baselines", action="store_true", help="Save current contracts as baselines")
    parser.add_argument("--specific-tests", action="store_true", help="Run specific parameter mismatch tests")
    
    args = parser.parse_args()
    
    # Default to validate all if no specific action
    if not any([args.validate_all, args.validate_user_context, args.check_breaking_changes, 
                args.save_baselines, args.specific_tests]):
        args.validate_all = True
    
    runner = FactoryValidationRunner()
    success = True
    
    if args.validate_all:
        success &= runner.validate_all_factories()
    
    if args.validate_user_context:
        success &= runner.validate_user_execution_context()
    
    if args.check_breaking_changes:
        success &= runner.check_breaking_changes()
    
    if args.save_baselines:
        runner.save_contract_baselines()
    
    if args.specific_tests:
        success &= runner.run_specific_validation_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()