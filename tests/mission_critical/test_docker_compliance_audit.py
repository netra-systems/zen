#!/usr/bin/env python3
'''
Mission Critical Test: Docker Management Compliance Audit

TEAM DELTA INFRASTRUCTURE TESTS: Comprehensive compliance auditing and enforcement
LIFE OR DEATH CRITICAL: Platform MUST enforce Docker management compliance at all times

This test ensures that ALL Docker operations in the codebase use the UnifiedDockerManager
and that no manual docker-compose commands are being executed outside of the central manager.

CRITICAL: Per CLAUDE.md Section 7.1, all Docker operations MUST go through UnifiedDockerManager.

INFRASTRUCTURE VALIDATION:
- Compliance auditing and violation detection
- Performance impact of compliance enforcement
- Automated remediation and fix generation
- Continuous monitoring and alerting for violations
- Risk assessment and impact analysis
- Cross-platform compliance validation
'''

import os
import sys
import re
import subprocess
import logging
import time
import threading
import statistics
import psutil
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import ast
from shared.isolated_environment import IsolatedEnvironment

    # Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import UnifiedDockerManager, get_default_manager

logging.basicConfig( )
level=logging.INFO,
format='%(asctime)s | %(levelname)s | %(message)s',
datefmt='%Y-%m-%d %H:%M:%S'
    
logger = logging.getLogger(__name__)


