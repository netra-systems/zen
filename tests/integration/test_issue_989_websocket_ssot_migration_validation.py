"""MISSION CRITICAL: Issue #989 WebSocket SSOT Migration Validation Test

GitHub Issue: #989 WebSocket factory deprecation SSOT violation - get_websocket_manager_factory()
GitHub Stage: Step 2 - EXECUTE THE TEST PLAN (Migration Validation)

BUSINESS VALUE: $500K+ ARR - Validates successful SSOT migration without breaking changes
Ensures single WebSocket initialization pattern after deprecated factory removal.

PURPOSE:
- Validate successful SSOT migration eliminates deprecated factory patterns
- Test that all WebSocket initialization uses single SSOT pattern post-migration
- Ensure no imports remain that reference deprecated get_websocket_manager_factory()
- Validate backward compatibility during transition period
- Create tests that PASS after migration (proving successful remediation)

MIGRATION VALIDATION STRATEGY:
1. Test canonical imports no longer export deprecated factory functions
2. Validate all codebase imports use SSOT WebSocket patterns
3. Test single initialization pattern compliance across services
4. Ensure no circular imports or dependency conflicts post-migration
5. Validate staging/production compatibility with SSOT pattern only

CRITICAL MIGRATION CHECKPOINTS:
- canonical_imports.py removes get_websocket_manager_factory from __all__
- All test files use SSOT WebSocketManager initialization
- No remaining imports of deprecated factory functions
- WebSocket manager creation uses consistent SSOT pattern
- User isolation maintained through migration

EXPECTED BEHAVIOR:
- BEFORE Migration: Tests MAY FAIL (deprecated patterns still exist)
- AFTER Migration: Tests MUST PASS (proving successful SSOT consolidation)
- Tests validate migration completion and SSOT compliance achievement
"""
import os
import sys
import ast
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from test_framework.ssot.base_test_case import SSotBaseTestCase
import pytest
from loguru import logger

@dataclass
class MigrationValidationResult:
    """Results from SSOT migration validation"""
    validation_name: str
    pre_migration_violations: int
    post_migration_violations: int
    migration_success: bool
    remaining_issues: List[str] = field(default_factory=list)
    compliance_percentage: float = 0.0

@dataclass
class ImportPatternAnalysis:
    """Analysis of import patterns post-migration"""
    total_files_analyzed: int
    ssot_compliant_files: int
    deprecated_pattern_files: int
    mixed_pattern_files: int
    import_analysis_by_pattern: Dict[str, List[str]] = field(default_factory=dict)

