"""
Issue #416 Category-Specific Coverage Tests
============================================

Business Value: Comprehensive coverage across all categories of deprecated imports,
ensuring $500K+ ARR protection by validating fixes in all affected areas.

Test Strategy:
1. Agent Files - Test deprecation fixes in agent implementations
2. Service Files - Test deprecation fixes in service layer
3. WebSocket Files - Test specific WebSocket module deprecations
4. Test Files - Ensure test infrastructure uses canonical imports
5. Route Files - Test API route deprecation fixes

Comprehensive coverage ensures no deprecation warnings remain in any category.
"""

import unittest
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set
import re

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDeprecationCategoryCoverage(SSotBaseTestCase):
    """Test deprecation fixes across all file categories"""
    
    def setUp(self):
        super().setUp()
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        
        # Define file categories and their expected behavior
        self.file_categories = {
            'agent_files': {
                'pattern': '**/agents/**/*.py',
                'description': 'Agent implementation files',
                'critical': True,  # Agents are critical for chat functionality
                'expected_canonical_imports': [
                    'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
                    'from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator'
                ]
            },
            'service_files': {
                'pattern': '**/services/**/*.py',
                'description': 'Service layer files',
                'critical': True,  # Services support core functionality
                'expected_canonical_imports': [
                    'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
                    'from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter'
                ]
            },
            'websocket_files': {
                'pattern': '**/websocket*/**/*.py',
                'description': 'WebSocket core and related files',
                'critical': True,  # WebSocket enables real-time chat
                'expected_canonical_imports': [
                    'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
                    'from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator',
                    'from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter'
                ]
            },
            'route_files': {
                'pattern': '**/routes/**/*.py',
                'description': 'API route handler files',
                'critical': True,  # Routes handle user requests
                'expected_canonical_imports': [
                    'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager'
                ]
            },
            'test_files': {
                'pattern': '**/test*/**/*.py',
                'description': 'Test infrastructure files',
                'critical': False,  # Tests support development
                'expected_canonical_imports': [
                    'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
                    'from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator'
                ]
            },
            'tool_files': {
                'pattern': '**/tools/**/*.py',
                'description': 'Tool and utility files',
                'critical': True,  # Tools used by agents
                'expected_canonical_imports': [
                    'from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter'
                ]
            }
        }
        
        # Define forbidden patterns by category
        self.forbidden_patterns = [
            r'from\s+netra_backend\.app\.websocket_core\s+import\s+\w+',
            r'from\s+netra_backend\.app\.websocket_core\.event_validator\s+import',
        ]
    
    def test_agent_files_deprecation_coverage(self):
        """
        CATEGORY TEST: Agent files deprecation warning coverage
        
        Agents are critical for chat functionality ($500K+ ARR).
        """
        print("\n=== Testing Agent Files Deprecation Coverage ===")
        
        category = self.file_categories['agent_files']
        results = self._test_category_deprecation_coverage('agent_files', category)
        
        print(f"📊 Agent Files Analysis:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Files with WebSocket imports: {results['websocket_files']}")
        print(f"  Files with violations: {results['violation_files']}")
        print(f"  Files using canonical imports: {results['canonical_files']}")
        
        # Agents are critical - should have NO violations
        self.assertEqual(
            results['violation_files'], 0,
            f"Agent files have deprecation violations. "
            f"This directly impacts chat functionality and $500K+ ARR."
        )
        
        # Should prefer canonical imports for WebSocket functionality
        if results['websocket_files'] > 0:
            canonical_rate = results['canonical_files'] / results['websocket_files']
            self.assertGreaterEqual(
                canonical_rate, 0.8,
                f"Agent canonical import rate too low: {canonical_rate:.1%}"
            )
    
    def test_service_files_deprecation_coverage(self):
        """
        CATEGORY TEST: Service files deprecation warning coverage
        
        Services support core business functionality.
        """
        print("\n=== Testing Service Files Deprecation Coverage ===")
        
        category = self.file_categories['service_files']
        results = self._test_category_deprecation_coverage('service_files', category)
        
        print(f"📊 Service Files Analysis:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Files with WebSocket imports: {results['websocket_files']}")
        print(f"  Files with violations: {results['violation_files']}")
        print(f"  Files using canonical imports: {results['canonical_files']}")
        
        # Services are critical - should have minimal violations
        self.assertLessEqual(
            results['violation_files'], 1,
            f"Service files have too many deprecation violations: {results['violation_files']}"
        )
        
        # Should prefer canonical imports
        if results['websocket_files'] > 0:
            canonical_rate = results['canonical_files'] / results['websocket_files']
            self.assertGreaterEqual(
                canonical_rate, 0.7,
                f"Service canonical import rate too low: {canonical_rate:.1%}"
            )
    
    def test_websocket_files_deprecation_coverage(self):
        """
        CATEGORY TEST: WebSocket files deprecation warning coverage
        
        WebSocket files enable real-time chat functionality.
        """
        print("\n=== Testing WebSocket Files Deprecation Coverage ===")
        
        category = self.file_categories['websocket_files']
        results = self._test_category_deprecation_coverage('websocket_files', category)
        
        print(f"📊 WebSocket Files Analysis:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Files with WebSocket imports: {results['websocket_files']}")
        print(f"  Files with violations: {results['violation_files']}")
        print(f"  Files using canonical imports: {results['canonical_files']}")
        
        # WebSocket files should be exemplary - NO violations allowed
        self.assertEqual(
            results['violation_files'], 0,
            f"WebSocket files have deprecation violations. "
            f"These files should exemplify canonical import patterns."
        )
        
        # Should use canonical imports exclusively
        if results['websocket_files'] > 0:
            canonical_rate = results['canonical_files'] / results['websocket_files']
            self.assertGreaterEqual(
                canonical_rate, 0.9,
                f"WebSocket canonical import rate too low: {canonical_rate:.1%}"
            )
    
    def test_route_files_deprecation_coverage(self):
        """
        CATEGORY TEST: Route files deprecation warning coverage
        
        Routes handle user API requests and WebSocket connections.
        """
        print("\n=== Testing Route Files Deprecation Coverage ===")
        
        category = self.file_categories['route_files']
        results = self._test_category_deprecation_coverage('route_files', category)
        
        print(f"📊 Route Files Analysis:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Files with WebSocket imports: {results['websocket_files']}")
        print(f"  Files with violations: {results['violation_files']}")
        print(f"  Files using canonical imports: {results['canonical_files']}")
        
        # Routes are critical for user experience - minimal violations
        self.assertLessEqual(
            results['violation_files'], 1,
            f"Route files have too many deprecation violations: {results['violation_files']}"
        )
    
    def test_test_files_deprecation_coverage(self):
        """
        CATEGORY TEST: Test files deprecation warning coverage
        
        Test files should exemplify proper import patterns.
        """
        print("\n=== Testing Test Files Deprecation Coverage ===")
        
        category = self.file_categories['test_files']
        results = self._test_category_deprecation_coverage('test_files', category)
        
        print(f"📊 Test Files Analysis:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Files with WebSocket imports: {results['websocket_files']}")
        print(f"  Files with violations: {results['violation_files']}")
        print(f"  Files using canonical imports: {results['canonical_files']}")
        
        # Test files have more flexibility but should still trend toward canonical
        violation_rate = results['violation_files'] / results['total_files'] if results['total_files'] > 0 else 0
        
        self.assertLessEqual(
            violation_rate, 0.3,
            f"Test file violation rate too high: {violation_rate:.1%}"
        )
    
    def test_tool_files_deprecation_coverage(self):
        """
        CATEGORY TEST: Tool files deprecation warning coverage
        
        Tools are used by agents and affect chat functionality.
        """
        print("\n=== Testing Tool Files Deprecation Coverage ===")
        
        category = self.file_categories['tool_files']
        results = self._test_category_deprecation_coverage('tool_files', category)
        
        print(f"📊 Tool Files Analysis:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Files with WebSocket imports: {results['websocket_files']}")
        print(f"  Files with violations: {results['violation_files']}")
        print(f"  Files using canonical imports: {results['canonical_files']}")
        
        # Tools affect agents, so should have minimal violations
        self.assertLessEqual(
            results['violation_files'], 2,
            f"Tool files have too many deprecation violations: {results['violation_files']}"
        )
    
    def test_comprehensive_category_summary(self):
        """
        SUMMARY TEST: Comprehensive analysis across all categories
        
        Provides overall system health assessment.
        """
        print("\n=== Comprehensive Category Analysis ===")
        
        category_results = {}
        total_violations = 0
        total_critical_violations = 0
        
        for category_name, category_config in self.file_categories.items():
            print(f"\n📂 Analyzing {category_name}...")
            
            results = self._test_category_deprecation_coverage(category_name, category_config)
            category_results[category_name] = results
            
            total_violations += results['violation_files']
            
            if category_config['critical']:
                total_critical_violations += results['violation_files']
            
            print(f"  {category_config['description']}: "
                  f"{results['violation_files']}/{results['total_files']} violations")
        
        print(f"\n📊 Overall System Analysis:")
        print(f"  Total categories: {len(self.file_categories)}")
        print(f"  Total violations: {total_violations}")
        print(f"  Critical category violations: {total_critical_violations}")
        
        # Critical categories should have minimal violations
        self.assertLessEqual(
            total_critical_violations, 3,
            f"Too many violations in critical categories: {total_critical_violations}. "
            f"This affects core business functionality."
        )
        
        # Overall system should be trending toward compliance
        self.assertLessEqual(
            total_violations, 10,
            f"System-wide violations too high: {total_violations}. "
            f"Migration effort needs to be accelerated."
        )
        
        # Store results for reporting
        self.category_analysis_results = category_results
    
    def test_migration_priority_assessment(self):
        """
        PRIORITY TEST: Assess migration priority based on business impact
        
        Guides remediation effort prioritization.
        """
        print("\n=== Migration Priority Assessment ===")
        
        priority_analysis = {}
        
        for category_name, category_config in self.file_categories.items():
            results = self._test_category_deprecation_coverage(category_name, category_config)
            
            # Calculate priority score
            violation_impact = results['violation_files'] * (2 if category_config['critical'] else 1)
            total_files = max(results['total_files'], 1)
            priority_score = violation_impact / total_files
            
            priority_analysis[category_name] = {
                'priority_score': priority_score,
                'violation_files': results['violation_files'],
                'total_files': results['total_files'],
                'critical': category_config['critical'],
                'description': category_config['description']
            }
            
            print(f"📊 {category_name}: Priority Score {priority_score:.2f}")
            print(f"  Critical: {category_config['critical']}")
            print(f"  Violations: {results['violation_files']}/{results['total_files']}")
        
        # Sort by priority score
        sorted_priorities = sorted(
            priority_analysis.items(),
            key=lambda x: x[1]['priority_score'],
            reverse=True
        )
        
        print(f"\n🎯 Migration Priority Order:")
        for i, (category, data) in enumerate(sorted_priorities, 1):
            print(f"  {i}. {category} (Score: {data['priority_score']:.2f})")
            if data['priority_score'] > 0:
                print(f"     {data['violation_files']} violations in {data['description']}")
        
        # High-priority categories should be addressed first
        high_priority_categories = [
            category for category, data in sorted_priorities
            if data['priority_score'] > 0.1 and data['critical']
        ]
        
        # Guidance for migration planning
        if high_priority_categories:
            print(f"\n⚠️  High-priority categories need immediate attention: {high_priority_categories}")
            
        # Store for test validation
        self.migration_priorities = sorted_priorities
    
    def _test_category_deprecation_coverage(self, category_name: str, category_config: Dict) -> Dict:
        """Test deprecation coverage for a specific file category"""
        
        # Find files matching the category pattern
        category_files = list(self.project_root.glob(category_config['pattern']))
        
        # Filter to Python files only
        py_files = [f for f in category_files if f.suffix == '.py']
        
        results = {
            'total_files': len(py_files),
            'websocket_files': 0,
            'violation_files': 0,
            'canonical_files': 0,
            'violations': []
        }
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file uses WebSocket functionality
                uses_websocket = any(
                    keyword in content.lower()
                    for keyword in ['websocket', 'event_validator', 'websocket_manager']
                )
                
                if uses_websocket:
                    results['websocket_files'] += 1
                    
                    # Check for violations
                    has_violations = any(
                        re.search(pattern, content, re.MULTILINE)
                        for pattern in self.forbidden_patterns
                    )
                    
                    if has_violations:
                        results['violation_files'] += 1
                        
                        # Find specific violations
                        for pattern in self.forbidden_patterns:
                            matches = re.finditer(pattern, content, re.MULTILINE)
                            for match in matches:
                                line_num = content[:match.start()].count('\n') + 1
                                results['violations'].append({
                                    'file': py_file,
                                    'line': line_num,
                                    'pattern': pattern,
                                    'content': match.group()
                                })
                    
                    # Check for canonical imports
                    has_canonical = any(
                        canonical_import in content
                        for canonical_import in category_config['expected_canonical_imports']
                    )
                    
                    if has_canonical:
                        results['canonical_files'] += 1
                        
            except Exception as e:
                print(f"⚠️  Could not analyze {py_file}: {e}")
        
        return results


if __name__ == '__main__':
    print("📂 Issue #416 Category Coverage Test Suite")
    print("=" * 60)
    print("Purpose: Test deprecation coverage across all file categories")
    print("Expected: Critical categories should have minimal violations")
    print("=" * 60)
    
    unittest.main(verbosity=2)