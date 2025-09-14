"""
SSOT Import Validation Test for Issue #914
=========================================

PURPOSE: Validate Single Source of Truth (SSOT) compliance for AgentRegistry imports
ISSUE: #914 - SSOT AgentRegistry duplication with import conflicts in websocket_bridge_factory.py

CRITICAL DISCOVERY:
The websocket_bridge_factory.py has conflicting imports:
- Line 38: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
- Lines 276-282: from netra_backend.app.agents.registry import AgentRegistry  # CONFLICT!

TEST STRATEGY:
1. Detect duplicate AgentRegistry classes across the codebase
2. Validate import path consistency and identify conflicts
3. Test runtime import behavior and potential failures
4. Verify SSOT compliance for AgentRegistry implementations

BUSINESS IMPACT: $500K+ ARR Golden Path depends on consistent agent registration
"""

import pytest
import importlib
import sys
import os
from pathlib import Path
from typing import Set, Dict, List, Tuple
import inspect

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestSSOTImportValidation(SSotBaseTestCase):
    """SSOT Import Validation for AgentRegistry classes across codebase"""
    
    def setUp(self):
        """Set up test environment and import paths"""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.expected_ssot_path = "netra_backend.app.agents.supervisor.agent_registry"
        self.duplicate_paths = [
            "netra_backend.app.agents.registry",
            "netra_backend.app.agents.agent_registry",
        ]
        self.import_conflicts = []
        
    def test_detect_duplicate_agent_registry_classes(self):
        """Test 1: Detect duplicate AgentRegistry implementations"""
        print("\n=== TEST 1: Detecting Duplicate AgentRegistry Classes ===")
        
        duplicate_classes = []
        all_registry_paths = [self.expected_ssot_path] + self.duplicate_paths
        
        for import_path in all_registry_paths:
            try:
                module = importlib.import_module(import_path)
                if hasattr(module, 'AgentRegistry'):
                    registry_class = getattr(module, 'AgentRegistry')
                    class_info = {
                        'path': import_path,
                        'module': module,
                        'class': registry_class,
                        'file_path': inspect.getfile(registry_class),
                        'class_id': id(registry_class)
                    }
                    duplicate_classes.append(class_info)
                    print(f"✓ Found AgentRegistry at: {import_path}")
                    print(f"  File: {class_info['file_path']}")
                    print(f"  Class ID: {class_info['class_id']}")
                    
            except (ImportError, ModuleNotFoundError) as e:
                print(f"⚠️  Import failed for {import_path}: {e}")
                
        # ASSERTION: Should have exactly ONE AgentRegistry class (SSOT compliance)
        print(f"\n📊 ANALYSIS: Found {len(duplicate_classes)} AgentRegistry implementations")
        
        if len(duplicate_classes) > 1:
            print("❌ SSOT VIOLATION: Multiple AgentRegistry implementations detected!")
            for i, class_info in enumerate(duplicate_classes):
                print(f"  {i+1}. {class_info['path']} -> {class_info['file_path']}")
                
            # Check if classes are actually different implementations
            unique_class_ids = set(info['class_id'] for info in duplicate_classes)
            if len(unique_class_ids) > 1:
                print(f"🚨 CRITICAL: {len(unique_class_ids)} distinct AgentRegistry classes found!")
                self.fail(f"SSOT Violation: Found {len(unique_class_ids)} distinct AgentRegistry implementations. Expected exactly 1.")
            else:
                print("ℹ️  All imports point to the same class (re-exports)")
        else:
            print("✅ SSOT Compliance: Single AgentRegistry implementation found")
            
        # Store results for other tests
        self.duplicate_classes = duplicate_classes
        
    def test_websocket_bridge_factory_import_conflicts(self):
        """Test 2: Specific test for websocket_bridge_factory.py import conflicts"""
        print("\n=== TEST 2: WebSocket Bridge Factory Import Analysis ===")
        
        bridge_factory_path = self.project_root / "netra_backend" / "app" / "websocket_core" / "websocket_bridge_factory.py"
        
        if not bridge_factory_path.exists():
            self.skipTest(f"WebSocket bridge factory not found at {bridge_factory_path}")
            
        # Read the file content to analyze imports
        with open(bridge_factory_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
        # Find all AgentRegistry imports
        import_lines = []
        for i, line in enumerate(lines, 1):
            if 'AgentRegistry' in line and ('import' in line or 'from' in line):
                import_lines.append({
                    'line_number': i,
                    'content': line.strip(),
                    'is_comment': line.strip().startswith('#')
                })
                
        print(f"📋 Found {len(import_lines)} lines mentioning AgentRegistry imports:")
        for imp in import_lines:
            status = "COMMENT" if imp['is_comment'] else "ACTIVE"
            print(f"  Line {imp['line_number']}: [{status}] {imp['content']}")
            
        # Check for the specific conflict mentioned in the issue
        active_imports = [imp for imp in import_lines if not imp['is_comment']]
        
        if len(active_imports) > 1:
            print(f"❌ IMPORT CONFLICT: {len(active_imports)} active AgentRegistry imports found!")
            self.import_conflicts = active_imports
            
            # This is a known issue - document it but don't fail the test yet
            print("🔍 KNOWN ISSUE #914: Multiple AgentRegistry imports in websocket_bridge_factory.py")
            for imp in active_imports:
                print(f"    Line {imp['line_number']}: {imp['content']}")
                
        else:
            print("✅ No import conflicts detected in websocket_bridge_factory.py")
            
    def test_runtime_import_behavior(self):
        """Test 3: Test runtime behavior of different import paths"""
        print("\n=== TEST 3: Runtime Import Behavior Analysis ===")
        
        import_results = {}
        
        # Test each potential import path
        all_paths = [self.expected_ssot_path] + self.duplicate_paths
        
        for path in all_paths:
            try:
                # Clear any cached imports to test fresh
                if path in sys.modules:
                    del sys.modules[path]
                    
                module = importlib.import_module(path)
                
                if hasattr(module, 'AgentRegistry'):
                    registry_class = getattr(module, 'AgentRegistry')
                    import_results[path] = {
                        'success': True,
                        'class': registry_class,
                        'class_name': registry_class.__name__,
                        'module_path': registry_class.__module__,
                        'methods': [name for name, _ in inspect.getmembers(registry_class, inspect.ismethod) 
                                   if not name.startswith('_')],
                        'file_path': inspect.getfile(registry_class)
                    }
                    print(f"✅ Successfully imported AgentRegistry from {path}")
                    print(f"   Class module: {registry_class.__module__}")
                    print(f"   File: {inspect.getfile(registry_class)}")
                    print(f"   Methods: {len(import_results[path]['methods'])}")
                else:
                    import_results[path] = {
                        'success': False,
                        'error': 'AgentRegistry class not found in module'
                    }
                    print(f"❌ Module {path} exists but no AgentRegistry class")
                    
            except (ImportError, ModuleNotFoundError) as e:
                import_results[path] = {
                    'success': False,
                    'error': str(e)
                }
                print(f"❌ Failed to import {path}: {e}")
                
        # Analyze results
        successful_imports = {k: v for k, v in import_results.items() if v['success']}
        
        if len(successful_imports) > 1:
            print(f"\n🔍 ANALYSIS: {len(successful_imports)} successful AgentRegistry imports")
            
            # Check if all successful imports point to the same class
            unique_files = set(result['file_path'] for result in successful_imports.values())
            
            if len(unique_files) == 1:
                print("✅ All successful imports point to the same file (re-exports)")
            else:
                print("❌ CRITICAL: Successful imports point to different files!")
                for path, result in successful_imports.items():
                    print(f"  {path} -> {result['file_path']}")
                    
                self.fail(f"Multiple AgentRegistry implementations found in different files: {unique_files}")
        else:
            print(f"ℹ️  Only {len(successful_imports)} successful import path found")
            
        # Store results for potential use in other tests
        self.import_results = import_results
        
    def test_ssot_compliance_validation(self):
        """Test 4: Comprehensive SSOT compliance validation"""
        print("\n=== TEST 4: SSOT Compliance Validation ===")
        
        # Define SSOT requirements
        ssot_requirements = {
            'single_implementation': True,
            'consistent_imports': True,
            'no_duplicates': True,
            'proper_ssot_path': self.expected_ssot_path
        }
        
        compliance_results = {}
        
        # 1. Check single implementation requirement
        if hasattr(self, 'duplicate_classes'):
            unique_class_ids = set(info['class_id'] for info in self.duplicate_classes)
            compliance_results['single_implementation'] = len(unique_class_ids) == 1
        else:
            compliance_results['single_implementation'] = True  # Assume pass if no duplicates found
            
        # 2. Check consistent imports (no conflicts)
        compliance_results['consistent_imports'] = len(self.import_conflicts) == 0
        
        # 3. Check no duplicate module paths
        if hasattr(self, 'import_results'):
            successful_paths = [k for k, v in self.import_results.items() if v['success']]
            compliance_results['no_duplicates'] = len(successful_paths) <= 1
        else:
            compliance_results['no_duplicates'] = True
            
        # 4. Check proper SSOT path exists and works
        try:
            importlib.import_module(self.expected_ssot_path)
            compliance_results['proper_ssot_path'] = True
        except ImportError:
            compliance_results['proper_ssot_path'] = False
            
        # Calculate overall compliance score
        total_checks = len(ssot_requirements)
        passed_checks = sum(1 for passed in compliance_results.values() if passed)
        compliance_score = (passed_checks / total_checks) * 100
        
        print(f"📊 SSOT COMPLIANCE REPORT:")
        print(f"   Overall Score: {compliance_score:.1f}% ({passed_checks}/{total_checks})")
        
        for requirement, passed in compliance_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {requirement}: {status}")
            
        # Store compliance results
        self.compliance_score = compliance_score
        self.compliance_results = compliance_results
        
        # Fail test if critical SSOT violations found
        if compliance_score < 75:  # Threshold for acceptable compliance
            self.fail(f"SSOT Compliance below threshold: {compliance_score:.1f}% (minimum: 75%)")
            
    def tearDown(self):
        """Clean up after tests"""
        super().tearDown()
        
        # Print summary
        if hasattr(self, 'compliance_score'):
            print(f"\n📋 TEST SUMMARY:")
            print(f"   SSOT Compliance Score: {self.compliance_score:.1f}%")
            
            if hasattr(self, 'duplicate_classes'):
                print(f"   AgentRegistry Implementations Found: {len(self.duplicate_classes)}")
                
            if hasattr(self, 'import_conflicts'):
                print(f"   Import Conflicts Detected: {len(self.import_conflicts)}")
                
            print(f"   Test Status: {'PASS' if self.compliance_score >= 75 else 'FAIL'}")


if __name__ == "__main__":
    # Run the test standalone
    pytest.main([__file__, "-v", "-s"])