@pytest.mark.integration
class Issue989WebSocketSSOTMigrationValidationTests(SSotBaseTestCase):
    """Mission Critical: Issue #989 WebSocket SSOT Migration Validation

    This test suite validates that WebSocket factory SSOT migration has been
    completed successfully without breaking the $500K+ ARR Golden Path.

    Expected Test Behavior:
    - Tests FAIL if deprecated patterns still exist (migration incomplete)
    - Tests PASS when SSOT migration is complete (single pattern achieved)
    """

    def setup_method(self, method):
        """Set up migration validation test environment for Issue #989."""
        super().setup_method(method)
        self.canonical_imports_path = Path(project_root) / 'netra_backend' / 'app' / 'websocket_core' / 'canonical_imports.py'
        self.websocket_manager_path = Path(project_root) / 'netra_backend' / 'app' / 'websocket_core' / 'websocket_manager.py'
        self.search_paths = [Path(project_root) / 'netra_backend' / 'app', Path(project_root) / 'tests', Path(project_root) / 'test_framework', Path(project_root) / 'scripts']
        self.ssot_target_patterns = ['get_websocket_manager', 'WebSocketManager', 'from netra_backend.app.websocket_core.websocket_manager import']
        self.deprecated_patterns = ['get_websocket_manager_factory', 'WebSocketManagerFactory', 'from netra_backend.app.websocket_core.websocket_manager_factory import', 'canonical_imports.*get_websocket_manager_factory']
        self.migration_results: List[MigrationValidationResult] = []
        logger.info('📋 Issue #989 SSOT Migration Validation - Starting comprehensive validation...')

    def test_validate_canonical_imports_deprecated_export_removal(self):
        """CRITICAL: Validate deprecated exports removed from canonical_imports.py

        This test verifies that get_websocket_manager_factory() is no longer
        exported from canonical_imports.py after SSOT migration completion.

        MIGRATION SUCCESS CRITERIA: No deprecated exports in __all__ list.
        """
        logger.info('📋 Validating deprecated export removal from canonical_imports.py...')
        validation_result = MigrationValidationResult(validation_name='canonical_imports_export_removal', pre_migration_violations=1, post_migration_violations=0, migration_success=False)
        if self.canonical_imports_path.exists():
            try:
                content = self.canonical_imports_path.read_text(encoding='utf-8')
                tree = ast.parse(content)
                current_exports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == '__all__':
                                if isinstance(node.value, ast.List):
                                    for elt in node.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            current_exports.add(elt.value)
                deprecated_exports_found = []
                for deprecated_pattern in self.deprecated_patterns:
                    if deprecated_pattern in current_exports:
                        deprecated_exports_found.append(deprecated_pattern)
                        validation_result.remaining_issues.append(f'Still exports deprecated: {deprecated_pattern}')
                validation_result.post_migration_violations = len(deprecated_exports_found)
                validation_result.migration_success = len(deprecated_exports_found) == 0
                total_patterns = len(self.deprecated_patterns)
                removed_patterns = total_patterns - len(deprecated_exports_found)
                validation_result.compliance_percentage = removed_patterns / total_patterns * 100
                if validation_result.migration_success:
                    logger.info('✅ Canonical imports deprecated export removal: SUCCESS')
                else:
                    logger.error(f'❌ Found {len(deprecated_exports_found)} deprecated exports still present')
                    for export in deprecated_exports_found:
                        logger.error(f'   - {export}')
            except Exception as e:
                logger.error(f'❌ Failed to analyze canonical imports: {e}')
                validation_result.remaining_issues.append(f'Analysis failed: {e}')
                validation_result.migration_success = False
        else:
            logger.error('❌ canonical_imports.py not found')
            validation_result.remaining_issues.append('canonical_imports.py missing')
            validation_result.migration_success = False
        self.migration_results.append(validation_result)
        assert validation_result.migration_success, f'SSOT MIGRATION INCOMPLETE: Found {validation_result.post_migration_violations} deprecated exports still present in canonical_imports.py. Remaining issues: {validation_result.remaining_issues}. Migration success requires removal of ALL deprecated exports.'

    def test_validate_codebase_import_pattern_consolidation(self):
        """CRITICAL: Validate all codebase imports use SSOT patterns post-migration

        Scans entire codebase to ensure no files still import deprecated
        WebSocket factory patterns after SSOT migration completion.

        MIGRATION SUCCESS CRITERIA: 100% SSOT import pattern compliance.
        """
        logger.info('📋 Validating codebase import pattern consolidation...')
        import_analysis = ImportPatternAnalysis(total_files_analyzed=0, ssot_compliant_files=0, deprecated_pattern_files=0, mixed_pattern_files=0)
        validation_result = MigrationValidationResult(validation_name='codebase_import_consolidation', pre_migration_violations=0, post_migration_violations=0, migration_success=False)
        deprecated_import_files = []
        mixed_pattern_files = []
        import re
        for search_path in self.search_paths:
            if search_path.exists():
                for py_file in search_path.rglob('*.py'):
                    if py_file.name in ['websocket_manager_factory.py', 'canonical_imports.py']:
                        continue
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        if 'websocket' not in content.lower() or 'import' not in content:
                            continue
                        import_analysis.total_files_analyzed += 1
                        has_deprecated_imports = False
                        deprecated_matches = []
                        for pattern in self.deprecated_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                has_deprecated_imports = True
                                deprecated_matches.append(pattern)
                        has_ssot_imports = False
                        ssot_matches = []
                        for pattern in self.ssot_target_patterns:
                            if re.search(pattern, content):
                                has_ssot_imports = True
                                ssot_matches.append(pattern)
                        file_rel_path = str(py_file.relative_to(project_root))
                        if has_deprecated_imports and has_ssot_imports:
                            mixed_pattern_files.append({'file': file_rel_path, 'deprecated_patterns': deprecated_matches, 'ssot_patterns': ssot_matches})
                            import_analysis.mixed_pattern_files += 1
                            logger.warning(f'⚠️ MIXED PATTERNS: {file_rel_path}')
                        elif has_deprecated_imports:
                            deprecated_import_files.append({'file': file_rel_path, 'deprecated_patterns': deprecated_matches})
                            import_analysis.deprecated_pattern_files += 1
                            logger.error(f'❌ DEPRECATED PATTERNS: {file_rel_path}')
                        elif has_ssot_imports:
                            import_analysis.ssot_compliant_files += 1
                            logger.debug(f'✅ SSOT COMPLIANT: {file_rel_path}')
                    except (UnicodeDecodeError, PermissionError):
                        continue
        total_violations = import_analysis.deprecated_pattern_files + import_analysis.mixed_pattern_files
        validation_result.post_migration_violations = total_violations
        validation_result.migration_success = total_violations == 0
        if import_analysis.total_files_analyzed > 0:
            validation_result.compliance_percentage = import_analysis.ssot_compliant_files / import_analysis.total_files_analyzed * 100
        logger.info('📊 Import Pattern Consolidation Analysis:')
        logger.info(f'  Total files analyzed: {import_analysis.total_files_analyzed}')
        logger.info(f'  SSOT compliant files: {import_analysis.ssot_compliant_files}')
        logger.info(f'  Deprecated pattern files: {import_analysis.deprecated_pattern_files}')
        logger.info(f'  Mixed pattern files: {import_analysis.mixed_pattern_files}')
        logger.info(f'  SSOT compliance: {validation_result.compliance_percentage:.1f}%')
        for file_info in deprecated_import_files[:5]:
            validation_result.remaining_issues.append(f"Deprecated imports in {file_info['file']}: {file_info['deprecated_patterns']}")
        for file_info in mixed_pattern_files[:5]:
            validation_result.remaining_issues.append(f"Mixed patterns in {file_info['file']}")
        self.migration_results.append(validation_result)
        assert validation_result.migration_success, f'SSOT MIGRATION INCOMPLETE: Found {validation_result.post_migration_violations} files with deprecated import patterns. Deprecated pattern files: {import_analysis.deprecated_pattern_files}, Mixed pattern files: {import_analysis.mixed_pattern_files}. SSOT compliance: {validation_result.compliance_percentage:.1f}%. Migration requires 100% SSOT compliance.'

    def test_validate_single_websocket_initialization_pattern_enforcement(self):
        """CRITICAL: Validate single WebSocket initialization pattern enforcement

        Tests that all WebSocket manager creation uses consistent SSOT pattern
        after migration, with no multiple initialization approaches.

        MIGRATION SUCCESS CRITERIA: Single initialization pattern only.
        """
        logger.info('📋 Validating single WebSocket initialization pattern enforcement...')
        validation_result = MigrationValidationResult(validation_name='single_initialization_pattern', pre_migration_violations=2, post_migration_violations=0, migration_success=False)
        initialization_patterns = defaultdict(list)
        pattern_violations = []
        import re
        init_patterns = {'ssot_get_websocket_manager': 'get_websocket_manager\\(', 'direct_websocket_manager': 'WebSocketManager\\(', 'deprecated_factory_func': 'get_websocket_manager_factory\\(', 'deprecated_factory_class': 'WebSocketManagerFactory\\(', 'compatibility_create': 'create_websocket_manager\\('}
        for search_path in self.search_paths:
            if search_path.exists():
                for py_file in search_path.rglob('*.py'):
                    if py_file.name in ['websocket_manager_factory.py', 'websocket_manager.py']:
                        continue
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        if 'websocket' not in content.lower():
                            continue
                        file_rel_path = str(py_file.relative_to(project_root))
                        file_patterns = []
                        for pattern_name, pattern_regex in init_patterns.items():
                            if re.search(pattern_regex, content):
                                file_patterns.append(pattern_name)
                                initialization_patterns[pattern_name].append(file_rel_path)
                        if len(file_patterns) > 1:
                            pattern_violations.append({'file': file_rel_path, 'patterns': file_patterns})
                            logger.warning(f'⚠️ MULTIPLE PATTERNS: {file_rel_path} uses {file_patterns}')
                    except (UnicodeDecodeError, PermissionError):
                        continue
        validation_result.post_migration_violations = len(pattern_violations)
        deprecated_patterns_in_use = []
        for pattern_name in ['deprecated_factory_func', 'deprecated_factory_class']:
            if initialization_patterns[pattern_name]:
                deprecated_patterns_in_use.extend(initialization_patterns[pattern_name])
        if deprecated_patterns_in_use:
            validation_result.post_migration_violations += len(deprecated_patterns_in_use)
        validation_result.migration_success = validation_result.post_migration_violations == 0
        logger.info('📊 WebSocket Initialization Pattern Distribution:')
        total_files_with_patterns = 0
        for pattern_name, files in initialization_patterns.items():
            if files:
                total_files_with_patterns += len(files)
                logger.info(f'  {pattern_name}: {len(files)} files')
        if total_files_with_patterns > 0:
            ssot_files = len(initialization_patterns['ssot_get_websocket_manager'])
            validation_result.compliance_percentage = ssot_files / total_files_with_patterns * 100
        for violation in pattern_violations[:5]:
            validation_result.remaining_issues.append(f"Multiple patterns in {violation['file']}: {violation['patterns']}")
        if deprecated_patterns_in_use:
            validation_result.remaining_issues.append(f'Deprecated patterns still used in {len(deprecated_patterns_in_use)} files')
        self.migration_results.append(validation_result)
        assert validation_result.migration_success, f'SINGLE PATTERN ENFORCEMENT FAILED: Found {validation_result.post_migration_violations} pattern violations. Multiple pattern files: {len(pattern_violations)}, Deprecated pattern files: {len(deprecated_patterns_in_use)}. SSOT requires single initialization pattern only.'

    def test_validate_websocket_import_path_consistency_post_migration(self):
        """CRITICAL: Validate WebSocket import path consistency after migration

        Ensures all WebSocket-related imports use consistent SSOT import paths
        without circular dependencies or import conflicts.

        MIGRATION SUCCESS CRITERIA: Consistent import paths, no conflicts.
        """
        logger.info('📋 Validating WebSocket import path consistency post-migration...')
        validation_result = MigrationValidationResult(validation_name='import_path_consistency', pre_migration_violations=0, post_migration_violations=0, migration_success=False)
        import_paths = defaultdict(list)
        inconsistent_files = []
        circular_dependency_risks = []
        import re
        canonical_import_paths = {'websocket_manager': 'from netra_backend.app.websocket_core.websocket_manager import', 'websocket_protocols': 'from netra_backend.app.websocket_core.protocols import', 'websocket_unified': 'from netra_backend.app.websocket_core.unified_manager import'}
        deprecated_import_paths = {'factory_imports': 'from netra_backend.app.websocket_core.websocket_manager_factory import', 'canonical_factory': 'from netra_backend.app.websocket_core.canonical_imports import.*get_websocket_manager_factory'}
        for search_path in self.search_paths:
            if search_path.exists():
                for py_file in search_path.rglob('*.py'):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        lines = content.split('\n')
                        file_rel_path = str(py_file.relative_to(project_root))
                        file_import_paths = []
                        for line_num, line in enumerate(lines, 1):
                            if 'websocket' in line.lower() and ('import' in line or 'from' in line):
                                for path_name, path_pattern in canonical_import_paths.items():
                                    if re.search(path_pattern, line, re.IGNORECASE):
                                        file_import_paths.append(path_name)
                                        import_paths[path_name].append({'file': file_rel_path, 'line_num': line_num, 'line': line.strip()})
                                for path_name, path_pattern in deprecated_import_paths.items():
                                    if re.search(path_pattern, line, re.IGNORECASE):
                                        validation_result.post_migration_violations += 1
                                        validation_result.remaining_issues.append(f'Deprecated import in {file_rel_path}:{line_num}: {line.strip()}')
                        unique_paths = set(file_import_paths)
                        if len(unique_paths) > 1:
                            inconsistent_files.append({'file': file_rel_path, 'import_paths': list(unique_paths)})
                    except (UnicodeDecodeError, PermissionError):
                        continue
        validation_result.post_migration_violations += len(inconsistent_files)
        validation_result.migration_success = validation_result.post_migration_violations == 0
        total_import_usages = sum((len(files) for files in import_paths.values()))
        canonical_usages = sum((len(import_paths[path]) for path in canonical_import_paths.keys() if path in import_paths))
        if total_import_usages > 0:
            validation_result.compliance_percentage = canonical_usages / total_import_usages * 100
        logger.info('📊 WebSocket Import Path Consistency Analysis:')
        logger.info(f'  Total import usages: {total_import_usages}')
        logger.info(f'  Canonical import usages: {canonical_usages}')
        logger.info(f'  Inconsistent files: {len(inconsistent_files)}')
        logger.info(f'  Import path compliance: {validation_result.compliance_percentage:.1f}%')
        for file_info in inconsistent_files[:5]:
            validation_result.remaining_issues.append(f"Inconsistent imports in {file_info['file']}: {file_info['import_paths']}")
        self.migration_results.append(validation_result)
        assert validation_result.migration_success, f'IMPORT PATH CONSISTENCY FAILED: Found {validation_result.post_migration_violations} import path violations. Inconsistent files: {len(inconsistent_files)}. Import path compliance: {validation_result.compliance_percentage:.1f}%. SSOT migration requires consistent import paths.'

    def teardown_method(self, method):
        """Clean up and log Issue #989 SSOT migration validation results."""
        if self.migration_results:
            logger.info('📋 Issue #989 SSOT Migration Validation Summary:')
            total_validations = len(self.migration_results)
            successful_validations = sum((1 for result in self.migration_results if result.migration_success))
            logger.info(f'  Total validations: {total_validations}')
            logger.info(f'  Successful validations: {successful_validations}')
            logger.info(f'  Migration success rate: {successful_validations / total_validations * 100:.1f}%')
            overall_violations = 0
            for result in self.migration_results:
                status = '✅ PASS' if result.migration_success else '❌ FAIL'
                logger.info(f'  {result.validation_name}: {status}')
                logger.info(f'    Post-migration violations: {result.post_migration_violations}')
                logger.info(f'    Compliance: {result.compliance_percentage:.1f}%')
                overall_violations += result.post_migration_violations
                if result.remaining_issues:
                    logger.warning(f'    Remaining issues ({len(result.remaining_issues)}):')
                    for issue in result.remaining_issues[:3]:
                        logger.warning(f'      - {issue}')
            if successful_validations == total_validations:
                logger.info('🎉 ✅ SSOT MIGRATION COMPLETE - All validations PASSED')
            else:
                logger.error(f'❌ SSOT MIGRATION INCOMPLETE - {overall_violations} total violations remain')
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')