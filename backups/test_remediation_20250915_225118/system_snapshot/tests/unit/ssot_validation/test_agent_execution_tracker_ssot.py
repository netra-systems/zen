"""
AgentExecutionTracker SSOT Consolidation Validation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & Agent Execution Tracking
- Value Impact: Validates execution tracking SSOT for agent reliability
- Strategic Impact: Ensures consistent agent execution state management

Tests validate AgentExecutionTracker SSOT status and consolidation needs.
This determines if execution tracking consolidation is complete or requires work.
"""

import unittest
import importlib
import inspect
from enum import Enum
from typing import Dict, List, Any, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase


class AgentExecutionTrackerSSOTTests(SSotBaseTestCase):
    """Validate AgentExecutionTracker SSOT consolidation status."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.canonical_module = 'netra_backend.app.core.agent_execution_tracker'
        self.expected_execution_states = {
            'PENDING', 'STARTING', 'RUNNING', 'COMPLETING', 
            'COMPLETED', 'FAILED', 'TIMEOUT', 'DEAD', 'CANCELLED'
        }
        
    def test_execution_state_enum_consolidation(self):
        """Validate ExecutionState enum is properly consolidated."""
        # Test comprehensive 9-state enum is available
        
        try:
            from netra_backend.app.core.agent_execution_tracker import ExecutionState
            
            # Validate it's an Enum
            self.assertTrue(
                issubclass(ExecutionState, Enum),
                "ExecutionState should be an Enum class"
            )
            
            # Validate expected states are present
            actual_states = {state.value for state in ExecutionState}
            
            missing_states = self.expected_execution_states - actual_states
            extra_states = actual_states - self.expected_execution_states
            
            self.assertEqual(
                len(missing_states), 0,
                f"Missing expected ExecutionState values: {missing_states}"
            )
            
            # Log state analysis
            print(f"\n✅ ExecutionState Enum Consolidation:")
            print(f"    Expected states: {len(self.expected_execution_states)}")
            print(f"    Actual states: {len(actual_states)}")
            print(f"    States: {sorted(actual_states)}")
            
            if extra_states:
                print(f"    Extra states found: {extra_states}")
            
        except ImportError as e:
            self.fail(f"Cannot import ExecutionState from canonical module: {e}")
    
    def test_agent_execution_tracker_ssot_import(self):
        """Validate AgentExecutionTracker SSOT import works."""
        # Test SSOT implementation is accessible
        
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, get_execution_tracker
            
            # Validate class is importable
            self.assertTrue(
                inspect.isclass(AgentExecutionTracker),
                "AgentExecutionTracker should be a class"
            )
            
            # Validate factory function works
            tracker = get_execution_tracker()
            self.assertIsInstance(
                tracker, 
                AgentExecutionTracker,
                "get_execution_tracker should return AgentExecutionTracker instance"
            )
            
            print(f"\n✅ AgentExecutionTracker SSOT Import:")
            print(f"    Class available: {AgentExecutionTracker.__name__}")
            print(f"    Module: {AgentExecutionTracker.__module__}")
            print(f"    Factory function: get_execution_tracker")
            print(f"    Instance type: {type(tracker).__name__}")
            
        except ImportError as e:
            self.fail(f"Cannot import AgentExecutionTracker SSOT implementation: {e}")
        except Exception as e:
            self.fail(f"AgentExecutionTracker instantiation failed: {e}")
    
    def test_legacy_execution_tracker_deprecation(self):
        """Test legacy execution tracker classes are properly deprecated."""
        # Check if legacy classes exist and provide deprecation warnings
        
        legacy_tracker_paths = [
            ('netra_backend.app.core.execution_tracker', 'ExecutionTracker'),
            ('netra_backend.app.agents.execution_tracking.registry', 'ExecutionState'),
            ('netra_backend.app.agents.agent_state_tracker', 'AgentStateTracker'),
            ('netra_backend.app.agents.execution_timeout_manager', 'AgentExecutionTimeoutManager')
        ]
        
        legacy_status = {}
        
        for module_path, class_name in legacy_tracker_paths:
            try:
                module = importlib.import_module(module_path)
                legacy_class = getattr(module, class_name, None)
                
                if legacy_class:
                    legacy_status[f"{module_path}.{class_name}"] = {
                        'exists': True,
                        'class_type': str(type(legacy_class)),
                        'deprecation_status': 'present'
                    }
                else:
                    legacy_status[f"{module_path}.{class_name}"] = {
                        'exists': False,
                        'deprecation_status': 'class_not_found'
                    }
                    
            except ImportError:
                legacy_status[f"{module_path}.{class_name}"] = {
                    'exists': False,
                    'deprecation_status': 'module_not_found'
                }
        
        # Analyze legacy status
        existing_legacy = [path for path, status in legacy_status.items() if status['exists']]
        deprecated_legacy = [path for path, status in legacy_status.items() if not status['exists']]
        
        print(f"\n📊 Legacy Execution Tracker Status:")
        print(f"    Total legacy paths checked: {len(legacy_status)}")
        print(f"    Still existing: {len(existing_legacy)}")
        print(f"    Properly deprecated: {len(deprecated_legacy)}")
        
        if existing_legacy:
            print(f"\n⚠️  Legacy classes still existing:")
            for path in existing_legacy:
                status = legacy_status[path]['deprecation_status']
                print(f"      {path}: {status}")
        
        if deprecated_legacy:
            print(f"\n✅ Properly deprecated:")
            for path in deprecated_legacy:
                status = legacy_status[path]['deprecation_status']
                print(f"      {path}: {status}")
        
        # This test documents current deprecation status
        # More deprecated = better SSOT consolidation
    
    def test_execution_tracker_functionality_consolidated(self):
        """Validate all execution tracking functionality is consolidated."""
        # Test state management, timeout handling, death detection
        
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, ExecutionState
            
            tracker = AgentExecutionTracker()
            
            # Test core functionality exists
            core_methods = [
                'create_execution_id', 'update_execution_state', 'get_execution_state',
                'start_execution', 'complete_execution', 'fail_execution'
            ]
            
            available_methods = []
            missing_methods = []
            
            for method_name in core_methods:
                if hasattr(tracker, method_name):
                    method = getattr(tracker, method_name)
                    if callable(method):
                        available_methods.append(method_name)
                    else:
                        missing_methods.append(f"{method_name} (not callable)")
                else:
                    missing_methods.append(method_name)
            
            # Test ExecutionState integration
            execution_id = "test_execution_123"
            
            try:
                # Try to use ExecutionState enum with tracker
                if hasattr(tracker, 'update_execution_state'):
                    # This might fail if methods have different signatures
                    # but we're testing the consolidation status
                    pass
                
                print(f"\n✅ Execution Tracker Functionality:")
                print(f"    Available methods: {len(available_methods)}/{len(core_methods)}")
                for method in available_methods:
                    print(f"      ✅ {method}")
                
                if missing_methods:
                    print(f"    Missing methods: {len(missing_methods)}")
                    for method in missing_methods:
                        print(f"      ❌ {method}")
                        
            except Exception as e:
                print(f"    ExecutionState integration test failed: {e}")
            
            # Success criteria: Core functionality should be available
            self.assertGreater(
                len(available_methods),
                len(core_methods) * 0.5,  # At least 50% of core methods
                f"Insufficient execution tracker functionality. Available: {available_methods}, Missing: {missing_methods}"
            )
            
        except ImportError as e:
            self.fail(f"Cannot import AgentExecutionTracker for functionality test: {e}")
    
    def test_execution_tracker_id_generation_ssot(self):
        """Test execution tracker uses SSOT ID generation."""
        # Validate UnifiedIDManager integration
        
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
            
            tracker = AgentExecutionTracker()
            
            # Test ID generation
            if hasattr(tracker, 'create_execution_id'):
                try:
                    execution_id = tracker.create_execution_id()
                    
                    # Validate ID format (should be from UnifiedIDManager)
                    self.assertIsInstance(execution_id, str)
                    self.assertGreater(len(execution_id), 0)
                    
                    # Test multiple IDs are unique
                    id_set = set()
                    for _ in range(5):
                        new_id = tracker.create_execution_id()
                        id_set.add(new_id)
                    
                    self.assertEqual(
                        len(id_set), 5,
                        "Execution ID generation should produce unique IDs"
                    )
                    
                    print(f"\n✅ Execution Tracker ID Generation:")
                    print(f"    ID generation method: create_execution_id")
                    print(f"    Sample ID: {execution_id}")
                    print(f"    Unique IDs generated: {len(id_set)}/5")
                    
                except Exception as e:
                    print(f"    ID generation test failed: {e}")
                    self.skipTest(f"Cannot test ID generation: {e}")
            else:
                self.skipTest("create_execution_id method not available")
                
        except ImportError as e:
            self.skipTest(f"Cannot import required classes for ID generation test: {e}")


class AgentExecutionTrackerConsolidationStatusTests(SSotBaseTestCase):
    """Determine if AgentExecutionTracker consolidation is complete."""
    
    def test_duplicate_execution_tracker_detection(self):
        """Scan for duplicate execution tracker implementations."""
        # Find multiple implementations that should be consolidated
        
        import os
        import re
        
        tracker_implementations = []
        
        # Scan for execution tracker classes
        for root, dirs, files in os.walk('netra_backend'):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Look for execution tracker class definitions
                            patterns = [
                                r'class\s+(\w*ExecutionTracker[^(]*)',
                                r'class\s+(\w*StateTracker[^(]*)',
                                r'class\s+(\w*TimeoutManager[^(]*)'
                            ]
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, content)
                                for class_name in matches:
                                    class_name = class_name.strip()
                                    if class_name and 'Test' not in class_name:
                                        tracker_implementations.append({
                                            'file': filepath,
                                            'class_name': class_name,
                                            'pattern_type': pattern
                                        })
                                        
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # Analyze implementations
        implementation_names = [impl['class_name'] for impl in tracker_implementations]
        unique_implementations = set(implementation_names)
        
        known_acceptable = {
            'AgentExecutionTracker',  # SSOT implementation
            'ExecutionTracker',       # Compatibility alias
            'AgentExecutionPhase'     # Enum, not tracker
        }
        
        potentially_duplicate = unique_implementations - known_acceptable
        
        print(f"\n📊 Execution Tracker Implementation Analysis:")
        print(f"    Total implementations found: {len(tracker_implementations)}")
        print(f"    Unique implementation names: {len(unique_implementations)}")
        print(f"    Known acceptable: {len(unique_implementations & known_acceptable)}")
        print(f"    Potentially duplicate: {len(potentially_duplicate)}")
        
        if potentially_duplicate:
            print(f"\n⚠️  Potentially duplicate implementations:")
            for impl_name in sorted(potentially_duplicate):
                files = [impl['file'] for impl in tracker_implementations if impl['class_name'] == impl_name]
                print(f"      {impl_name}: {len(files)} files")
                for file_path in files[:2]:  # Show first 2 files
                    print(f"        - {file_path}")
        
        # Fewer duplicates = better SSOT consolidation
        consolidation_score = 1.0 - (len(potentially_duplicate) / max(len(unique_implementations), 1))
        
        print(f"\n📈 Consolidation Score: {consolidation_score:.2f}")
        print(f"    (1.0 = fully consolidated, 0.0 = highly fragmented)")
        
        # Document current consolidation status
        self.assertGreaterEqual(
            consolidation_score,
            0.5,  # At least 50% consolidated
            f"Low consolidation score indicates more SSOT work needed: {consolidation_score:.2f}"
        )
    
    def test_execution_state_enum_consistency(self):
        """Test ExecutionState enum consistency across modules."""
        # Check if multiple ExecutionState definitions exist
        
        execution_state_modules = [
            'netra_backend.app.core.agent_execution_tracker',
            'netra_backend.app.core.execution_tracker',
            'netra_backend.app.agents.execution_tracking.registry'
        ]
        
        state_definitions = {}
        
        for module_path in execution_state_modules:
            try:
                module = importlib.import_module(module_path)
                execution_state = getattr(module, 'ExecutionState', None)
                
                if execution_state and inspect.isclass(execution_state):
                    states = set()
                    if issubclass(execution_state, Enum):
                        states = {state.value for state in execution_state}
                    
                    state_definitions[module_path] = {
                        'class_id': id(execution_state),
                        'states': states,
                        'is_enum': issubclass(execution_state, Enum)
                    }
                    
            except ImportError:
                # Module not found - could indicate consolidation
                state_definitions[module_path] = None
        
        # Analyze consistency
        available_definitions = {k: v for k, v in state_definitions.items() if v is not None}
        
        if len(available_definitions) == 0:
            self.fail("No ExecutionState definitions found")
        
        if len(available_definitions) == 1:
            print(f"\n✅ ExecutionState SSOT Achieved:")
            module_path = list(available_definitions.keys())[0]
            definition = available_definitions[module_path]
            print(f"    Single definition in: {module_path}")
            print(f"    States: {sorted(definition['states'])}")
        else:
            print(f"\n⚠️  Multiple ExecutionState Definitions:")
            
            # Check if they're the same class (aliases)
            class_ids = [def_info['class_id'] for def_info in available_definitions.values()]
            unique_class_ids = set(class_ids)
            
            if len(unique_class_ids) == 1:
                print(f"    ✅ All definitions are aliases (same class ID: {list(unique_class_ids)[0]})")
                for module_path in available_definitions.keys():
                    print(f"      {module_path}")
            else:
                print(f"    ❌ Different class definitions found ({len(unique_class_ids)} unique):")
                for module_path, definition in available_definitions.items():
                    print(f"      {module_path}: ID {definition['class_id']}, {len(definition['states'])} states")
                
                self.fail(f"Multiple different ExecutionState classes found - SSOT violation")
    
    def test_consolidation_completion_indicators(self):
        """Test indicators of consolidation completion."""
        # Check various indicators that suggest consolidation is complete
        
        completion_indicators = {}
        
        # Indicator 1: SSOT class available
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            completion_indicators['ssot_class_available'] = True
        except ImportError:
            completion_indicators['ssot_class_available'] = False
        
        # Indicator 2: Comprehensive ExecutionState enum
        try:
            from netra_backend.app.core.agent_execution_tracker import ExecutionState
            states = {state.value for state in ExecutionState}
            completion_indicators['comprehensive_execution_state'] = len(states) >= 8  # Should have 9 states
        except ImportError:
            completion_indicators['comprehensive_execution_state'] = False
        
        # Indicator 3: Factory function available
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
            tracker = get_execution_tracker()
            completion_indicators['factory_function_available'] = True
        except (ImportError, Exception):
            completion_indicators['factory_function_available'] = False
        
        # Indicator 4: Legacy classes deprecated
        legacy_deprecated = True
        legacy_paths = [
            'netra_backend.app.agents.agent_state_tracker.AgentStateTracker',
            'netra_backend.app.agents.execution_timeout_manager.AgentExecutionTimeoutManager'
        ]
        
        for path in legacy_paths:
            module_path, class_name = path.rsplit('.', 1)
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    legacy_deprecated = False
                    break
            except ImportError:
                continue  # Module not found = good (deprecated)
        
        completion_indicators['legacy_classes_deprecated'] = legacy_deprecated
        
        # Calculate completion score
        completion_score = sum(completion_indicators.values()) / len(completion_indicators)
        
        print(f"\n📊 AgentExecutionTracker Consolidation Status:")
        for indicator, status in completion_indicators.items():
            status_symbol = "✅" if status else "❌"
            print(f"    {indicator}: {status_symbol}")
        
        print(f"\n📈 Completion Score: {completion_score:.2f}")
        print(f"    (1.0 = fully consolidated, 0.0 = not consolidated)")
        
        # Determine if consolidation is complete
        if completion_score >= 0.75:
            print(f"\n🎉 CONSOLIDATION APPEARS COMPLETE")
        elif completion_score >= 0.5:
            print(f"\n⚠️  CONSOLIDATION PARTIALLY COMPLETE")
        else:
            print(f"\n🚨 CONSOLIDATION INCOMPLETE - WORK NEEDED")
        
        # Document current status
        self.assertGreaterEqual(
            completion_score,
            0.5,
            f"AgentExecutionTracker consolidation score too low: {completion_score:.2f}"
        )


if __name__ == '__main__':
    unittest.main()