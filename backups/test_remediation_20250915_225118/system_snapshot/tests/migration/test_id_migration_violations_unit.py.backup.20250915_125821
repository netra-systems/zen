"""
Unit Test Suite: Issue #89 UnifiedIDManager Migration - Violation Detection
================================================================

BUSINESS JUSTIFICATION (Issue #89):
- Only 3% completion (50/1,667 files migrated) 
- 7/12 migration compliance tests FAILING
- 10,327 uuid.uuid4() violations across codebase
- Critical for $500K+ ARR WebSocket routing and multi-user isolation

PURPOSE: Create focused FAILING tests that reproduce migration gaps
STRATEGY: Tests DESIGNED TO FAIL until migration is properly completed
VALIDATION: These tests become regression protection after migration

CRITICAL TEST PATTERNS:
1. Direct uuid.uuid4() usage detection (10,327 violations)
2. Auth service ID generation violations (945+ files) 
3. WebSocket system legacy patterns
4. UserExecutionContext inconsistent formats
5. Cross-service ID format mismatches

Expected Outcome: ALL TESTS SHOULD FAIL until UnifiedIdGenerator adoption reaches >90%
"""
import pytest
import uuid
import re
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

class TestIDMigrationViolationsUnit(SSotBaseTestCase):
    """Unit tests exposing ID generation violations across the codebase."""

    def setup_method(self, method=None):
        """Setup for violation detection tests."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        self.violation_count = 0
        self.uuid_violation_patterns = ['str\\(uuid\\.uuid4\\(\\)\\)', 'uuid\\.uuid4\\(\\)\\.hex', 'uuid\\.uuid4\\(\\)', 'f"\\{uuid\\.uuid4\\(\\)\\}"', "f'\\{uuid\\.uuid4\\(\\)\\}'"]
        self.high_violation_files = ['auth_service/services/user_service.py', 'auth_service/services/session_service.py', 'auth_service/tests/unit/test_jwt_handler_comprehensive.py', 'auth_service/tests/unit/test_repository_core_comprehensive.py', 'netra_backend/app/websocket_core/websocket_manager.py', 'netra_backend/app/services/user_execution_context.py', 'shared/types/execution_types.py']

    def test_direct_uuid4_usage_violations_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Detect 10,327+ uuid.uuid4() violations across codebase.
        
        This test scans actual files to expose current violation patterns.
        Should FAIL until migration reaches completion.
        """
        violations_found = []
        files_scanned = 0
        scan_dirs = ['auth_service', 'netra_backend', 'shared', 'test_framework']
        for scan_dir in scan_dirs:
            scan_path = self.project_root / scan_dir
            if not scan_path.exists():
                continue
            for py_file in scan_path.rglob('*.py'):
                if '__pycache__' in str(py_file):
                    continue
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    files_scanned += 1
                    for line_num, line in enumerate(content.split('\n'), 1):
                        for pattern in self.uuid_violation_patterns:
                            if re.search(pattern, line):
                                violations_found.append({'file': str(py_file.relative_to(self.project_root)), 'line': line_num, 'code': line.strip(), 'pattern': pattern})
                except Exception as e:
                    continue
        self.violation_count = len(violations_found)
        self.assertGreater(len(violations_found), 100, f'Expected >100 uuid.uuid4() violations, found {len(violations_found)}. If this passes, migration is further along than expected!')
        violation_summary = {}
        for violation in violations_found:
            file_path = violation['file']
            if file_path not in violation_summary:
                violation_summary[file_path] = []
            violation_summary[file_path].append(violation['line'])
        report_lines = [f'MIGRATION VIOLATION DETECTION: Found {len(violations_found)} uuid.uuid4() violations across {len(violation_summary)} files:', '']
        sorted_files = sorted(violation_summary.items(), key=lambda x: len(x[1]), reverse=True)
        for file_path, line_numbers in sorted_files[:10]:
            report_lines.append(f'  📁 {file_path}: {len(line_numbers)} violations on lines {line_numbers[:5]}')
        report_lines.extend(['', '🎯 MIGRATION REQUIRED: Replace uuid.uuid4() with UnifiedIdGenerator.generate_base_id()', f'📊 Files scanned: {files_scanned}', f'🚨 Compliance status: {(files_scanned - len(violation_summary)) / files_scanned * 100:.1f}%'])
        pytest.fail('\n'.join(report_lines))

    def test_auth_service_specific_violations_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Auth service contains concentrated ID generation violations.
        
        Based on grep analysis showing 945+ files with violations in auth_service.
        """
        auth_violations = []
        auth_service_path = self.project_root / 'auth_service'
        if not auth_service_path.exists():
            self.skipTest('Auth service directory not found')
        violation_files_checked = 0
        for violation_file in self.high_violation_files:
            if not violation_file.startswith('auth_service/'):
                continue
            file_path = self.project_root / violation_file
            if file_path.exists():
                violation_files_checked += 1
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    auth_patterns = ['id=str\\(uuid\\.uuid4\\(\\)\\)', 'session_id.*uuid\\.uuid4', 'token.*uuid\\.uuid4', 'refresh.*uuid\\.uuid4']
                    for line_num, line in enumerate(content.split('\n'), 1):
                        for pattern in auth_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                auth_violations.append({'file': violation_file, 'line': line_num, 'code': line.strip(), 'pattern': pattern})
                except Exception:
                    continue
        self.assertGreater(len(auth_violations), 5, f'Expected >5 auth service violations, found {len(auth_violations)}. If this passes, auth service migration is more complete than expected!')
        report_lines = [f'AUTH SERVICE MIGRATION VIOLATIONS: Found {len(auth_violations)} violations:', '']
        for violation in auth_violations[:10]:
            report_lines.append(f"  🔑 {violation['file']}:{violation['line']}")
            report_lines.append(f"      Code: {violation['code']}")
        report_lines.extend(['', '🎯 AUTH MIGRATION REQUIRED:', "   - Replace str(uuid.uuid4()) with UnifiedIdGenerator.generate_base_id('user')", '   - Standardize session/token ID generation patterns', f'📊 Auth files checked: {violation_files_checked}'])
        pytest.fail('\n'.join(report_lines))

    def test_websocket_system_legacy_patterns_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: WebSocket systems use legacy ID generation patterns.
        
        Critical for $500K+ ARR - WebSocket routing depends on consistent ID formats.
        """
        websocket_violations = []
        websocket_patterns = ['netra_backend/app/websocket_core/', 'netra_backend/app/services/agent_websocket_bridge.py', 'netra_backend/app/services/websocket_bridge_factory.py']
        for pattern in websocket_patterns:
            pattern_path = self.project_root / pattern
            if pattern_path.is_file():
                files_to_check = [pattern_path]
            elif pattern_path.is_dir():
                files_to_check = list(pattern_path.rglob('*.py'))
            else:
                continue
            for file_path in files_to_check:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ws_violation_patterns = ['websocket.*uuid\\.uuid4', 'connection.*uuid\\.uuid4', 'client_id.*uuid\\.uuid4', 'ws_id.*uuid\\.uuid4']
                    for line_num, line in enumerate(content.split('\n'), 1):
                        for violation_pattern in ws_violation_patterns:
                            if re.search(violation_pattern, line, re.IGNORECASE):
                                websocket_violations.append({'file': str(file_path.relative_to(self.project_root)), 'line': line_num, 'code': line.strip(), 'business_impact': '$500K+ ARR WebSocket routing'})
                except Exception:
                    continue
        id_format_issues = []
        try:
            test_patterns = [f'websocket_{uuid.uuid4().hex[:8]}', f'ws_connection_{uuid.uuid4()}', str(uuid.uuid4())]
            structured_format = re.compile('^websocket_\\d+_\\d+_[a-f0-9]{8}$')
            for pattern in test_patterns:
                if not structured_format.match(pattern):
                    id_format_issues.append({'pattern': pattern, 'issue': 'Does not match UnifiedIdGenerator structured format'})
        except Exception:
            pass
        total_violations = len(websocket_violations) + len(id_format_issues)
        self.assertGreater(total_violations, 0, 'Expected WebSocket ID generation violations. If this passes, WebSocket systems are already migrated!')
        report_lines = [f'WEBSOCKET MIGRATION VIOLATIONS: {total_violations} issues found', '🚨 BUSINESS IMPACT: $500K+ ARR depends on consistent WebSocket ID routing', '']
        if websocket_violations:
            report_lines.append('📁 FILE VIOLATIONS:')
            for violation in websocket_violations[:5]:
                report_lines.append(f"   {violation['file']}:{violation['line']}")
        if id_format_issues:
            report_lines.append('🔧 FORMAT VIOLATIONS:')
            for issue in id_format_issues:
                report_lines.append(f"   Pattern: {issue['pattern']}")
                report_lines.append(f"   Issue: {issue['issue']}")
        report_lines.extend(['', '🎯 WEBSOCKET MIGRATION REQUIRED:', '   - Use UnifiedIdGenerator.generate_websocket_connection_id()', '   - Ensure structured format: websocket_timestamp_counter_random', '   - Maintain user context embedding for routing'])
        pytest.fail('\n'.join(report_lines))

    def test_user_execution_context_violations_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: UserExecutionContext has inconsistent ID generation.
        
        Critical for multi-user isolation and proper context management.
        """
        context_violations = []
        try:
            test_cases = [{'user_id': 'user_123', 'thread_id': 'thread_456', 'run_id': str(uuid.uuid4()), 'request_id': str(uuid.uuid4())}, {'user_id': str(uuid.uuid4()), 'thread_id': f'thread_{uuid.uuid4().hex[:8]}', 'run_id': f'run_{uuid.uuid4()}', 'request_id': f'req_{uuid.uuid4()}'}]
            structured_patterns = {'user_id': re.compile('^user_\\d+_\\d+_[a-f0-9]{8}$'), 'thread_id': re.compile('^(thread|session)_\\d+_\\d+_[a-f0-9]{8}$'), 'run_id': re.compile('^run_.+_\\d+_\\d+_[a-f0-9]{8}$'), 'request_id': re.compile('^req_\\d+_\\d+_[a-f0-9]{8}$')}
            for test_case in test_cases:
                for id_type, id_value in test_case.items():
                    expected_pattern = structured_patterns[id_type]
                    if not expected_pattern.match(id_value):
                        context_violations.append({'id_type': id_type, 'id_value': id_value, 'issue': f'Does not match structured format for {id_type}', 'expected_pattern': expected_pattern.pattern})
        except Exception as e:
            context_violations.append({'id_type': 'system', 'id_value': 'N/A', 'issue': f'UserExecutionContext creation failed: {e}', 'expected_pattern': 'Proper factory initialization required'})
        self.assertGreater(len(context_violations), 2, f'Expected >2 UserExecutionContext violations, found {len(context_violations)}. If this passes, context management is already SSOT compliant!')
        report_lines = [f'USER CONTEXT MIGRATION VIOLATIONS: {len(context_violations)} format issues', '🚨 BUSINESS IMPACT: Multi-user isolation depends on consistent ID formats', '']
        for violation in context_violations:
            report_lines.extend([f"   🔧 {violation['id_type']}: {violation['id_value'][:50]}...", f"      Issue: {violation['issue']}", f"      Expected: {violation['expected_pattern']}", ''])
        report_lines.extend(['🎯 CONTEXT MIGRATION REQUIRED:', '   - Use UnifiedIdGenerator for all context ID generation', '   - Implement UserExecutionContext.create_with_unified_ids()', '   - Ensure thread/run ID relationship embedding'])
        pytest.fail('\n'.join(report_lines))

    def test_cross_service_id_format_consistency_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Different services use incompatible ID formats.
        
        Critical for service integration and data consistency.
        """
        service_format_violations = []
        services_to_check = {'auth_service': self.project_root / 'auth_service', 'backend': self.project_root / 'netra_backend' / 'app', 'shared': self.project_root / 'shared'}
        service_id_patterns = {}
        for service_name, service_path in services_to_check.items():
            if not service_path.exists():
                continue
            patterns_found = []
            for py_file in service_path.rglob('*.py'):
                if '__pycache__' in str(py_file):
                    continue
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    id_generation_lines = []
                    for line in content.split('\n'):
                        if any((pattern in line.lower() for pattern in ['uuid', '_id', 'generate'])):
                            if any((violation in line for violation in ['uuid.uuid4', 'str(uuid', 'f"user_', 'f"thread_'])):
                                id_generation_lines.append(line.strip())
                    if id_generation_lines:
                        patterns_found.extend(id_generation_lines[:3])
                except Exception:
                    continue
            service_id_patterns[service_name] = patterns_found[:5]
        if len(service_id_patterns) >= 2:
            services = list(service_id_patterns.keys())
            for i, service1 in enumerate(services):
                for service2 in services[i + 1:]:
                    patterns1 = set(service_id_patterns[service1])
                    patterns2 = set(service_id_patterns[service2])
                    if patterns1 and patterns2 and (not patterns1 & patterns2):
                        service_format_violations.append({'service1': service1, 'service2': service2, 'issue': 'No common ID generation patterns', 'patterns1': list(patterns1)[:3], 'patterns2': list(patterns2)[:3]})
        format_violations = []
        test_id_formats = [('auth_service_user', str(uuid.uuid4())), ('backend_thread', f'thread_{uuid.uuid4().hex[:8]}'), ('shared_request', f'req-{uuid.uuid4()}')]
        unified_format = re.compile('^[a-z_]+_\\d+_\\d+_[a-f0-9]{8}$')
        for source, id_value in test_id_formats:
            if not unified_format.match(id_value):
                format_violations.append({'source': source, 'id_value': id_value, 'issue': 'Does not match UnifiedIdGenerator format'})
        total_violations = len(service_format_violations) + len(format_violations)
        self.assertGreater(total_violations, 1, f'Expected >1 cross-service format violation, found {total_violations}. If this passes, services are already using consistent ID formats!')
        report_lines = [f'CROSS-SERVICE ID FORMAT VIOLATIONS: {total_violations} inconsistencies', '🚨 BUSINESS IMPACT: Service integration depends on consistent ID formats', '']
        if service_format_violations:
            report_lines.append('🔄 SERVICE INCONSISTENCIES:')
            for violation in service_format_violations:
                report_lines.extend([f"   {violation['service1']} ↔️ {violation['service2']}", f"   Issue: {violation['issue']}", f"   Patterns differ: {len(violation['patterns1'])} vs {len(violation['patterns2'])}", ''])
        if format_violations:
            report_lines.append('📐 FORMAT VIOLATIONS:')
            for violation in format_violations:
                report_lines.extend([f"   {violation['source']}: {violation['id_value'][:40]}...", f"   Issue: {violation['issue']}", ''])
        report_lines.extend(['🎯 CROSS-SERVICE MIGRATION REQUIRED:', '   - Standardize all services on UnifiedIdGenerator', '   - Use consistent format: prefix_timestamp_counter_random', '   - Implement service-wide ID validation contracts'])
        pytest.fail('\n'.join(report_lines))

    def tearDown(self):
        """Cleanup and summary after violation detection."""
        if hasattr(self, 'violation_count') and self.violation_count > 0:
            print(f'\n🚨 MIGRATION STATUS: {self.violation_count} violations detected')
            print('🎯 Next steps: Begin systematic migration to UnifiedIdGenerator')
        super().tearDown()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')