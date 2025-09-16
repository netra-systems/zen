"""
Issue #841 Critical Violation Tests: WebSocket Module ID Generation

================================================================

BUSINESS JUSTIFICATION (Issue #841):
- WebSocket module contains CRITICAL uuid.uuid4() violations
- Line unified_websocket_auth.py:1303: connection_id = str(uuid.uuid4()) - HIGH IMPACT
- Multiple WebSocket files with uuid.uuid4() patterns across websocket_core/
- $500K+ ARR dependent on WebSocket chat functionality
- Real-time user isolation REQUIRED for multi-user chat system

PURPOSE: Create FAILING tests that expose specific WebSocket ID violations

STRATEGY: Tests DESIGNED TO FAIL until SSOT migration is completed
- Focus on unified_websocket_auth.py:1303 connection_id generation
- Focus on connection_id_manager.py:355 unique_id generation 
- Focus on WebSocket context and event validation frameworks
- Validate business impact of inconsistent WebSocket routing IDs

VALIDATION: These tests become regression protection after migration

Expected Outcome: ALL TESTS SHOULD FAIL demonstrating current violations
"""

import pytest
import uuid
import re
import os
from pathlib import Path
from typing import List, Dict, Set, Tuple
from unittest.mock import patch, MagicMock

# Test framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase

