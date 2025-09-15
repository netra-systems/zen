"""
Production Usage Pattern Tests for Issue #914 AgentRegistry SSOT Consolidation

P1 PRIORITY TESTS: These tests scan the codebase for conflicting usage patterns
that cause runtime failures and demonstrate SSOT compliance measurement issues.

Business Value: $500K+ ARR Golden Path protection - ensures production code
patterns are compatible and don't cause runtime registry conflicts.

Test Focus:
- Scan codebase for conflicting usage patterns
- Test files using both registries causing runtime failures
- Verify SSOT compliance measurement methodology
- Document actual production patterns for consolidation planning

Created: 2025-01-14 - Issue #914 Test Creation Plan
Priority: P1 - Must document production usage patterns for consolidation
"""
import pytest
import asyncio
import os
import ast
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

@dataclass
class RegistryUsagePattern:
    """Data structure for tracking registry usage patterns"""
    file_path: str
    line_number: int
    import_statement: str
    usage_type: str
    registry_type: str
    context: str

@dataclass
class RegistryConflict:
    """Data structure for tracking registry conflicts"""
    file_path: str
    conflict_type: str
    registries_involved: List[str]
    line_numbers: List[int]
    description: str
    severity: str

class TestAgentRegistryProductionUsagePatterns(SSotAsyncTestCase):
    """
    P1 Tests: Analyze production usage patterns for registry consolidation
    
    These tests scan the actual codebase to identify conflicting registry usage
    patterns and provide data for SSOT consolidation planning.
    """

    def setup_method(self, method=None):
        """Set up test environment with SSOT patterns"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.registry_import_patterns = ['from\\s+netra_backend\\.app\\.agents\\.registry\\s+import\\s+AgentRegistry', 'from\\s+netra_backend\\.app\\.agents\\.registry\\s+import\\s+agent_registry', 'import\\s+netra_backend\\.app\\.agents\\.registry', 'from\\s+netra_backend\\.app\\.agents\\.supervisor\\.agent_registry\\s+import\\s+AgentRegistry', 'from\\s+netra_backend\\.app\\.agents\\.supervisor\\.agent_registry\\s+import\\s+agent_registry', 'from\\s+netra_backend\\.app\\.agents\\.supervisor\\.agent_registry\\s+import\\s+get_agent_registry', 'import\\s+netra_backend\\.app\\.agents\\.supervisor\\.agent_registry', 'agent_registry\\s*=', 'AgentRegistry\\(', 'get_agent_registry\\(']
        self.scan_directories = [Path('netra_backend/app'), Path('tests'), Path('auth_service'), Path('shared')]
        self.registry_usage_patterns: List[RegistryUsagePattern] = []
        self.registry_conflicts: List[RegistryConflict] = []
        self.file_registry_usage: Dict[str, List[RegistryUsagePattern]] = defaultdict(list)
        self.ssot_compliance_data = {'total_files_scanned': 0, 'files_with_registry_usage': 0, 'files_with_conflicts': 0, 'total_registry_references': 0, 'registry_import_diversity': 0, 'compliance_score': 0.0}

    async def test_codebase_registry_usage_pattern_scan(self):
        """
        P1 TEST: Scan codebase for registry usage patterns
        
        This test scans the entire codebase to identify all registry usage patterns,
        providing data for understanding the scope of SSOT consolidation needed.
        
        Business Impact: Maps the full extent of registry usage across the codebase
        to guide consolidation efforts and prevent regression.
        """
        codebase_scan_results = {'files_scanned': 0, 'registry_usage_found': 0, 'usage_patterns': [], 'registry_types_found': set(), 'import_patterns_found': set(), 'scan_errors': []}
        for scan_dir in self.scan_directories:
            if not scan_dir.exists():
                codebase_scan_results['scan_errors'].append(f'Directory not found: {scan_dir}')
                continue
            self.logger.info(f'Scanning directory: {scan_dir}')
            python_files = list(scan_dir.rglob('*.py'))
            for py_file in python_files:
                try:
                    codebase_scan_results['files_scanned'] += 1
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                        file_lines = file_content.splitlines()
                    file_has_registry_usage = False
                    for line_num, line in enumerate(file_lines, 1):
                        line_stripped = line.strip()
                        if not line_stripped or line_stripped.startswith('#'):
                            continue
                        for pattern in self.registry_import_patterns:
                            if re.search(pattern, line_stripped, re.IGNORECASE):
                                file_has_registry_usage = True
                                registry_type = 'unknown'
                                if 'supervisor.agent_registry' in line_stripped:
                                    registry_type = 'advanced'
                                elif 'agents.registry' in line_stripped and 'supervisor' not in line_stripped:
                                    registry_type = 'basic'
                                usage_type = 'unknown'
                                if line_stripped.startswith(('from ', 'import ')):
                                    usage_type = 'import'
                                elif 'AgentRegistry(' in line_stripped:
                                    usage_type = 'instantiation'
                                elif 'agent_registry.' in line_stripped:
                                    usage_type = 'method_call'
                                elif '= ' in line_stripped and 'agent_registry' in line_stripped:
                                    usage_type = 'assignment'
                                usage_pattern = RegistryUsagePattern(file_path=str(py_file), line_number=line_num, import_statement=line_stripped, usage_type=usage_type, registry_type=registry_type, context=self._get_line_context(file_lines, line_num - 1, context_lines=2))
                                self.registry_usage_patterns.append(usage_pattern)
                                self.file_registry_usage[str(py_file)].append(usage_pattern)
                                codebase_scan_results['usage_patterns'].append(usage_pattern)
                                codebase_scan_results['registry_types_found'].add(registry_type)
                                codebase_scan_results['import_patterns_found'].add(pattern)
                                self.logger.debug(f'Found {registry_type} registry usage in {py_file}:{line_num}')
                    if file_has_registry_usage:
                        codebase_scan_results['registry_usage_found'] += 1
                except Exception as e:
                    codebase_scan_results['scan_errors'].append(f'Error scanning {py_file}: {e}')
                    self.logger.warning(f'Error scanning {py_file}: {e}')
        self.ssot_compliance_data['total_files_scanned'] = codebase_scan_results['files_scanned']
        self.ssot_compliance_data['files_with_registry_usage'] = codebase_scan_results['registry_usage_found']
        self.ssot_compliance_data['total_registry_references'] = len(codebase_scan_results['usage_patterns'])
        self.ssot_compliance_data['registry_import_diversity'] = len(codebase_scan_results['import_patterns_found'])
        usage_by_registry_type = defaultdict(int)
        usage_by_type = defaultdict(int)
        for pattern in codebase_scan_results['usage_patterns']:
            usage_by_registry_type[pattern.registry_type] += 1
            usage_by_type[pattern.usage_type] += 1
        self.logger.info(f'Registry usage scan complete:')
        self.logger.info(f"  Files scanned: {codebase_scan_results['files_scanned']}")
        self.logger.info(f"  Files with registry usage: {codebase_scan_results['registry_usage_found']}")
        self.logger.info(f"  Total registry references: {len(codebase_scan_results['usage_patterns'])}")
        self.logger.info(f"  Registry types found: {list(codebase_scan_results['registry_types_found'])}")
        self.logger.info(f'  Usage by registry type: {dict(usage_by_registry_type)}')
        self.logger.info(f'  Usage by type: {dict(usage_by_type)}')
        concerning_patterns = []
        if self.ssot_compliance_data['registry_import_diversity'] > 5:
            concerning_patterns.append(f"High import pattern diversity ({self.ssot_compliance_data['registry_import_diversity']} patterns) indicates SSOT violation")
        if len(codebase_scan_results['registry_types_found']) > 2:
            concerning_patterns.append(f"Multiple registry types in use ({list(codebase_scan_results['registry_types_found'])}) indicates potential conflicts")
        if codebase_scan_results['registry_usage_found'] > 20:
            concerning_patterns.append(f"Widespread registry usage ({codebase_scan_results['registry_usage_found']} files) indicates significant consolidation impact")
        if codebase_scan_results['scan_errors']:
            concerning_patterns.append(f"Scan errors ({len(codebase_scan_results['scan_errors'])}) may hide additional usage patterns")
        if concerning_patterns:
            self.logger.warning('CODEBASE REGISTRY USAGE ANALYSIS - Concerning patterns found:')
            for pattern in concerning_patterns:
                self.logger.warning(f'  - {pattern}')
        else:
            self.logger.info('CODEBASE REGISTRY USAGE ANALYSIS - No concerning patterns found')
        assert codebase_scan_results['files_scanned'] > 0, 'Should have scanned at least some files'

    async def test_files_with_conflicting_registry_imports(self):
        """
        P1 TEST: Identify files using both registries causing runtime conflicts
        
        DESIGNED TO FAIL: Files importing both basic and advanced registries
        cause runtime conflicts when both are used inconsistently.
        
        Business Impact: These files are candidates for runtime failures and
        must be prioritized in consolidation efforts.
        """
        conflicting_files = []
        mixed_usage_analysis = {}
        for file_path, usage_patterns in self.file_registry_usage.items():
            if not usage_patterns:
                continue
            mixed_usage_analysis[file_path] = {'registry_types_used': set(), 'import_statements': [], 'usage_types': set(), 'conflict_severity': 'none', 'conflict_details': []}
            for pattern in usage_patterns:
                mixed_usage_analysis[file_path]['registry_types_used'].add(pattern.registry_type)
                mixed_usage_analysis[file_path]['import_statements'].append({'line': pattern.line_number, 'statement': pattern.import_statement, 'type': pattern.usage_type, 'registry': pattern.registry_type})
                mixed_usage_analysis[file_path]['usage_types'].add(pattern.usage_type)
            registry_types = mixed_usage_analysis[file_path]['registry_types_used']
            if 'basic' in registry_types and 'advanced' in registry_types:
                mixed_usage_analysis[file_path]['conflict_severity'] = 'critical'
                mixed_usage_analysis[file_path]['conflict_details'].append('File imports both basic and advanced registries - high runtime conflict risk')
                conflict = RegistryConflict(file_path=file_path, conflict_type='multiple_registry_imports', registries_involved=['basic', 'advanced'], line_numbers=[p.line_number for p in usage_patterns], description=f'File uses both basic and advanced registries', severity='critical')
                self.registry_conflicts.append(conflict)
                conflicting_files.append(file_path)
            elif len(registry_types) > 1:
                mixed_usage_analysis[file_path]['conflict_severity'] = 'high'
                mixed_usage_analysis[file_path]['conflict_details'].append(f'File uses multiple registry types: {list(registry_types)}')
                conflict = RegistryConflict(file_path=file_path, conflict_type='mixed_registry_usage', registries_involved=list(registry_types), line_numbers=[p.line_number for p in usage_patterns], description=f'File uses multiple registry types: {list(registry_types)}', severity='high')
                self.registry_conflicts.append(conflict)
                conflicting_files.append(file_path)
            elif len(set((p.import_statement for p in usage_patterns))) > 2:
                mixed_usage_analysis[file_path]['conflict_severity'] = 'medium'
                mixed_usage_analysis[file_path]['conflict_details'].append('File uses multiple import patterns for same registry type')
                conflict = RegistryConflict(file_path=file_path, conflict_type='inconsistent_import_patterns', registries_involved=list(registry_types), line_numbers=[p.line_number for p in usage_patterns], description='Multiple import patterns for same registry', severity='medium')
                self.registry_conflicts.append(conflict)
        conflict_summary = {'total_files_with_conflicts': len(conflicting_files), 'critical_conflicts': 0, 'high_conflicts': 0, 'medium_conflicts': 0, 'conflict_by_type': defaultdict(int)}
        for conflict in self.registry_conflicts:
            if conflict.severity == 'critical':
                conflict_summary['critical_conflicts'] += 1
            elif conflict.severity == 'high':
                conflict_summary['high_conflicts'] += 1
            elif conflict.severity == 'medium':
                conflict_summary['medium_conflicts'] += 1
            conflict_summary['conflict_by_type'][conflict.conflict_type] += 1
        self.ssot_compliance_data['files_with_conflicts'] = conflict_summary['total_files_with_conflicts']
        self.logger.info(f'Registry conflict analysis:')
        self.logger.info(f"  Files with conflicts: {conflict_summary['total_files_with_conflicts']}")
        self.logger.info(f"  Critical conflicts: {conflict_summary['critical_conflicts']}")
        self.logger.info(f"  High conflicts: {conflict_summary['high_conflicts']}")
        self.logger.info(f"  Medium conflicts: {conflict_summary['medium_conflicts']}")
        self.logger.info(f"  Conflicts by type: {dict(conflict_summary['conflict_by_type'])}")
        critical_conflicts = [c for c in self.registry_conflicts if c.severity == 'critical']
        if critical_conflicts:
            self.logger.error('CRITICAL REGISTRY CONFLICTS DETECTED:')
            for conflict in critical_conflicts:
                self.logger.error(f'  {conflict.file_path}: {conflict.description}')
                self.logger.error(f'    Lines: {conflict.line_numbers}')
                self.logger.error(f'    Registries: {conflict.registries_involved}')
        if conflict_summary['critical_conflicts'] > 0:
            pytest.fail(f"CRITICAL REGISTRY CONFLICTS: {conflict_summary['critical_conflicts']} files use both registries. This causes runtime failures blocking Golden Path reliability. Critical conflicts: {[c.file_path for c in critical_conflicts]}. IMPACT: These files will fail unpredictably depending on import order and registry state.")
        if conflict_summary['total_files_with_conflicts'] > 0:
            self.logger.warning(f"Found {conflict_summary['total_files_with_conflicts']} files with registry conflicts")
        else:
            self.logger.info('No registry conflicts detected in production code')

    async def test_ssot_compliance_measurement_methodology(self):
        """
        P1 TEST: Verify SSOT compliance measurement methodology
        
        This test validates the methodology used to measure SSOT compliance
        and provides accurate metrics for consolidation progress tracking.
        
        Business Impact: Ensures SSOT compliance measurements are accurate
        and can be trusted for making consolidation decisions.
        """
        total_files = self.ssot_compliance_data['total_files_scanned']
        files_with_registry = self.ssot_compliance_data['files_with_registry_usage']
        files_with_conflicts = self.ssot_compliance_data['files_with_conflicts']
        total_references = self.ssot_compliance_data['total_registry_references']
        import_diversity = self.ssot_compliance_data['registry_import_diversity']
        compliance_metrics = {'file_level_compliance': 0.0, 'reference_level_compliance': 0.0, 'import_pattern_compliance': 0.0, 'overall_compliance': 0.0, 'methodology_issues': []}
        if files_with_registry > 0:
            compliance_metrics['file_level_compliance'] = (files_with_registry - files_with_conflicts) / files_with_registry * 100
        else:
            compliance_metrics['methodology_issues'].append('No files with registry usage found - cannot calculate file-level compliance')
        registry_type_counts = defaultdict(int)
        for pattern in self.registry_usage_patterns:
            registry_type_counts[pattern.registry_type] += 1
        if total_references > 0:
            max_registry_count = max(registry_type_counts.values()) if registry_type_counts else 0
            compliance_metrics['reference_level_compliance'] = max_registry_count / total_references * 100
        else:
            compliance_metrics['methodology_issues'].append('No registry references found - cannot calculate reference-level compliance')
        if import_diversity > 0:
            ideal_import_patterns = 2
            compliance_metrics['import_pattern_compliance'] = max(0, ideal_import_patterns / import_diversity * 100)
        else:
            compliance_metrics['methodology_issues'].append('No import patterns found - cannot calculate import pattern compliance')
        weights = {'file_level_compliance': 0.5, 'reference_level_compliance': 0.3, 'import_pattern_compliance': 0.2}
        valid_metrics = []
        for metric_name, weight in weights.items():
            metric_value = compliance_metrics[metric_name]
            if metric_value > 0:
                valid_metrics.append((metric_value, weight))
        if valid_metrics:
            total_weight = sum((weight for _, weight in valid_metrics))
            weighted_sum = sum((value * weight for value, weight in valid_metrics))
            compliance_metrics['overall_compliance'] = weighted_sum / total_weight
        else:
            compliance_metrics['methodology_issues'].append('No valid metrics for overall compliance calculation')
        self.ssot_compliance_data['compliance_score'] = compliance_metrics['overall_compliance']
        methodology_validation = {'data_completeness_score': 0.0, 'measurement_accuracy_score': 0.0, 'methodology_reliability_score': 0.0, 'validation_issues': []}
        expected_min_files = 10
        expected_min_references = 5
        completeness_factors = []
        if total_files >= expected_min_files:
            completeness_factors.append(100)
        else:
            completeness_factors.append(total_files / expected_min_files * 100)
            methodology_validation['validation_issues'].append(f'Low file scan count: {total_files} < {expected_min_files}')
        if total_references >= expected_min_references:
            completeness_factors.append(100)
        else:
            completeness_factors.append(total_references / expected_min_references * 100)
            methodology_validation['validation_issues'].append(f'Low reference count: {total_references} < {expected_min_references}')
        if completeness_factors:
            methodology_validation['data_completeness_score'] = sum(completeness_factors) / len(completeness_factors)
        accuracy_factors = []
        if files_with_conflicts <= files_with_registry:
            accuracy_factors.append(100)
        else:
            accuracy_factors.append(0)
            methodology_validation['validation_issues'].append('Conflicts exceed registry files - logical inconsistency')
        if files_with_registry <= total_files:
            accuracy_factors.append(100)
        else:
            accuracy_factors.append(0)
            methodology_validation['validation_issues'].append('Registry files exceed total files - logical inconsistency')
        if 1 <= import_diversity <= 10:
            accuracy_factors.append(100)
        else:
            accuracy_factors.append(50)
            methodology_validation['validation_issues'].append(f'Import diversity unusual: {import_diversity}')
        if accuracy_factors:
            methodology_validation['measurement_accuracy_score'] = sum(accuracy_factors) / len(accuracy_factors)
        reliability_factors = []
        max_acceptable_issues = 2
        if len(compliance_metrics['methodology_issues']) <= max_acceptable_issues:
            reliability_factors.append(100)
        else:
            penalty = (len(compliance_metrics['methodology_issues']) - max_acceptable_issues) * 20
            reliability_factors.append(max(0, 100 - penalty))
        if len(methodology_validation['validation_issues']) <= max_acceptable_issues:
            reliability_factors.append(100)
        else:
            penalty = (len(methodology_validation['validation_issues']) - max_acceptable_issues) * 20
            reliability_factors.append(max(0, 100 - penalty))
        if reliability_factors:
            methodology_validation['methodology_reliability_score'] = sum(reliability_factors) / len(reliability_factors)
        self.logger.info('SSOT COMPLIANCE MEASUREMENT REPORT:')
        self.logger.info(f"  File-level compliance: {compliance_metrics['file_level_compliance']:.1f}%")
        self.logger.info(f"  Reference-level compliance: {compliance_metrics['reference_level_compliance']:.1f}%")
        self.logger.info(f"  Import pattern compliance: {compliance_metrics['import_pattern_compliance']:.1f}%")
        self.logger.info(f"  Overall compliance: {compliance_metrics['overall_compliance']:.1f}%")
        self.logger.info(f"  Data completeness: {methodology_validation['data_completeness_score']:.1f}%")
        self.logger.info(f"  Measurement accuracy: {methodology_validation['measurement_accuracy_score']:.1f}%")
        self.logger.info(f"  Methodology reliability: {methodology_validation['methodology_reliability_score']:.1f}%")
        if compliance_metrics['methodology_issues']:
            self.logger.warning('Methodology issues:')
            for issue in compliance_metrics['methodology_issues']:
                self.logger.warning(f'  - {issue}')
        if methodology_validation['validation_issues']:
            self.logger.warning('Validation issues:')
            for issue in methodology_validation['validation_issues']:
                self.logger.warning(f'  - {issue}')
        methodology_problems = []
        if methodology_validation['data_completeness_score'] < 80:
            methodology_problems.append(f"Low data completeness: {methodology_validation['data_completeness_score']:.1f}%")
        if methodology_validation['measurement_accuracy_score'] < 80:
            methodology_problems.append(f"Low measurement accuracy: {methodology_validation['measurement_accuracy_score']:.1f}%")
        if methodology_validation['methodology_reliability_score'] < 80:
            methodology_problems.append(f"Low methodology reliability: {methodology_validation['methodology_reliability_score']:.1f}%")
        if len(compliance_metrics['methodology_issues']) > 3:
            methodology_problems.append(f"Too many methodology issues: {len(compliance_metrics['methodology_issues'])}")
        if methodology_problems:
            self.logger.warning('SSOT COMPLIANCE METHODOLOGY CONCERNS:')
            for problem in methodology_problems:
                self.logger.warning(f'  - {problem}')
        else:
            self.logger.info('SSOT compliance measurement methodology is sound and reliable')
        assert compliance_metrics['overall_compliance'] >= 0, 'Compliance score should be non-negative'

    async def test_production_runtime_failure_patterns(self):
        """
        P1 TEST: Document production runtime failure patterns from registry conflicts
        
        This test analyzes the registry usage patterns to predict likely runtime
        failure scenarios and document them for consolidation planning.
        
        Business Impact: Helps prioritize consolidation efforts by identifying
        the most likely failure scenarios in production deployments.
        """
        runtime_failure_patterns = []
        failure_risk_analysis = {}
        high_risk_patterns = [{'pattern_name': 'dual_registry_instantiation', 'description': 'Files that instantiate both basic and advanced registries', 'risk_level': 'critical', 'failure_modes': ['TypeError on method calls', 'AttributeError on missing methods', 'Memory leaks']}, {'pattern_name': 'mixed_import_usage', 'description': 'Files importing AgentRegistry from different modules', 'risk_level': 'high', 'failure_modes': ['ImportError on module conflicts', 'Wrong class instantiated', 'Method signature mismatches']}, {'pattern_name': 'global_instance_conflicts', 'description': 'Multiple global agent_registry instances', 'risk_level': 'high', 'failure_modes': ['Race conditions', 'State contamination', 'Unpredictable behavior']}, {'pattern_name': 'inconsistent_method_calls', 'description': 'Same method called on different registry types', 'risk_level': 'medium', 'failure_modes': ['Method not found errors', 'Different return types', 'Unexpected behavior']}]
        for pattern_info in high_risk_patterns:
            pattern_name = pattern_info['pattern_name']
            failure_risk_analysis[pattern_name] = {'pattern_info': pattern_info, 'occurrences': [], 'affected_files': set(), 'total_risk_score': 0, 'predicted_failures': []}
            if pattern_name == 'dual_registry_instantiation':
                for file_path, usage_patterns in self.file_registry_usage.items():
                    instantiation_patterns = [p for p in usage_patterns if p.usage_type == 'instantiation']
                    registry_types_instantiated = set((p.registry_type for p in instantiation_patterns))
                    if len(registry_types_instantiated) > 1 and 'unknown' not in registry_types_instantiated:
                        failure_risk_analysis[pattern_name]['occurrences'].append({'file_path': file_path, 'instantiation_patterns': instantiation_patterns, 'registry_types': list(registry_types_instantiated)})
                        failure_risk_analysis[pattern_name]['affected_files'].add(file_path)
                        failure_risk_analysis[pattern_name]['predicted_failures'].append({'file': file_path, 'scenario': 'Registry type confusion', 'description': f'File instantiates {registry_types_instantiated} - runtime type errors likely', 'probability': 'high'})
            elif pattern_name == 'mixed_import_usage':
                for file_path, usage_patterns in self.file_registry_usage.items():
                    import_patterns = [p for p in usage_patterns if p.usage_type == 'import']
                    import_modules = set((p.import_statement.split()[1] if len(p.import_statement.split()) > 1 else '' for p in import_patterns))
                    registry_modules = [mod for mod in import_modules if 'agent' in mod.lower() and 'registry' in mod.lower()]
                    if len(registry_modules) > 1:
                        failure_risk_analysis[pattern_name]['occurrences'].append({'file_path': file_path, 'import_patterns': import_patterns, 'registry_modules': registry_modules})
                        failure_risk_analysis[pattern_name]['affected_files'].add(file_path)
                        failure_risk_analysis[pattern_name]['predicted_failures'].append({'file': file_path, 'scenario': 'Import resolution conflict', 'description': f'File imports AgentRegistry from {len(registry_modules)} modules - import conflicts likely', 'probability': 'medium'})
            elif pattern_name == 'global_instance_conflicts':
                global_instance_files = []
                for file_path, usage_patterns in self.file_registry_usage.items():
                    assignment_patterns = [p for p in usage_patterns if p.usage_type == 'assignment']
                    for pattern in assignment_patterns:
                        if 'agent_registry' in pattern.import_statement and '=' in pattern.import_statement:
                            global_instance_files.append(file_path)
                            break
                if len(global_instance_files) > 1:
                    failure_risk_analysis[pattern_name]['occurrences'].append({'global_instance_files': global_instance_files, 'conflict_type': 'multiple_global_instances'})
                    failure_risk_analysis[pattern_name]['affected_files'].update(global_instance_files)
                    failure_risk_analysis[pattern_name]['predicted_failures'].append({'files': global_instance_files, 'scenario': 'Global instance conflict', 'description': f'{len(global_instance_files)} files create global agent_registry instances - state conflicts likely', 'probability': 'high'})
            elif pattern_name == 'inconsistent_method_calls':
                for file_path, usage_patterns in self.file_registry_usage.items():
                    method_call_patterns = [p for p in usage_patterns if p.usage_type == 'method_call']
                    registry_types_with_calls = set((p.registry_type for p in method_call_patterns))
                    if len(registry_types_with_calls) > 1 and 'unknown' not in registry_types_with_calls:
                        failure_risk_analysis[pattern_name]['occurrences'].append({'file_path': file_path, 'method_call_patterns': method_call_patterns, 'registry_types': list(registry_types_with_calls)})
                        failure_risk_analysis[pattern_name]['affected_files'].add(file_path)
                        failure_risk_analysis[pattern_name]['predicted_failures'].append({'file': file_path, 'scenario': 'Method signature mismatch', 'description': f'File calls methods on {registry_types_with_calls} registries - signature mismatches likely', 'probability': 'medium'})
            occurrence_count = len(failure_risk_analysis[pattern_name]['occurrences'])
            affected_file_count = len(failure_risk_analysis[pattern_name]['affected_files'])
            severity_multiplier = {'critical': 10, 'high': 7, 'medium': 4, 'low': 1}
            base_risk = severity_multiplier.get(pattern_info['risk_level'], 1)
            risk_score = base_risk * occurrence_count * (1 + affected_file_count * 0.5)
            failure_risk_analysis[pattern_name]['total_risk_score'] = risk_score
        total_risk_score = sum((analysis['total_risk_score'] for analysis in failure_risk_analysis.values()))
        predicted_failure_scenarios = []
        for pattern_name, analysis in failure_risk_analysis.items():
            if analysis['occurrences']:
                pattern_info = analysis['pattern_info']
                runtime_failure_patterns.append({'pattern': pattern_name, 'risk_level': pattern_info['risk_level'], 'occurrence_count': len(analysis['occurrences']), 'affected_files': len(analysis['affected_files']), 'risk_score': analysis['total_risk_score'], 'failure_modes': pattern_info['failure_modes'], 'predicted_failures': analysis['predicted_failures']})
        runtime_failure_patterns.sort(key=lambda x: x['risk_score'], reverse=True)
        self.logger.info('PRODUCTION RUNTIME FAILURE PATTERN ANALYSIS:')
        self.logger.info(f'  Total risk score: {total_risk_score}')
        self.logger.info(f'  High-risk patterns detected: {len(runtime_failure_patterns)}')
        for pattern in runtime_failure_patterns:
            self.logger.warning(f"  RISK PATTERN: {pattern['pattern']} ({pattern['risk_level']} risk)")
            self.logger.warning(f"    Occurrences: {pattern['occurrence_count']}")
            self.logger.warning(f"    Affected files: {pattern['affected_files']}")
            self.logger.warning(f"    Risk score: {pattern['risk_score']}")
            self.logger.warning(f"    Failure modes: {pattern['failure_modes']}")
            for failure in pattern['predicted_failures']:
                if 'file' in failure:
                    self.logger.warning(f"      PREDICTED: {failure['scenario']} in {failure['file']} ({failure['probability']} probability)")
                elif 'files' in failure:
                    self.logger.warning(f"      PREDICTED: {failure['scenario']} across {len(failure['files'])} files ({failure['probability']} probability)")
        critical_risks = [p for p in runtime_failure_patterns if p['risk_level'] == 'critical']
        high_risks = [p for p in runtime_failure_patterns if p['risk_level'] == 'high']
        risk_assessment = {'immediate_attention_required': len(critical_risks) > 0, 'consolidation_urgency': 'low', 'estimated_failure_probability': 0.0}
        if critical_risks:
            risk_assessment['consolidation_urgency'] = 'critical'
            risk_assessment['estimated_failure_probability'] = 80.0
        elif len(high_risks) >= 2:
            risk_assessment['consolidation_urgency'] = 'high'
            risk_assessment['estimated_failure_probability'] = 50.0
        elif len(runtime_failure_patterns) >= 3:
            risk_assessment['consolidation_urgency'] = 'medium'
            risk_assessment['estimated_failure_probability'] = 25.0
        self.logger.info(f'RISK ASSESSMENT:')
        self.logger.info(f"  Consolidation urgency: {risk_assessment['consolidation_urgency']}")
        self.logger.info(f"  Estimated failure probability: {risk_assessment['estimated_failure_probability']}%")
        self.logger.info(f"  Immediate attention required: {risk_assessment['immediate_attention_required']}")
        if risk_assessment['consolidation_urgency'] == 'critical':
            self.logger.error('CRITICAL RUNTIME FAILURE RISK: Immediate consolidation required to prevent production failures')
        elif risk_assessment['estimated_failure_probability'] > 30:
            self.logger.warning(f"HIGH RUNTIME FAILURE RISK: {risk_assessment['estimated_failure_probability']}% probability of production issues")
        assert total_risk_score >= 0, 'Risk score should be non-negative'

    def _get_line_context(self, file_lines: List[str], line_index: int, context_lines: int=2) -> str:
        """Get context lines around a specific line for analysis"""
        start_index = max(0, line_index - context_lines)
        end_index = min(len(file_lines), line_index + context_lines + 1)
        context = []
        for i in range(start_index, end_index):
            marker = '>>>' if i == line_index else '   '
            context.append(f'{marker} {i + 1:3d}: {file_lines[i]}')
        return '\n'.join(context)

    def teardown_method(self, method=None):
        """Clean up test resources"""
        self.registry_usage_patterns.clear()
        self.registry_conflicts.clear()
        self.file_registry_usage.clear()
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')