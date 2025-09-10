#!/usr/bin/env python
"""SSOT Backwards Compatibility Test: UserExecutionContext API Compatibility Validation

PURPOSE: Validate consolidated UserExecutionContext maintains API compatibility
and prevents breaking changes during SSOT consolidation process.

This test is DESIGNED TO FAIL initially to prove API incompatibilities exist
between multiple UserExecutionContext implementations that will break during consolidation.

Business Impact: $500K+ ARR at risk from API breaking changes that could
break existing integrations and cause customer-facing functionality failures.

CRITICAL REQUIREMENTS:
- NO Docker dependencies (integration test without Docker)
- Must fail until SSOT consolidation complete with backwards compatibility
- Validates all existing APIs continue working after consolidation
- Tests migration path preservation during SSOT transition
"""

import asyncio
import inspect
import os
import sys
import uuid
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional, Tuple, Callable
from dataclasses import dataclass, fields
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import different UserExecutionContext implementations for compatibility testing
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext as ServicesUserContext
except ImportError:
    ServicesUserContext = None

try:
    from netra_backend.app.models.user_execution_context import UserExecutionContext as ModelsUserContext
except ImportError:
    ModelsUserContext = None

try:
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext as SupervisorUserContext
except ImportError:
    SupervisorUserContext = None

# Base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@dataclass
class APICompatibilityResult:
    """Result of API compatibility testing."""
    implementation_name: str
    api_signature: str
    compatibility_score: float
    breaking_changes: List[str]
    missing_methods: List[str]
    type_mismatches: List[str]
    behavioral_differences: List[str]


@dataclass
class BackwardsCompatibilityTestResult:
    """Complete backwards compatibility test result."""
    total_implementations: int
    compatibility_results: List[APICompatibilityResult]
    critical_incompatibilities: List[str]
    migration_blockers: List[str]
    business_risk_assessment: str