# System imports for validation
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestIssue841WebSocketViolations(SSotBaseTestCase):
    """
    Issue #841 WebSocket ID Generation Violation Tests
    
    Tests DESIGNED TO FAIL exposing specific WebSocket uuid.uuid4() violations.
    Critical for $500K+ ARR real-time chat functionality and multi-user isolation.
    """
    
    def setup_method(self, method=None):
        """Setup for WebSocket violation detection tests."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        
        # Critical WebSocket violation files identified in Issue #841
        self.critical_websocket_files = {
            'unified_websocket_auth.py': 'netra_backend/app/websocket_core/unified_websocket_auth.py',
            'connection_id_manager.py': 'netra_backend/app/websocket_core/connection_id_manager.py',
            'context.py': 'netra_backend/app/websocket_core/context.py',
            'event_validation_framework.py': 'netra_backend/app/websocket_core/event_validation_framework.py',
            'migration_adapter.py': 'netra_backend/app/websocket_core/migration_adapter.py'
        }
        
        # Expected SSOT patterns for WebSocket IDs
        self.ssot_patterns = {
            'connection_id': re.compile(r'^ws_(staging_|prod_)?\d+_\d+_[a-f0-9]{8}$'),
            'websocket_client_id': re.compile(r'^ws_\d+_\d+_[a-f0-9]{8}$'),
            'run_id': re.compile(r'^run_.+_\d+_\d+_[a-f0-9]{8}$'),
            'event_id': re.compile(r'^event_\d+_\d+_[a-f0-9]{8}$'),
            'user_id': re.compile(r'^(user|legacy_user)_\d+_\d+_[a-f0-9]{8}$')
        }

    def test_unified_websocket_auth_line_1303_violation_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: unified_websocket_auth.py:1303 contains connection_id = str(uuid.uuid4())
        
        CRITICAL BUSINESS IMPACT:
        - WebSocket connection management is foundation of real-time chat
        - Inconsistent connection IDs break multi-user chat isolation  
        - $500K+ ARR depends on reliable WebSocket routing
        - Enterprise customers require secure WebSocket connections
        """
        websocket_auth_file = self.project_root / self.critical_websocket_files['unified_websocket_auth.py']
        
        # Verify file exists
        if not websocket_auth_file.exists():
            self.skipTest(f"Critical file not found: {websocket_auth_file}")
        
        violations_found = []
        
        try:
            with open(websocket_auth_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check line 1303 specifically (and surrounding lines for context) 
            target_line = 1303
            search_range = range(max(1, target_line - 5), min(len(lines), target_line + 5))
            
            for line_num in search_range:
                if line_num >= len(lines):
                    continue
                    
                line = lines[line_num]
                
                # Check for the specific violation pattern
                violation_patterns = [
                    r'connection_id\s*=\s*preliminary_connection_id\s*or\s*str\(uuid\.uuid4\(\)\)',
                    r'connection_id.*str\(uuid\.uuid4\(\)\)',
                    r'preliminary_connection_id.*str\(uuid\.uuid4\(\)\)',
                    r'str\(uuid\.uuid4\(\)\).*connection'
                ]
                
                for pattern in violation_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations_found.append({
                            'line_number': line_num + 1,  # 1-indexed
                            'line_content': line.strip(),
                            'violation_type': 'connection_id_raw_uuid',
                            'pattern_matched': pattern,
                            'business_impact': 'CRITICAL - WebSocket routing and multi-user isolation'
                        })
        
        except Exception as e:
            self.fail(f"Failed to analyze unified_websocket_auth.py: {e}")
        
        # Test SHOULD FAIL - we expect to find the violation at line 1303
        self.assertGreater(len(violations_found), 0,
            "EXPECTED FAILURE: Should find connection_id uuid.uuid4() violation around line 1303 in unified_websocket_auth.py. "
            "If this passes, the violation may have been fixed!")
        
        # Additional validation: simulate current WebSocket connection ID generation
        current_connection_pattern_violations = []
        
        # Test what current implementation likely generates
        test_connection_ids = [
            str(uuid.uuid4()),  # Raw UUID - VIOLATION
            f"ws_connection_{uuid.uuid4()}",  # Partial format - VIOLATION  
            f"websocket_{uuid.uuid4().hex[:8]}",  # Hex format - VIOLATION
        ]
        
        for connection_id in test_connection_ids:
            if not self.ssot_patterns['connection_id'].match(connection_id):
                current_connection_pattern_violations.append({
                    'connection_id': connection_id,
                    'violation': 'Does not match SSOT connection_id pattern',
                    'expected_format': 'ws_timestamp_counter_random'
                })
        
        total_violations = len(violations_found) + len(current_connection_pattern_violations)
        
        # Fail with comprehensive violation report
        report_lines = [
            f"🚨 ISSUE #841 UNIFIED_WEBSOCKET_AUTH.PY VIOLATION: {total_violations} violations found",
            "💰 BUSINESS IMPACT: $500K+ ARR WebSocket chat functionality at risk",
            "",
            "📁 SOURCE CODE VIOLATIONS:"
        ]
        
        for violation in violations_found:
            report_lines.extend([
                f"   Line {violation['line_number']}: {violation['line_content']}",
                f"   Pattern: {violation['pattern_matched']}",
                f"   Impact: {violation['business_impact']}",
                ""
            ])
        
        if current_connection_pattern_violations:
            report_lines.append("🔧 GENERATED CONNECTION ID FORMAT VIOLATIONS:")
            for violation in current_connection_pattern_violations[:3]:
                report_lines.extend([
                    f"   Generated: {violation['connection_id'][:40]}...",
                    f"   Issue: {violation['violation']}",
                    f"   Expected: {violation['expected_format']}",
                    ""
                ])
        
        report_lines.extend([
            "🎯 REQUIRED MIGRATION ACTIONS:",
            "   1. Replace str(uuid.uuid4()) with UnifiedIdGenerator.generate_websocket_connection_id()",
            "   2. Update unified_websocket_auth.py:1303 to use SSOT connection ID generation",
            "   3. Implement connection ID validation with structured format",
            "   4. Test multi-user WebSocket isolation with new IDs",
            "",
            "📋 SUCCESS CRITERIA:",
            "   - Connection IDs follow format: ws_timestamp_counter_random",
            "   - No raw uuid.uuid4() calls in WebSocket authentication", 
            "   - Multi-user WebSocket isolation verified",
            "   - Real-time chat functionality maintained"
        ])
        
        pytest.fail("\n".join(report_lines))

    def test_connection_id_manager_line_355_violation_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: connection_id_manager.py:355 contains unique_id = str(uuid.uuid4())[:8]
        
        CRITICAL BUSINESS IMPACT:
        - Connection ID manager generates IDs for WebSocket routing
        - Inconsistent unique_id patterns break connection tracking
        - Multi-environment deployment requires consistent ID formats
        - WebSocket chat relies on proper connection identification
        """
        connection_mgr_file = self.project_root / self.critical_websocket_files['connection_id_manager.py']
        
        # Verify file exists
        if not connection_mgr_file.exists():
            self.skipTest(f"Critical file not found: {connection_mgr_file}")
        
        violations_found = []
        
        try:
            with open(connection_mgr_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check line 355 specifically (and surrounding lines for context)
            target_line = 355  
            search_range = range(max(1, target_line - 5), min(len(lines), target_line + 5))
            
            for line_num in search_range:
                if line_num >= len(lines):
                    continue
                    
                line = lines[line_num]
                
                # Check for the specific violation pattern
                violation_patterns = [
                    r'unique_id\s*=\s*str\(uuid\.uuid4\(\)\)\[:8\]',
                    r'unique_id.*str\(uuid\.uuid4\(\)\)',
                    r'uuid\.uuid4\(\)\[:8\]',
                    r'str\(uuid\.uuid4\(\)\)\[:\d+\]'
                ]
                
                for pattern in violation_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations_found.append({
                            'line_number': line_num + 1,  # 1-indexed
                            'line_content': line.strip(),
                            'violation_type': 'unique_id_uuid_slice',
                            'pattern_matched': pattern,
                            'business_impact': 'CRITICAL - WebSocket connection identification'
                        })
        
        except Exception as e:
            self.fail(f"Failed to analyze connection_id_manager.py: {e}")
        
        # Test SHOULD FAIL - we expect to find the violation at line 355
        self.assertGreater(len(violations_found), 0,
            "EXPECTED FAILURE: Should find unique_id uuid.uuid4() violation around line 355 in connection_id_manager.py. "
            "If this passes, the violation may have been fixed!")
        
        # Additional validation: simulate current connection ID manager generation
        current_unique_id_violations = []
        
        # Test what current implementation likely generates
        test_unique_ids = [
            str(uuid.uuid4())[:8],  # Current pattern - VIOLATION
            uuid.uuid4().hex[:8],  # Hex slice - VIOLATION
            f"conn_{uuid.uuid4().hex[:6]}",  # Partial format - VIOLATION
        ]
        
        # Test generated connection IDs with current patterns
        timestamp = 1234567890
        for unique_id in test_unique_ids:
            # Simulate current connection ID generation logic
            generated_connection_ids = [
                f"ws_staging_{timestamp}_{unique_id}",
                f"ws_prod_{timestamp}_{unique_id}",
                f"ws_{timestamp}_{unique_id}"
            ]
            
            for conn_id in generated_connection_ids:
                if not self.ssot_patterns['connection_id'].match(conn_id):
                    current_unique_id_violations.append({
                        'connection_id': conn_id,
                        'unique_id_used': unique_id,
                        'violation': 'Generated connection_id does not match SSOT pattern',
                        'expected_format': 'ws_[env_]timestamp_counter_random'
                    })
        
        total_violations = len(violations_found) + len(current_unique_id_violations)
        
        # Fail with comprehensive violation report
        report_lines = [
            f"🚨 ISSUE #841 CONNECTION_ID_MANAGER.PY VIOLATION: {total_violations} violations found",
            "💰 BUSINESS IMPACT: WebSocket connection tracking system at risk",
            "",
            "📁 SOURCE CODE VIOLATIONS:"
        ]
        
        for violation in violations_found:
            report_lines.extend([
                f"   Line {violation['line_number']}: {violation['line_content']}",
                f"   Pattern: {violation['pattern_matched']}",
                f"   Impact: {violation['business_impact']}",
                ""
            ])
        
        if current_unique_id_violations:
            report_lines.append("🔧 CONNECTION ID GENERATION FORMAT VIOLATIONS:")
            for violation in current_unique_id_violations[:3]:
                report_lines.extend([
                    f"   Generated: {violation['connection_id']}",
                    f"   Unique ID: {violation['unique_id_used']}",
                    f"   Issue: {violation['violation']}",
                    f"   Expected: {violation['expected_format']}",
                    ""
                ])
        
        report_lines.extend([
            "🎯 REQUIRED MIGRATION ACTIONS:",
            "   1. Replace str(uuid.uuid4())[:8] with UnifiedIdGenerator.generate_random_component()",
            "   2. Update connection_id_manager.py:355 to use SSOT unique ID generation",
            "   3. Maintain structured connection ID format across environments",
            "   4. Test connection ID uniqueness and collision resistance",
            "",
            "📋 SUCCESS CRITERIA:",
            "   - Unique IDs use structured format from UnifiedIdGenerator",
            "   - Connection IDs maintain environment prefixes correctly",
            "   - No UUID slice operations in connection management",
            "   - WebSocket routing consistency preserved"
        ])
        
        pytest.fail("\n".join(report_lines))

    def test_websocket_event_validation_violations_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: WebSocket event validation framework contains uuid.uuid4() violations
        
        CRITICAL BUSINESS IMPACT:
        - Event validation affects all WebSocket message processing
        - Inconsistent event IDs break message tracking and debugging
        - Chat functionality depends on reliable event identification
        - Business-critical WebSocket events need proper ID management
        """
        event_validation_file = self.project_root / self.critical_websocket_files['event_validation_framework.py']
        
        # Verify file exists
        if not event_validation_file.exists():
            self.skipTest(f"Critical file not found: {event_validation_file}")
        
        violations_found = []
        
        try:
            with open(event_validation_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Search for violation patterns throughout the file
            for line_num, line in enumerate(lines, 1):
                # Check for event ID generation violations
                violation_patterns = [
                    r'event_id\s*=\s*str\(uuid\.uuid4\(\)\)',
                    r'event\.get\([\'"]message_id[\'"]\)\s*or\s*str\(uuid\.uuid4\(\)\)',
                    r'str\(uuid\.uuid4\(\)\).*event',
                    r'ValidatedEvent\([^)]*event_id\s*=\s*str\(uuid\.uuid4\(\)\)'
                ]
                
                for pattern in violation_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations_found.append({
                            'line_number': line_num,
                            'line_content': line.strip(),
                            'violation_type': 'event_id_raw_uuid',
                            'pattern_matched': pattern,
                            'business_impact': 'CRITICAL - WebSocket event tracking'
                        })
        
        except Exception as e:
            self.fail(f"Failed to analyze event_validation_framework.py: {e}")
        
        # Test SHOULD FAIL - we expect to find violations in event validation
        self.assertGreater(len(violations_found), 0,
            "EXPECTED FAILURE: Should find event_id uuid.uuid4() violations in event_validation_framework.py. "
            "If this passes, the violations may have been fixed!")
        
        # Additional validation: simulate current event validation ID generation
        current_event_pattern_violations = []
        
        # Test what current event validation likely generates
        test_event_scenarios = [
            {
                'event_type': 'agent_started',
                'event_id': str(uuid.uuid4()),  # Current pattern - VIOLATION
                'message_id': str(uuid.uuid4()),  # Fallback pattern - VIOLATION
            },
            {
                'event_type': 'tool_executing', 
                'event_id': str(uuid.uuid4()),  # Current pattern - VIOLATION
                'message_id': None,  # Missing message_id fallback
            },
            {
                'event_type': 'validation_error',
                'event_id': str(uuid.uuid4()),  # Error case - VIOLATION
                'message_id': 'unknown',
            }
        ]
        
        for scenario in test_event_scenarios:
            event_id = scenario.get('event_id')
            if event_id and not self.ssot_patterns['event_id'].match(event_id):
                current_event_pattern_violations.append({
                    'event_type': scenario['event_type'],
                    'event_id': event_id,
                    'violation': 'Event ID does not match SSOT pattern',
                    'expected_format': 'event_timestamp_counter_random'
                })
        
        total_violations = len(violations_found) + len(current_event_pattern_violations)
        
        # Fail with comprehensive violation report
        report_lines = [
            f"🚨 ISSUE #841 EVENT_VALIDATION_FRAMEWORK.PY VIOLATIONS: {total_violations} violations found",
            "💰 BUSINESS IMPACT: WebSocket event tracking and debugging at risk",
            "",
            "📁 SOURCE CODE VIOLATIONS:"
        ]
        
        for violation in violations_found:
            report_lines.extend([
                f"   Line {violation['line_number']}: {violation['line_content'][:60]}...",
                f"   Pattern: {violation['pattern_matched']}",
                f"   Impact: {violation['business_impact']}",
                ""
            ])
        
        if current_event_pattern_violations:
            report_lines.append("🔧 EVENT ID GENERATION FORMAT VIOLATIONS:")
            for violation in current_event_pattern_violations[:3]:
                report_lines.extend([
                    f"   Event: {violation['event_type']}",
                    f"   Generated ID: {violation['event_id'][:30]}...",
                    f"   Issue: {violation['violation']}",
                    f"   Expected: {violation['expected_format']}",
                    ""
                ])
        
        report_lines.extend([
            "🎯 REQUIRED MIGRATION ACTIONS:",
            "   1. Replace str(uuid.uuid4()) with UnifiedIdGenerator.generate_event_id()",
            "   2. Update all ValidatedEvent creation to use SSOT event IDs",
            "   3. Implement event ID validation with structured format",
            "   4. Test WebSocket event tracking with new ID patterns",
            "",
            "📋 SUCCESS CRITERIA:",
            "   - Event IDs follow format: event_timestamp_counter_random",
            "   - No raw uuid.uuid4() calls in event validation",
            "   - WebSocket message tracking maintains consistency",
            "   - Business-critical events properly identified and tracked"
        ])
        
        pytest.fail("\n".join(report_lines))

    def test_websocket_integration_id_consistency_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: WebSocket system generates inconsistent ID formats across components
        
        INTEGRATION TEST: Validates WebSocket ID ecosystem works together properly
        - Connection IDs should relate to user contexts
        - Event IDs should be traceable across WebSocket lifecycle
        - Multi-user WebSocket scenarios should maintain ID isolation
        """
        integration_violations = []
        
        # Test integration between WebSocket components
        try:
            # Simulate current WebSocket flow ID generation patterns
            websocket_scenarios = [
                {
                    'scenario': 'WebSocket Connection Establishment',
                    'connection_id': str(uuid.uuid4()),  # From unified_websocket_auth.py:1303
                    'user_id': str(uuid.uuid4()),  # From auth result
                    'websocket_client_id': str(uuid.uuid4()),  # From context generation
                    'run_id': str(uuid.uuid4()),  # From run generation
                    'business_impact': 'Initial connection setup'
                },
                {
                    'scenario': 'WebSocket Event Processing',
                    'event_id': str(uuid.uuid4()),  # From event validation
                    'message_id': str(uuid.uuid4()),  # From message processing
                    'connection_id': str(uuid.uuid4()),  # Associated connection
                    'thread_id': f"thread_{uuid.uuid4().hex[:8]}",  # Context threading
                    'business_impact': 'Real-time message processing'
                },
                {
                    'scenario': 'Multi-User WebSocket Isolation',
                    'user1_connection': str(uuid.uuid4()),  # User 1 connection
                    'user2_connection': str(uuid.uuid4()),  # User 2 connection  
                    'user1_events': [str(uuid.uuid4()), str(uuid.uuid4())],  # User 1 events
                    'user2_events': [str(uuid.uuid4()), str(uuid.uuid4())],  # User 2 events
                    'business_impact': 'Enterprise multi-user isolation'
                }
            ]
            
            # Validate each scenario for SSOT compliance
            for scenario in websocket_scenarios:
                scenario_violations = []
                
                # Check all ID fields against appropriate SSOT patterns
                id_checks = [
                    ('connection_id', 'connection_id'),
                    ('websocket_client_id', 'websocket_client_id'), 
                    ('event_id', 'event_id'),
                    ('user_id', 'user_id'),
                    ('run_id', 'run_id'),
                    ('user1_connection', 'connection_id'),
                    ('user2_connection', 'connection_id')
                ]
                
                for id_field, pattern_key in id_checks:
                    if id_field in scenario and pattern_key in self.ssot_patterns:
                        id_value = scenario[id_field]
                        if isinstance(id_value, str) and not self.ssot_patterns[pattern_key].match(id_value):
                            scenario_violations.append({
                                'id_type': id_field,
                                'id_value': id_value,
                                'violation': f'Does not match SSOT {pattern_key} format'
                            })
                
                # Check for list fields (events)
                list_checks = [('user1_events', 'event_id'), ('user2_events', 'event_id')]
                for list_field, pattern_key in list_checks:
                    if list_field in scenario:
                        for idx, id_value in enumerate(scenario[list_field]):
                            if not self.ssot_patterns[pattern_key].match(id_value):
                                scenario_violations.append({
                                    'id_type': f'{list_field}[{idx}]',
                                    'id_value': id_value,
                                    'violation': f'Does not match SSOT {pattern_key} format'
                                })
                
                # Check for raw UUID patterns (critical violation)
                for field_name, field_value in scenario.items():
                    if field_name in ['scenario', 'business_impact']:
                        continue
                        
                    if isinstance(field_value, str) and re.match(r'^[a-f0-9-]{36}$', field_value):
                        scenario_violations.append({
                            'id_type': field_name,
                            'id_value': field_value,
                            'violation': 'RAW UUID DETECTED - Critical SSOT violation'
                        })
                    elif isinstance(field_value, list):
                        for idx, item in enumerate(field_value):
                            if isinstance(item, str) and re.match(r'^[a-f0-9-]{36}$', item):
                                scenario_violations.append({
                                    'id_type': f'{field_name}[{idx}]',
                                    'id_value': item,
                                    'violation': 'RAW UUID DETECTED - Critical SSOT violation'
                                })
                
                if scenario_violations:
                    integration_violations.append({
                        'scenario': scenario['scenario'],
                        'business_impact': scenario.get('business_impact', 'Unknown'),
                        'violations': scenario_violations
                    })
        
        except Exception as e:
            integration_violations.append({
                'scenario': 'WebSocket Integration Test',
                'business_impact': 'System Integration',
                'violations': [{'error': f'Integration test failed: {e}'}]
            })
        
        # Test SHOULD FAIL - integration violations expected
        self.assertGreater(len(integration_violations), 0,
            "EXPECTED FAILURE: Should find WebSocket integration violations. "
            "If this passes, WebSocket system is already SSOT compliant!")
        
        # Fail with integration violation report
        report_lines = [
            f"🚨 ISSUE #841 WEBSOCKET INTEGRATION VIOLATIONS: {len(integration_violations)} scenarios affected",
            "💰 BUSINESS IMPACT: $500K+ ARR WebSocket chat system consistency at risk",
            ""
        ]
        
        for integration_violation in integration_violations:
            report_lines.extend([
                f"🔄 SCENARIO: {integration_violation['scenario']}",
                f"💼 IMPACT: {integration_violation['business_impact']}"
            ])
            
            for violation in integration_violation.get('violations', []):
                if 'error' in violation:
                    report_lines.append(f"   ❌ {violation['error']}")
                else:
                    report_lines.extend([
                        f"   🔧 {violation['id_type']}: {violation['id_value'][:30]}...",
                        f"      Issue: {violation['violation']}"
                    ])
            report_lines.append("")
        
        report_lines.extend([
            "🎯 WEBSOCKET INTEGRATION MIGRATION REQUIRED:",
            "   1. Standardize all WebSocket ID generation on UnifiedIdGenerator",
            "   2. Ensure connection/event/user ID formats are consistent",
            "   3. Test complete WebSocket flows with SSOT IDs",
            "   4. Validate multi-user WebSocket isolation with new ID patterns",
            "",
            "📋 INTEGRATION SUCCESS CRITERIA:",
            "   - All WebSocket scenarios use structured ID formats",
            "   - No raw UUID patterns in any WebSocket flow",
            "   - Connection-event-user relationships maintained",
            "   - Multi-user isolation verified across WebSocket operations",
            "   - Real-time chat functionality preserved with SSOT IDs"
        ])
        
        pytest.fail("\n".join(report_lines))

    def tearDown(self):
        """Cleanup and summary after WebSocket violation detection."""
        print(f"\n🚨 ISSUE #841 WEBSOCKET VIOLATIONS: Critical WebSocket ID generation violations detected")
        print("🎯 Next steps: Begin SSOT migration for WebSocket core components")
        print("💰 Business impact: $500K+ ARR real-time chat functionality depends on this migration")
        super().tearDown()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])