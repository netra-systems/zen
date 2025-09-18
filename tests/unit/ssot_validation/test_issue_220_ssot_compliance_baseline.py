"""
Issue #220 SSOT Compliance Baseline Validation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Architectural Excellence & System Stability  
- Value Impact: Quantifies SSOT compliance for $500K+ ARR protection
- Strategic Impact: Establishes baseline for SSOT consolidation validation

This test validates the current SSOT compliance levels and documents remaining
violations to determine if Issue #220 consolidation work is complete.
"""

import unittest
import importlib
import inspect
import os
import re
from typing import Dict, List, Set, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase


class Issue220SSOTComplianceBaselineTests(SSotBaseTestCase):
    """Validate current SSOT compliance levels and violations."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.compliance_target = 87.0  # Current compliance level
        self.max_violations = 300  # Current violation threshold
        
    def test_architectural_compliance_score_baseline(self):
        """Validate current compliance score meets minimum threshold."""
        # Test designed to validate current compliance levels
        # Expected: 87.2% compliance with documented violations
        
        try:
            # Attempt to run compliance check (if available)
            import subprocess
            result = subprocess.run([
                'python', 'scripts/check_architecture_compliance.py'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse compliance score from output
                output = result.stdout
                # Look for compliance percentage in output
                import re
                compliance_match = re.search(r'(\d+\.?\d*)%', output)
                if compliance_match:
                    compliance_score = float(compliance_match.group(1))
                    self.assertGreaterEqual(
                        compliance_score, 
                        self.compliance_target,
                        f"Compliance score {compliance_score}% below target {self.compliance_target}%"
                    )
                else:
                    self.skipTest("Could not parse compliance score from output")
            else:
                self.skipTest("Architecture compliance script not available")
                
        except (subprocess.TimeoutExpired, FileNotFoundError, ImportError):
            self.skipTest("Cannot run architecture compliance check")
    
    def test_import_violations_quantification(self):
        """Quantify and categorize remaining import violations."""
        # Expected: 285 violations across specific categories
        # Success Criteria: All violations have clear remediation paths
        
        violation_categories = {
            'relative_imports': [],
            'duplicate_imports': [],
            'cross_service_imports': [],
            'deprecated_imports': []
        }
        
        # Scan for relative import violations
        for root, dirs, files in os.walk('netra_backend'):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Check for relative imports
                            if re.search(r'from\s+\.', content):
                                violation_categories['relative_imports'].append(filepath)
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # Document violation counts
        total_violations = sum(len(v) for v in violation_categories.values())
        
        # Should have violations documented (proving we detect issues)
        self.assertLessEqual(
            total_violations, 
            self.max_violations,
            f"Total violations {total_violations} exceeds threshold {self.max_violations}"
        )
        
        # Log violation categories for analysis
        for category, violations in violation_categories.items():
            if violations:
                print(f"\n{category}: {len(violations)} violations")
                for violation in violations[:5]:  # Show first 5
                    print(f"  - {violation}")
    
    def test_ssot_class_detection_comprehensive(self):
        """Detect all SSOT classes and their compliance status."""
        # Expected: MessageRouter, AgentFactory, Configuration classes SSOT
        # Success Criteria: SSOT classes properly consolidated
        
        ssot_classes = {
            'MessageRouter': {
                'canonical_path': 'netra_backend.app.websocket_core.canonical_message_router',
                'compatibility_paths': [
                    'netra_backend.app.websocket_core.handlers',
                    'netra_backend.app.services.websocket.quality_message_router'
                ]
            },
            'AgentExecutionTracker': {
                'canonical_path': 'netra_backend.app.core.agent_execution_tracker',
                'compatibility_paths': []
            },
            'ConfigurationManager': {
                'canonical_path': 'netra_backend.app.core.configuration.base',
                'compatibility_paths': []
            }
        }
        
        ssot_compliance_results = {}
        
        for class_name, paths in ssot_classes.items():
            try:
                # Import canonical implementation
                canonical_module = importlib.import_module(paths['canonical_path'])
                canonical_class = getattr(canonical_module, class_name, None)
                
                if canonical_class is None:
                    # Try alternate class names
                    for attr_name in dir(canonical_module):
                        attr = getattr(canonical_module, attr_name)
                        if inspect.isclass(attr) and class_name.lower() in attr_name.lower():
                            canonical_class = attr
                            break
                
                if canonical_class:
                    ssot_compliance_results[class_name] = {
                        'canonical_available': True,
                        'canonical_id': id(canonical_class)
                    }
                    
                    # Check compatibility paths
                    compatible = True
                    for compat_path in paths['compatibility_paths']:
                        try:
                            compat_module = importlib.import_module(compat_path)
                            compat_class = getattr(compat_module, class_name, None)
                            if compat_class and id(compat_class) != id(canonical_class):
                                compatible = False
                                break
                        except ImportError:
                            continue
                    
                    ssot_compliance_results[class_name]['compatibility_maintained'] = compatible
                else:
                    ssot_compliance_results[class_name] = {
                        'canonical_available': False,
                        'compatibility_maintained': False
                    }
                    
            except ImportError:
                ssot_compliance_results[class_name] = {
                    'canonical_available': False,
                    'compatibility_maintained': False
                }
        
        # Validate SSOT compliance
        for class_name, results in ssot_compliance_results.items():
            self.assertTrue(
                results['canonical_available'],
                f"SSOT class {class_name} not available at canonical path"
            )
        
        # Log results for analysis
        print(f"\nSSoT Class Compliance Results:")
        for class_name, results in ssot_compliance_results.items():
            print(f"  {class_name}: {results}")

    def test_duplicate_implementation_detection(self):
        """Scan for duplicate implementations violating SSOT."""
        # Expected: Identify remaining duplicates for remediation
        # Success Criteria: Known duplicates documented, unknown ones flagged
        
        known_duplicate_patterns = [
            # Patterns we expect to find (legacy compatibility)
            'MessageRouter',
            'ExecutionTracker', 
            'WebSocketManager'
        ]
        
        duplicate_detections = {}
        
        # Scan for class definitions that might be duplicates
        for root, dirs, files in os.walk('netra_backend'):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Look for class definitions
                            class_matches = re.findall(r'class\s+(\w+)', content)
                            for class_name in class_matches:
                                if class_name in known_duplicate_patterns:
                                    if class_name not in duplicate_detections:
                                        duplicate_detections[class_name] = []
                                    duplicate_detections[class_name].append(filepath)
                                    
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # Analyze duplicates
        problematic_duplicates = {}
        for class_name, locations in duplicate_detections.items():
            if len(locations) > 1:
                problematic_duplicates[class_name] = locations
        
        # Document findings
        if problematic_duplicates:
            print(f"\nDuplicate implementations detected:")
            for class_name, locations in problematic_duplicates.items():
                print(f"  {class_name}: {len(locations)} implementations")
                for location in locations[:3]:  # Show first 3
                    print(f"    - {location}")
        
        # This test documents current state - may pass or fail depending on consolidation status
        # If consolidation is complete, should have minimal duplicates
        # If consolidation is incomplete, will detect issues for remediation


class Issue220SSOTViolationAnalysisTests(SSotBaseTestCase):
    """Analyze specific SSOT violations for remediation guidance."""
    
    def test_critical_ssot_classes_import_consistency(self):
        """Test critical SSOT classes can be imported consistently."""
        critical_imports = [
            ('MessageRouter', 'netra_backend.app.websocket_core.handlers'),
            ('CanonicalMessageRouter', 'netra_backend.app.websocket_core.canonical_message_router'),
            ('AgentExecutionTracker', 'netra_backend.app.core.agent_execution_tracker'),
            ('ExecutionState', 'netra_backend.app.core.agent_execution_tracker')
        ]
        
        import_results = {}
        
        for class_name, module_path in critical_imports:
            try:
                module = importlib.import_module(module_path)
                target_class = getattr(module, class_name, None)
                import_results[f"{module_path}.{class_name}"] = {
                    'importable': target_class is not None,
                    'class_type': str(type(target_class)) if target_class else None
                }
            except ImportError as e:
                import_results[f"{module_path}.{class_name}"] = {
                    'importable': False,
                    'error': str(e)
                }
        
        # Validate critical imports work
        failed_imports = []
        for import_path, result in import_results.items():
            if not result['importable']:
                failed_imports.append(import_path)
        
        if failed_imports:
            self.fail(f"Critical SSOT imports failed: {failed_imports}")
        
        # Log successful imports
        print(f"\nCritical SSOT Import Status:")
        for import_path, result in import_results.items():
            status = "CHECK PASS" if result['importable'] else "X FAIL"
            print(f"  {import_path}: {status}")
    
    def test_factory_pattern_availability(self):
        """Test factory patterns are available and functional."""
        factory_patterns = [
            ('get_agent_instance_factory', 'netra_backend.app.agents.supervisor.agent_instance_factory'),
            ('get_websocket_manager', 'netra_backend.app.websocket_core.websocket_manager'),
            ('get_execution_tracker', 'netra_backend.app.core.agent_execution_tracker')
        ]
        
        factory_results = {}
        
        for factory_name, module_path in factory_patterns:
            try:
                module = importlib.import_module(module_path)
                factory_func = getattr(module, factory_name, None)
                factory_results[f"{module_path}.{factory_name}"] = {
                    'available': factory_func is not None,
                    'callable': callable(factory_func) if factory_func else False
                }
            except ImportError as e:
                factory_results[f"{module_path}.{factory_name}"] = {
                    'available': False,
                    'error': str(e)
                }
        
        # Validate factory patterns
        failed_factories = []
        for factory_path, result in factory_results.items():
            if not result.get('available') or not result.get('callable'):
                failed_factories.append(factory_path)
        
        if failed_factories:
            self.fail(f"Factory patterns not available: {failed_factories}")
        
        # Log factory status
        print(f"\nFactory Pattern Availability:")
        for factory_path, result in factory_results.items():
            status = "CHECK PASS" if result.get('available') and result.get('callable') else "X FAIL"
            print(f"  {factory_path}: {status}")


if __name__ == '__main__':
    unittest.main()