class DockerComplianceAuditor:
    "Audits codebase for Docker management compliance

    # Files that are allowed to have docker-compose references for documentation
    DOCUMENTATION_EXCEPTIONS = {
    'DOCKER_QUICKSTART.md',
    'DOCKER_README.md',
    'docker-compose.yml',  # The actual compose file
    'AUDIT_DOCKER_TEST_ORCHESTRATION.md',
    'DEPLOYMENT_CHECKLIST.md',
    'DOCKER_REFRESH_GUIDE.md',
    'docker_orchestration.md',
    'TESTING_GUIDE.md',
    'PORT_ALLOCATION.md',
    'ORCHESTRATION_SYSTEM_GUIDE.md',
    'docker-dual-environment-setup.md',
    'DOCKER_INTENT_CLARIFICATION.md'
    

    # Files that must use UnifiedDockerManager
    MUST_USE_MANAGER = {
    'unified_test_runner.py',
    'docker_manual.py',
    'refresh_dev_services.py',
    'integrated_test_runner.py',
    'test_adaptive_workflow.py',
    'intelligent_docker_remediation.py',
    'intelligent_remediation_orchestrator.py'
    

    def __init__(self):
        pass
        self.project_root = project_root
        self.violations = []
        self.compliant_files = []
        self.manager = get_default_manager()

    def audit_file_for_docker_commands(self, file_path: Path) -> List[Dict]:
        ""Check a file for direct docker/docker-compose commands
        violations = []

    # Skip non-Python and non-script files for command analysis
        if file_path.suffix not in ['.py', '.sh', '.bat', '.ps1']:
        return violations

        try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.split( )"
        )

        for line_num, line in enumerate(lines, 1):
                    # Skip comments
        if line.strip().startswith('#'):
        continue

                        # Check for subprocess calls to docker/docker-compose
        if re.search(rsubprocess\.(run|call|check_call|check_output|Popen)\s*\([^)]*["\]docker(-compose)?[\s], line):
                            # Check if it's using UnifiedDockerManager context
        context_start = max(0, line_num - 10)
        context_end = min(len(lines), line_num + 10)
        context = 
        ".join(lines[context_start:context_end]"

        if 'UnifiedDockerManager' not in context and 'get_default_manager' not in context:
        violations.append({}
        'file': str(file_path.relative_to(self.project_root)),
        'line': line_num,
        'content': line.strip(),
        'type': 'subprocess_docker_call'
                                

                                # Check for os.system calls to docker
        if re.search(ros\.system\s*\([^)]*[\]docker(-compose)?[\s], line):
        violations.append({}
        'file': str(file_path.relative_to(self.project_root)),
        'line': line_num,
        'content': line.strip(),
        'type': 'os_system_docker_call'
                                    

                                    # Check for direct docker-compose commands in shell scripts
        if file_path.suffix in ['.sh', '.bat'] and re.search(r'^docker(-compose)?\s+', line.strip()):
                                        # Check if it's in a function that wraps UnifiedDockerManager
        if 'docker_manual.py' not in line and 'unified_docker_manager' not in line.lower():
        violations.append({}
        'file': str(file_path.relative_to(self.project_root)),
        'line': line_num,
        'content': line.strip(),
        'type': 'shell_docker_command'
                                            

        except Exception as e:
        logger.warning(formatted_string)"

        return violations

    def verify_unified_manager_usage(self, file_path: Path) -> bool:
        "Verify that a file properly uses UnifiedDockerManager
        if file_path.suffix != '.py':
        return True

        try:
        with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

                # Check for proper imports
        has_manager_import = any([]
        'from test_framework.unified_docker_manager import' in content,
        'import test_framework.unified_docker_manager' in content,
        'get_default_manager' in content
                

                # Check if file needs Docker functionality
        needs_docker = any([]
        'docker' in content.lower(),
        'container' in content.lower(),
        'compose' in content.lower()
                

                If it needs Docker and is in MUST_USE_MANAGER list, it must import the manager
        if file_path.name in self.MUST_USE_MANAGER and needs_docker:
        return has_manager_import

        return True

        except Exception as e:
        logger.warning(formatted_string")"
        return True

    def audit_frontend_service_integration(self) -> Dict:
        Verify frontend service is properly integrated in UnifiedDockerManager"
        results = {
        'frontend_in_configs': False,
        'frontend_in_health_checks': False,
        'frontend_in_port_mappings': False,
        'frontend_dockerfile_exists': False
    

    # Check UnifiedDockerManager configuration
        manager_path = self.project_root / 'test_framework' / 'unified_docker_manager.py'
        if manager_path.exists():
        with open(manager_path, 'r') as f:
        content = f.read()

            # Check SERVICE_CONFIGS
        if 'frontend"' in content and 'SERVICE_CONFIGS' in content:
        results['frontend_in_configs'] = True

                # Check health check logic
        if 'frontend' in content and 'health' in content.lower():
        results['frontend_in_health_checks'] = True

                    # Check port mappings
        if 'frontend: 3000' in content or 'frontend': 3000 in content:
        results['frontend_in_port_mappings'] = True

                        # Check for frontend Dockerfile
        frontend_dockerfile = self.project_root / 'docker' / 'frontend.Dockerfile'
        if frontend_dockerfile.exists():
        results['frontend_dockerfile_exists'] = True

        return results

    def run_audit(self) -> Dict:
        "Run complete Docker compliance audit"
        logger.info( SEARCH:  Starting Docker Management Compliance Audit...)"

    # Find all relevant files
        patterns = ['**/*.py', '**/*.sh', '**/*.bat', '**/*.ps1']
        all_files = []
        for pattern in patterns:
        all_files.extend(self.project_root.glob(pattern))

        # Audit each file
        for file_path in all_files:
            # Skip documentation and test data
        relative_path = file_path.relative_to(self.project_root)
        if any(exc in str(relative_path) for exc in self.DOCUMENTATION_EXCEPTIONS):
        continue

                # Skip __pycache__ and .git
        if '__pycache__' in str(relative_path) or '.git' in str(relative_path):
        continue

                    # Check for violations
        file_violations = self.audit_file_for_docker_commands(file_path)
        if file_violations:
        self.violations.extend(file_violations)

                        # Verify proper usage in critical files
        if file_path.name in self.MUST_USE_MANAGER:
        if self.verify_unified_manager_usage(file_path):
        self.compliant_files.append(str(relative_path))
        else:
        self.violations.append({}
        'file': str(relative_path),
        'line': 0,
        'content': 'Missing UnifiedDockerManager import',
        'type': 'missing_manager_import'
                                    

                                    # Audit frontend service integration
        frontend_status = self.audit_frontend_service_integration()

                                    # Generate report
        report = {
        'total_files_audited': len(all_files),
        'violations_found': len(self.violations),
        'compliant_critical_files': len(self.compliant_files),
        'frontend_integration': frontend_status,
        'violations': self.violations[:10] if self.violations else [],  # Show first 10
        'compliance_score': 100 - (len(self.violations) * 2)  # Deduct 2% per violation
                                    

        return report

    def generate_remediation_script(self) -> str:
        "Generate a script to fix violations
        script = []
        script.append(#!/usr/bin/env python3")"
        script.append(# Auto-generated Docker compliance remediation script)
        script.append()"
        script.append("import sys)
        script.append(from pathlib import Path)
        script.append("sys.path.insert(0, str(Path(__file__).parent.parent)))"
        script.append()
        script.append(from test_framework.unified_docker_manager import get_default_manager)"
        script.append(")
        script.append(# Initialize central Docker manager)
        script.append(manager = get_default_manager()")"
        script.append()

    # Add remediation for each violation type
        for violation in self.violations:
        if violation['type'] == 'subprocess_docker_call':
        script.append(formatted_string)"
        script.append("
        script.append(# With: manager.execute_docker_command(...))"
        script.append(")

        return 
        .join(script)


        @dataclass
class ComplianceMetrics:
        "Metrics for Docker compliance auditing."
        total_files_scanned: int = 0
        violations_detected: int = 0
        compliance_score: float = 0.0
        audit_duration_ms: float = 0.0
        memory_usage_mb: float = 0.0
        false_positive_rate: float = 0.0
        remediation_time_estimate: float = 0.0
        risk_score: float = 0.0
        violation_categories: Dict[str, int] = field(default_factory=dict)


class DockerComplianceInfrastructureTests:
        "Infrastructure tests for Docker compliance auditing."

    def __init__(self):
        pass
        self.logger = logging.getLogger("
        self.project_root = project_root

    def test_compliance_audit_performance_scalability(self) -> ComplianceMetrics:
        "Test performance and scalability of compliance auditing.
        self.logger.info(" CHART:  Testing compliance audit performance scalability)"

        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        start_time = time.time()

    # Run compliance audit with performance monitoring
        auditor = DockerComplianceAuditor()
        audit_report = auditor.run_audit()

        audit_duration = (time.time() - start_time) * 1000
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        memory_usage = final_memory - initial_memory

    # Calculate metrics
        metrics = ComplianceMetrics( )
        total_files_scanned=audit_report['total_files_audited'],
        violations_detected=audit_report['violations_found'],
        compliance_score=audit_report['compliance_score'],
        audit_duration_ms=audit_duration,
        memory_usage_mb=memory_usage,
        violation_categories=self._categorize_violations(audit_report.get('violations', [])
    

    # Performance benchmarks
        files_per_second = metrics.total_files_scanned / (audit_duration / 1000) if audit_duration > 0 else 0
        memory_per_file = memory_usage / metrics.total_files_scanned if metrics.total_files_scanned > 0 else 0

        self.logger.info(f PASS:  Compliance audit performance:)
        self.logger.info(""
        self.logger.info(formatted_string)
        self.logger.info(""
        self.logger.info(formatted_string)
        self.logger.info(""
        self.logger.info(formatted_string)
        self.logger.info(""

    # Performance assertions
        assert files_per_second > 50, formatted_string
        assert memory_per_file < 0.5, formatted_string"
        assert audit_duration < 30000, formatted_string"

        return metrics

    def test_compliance_violation_detection_accuracy(self) -> Dict[str, Any]:
        Test accuracy of compliance violation detection.""
        self.logger.info( SEARCH:  Testing compliance violation detection accuracy)

    # Create test files with known violations and compliant code
        test_cases = self._create_compliance_test_cases()

        detection_results = []
        for test_case in test_cases:
        # Write test file
        test_file = self.project_root / temp_compliance_test.py"
        try:
        with open(test_file, 'w') as f:
        f.write(test_case['code']

                # Run audit on test file
        auditor = DockerComplianceAuditor()
        violations = auditor.audit_file_for_docker_commands(test_file)

                # Analyze results
        expected_violations = test_case['expected_violations']
        detected_violations = len(violations)

        detection_results.append({}
        'test_name': test_case['name'],
        'expected': expected_violations,
        'detected': detected_violations,
        'accurate': expected_violations == detected_violations,
        'false_positives': max(0, detected_violations - expected_violations),
        'false_negatives': max(0, expected_violations - detected_violations),
        'violation_types': [v['type'] for v in violations]
                

        finally:
                    # Clean up test file
        if test_file.exists():
        test_file.unlink()

                        # Calculate accuracy metrics
        total_tests = len(detection_results)
        accurate_tests = sum(1 for r in detection_results if r['accurate']
        accuracy_rate = (accurate_tests / total_tests) * 100 if total_tests > 0 else 0

        total_false_positives = sum(r['false_positives'] for r in detection_results)
        total_false_negatives = sum(r['false_negatives'] for r in detection_results)

        false_positive_rate = (total_false_positives / total_tests) if total_tests > 0 else 0
        false_negative_rate = (total_false_negatives / total_tests) if total_tests > 0 else 0

        self.logger.info(f PASS:  Violation detection accuracy:")
        self.logger.info("
        self.logger.info(formatted_string")
        self.logger.info("
        self.logger.info(formatted_string")

                        # Accuracy assertions
        assert accuracy_rate >= 90, formatted_string
        assert false_positive_rate <= 0.1, formatted_string""
        assert false_negative_rate <= 0.05, formatted_string

        return {
        'accuracy_rate': accuracy_rate,
        'false_positive_rate': false_positive_rate,
        'false_negative_rate': false_negative_rate,
        'test_results': detection_results
                        

    def test_automated_remediation_effectiveness(self) -> Dict[str, Any]:
        "Test effectiveness of automated compliance remediation."
        self.logger.info([U+1F527] Testing automated remediation effectiveness)

    # Create files with known violations
        violations_created = []
        remediation_results = []

        test_violations = [
        {
        'name': 'subprocess_docker_call',
        code": "import subprocess
        subprocess.run([docker, ps],
        'expected_fix': 'manager.execute_docker_command'
        },
        {
        'name': 'os_system_docker_call',
        code: "import os
        os.system(docker-compose up)",
        'expected_fix': 'manager.docker_compose_command'
    
    

        for violation in test_violations:
        test_file = self.project_root / formatted_string
        try:
            # Create violation
        with open(test_file, 'w') as f:
        f.write(violation['code']

                # Run audit to detect violation
        auditor = DockerComplianceAuditor()
        initial_violations = auditor.audit_file_for_docker_commands(test_file)

                # Generate remediation script
        remediation_script = auditor.generate_remediation_script()

                # Measure remediation quality
        remediation_quality = self._assess_remediation_quality( )
        violation['code'],
        remediation_script,
        violation['expected_fix']
                

        remediation_results.append({}
        'violation_type': violation['name'],
        'initial_violations': len(initial_violations),
        'remediation_generated': len(remediation_script) > 0,
        'quality_score': remediation_quality['score'],
        'contains_expected_fix': remediation_quality['contains_expected_fix'],
        remediation_lines": len(remediation_script.split(" ))
        ))
                

        finally:
        if test_file.exists():
        test_file.unlink()

                        # Calculate remediation effectiveness
        total_remediations = len(remediation_results)
        successful_remediations = sum(1 for r in remediation_results if r['remediation_generated']
        quality_scores = [r['quality_score'] for r in remediation_results]
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0

        effectiveness_rate = (successful_remediations / total_remediations) * 100 if total_remediations > 0 else 0

        self.logger.info(f PASS:  Automated remediation effectiveness:)
        self.logger.info(""
        self.logger.info(formatted_string)
        self.logger.info(""

                        # Effectiveness assertions
        assert effectiveness_rate >= 80, formatted_string
        assert avg_quality >= 6.0, formatted_string"

        return {
        'effectiveness_rate': effectiveness_rate,
        'average_quality': avg_quality,
        'remediation_results': remediation_results
                        

    def test_continuous_monitoring_performance(self) -> Dict[str, Any]:
        "Test performance of continuous compliance monitoring.
        self.logger.info(" CHART:  Testing continuous compliance monitoring)"

        monitoring_results = []

    def compliance_monitoring_cycle(cycle_id: int) -> Dict[str, Any]:
        Single monitoring cycle for performance testing."
        start_time = time.time()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)

        try:
        # Run lightweight compliance check
        auditor = DockerComplianceAuditor()

        # Simulate monitoring specific files
        critical_files = [
        self.project_root / 'scripts' / 'docker_manual.py',
        self.project_root / 'tests' / 'unified_test_runner.py'
        

        violations_found = 0
        for file_path in critical_files:
        if file_path.exists():
        file_violations = auditor.audit_file_for_docker_commands(file_path)
        violations_found += len(file_violations)

        monitoring_time = (time.time() - start_time) * 1000
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        memory_delta = final_memory - initial_memory

        return {
        'cycle_id': cycle_id,
        'monitoring_time_ms': monitoring_time,
        'memory_delta_mb': memory_delta,
        'violations_found': violations_found,
        'files_monitored': len([item for item in []],
        'success': True
                

        except Exception as e:
        return {
        'cycle_id': cycle_id,
        'monitoring_time_ms': time.time() - start_time * 1000,
        'memory_delta_mb': 0,
        'violations_found': 0,
        'files_monitored': 0,
        'success': False,
        'error': str(e)
                    

                    # Run multiple monitoring cycles concurrently
        monitoring_cycles = 10
        with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(compliance_monitoring_cycle, i) for i in range(monitoring_cycles)]

        for future in futures:
        try:
        result = future.result(timeout=30)
        monitoring_results.append(result)
        except Exception as e:
        monitoring_results.append({}
        'success': False,
        'error': "formatted_string,
        'monitoring_time_ms': 30000
                                    

                                    # Analyze monitoring performance
        successful_cycles = [item for item in []]
        failed_cycles = len(monitoring_results) - len(successful_cycles)

        if successful_cycles:
        avg_monitoring_time = statistics.mean([r['monitoring_time_ms'] for r in successful_cycles]
        max_monitoring_time = max([r['monitoring_time_ms'] for r in successful_cycles]
        avg_memory_delta = statistics.mean([abs(r['memory_delta_mb'] for r in successful_cycles]
        total_violations = sum([r['violations_found'] for r in successful_cycles]
        else:
        avg_monitoring_time = 0
        max_monitoring_time = 0
        avg_memory_delta = 0
        total_violations = 0

        success_rate = (len(successful_cycles) / len(monitoring_results)) * 100 if monitoring_results else 0

        self.logger.info(f PASS:  Continuous monitoring performance:)
        self.logger.info(""
        self.logger.info(formatted_string)
        self.logger.info(""
        self.logger.info(formatted_string)
        self.logger.info(""
        self.logger.info(formatted_string)
        self.logger.info(""

                                            # Performance assertions
        assert success_rate >= 95, formatted_string
        assert avg_monitoring_time < 1000, ""
        assert max_monitoring_time < 5000, formatted_string
        assert failed_cycles == 0, formatted_string"

        return {
        'success_rate': success_rate,
        'avg_monitoring_time_ms': avg_monitoring_time,
        'max_monitoring_time_ms': max_monitoring_time,
        'avg_memory_delta_mb': avg_memory_delta,
        'total_violations': total_violations,
        'monitoring_results': successful_cycles
                                            

    def test_risk_assessment_and_impact_analysis(self) -> Dict[str, Any]:
        "Test risk assessment and impact analysis for compliance violations.
        self.logger.info(" WARNING: [U+FE0F] Testing risk assessment and impact analysis)"

    # Run compliance audit to get current violations
        auditor = DockerComplianceAuditor()
        audit_report = auditor.run_audit()

        violations = audit_report.get('violations', []
        risk_assessments = []

    # Assess risk for each violation type
        violation_risk_matrix = {
        'subprocess_docker_call': {
        'severity': 'HIGH',
        'impact_score': 8.5,
        'likelihood': 0.7,
        'remediation_effort': 'MEDIUM'
        },
        'os_system_docker_call': {
        'severity': 'CRITICAL',
        'impact_score': 9.2,
        'likelihood': 0.8,
        'remediation_effort': 'HIGH'
        },
        'shell_docker_command': {
        'severity': 'MEDIUM',
        'impact_score': 6.5,
        'likelihood': 0.5,
        'remediation_effort': 'LOW'
        },
        'missing_manager_import': {
        'severity': 'HIGH',
        'impact_score': 8.0,
        'likelihood': 0.9,
        'remediation_effort': 'LOW'
    
    

    # Calculate risk metrics
        total_risk_score = 0
        violation_counts = {}

        for violation in violations:
        violation_type = violation.get('type', 'unknown')
        violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1

        if violation_type in violation_risk_matrix:
        risk_data = violation_risk_matrix[violation_type]
        risk_score = risk_data['impact_score'] * risk_data['likelihood']
        total_risk_score += risk_score

        risk_assessments.append({}
        'violation_type': violation_type,
        'file': violation.get('file', 'unknown'),
        'line': violation.get('line', 0),
        'severity': risk_data['severity'],
        'impact_score': risk_data['impact_score'],
        'likelihood': risk_data['likelihood'],
        'risk_score': risk_score,
        'remediation_effort': risk_data['remediation_effort']
            

            # Calculate aggregate risk metrics
        total_violations = len(violations)
        avg_risk_score = total_risk_score / total_violations if total_violations > 0 else 0

            # Categorize overall risk level
        if avg_risk_score >= 8.0:
        overall_risk_level = 'CRITICAL'
        elif avg_risk_score >= 6.0:
        overall_risk_level = 'HIGH'
        elif avg_risk_score >= 4.0:
        overall_risk_level = 'MEDIUM'
        else:
        overall_risk_level = 'LOW'

                            # Estimate remediation time
        effort_weights = {'LOW': 1, 'MEDIUM': 3, 'HIGH': 8}
        total_remediation_effort = 0
        for assessment in risk_assessments:
        effort = effort_weights.get(assessment['remediation_effort'], 3)
        total_remediation_effort += effort

                                # Assume 1 hour per effort unit
        estimated_remediation_hours = total_remediation_effort

        self.logger.info(f PASS:  Risk assessment and impact analysis:)
        self.logger.info(""
        self.logger.info(formatted_string)
        self.logger.info(""
        self.logger.info(formatted_string)

                                # Log violation breakdown
        for violation_type, count in violation_counts.items():
        self.logger.info(""

                                    # Risk assertions - adjust based on acceptable risk levels
        assert overall_risk_level in ['LOW', 'MEDIUM'], formatted_string
        assert avg_risk_score < 7.0, formatted_string"
        assert estimated_remediation_hours < 40, formatted_string"

        return {
        'total_violations': total_violations,
        'avg_risk_score': avg_risk_score,
        'overall_risk_level': overall_risk_level,
        'estimated_remediation_hours': estimated_remediation_hours,
        'violation_counts': violation_counts,
        'risk_assessments': risk_assessments
                                    

    def test_cross_platform_compliance_validation(self) -> Dict[str, Any]:
        Test compliance validation across different platforms.""
        self.logger.info([U+1F310] Testing cross-platform compliance validation)

        platform_results = {}
        current_platform = os.name

    # Test platform-specific file patterns
        platform_patterns = {
        'nt': ['**/*.bat', '**/*.ps1'],  # Windows
        'posix': ['**/*.sh']  # Unix/Linux/macOS
    

        patterns_to_test = platform_patterns.get(current_platform, ['**/*.sh']

        for pattern in patterns_to_test:
        pattern_violations = []
        pattern_files = []

        try:
        files = list(self.project_root.glob(pattern))
        pattern_files = [str(f.relative_to(self.project_root)) for f in files]

            # Audit platform-specific files
        auditor = DockerComplianceAuditor()
        for file_path in files:
        if file_path.exists():
        file_violations = auditor.audit_file_for_docker_commands(file_path)
        pattern_violations.extend(file_violations)

        platform_results[pattern] = {
        'files_found': len(files),
        'violations_found': len(pattern_violations),
        'compliance_rate': ((len(files) - len(pattern_violations)) / len(files) * 100) if files else 100,
        'files_list': pattern_files[:10],  # Show first 10 files
        'violations': pattern_violations[:5]  # Show first 5 violations
                    

        except Exception as e:
        platform_results[pattern] = {
        'files_found': 0,
        'violations_found': 0,
        'compliance_rate': 100,
        'error': str(e)
                        

                        # Test Docker Compose file compatibility
        compose_files = ['docker-compose.yml', 'docker-compose.dev.yml', 'docker-compose.test.yml']
        compose_compatibility = {}

        for compose_file in compose_files:
        compose_path = self.project_root / compose_file
        if compose_path.exists():
        try:
        with open(compose_path, 'r') as f:
        content = f.read()

                                        # Check for platform-specific configurations
        has_windows_paths = '\\' in content and 'volumes:' in content
        has_unix_paths = content.count('/') > content.count('\\')
        has_env_vars = '${' in content )

        compose_compatibility[compose_file] = {
        'exists': True,
        'has_windows_paths': has_windows_paths,
        'has_unix_paths': has_unix_paths,
        'has_env_vars': has_env_vars,
        'size_bytes': len(content),
        'cross_platform_ready': not has_windows_paths or has_env_vars
                                        

        except Exception as e:
        compose_compatibility[compose_file] = {
        'exists': True,
        'error': str(e)
                                            
        else:
        compose_compatibility[compose_file] = {'exists': False}

                                                # Calculate overall cross-platform compliance
        total_files_checked = sum(result.get('files_found', 0) for result in platform_results.values())
        total_violations = sum(result.get('violations_found', 0) for result in platform_results.values())

        cross_platform_compliance = ((total_files_checked - total_violations) / total_files_checked * 100) if total_files_checked > 0 else 100

        self.logger.info(f PASS:  Cross-platform compliance validation:)
        self.logger.info(formatted_string")"
        self.logger.info(
        self.logger.info(formatted_string")"
        self.logger.info(

                                                # Log platform-specific results
        for pattern, result in platform_results.items():
        if 'error' not in result:
        self.logger.info(formatted_string")"

                                                        # Cross-platform assertions
        assert cross_platform_compliance >= 95, formatted_string

                                                        # Ensure at least one Docker Compose file exists
        existing_compose_files = [item for item in []]
        assert len(existing_compose_files) > 0, No Docker Compose files found"

        return {
        'platform': current_platform,
        'cross_platform_compliance': cross_platform_compliance,
        'total_files_checked': total_files_checked,
        'total_violations': total_violations,
        'platform_results': platform_results,
        'compose_compatibility': compose_compatibility
                                                        

                                                        # Helper methods
    def _categorize_violations(self, violations: List[Dict] -> Dict[str, int]:
        "Categorize violations by type.
        categories = {}
        for violation in violations:
        violation_type = violation.get('type', 'unknown')
        categories[violation_type] = categories.get(violation_type, 0) + 1
        return categories

    def _create_compliance_test_cases(self) -> List[Dict[str, Any]]:
        ""Create test cases for compliance violation detection.
        return [
        {
        'name': 'compliant_code',
        code: from test_framework.unified_docker_manager import get_default_manager"
        manager = get_default_manager()
        manager.start_services()",
        'expected_violations': 0
        },
        {
        'name': 'subprocess_violation',
        code: import subprocess
        subprocess.run(["docker", ps],
        'expected_violations': 1
        },
        {
        'name': 'os_system_violation',
        code: import os"
        os.system("docker-compose up -d),
        'expected_violations': 1
        },
        {
        'name': 'multiple_violations',
        code: import subprocess
        import os
        subprocess.run([docker, "ps"]
        os.system(docker stop container),
        'expected_violations': 2
        },
        {
        'name': 'commented_violation',
        code: # subprocess.run(["docker", ps]
        print(This is fine),
        'expected_violations': 0
    
    

    def _assess_remediation_quality(self, original_code: str, remediation_script: str, expected_fix: str") -> Dict[str, Any]:
        "Assess the quality of generated remediation script.

    # Basic quality indicators
        quality_score = 0
        contains_expected_fix = expected_fix in remediation_script

        if contains_expected_fix:
        quality_score += 5

        # Check for proper structure
        if 'get_default_manager' in remediation_script:
        quality_score += 2

        if 'manager =' in remediation_script:
        quality_score += 2

        if len(remediation_script) > 100:  # Reasonable length
        quality_score += 1

        return {
        'score': quality_score,
        'contains_expected_fix': contains_expected_fix,
        'script_length': len(remediation_script)
                


    def test_docker_compliance():
        "Main test function for Docker compliance"
        auditor = DockerComplianceAuditor()
        report = auditor.run_audit()

    # Print report
        print(")"
         + =*80)
        print("DOCKER MANAGEMENT COMPLIANCE AUDIT REPORT")
        print(=*80)
        print()
        print(formatted_string")
        print("")
        print(formatted_string)

        print("")
        [U+1F4E6] Frontend Service Integration Status:)
        for key, value in report['frontend_integration'].items("):
        status =  PASS:  if value else  FAIL: 
        print(formatted_string")"

        if report['violations']:
        print()
        WARNING: [U+FE0F] Violations Found (showing first 10):)
        for v in report['violations'][:10]:
        print("")
        print(formatted_string)

                # Generate remediation script if violations found
        if report['violations']:
        remediation_script = auditor.generate_remediation_script()
        script_path = auditor.project_root / 'scripts' / 'docker_compliance_remediation.py'
        with open(script_path, 'w') as f:
        f.write(remediation_script)
        print()

                        # Fail test if compliance score is below threshold
        assert report['compliance_score'] >= 95, formatted_string

                        # Verify frontend integration
        frontend_checks = report['frontend_integration']
        assert all(frontend_checks.values()"), "

        print()
        PASS:  Docker Management Compliance Test PASSED)
        return True


        if __name__ == "__main__:"
        try:
        success = test_docker_compliance()
        sys.exit(0 if success else 1)
        except AssertionError as e:
        logger.error(formatted_string)
        sys.exit(1)
        except Exception as e:
        logger.error(")
        sys.exit(1)
        pass
))