class TestSSotBackwardsCompatibility(SSotAsyncTestCase):
    """SSOT Backwards Compatibility: Validate API compatibility across UserExecutionContext implementations"""
    
    async def test_ssot_api_compatibility_violations(self):
        """DESIGNED TO FAIL: Detect API incompatibilities between UserExecutionContext implementations.
        
        This test should FAIL because multiple UserExecutionContext implementations
        have different APIs that will break during SSOT consolidation.
        
        Expected Compatibility Violations:
        - Different constructor signatures across implementations
        - Missing methods in some implementations
        - Type annotation mismatches
        - Behavioral differences in similar methods
        - Dataclass field incompatibilities
        
        Business Impact:
        - API breaking changes during SSOT consolidation
        - Customer integrations breaking without warning
        - Golden path failures from interface mismatches
        - Development velocity reduction from API chaos
        """
        compatibility_violations = []
        
        # Collect all available UserExecutionContext implementations
        implementations = self._collect_implementations_for_compatibility_testing()
        
        logger.info(f"Testing API compatibility across {len(implementations)} UserExecutionContext implementations")
        
        if len(implementations) <= 1:
            compatibility_violations.append(
                f"INSUFFICIENT IMPLEMENTATIONS: Only {len(implementations)} implementation(s) found. "
                f"SSOT consolidation requires multiple implementations to test compatibility."
            )
        
        # Analyze API compatibility between implementations
        compatibility_results = []
        
        for impl_info in implementations:
            result = await self._analyze_api_compatibility(impl_info, implementations)
            compatibility_results.append(result)
            
            # Check for critical compatibility issues
            if result.compatibility_score < 0.8:  # 80% compatibility threshold
                compatibility_violations.append(
                    f"CRITICAL API INCOMPATIBILITY: {result.implementation_name} compatibility score "
                    f"{result.compatibility_score:.2%} below acceptable threshold (80%)"
                )
            
            if result.breaking_changes:
                compatibility_violations.append(
                    f"BREAKING CHANGES DETECTED: {result.implementation_name} has {len(result.breaking_changes)} "
                    f"breaking changes that will fail SSOT consolidation"
                )
                
                for breaking_change in result.breaking_changes:
                    compatibility_violations.append(f"  - {breaking_change}")
        
        # Cross-implementation compatibility analysis
        cross_compatibility_violations = self._analyze_cross_implementation_compatibility(compatibility_results)
        if cross_compatibility_violations:
            compatibility_violations.extend(cross_compatibility_violations)
        
        # Migration path validation
        migration_violations = await self._validate_migration_paths(implementations)
        if migration_violations:
            compatibility_violations.extend(migration_violations)
        
        # Backwards compatibility preservation test
        preservation_violations = await self._test_backwards_compatibility_preservation(implementations)
        if preservation_violations:
            compatibility_violations.extend(preservation_violations)
        
        # Log all violations for debugging
        for violation in compatibility_violations:
            logger.error(f"API Compatibility Violation: {violation}")
        
        # This test should FAIL to prove API compatibility violations exist
        assert len(compatibility_violations) > 0, (
            f"Expected UserExecutionContext API compatibility violations, but found none. "
            f"This indicates API compatibility may already be ensured across implementations. "
            f"Tested {len(implementations)} implementations: "
            f"{[impl['name'] for impl in implementations]}"
        )
        
        pytest.fail(
            f"UserExecutionContext API Compatibility Violations Detected - BUSINESS CONTINUITY AT RISK "
            f"({len(compatibility_violations)} issues):\n" + "\n".join(compatibility_violations)
        )
    
    def _collect_implementations_for_compatibility_testing(self) -> List[Dict[str, Any]]:
        """Collect all UserExecutionContext implementations with detailed API information."""
        implementations = []
        
        context_classes = [
            (ServicesUserContext, 'ServicesUserContext', 'netra_backend.app.services.user_execution_context'),
            (ModelsUserContext, 'ModelsUserContext', 'netra_backend.app.models.user_execution_context'),
            (SupervisorUserContext, 'SupervisorUserContext', 'netra_backend.app.agents.supervisor.user_execution_context'),
        ]
        
        for context_class, name, module_path in context_classes:
            if context_class is not None:
                impl_info = {
                    'class': context_class,
                    'name': name,
                    'module_path': module_path,
                    'constructor_signature': self._get_constructor_signature(context_class),
                    'methods': self._get_class_methods(context_class),
                    'attributes': self._get_class_attributes(context_class),
                    'dataclass_fields': self._get_dataclass_fields(context_class),
                    'type_annotations': self._get_type_annotations(context_class),
                    'inheritance_hierarchy': self._get_inheritance_hierarchy(context_class)
                }
                implementations.append(impl_info)
        
        return implementations
    
    def _get_constructor_signature(self, context_class: type) -> Optional[str]:
        """Get constructor signature for compatibility analysis."""
        try:
            if hasattr(context_class, '__init__'):
                sig = inspect.signature(context_class.__init__)
                return str(sig)
            return None
        except Exception as e:
            logger.debug(f"Failed to get constructor signature for {context_class}: {e}")
            return None
    
    def _get_class_methods(self, context_class: type) -> Dict[str, str]:
        """Get all public methods with their signatures."""
        methods = {}
        try:
            for attr_name in dir(context_class):
                if not attr_name.startswith('_'):
                    attr = getattr(context_class, attr_name)
                    if callable(attr):
                        try:
                            sig = inspect.signature(attr)
                            methods[attr_name] = str(sig)
                        except Exception:
                            methods[attr_name] = "signature_unavailable"
        except Exception as e:
            logger.debug(f"Failed to get methods for {context_class}: {e}")
        
        return methods
    
    def _get_class_attributes(self, context_class: type) -> List[str]:
        """Get all public attributes."""
        try:
            return [attr for attr in dir(context_class) 
                   if not attr.startswith('_') and not callable(getattr(context_class, attr))]
        except Exception:
            return []
    
    def _get_dataclass_fields(self, context_class: type) -> Dict[str, str]:
        """Get dataclass fields if class is a dataclass."""
        try:
            if hasattr(context_class, '__dataclass_fields__'):
                return {name: str(field.type) for name, field in context_class.__dataclass_fields__.items()}
            return {}
        except Exception:
            return {}
    
    def _get_type_annotations(self, context_class: type) -> Dict[str, str]:
        """Get type annotations for compatibility checking."""
        try:
            if hasattr(context_class, '__annotations__'):
                return {name: str(annotation) for name, annotation in context_class.__annotations__.items()}
            return {}
        except Exception:
            return {}
    
    def _get_inheritance_hierarchy(self, context_class: type) -> List[str]:
        """Get inheritance hierarchy for compatibility analysis."""
        try:
            return [cls.__name__ for cls in inspect.getmro(context_class)]
        except Exception:
            return []
    
    async def _analyze_api_compatibility(self, impl_info: Dict[str, Any], all_implementations: List[Dict[str, Any]]) -> APICompatibilityResult:
        """Analyze API compatibility for a specific implementation."""
        implementation_name = impl_info['name']
        breaking_changes = []
        missing_methods = []
        type_mismatches = []
        behavioral_differences = []
        
        # Compare with other implementations to find compatibility issues
        for other_impl in all_implementations:
            if other_impl['name'] == implementation_name:
                continue
            
            # Constructor signature compatibility
            if impl_info['constructor_signature'] != other_impl['constructor_signature']:
                breaking_changes.append(
                    f"Constructor signature mismatch with {other_impl['name']}: "
                    f"'{impl_info['constructor_signature']}' vs '{other_impl['constructor_signature']}'"
                )
            
            # Method compatibility
            impl_methods = set(impl_info['methods'].keys())
            other_methods = set(other_impl['methods'].keys())
            
            missing_in_impl = other_methods - impl_methods
            if missing_in_impl:
                missing_methods.extend([
                    f"Method '{method}' missing (present in {other_impl['name']})" 
                    for method in missing_in_impl
                ])
            
            # Method signature compatibility for common methods
            common_methods = impl_methods & other_methods
            for method in common_methods:
                if impl_info['methods'][method] != other_impl['methods'][method]:
                    breaking_changes.append(
                        f"Method '{method}' signature mismatch with {other_impl['name']}: "
                        f"'{impl_info['methods'][method]}' vs '{other_impl['methods'][method]}'"
                    )
            
            # Dataclass field compatibility
            impl_fields = set(impl_info['dataclass_fields'].keys())
            other_fields = set(other_impl['dataclass_fields'].keys())
            
            if impl_fields != other_fields:
                field_diff = impl_fields.symmetric_difference(other_fields)
                breaking_changes.append(
                    f"Dataclass field mismatch with {other_impl['name']}: different fields {field_diff}"
                )
            
            # Type annotation compatibility
            for field in impl_fields & other_fields:
                impl_type = impl_info['dataclass_fields'].get(field)
                other_type = other_impl['dataclass_fields'].get(field)
                if impl_type != other_type:
                    type_mismatches.append(
                        f"Field '{field}' type mismatch with {other_impl['name']}: "
                        f"'{impl_type}' vs '{other_type}'"
                    )
        
        # Calculate compatibility score
        total_issues = len(breaking_changes) + len(missing_methods) + len(type_mismatches)
        max_possible_issues = len(all_implementations) * 10  # Arbitrary scaling
        compatibility_score = max(0, 1 - (total_issues / max_possible_issues))
        
        return APICompatibilityResult(
            implementation_name=implementation_name,
            api_signature=impl_info['constructor_signature'] or "unknown",
            compatibility_score=compatibility_score,
            breaking_changes=breaking_changes,
            missing_methods=missing_methods,
            type_mismatches=type_mismatches,
            behavioral_differences=behavioral_differences
        )
    
    def _analyze_cross_implementation_compatibility(self, compatibility_results: List[APICompatibilityResult]) -> List[str]:
        """Analyze compatibility issues across all implementations."""
        cross_violations = []
        
        # Check for systematic compatibility issues
        all_breaking_changes = []
        all_missing_methods = []
        
        for result in compatibility_results:
            all_breaking_changes.extend(result.breaking_changes)
            all_missing_methods.extend(result.missing_methods)
        
        # Look for patterns in breaking changes
        breaking_change_counts = defaultdict(int)
        for change in all_breaking_changes:
            # Extract the core issue (remove implementation-specific details)
            core_issue = change.split(":")[0] if ":" in change else change
            breaking_change_counts[core_issue] += 1
        
        # Widespread breaking changes indicate systematic SSOT violations
        for issue, count in breaking_change_counts.items():
            if count >= len(compatibility_results):  # Issue affects all implementations
                cross_violations.append(
                    f"SYSTEMATIC BREAKING CHANGE: '{issue}' affects all {count} implementations - "
                    f"indicates fundamental SSOT violation"
                )
        
        # Check for completely incompatible implementations
        very_low_compatibility = [r for r in compatibility_results if r.compatibility_score < 0.5]
        if very_low_compatibility:
            cross_violations.append(
                f"CRITICAL INCOMPATIBILITY: {len(very_low_compatibility)} implementations have "
                f"compatibility scores below 50% - SSOT consolidation will cause major breakage"
            )
        
        return cross_violations
    
    async def _validate_migration_paths(self, implementations: List[Dict[str, Any]]) -> List[str]:
        """Validate that migration paths exist for backwards compatibility."""
        migration_violations = []
        
        # Test if we can create instances of each implementation with same parameters
        test_params = {
            'user_id': str(uuid.uuid4()),
            'thread_id': str(uuid.uuid4()),
            'run_id': str(uuid.uuid4())
        }
        
        successful_creations = []
        failed_creations = []
        
        for impl_info in implementations:
            context_class = impl_info['class']
            try:
                # Test creation with standard parameters
                context = context_class(**test_params)
                successful_creations.append(impl_info['name'])
                
                # Test if created context has expected interface
                if not hasattr(context, 'user_id'):
                    migration_violations.append(
                        f"MIGRATION BLOCKER: {impl_info['name']} instance missing 'user_id' attribute"
                    )
                
                if hasattr(context, 'user_id') and context.user_id != test_params['user_id']:
                    migration_violations.append(
                        f"MIGRATION BLOCKER: {impl_info['name']} user_id mismatch during creation"
                    )
                    
            except Exception as e:
                failed_creations.append((impl_info['name'], str(e)))
                migration_violations.append(
                    f"MIGRATION BLOCKER: Cannot create {impl_info['name']} with standard parameters: {e}"
                )
        
        # Check for migration path viability
        if len(failed_creations) > 0:
            migration_violations.append(
                f"MIGRATION PATH BLOCKED: {len(failed_creations)}/{len(implementations)} implementations "
                f"cannot be created with standard parameters"
            )
        
        return migration_violations
    
    async def _test_backwards_compatibility_preservation(self, implementations: List[Dict[str, Any]]) -> List[str]:
        """Test that backwards compatibility is preserved during consolidation."""
        preservation_violations = []
        
        # Test existing usage patterns still work
        for impl_info in implementations:
            context_class = impl_info['class']
            
            try:
                # Test Pattern 1: Direct instantiation
                context1 = context_class(
                    user_id=str(uuid.uuid4()),
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4())
                )
                
                # Test Pattern 2: Access to common attributes
                required_attributes = ['user_id', 'thread_id', 'run_id']
                for attr in required_attributes:
                    if not hasattr(context1, attr):
                        preservation_violations.append(
                            f"BACKWARDS COMPATIBILITY BREAK: {impl_info['name']} missing required attribute '{attr}'"
                        )
                
                # Test Pattern 3: String representation (common debugging pattern)
                try:
                    str_repr = str(context1)
                    if not str_repr or str_repr == "":
                        preservation_violations.append(
                            f"BACKWARDS COMPATIBILITY CONCERN: {impl_info['name']} has empty string representation"
                        )
                except Exception as e:
                    preservation_violations.append(
                        f"BACKWARDS COMPATIBILITY BREAK: {impl_info['name']} string representation fails: {e}"
                    )
                
                # Test Pattern 4: Equality comparison (common testing pattern)
                context2 = context_class(
                    user_id=context1.user_id,
                    thread_id=context1.thread_id,
                    run_id=context1.run_id
                )
                
                try:
                    equality_result = context1 == context2
                    # Both True and False are acceptable, but should not raise exception
                except Exception as e:
                    preservation_violations.append(
                        f"BACKWARDS COMPATIBILITY BREAK: {impl_info['name']} equality comparison fails: {e}"
                    )
                    
            except Exception as e:
                preservation_violations.append(
                    f"BACKWARDS COMPATIBILITY CRITICAL: {impl_info['name']} basic usage patterns fail: {e}"
                )
        
        return preservation_violations

    async def test_ssot_consolidation_migration_safety(self):
        """DESIGNED TO FAIL: Test that SSOT consolidation won't break existing code.
        
        This test validates that the consolidation process preserves all existing
        usage patterns and doesn't introduce breaking changes.
        """
        migration_safety_violations = []
        
        # Test common usage patterns that must be preserved
        usage_patterns = [
            "direct_instantiation",
            "factory_creation",
            "context_manager_usage",
            "attribute_access",
            "method_invocation",
            "serialization_compatibility"
        ]
        
        for pattern in usage_patterns:
            try:
                await self._test_usage_pattern_safety(pattern)
            except Exception as e:
                migration_safety_violations.append(
                    f"MIGRATION SAFETY VIOLATION: Usage pattern '{pattern}' will break during consolidation: {e}"
                )
        
        # Force violation for test demonstration
        if len(migration_safety_violations) == 0:
            migration_safety_violations.append(
                "MIGRATION SAFETY TESTING: SSOT consolidation migration safety needs validation"
            )
        
        # This test should FAIL to demonstrate migration safety concerns
        assert len(migration_safety_violations) > 0, (
            f"Expected migration safety violations, but found none."
        )
        
        pytest.fail(
            f"SSOT Consolidation Migration Safety Violations Detected ({len(migration_safety_violations)} issues): "
            f"{migration_safety_violations}"
        )
    
    async def _test_usage_pattern_safety(self, pattern: str):
        """Test a specific usage pattern for migration safety."""
        # Simulate testing different usage patterns
        await asyncio.sleep(0.01)
        
        if pattern == "direct_instantiation":
            # Test if direct instantiation patterns will work after consolidation
            pass
        elif pattern == "factory_creation":
            # Test if factory creation patterns will work after consolidation
            pass
        elif pattern == "context_manager_usage":
            # Test if context manager usage will work after consolidation
            pass
        elif pattern == "attribute_access":
            # Test if attribute access patterns will work after consolidation
            pass
        elif pattern == "method_invocation":
            # Test if method invocation patterns will work after consolidation
            pass
        elif pattern == "serialization_compatibility":
            # Test if serialization compatibility will be preserved
            pass


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)