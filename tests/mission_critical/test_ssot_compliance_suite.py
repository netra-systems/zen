from shared.isolated_environment import get_env
"""
env = get_env()
SSOT Compliance Validation Suite - MISSION CRITICAL
==================================================

CRITICAL MISSION: Validate ALL SSOT fixes made to the Netra platform.

Business Value Justification:
- Segment: Platform/Internal - System Stability & Architecture Compliance
- Business Goal: Platform Stability & Development Velocity 
- Value Impact: Protects $1.8M+ ARR from SSOT violations causing chat failures, security breaches, and system instability
- Strategic Impact: Ensures Single Source of Truth compliance across all major subsystems

CRITICAL FIXES TO VALIDATE:
1. WebSocket Manager consolidation - Single manager, no duplicates
2. JWT validation security - No local validation, all through auth service
3. Agent Registry consolidation - Single registry with WebSocket integration
4. IsolatedEnvironment consolidation - Single shared implementation
5. Session Management consolidation - Redis-based canonical
6. Tool Execution Engine consolidation - Single implementation, no duplicates

This test suite MUST PASS before deployment and serves as a regression guard
against reintroducing any SSOT violations.

Author: Principal Engineering Team
Date: 2025-08-31
"""

import ast
import asyncio
import json
import os
import sys
import time
import subprocess
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict
import pytest

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.environment_isolation import get_test_env_manager


@dataclass
class SSotViolation:
    """Structure for SSOT violations."""
    violation_type: str
    file_path: str
    line_number: Optional[int]
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    business_impact: str


@dataclass 
class SSotComplianceResults:
    """SSOT compliance validation results."""
    overall_compliance_score: float
    websocket_manager_violations: List[SSotViolation]
    jwt_validation_violations: List[SSotViolation] 
    agent_registry_violations: List[SSotViolation]
    isolated_environment_violations: List[SSotViolation]
    session_management_violations: List[SSotViolation]
    tool_execution_violations: List[SSotViolation]
    direct_os_environ_violations: List[SSotViolation]
    total_violations: int
    critical_violations: int
    high_violations: int
    recommendations: List[str]


class SSotComplianceSuite:
    """Comprehensive SSOT compliance validation suite."""
    
    def __init__(self):
        """Initialize SSOT compliance suite."""
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.violations: List[SSotViolation] = []
        self.compliance_results = SSotComplianceResults(
            overall_compliance_score=0.0,
            websocket_manager_violations=[],
            jwt_validation_violations=[],
            agent_registry_violations=[],
            isolated_environment_violations=[],
            session_management_violations=[],
            tool_execution_violations=[],
            direct_os_environ_violations=[],
            total_violations=0,
            critical_violations=0,
            high_violations=0,
            recommendations=[]
        )
    
    def validate_websocket_manager_consolidation(self) -> List[SSotViolation]:
        """
        Validate WebSocket Manager consolidation - CRITICAL for chat functionality.
        
        BUSINESS IMPACT: $500K+ ARR at risk from chat failures if duplicates exist.
        """
        violations = []
        
        # Check for forbidden duplicate WebSocket managers
        forbidden_files = [
            'netra_backend/app/websocket_core/manager_ttl_implementation.py',
            'netra_backend/app/websocket/connection_manager.py'
        ]
        
        for forbidden_file in forbidden_files:
            file_path = self.project_root / forbidden_file
            if file_path.exists():
                violations.append(SSotViolation(
                    violation_type="DUPLICATE_WEBSOCKET_MANAGER",
                    file_path=str(file_path),
                    line_number=None,
                    description=f"Forbidden duplicate WebSocket manager still exists: {forbidden_file}",
                    severity="CRITICAL",
                    business_impact="Chat functionality at risk - WebSocket events may not reach users"
                ))
        
        # Validate canonical WebSocket manager exists and is properly structured
        canonical_manager = self.project_root / 'netra_backend/app/websocket_core/manager.py'
        if not canonical_manager.exists():
            violations.append(SSotViolation(
                violation_type="MISSING_CANONICAL_WEBSOCKET_MANAGER",
                file_path=str(canonical_manager),
                line_number=None,
                description="Canonical WebSocket manager is missing",
                severity="CRITICAL",
                business_impact="No WebSocket functionality - complete chat failure"
            ))
        else:
            # Validate canonical manager has singleton pattern
            try:
                with open(canonical_manager, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for singleton pattern
                if '_instance' not in content or '__new__' not in content:
                    violations.append(SSotViolation(
                        violation_type="MISSING_SINGLETON_PATTERN", 
                        file_path=str(canonical_manager),
                        line_number=None,
                        description="WebSocket manager missing singleton pattern",
                        severity="HIGH",
                        business_impact="Multiple WebSocket manager instances possible"
                    ))
                
                # Check for critical methods
                required_methods = [
                    'connect_user', 'disconnect_user', 'send_to_user', 
                    'broadcast_to_room', 'get_stats'
                ]
                for method in required_methods:
                    if f'def {method}(' not in content:
                        violations.append(SSotViolation(
                            violation_type="MISSING_CRITICAL_METHOD",
                            file_path=str(canonical_manager),
                            line_number=None,
                            description=f"Missing critical method: {method}",
                            severity="HIGH",
                            business_impact="WebSocket functionality incomplete"
                        ))
                        
            except Exception as e:
                violations.append(SSotViolation(
                    violation_type="WEBSOCKET_MANAGER_READ_ERROR",
                    file_path=str(canonical_manager),
                    line_number=None,
                    description=f"Could not validate WebSocket manager: {e}",
                    severity="HIGH", 
                    business_impact="WebSocket manager validation failed"
                ))
        
        # Check for imports of forbidden managers
        python_files = list(self.project_root.rglob('*.py'))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                forbidden_imports = [
                    'from netra_backend.app.websocket_core.manager_ttl_implementation',
                    'from netra_backend.app.websocket.connection_manager',
                    'import manager_ttl_implementation',
                    'import connection_manager'
                ]
                
                for line_num, line in enumerate(content.splitlines(), 1):
                    for forbidden_import in forbidden_imports:
                        if forbidden_import in line:
                            violations.append(SSotViolation(
                                violation_type="FORBIDDEN_WEBSOCKET_IMPORT",
                                file_path=str(py_file),
                                line_number=line_num,
                                description=f"Forbidden WebSocket manager import: {line.strip()}",
                                severity="CRITICAL",
                                business_impact="Using deprecated WebSocket manager"
                            ))
                            
            except Exception:
                continue
        
        return violations
    
    def validate_jwt_validation_security(self) -> List[SSotViolation]:
        """
        Validate JWT validation security - NO local validation allowed.
        
        BUSINESS IMPACT: $1M+ ARR at risk from authentication bypass vulnerabilities.
        """
        violations = []
        
        # Check for forbidden local JWT validation
        forbidden_patterns = [
            '_try_local_jwt_validation',
            'jwt_lib.decode',
            'jwt.decode(',
            'PyJWT.decode(',
            'local_jwt_validation'
        ]
        
        python_files = list(self.project_root.rglob('*.py'))
        for py_file in python_files:
            # Skip test files that are checking for absence of these patterns
            if 'test_jwt_ssot_validation.py' in str(py_file) or 'test_ssot_compliance_suite.py' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in forbidden_patterns:
                        if pattern in line and not line.strip().startswith('#'):
                            violations.append(SSotViolation(
                                violation_type="FORBIDDEN_LOCAL_JWT_VALIDATION",
                                file_path=str(py_file),
                                line_number=line_num,
                                description=f"Forbidden local JWT validation: {line.strip()}",
                                severity="CRITICAL",
                                business_impact="Authentication bypass vulnerability - security breach risk"
                            ))
                            
            except Exception:
                continue
        
        # Validate canonical JWT handler exists in auth service
        canonical_jwt_handler = self.project_root / 'auth_service/auth_core/core/jwt_handler.py'
        if not canonical_jwt_handler.exists():
            violations.append(SSotViolation(
                violation_type="MISSING_CANONICAL_JWT_HANDLER",
                file_path=str(canonical_jwt_handler),
                line_number=None,
                description="Canonical JWT handler in auth service is missing",
                severity="CRITICAL",
                business_impact="No centralized JWT validation - security breach risk"
            ))
        
        # Check for duplicate JWT validators
        jwt_validator_files = list(self.project_root.rglob('*jwt_validator*'))
        if jwt_validator_files:
            for jwt_file in jwt_validator_files:
                if jwt_file.suffix == '.py':
                    violations.append(SSotViolation(
                        violation_type="DUPLICATE_JWT_VALIDATOR",
                        file_path=str(jwt_file),
                        line_number=None,
                        description=f"Duplicate JWT validator found: {jwt_file}",
                        severity="CRITICAL",
                        business_impact="Multiple JWT validation paths - inconsistent security"
                    ))
        
        return violations
    
    def validate_agent_registry_consolidation(self) -> List[SSotViolation]:
        """
        Validate Agent Registry consolidation - CRITICAL for agent events.
        
        BUSINESS IMPACT: $500K+ ARR at risk if agent events don't reach users.
        """
        violations = []
        
        # Check for forbidden duplicate registries
        forbidden_registries = [
            'netra_backend/app/agents/registry/enhanced_agent_registry.py',
            'netra_backend/app/agents/enhanced_registry.py'  
        ]
        
        for forbidden_registry in forbidden_registries:
            file_path = self.project_root / forbidden_registry
            if file_path.exists():
                violations.append(SSotViolation(
                    violation_type="DUPLICATE_AGENT_REGISTRY",
                    file_path=str(file_path),
                    line_number=None,
                    description=f"Forbidden duplicate agent registry: {forbidden_registry}",
                    severity="CRITICAL",
                    business_impact="Agent events may not reach users - chat functionality broken"
                ))
        
        # Validate canonical agent registry
        canonical_registry = self.project_root / 'netra_backend/app/agents/supervisor/agent_registry.py'
        if not canonical_registry.exists():
            violations.append(SSotViolation(
                violation_type="MISSING_CANONICAL_AGENT_REGISTRY",
                file_path=str(canonical_registry),
                line_number=None,
                description="Canonical agent registry is missing",
                severity="CRITICAL", 
                business_impact="No agent registration system - agents cannot function"
            ))
        else:
            # Check for WebSocket integration
            try:
                with open(canonical_registry, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'set_websocket_manager' not in content:
                    violations.append(SSotViolation(
                        violation_type="MISSING_WEBSOCKET_INTEGRATION",
                        file_path=str(canonical_registry),
                        line_number=None,
                        description="Agent registry missing WebSocket integration",
                        severity="CRITICAL",
                        business_impact="Agent events cannot be delivered to users"
                    ))
                        
            except Exception as e:
                violations.append(SSotViolation(
                    violation_type="AGENT_REGISTRY_READ_ERROR",
                    file_path=str(canonical_registry),
                    line_number=None,
                    description=f"Could not validate agent registry: {e}",
                    severity="HIGH",
                    business_impact="Agent registry validation failed"
                ))
        
        return violations
    
    def validate_isolated_environment_consolidation(self) -> List[SSotViolation]:
        """
        Validate IsolatedEnvironment consolidation - CRITICAL for configuration consistency.
        
        BUSINESS IMPACT: Configuration drift threatens system stability.
        """
        violations = []
        
        # Check for forbidden duplicate IsolatedEnvironment implementations
        forbidden_isolated_envs = [
            'dev_launcher/isolated_environment.py',
            'netra_backend/app/core/isolated_environment.py',
            'auth_service/auth_core/isolated_environment.py',
            'analytics_service/analytics_core/isolated_environment.py'
        ]
        
        for forbidden_env in forbidden_isolated_envs:
            file_path = self.project_root / forbidden_env
            if file_path.exists():
                violations.append(SSotViolation(
                    violation_type="DUPLICATE_ISOLATED_ENVIRONMENT",
                    file_path=str(file_path),
                    line_number=None,
                    description=f"Forbidden duplicate IsolatedEnvironment: {forbidden_env}",
                    severity="HIGH",
                    business_impact="Configuration drift between services"
                ))
        
        # Validate canonical IsolatedEnvironment
        canonical_isolated_env = self.project_root / 'shared/isolated_environment.py'
        if not canonical_isolated_env.exists():
            violations.append(SSotViolation(
                violation_type="MISSING_CANONICAL_ISOLATED_ENVIRONMENT",
                file_path=str(canonical_isolated_env),
                line_number=None,
                description="Canonical IsolatedEnvironment is missing",
                severity="CRITICAL",
                business_impact="No centralized environment management - configuration chaos"
            ))
        
        return violations
    
    def validate_session_management_consolidation(self) -> List[SSotViolation]:
        """
        Validate Session Management consolidation - CRITICAL for user state.
        
        BUSINESS IMPACT: Session inconsistencies affect user experience.
        """
        violations = []
        
        # Check for forbidden duplicate session managers
        forbidden_session_managers = [
            'netra_backend/app/services/database/session_manager.py',
            'netra_backend/app/services/demo/session_manager.py'
        ]
        
        for forbidden_manager in forbidden_session_managers:
            file_path = self.project_root / forbidden_manager
            if file_path.exists():
                violations.append(SSotViolation(
                    violation_type="DUPLICATE_SESSION_MANAGER",
                    file_path=str(file_path),
                    line_number=None,
                    description=f"Forbidden duplicate session manager: {forbidden_manager}",
                    severity="HIGH",
                    business_impact="Session state inconsistencies - user experience failures"
                ))
        
        # Validate canonical Redis session manager exists
        canonical_session_manager = self.project_root / 'netra_backend/app/services/redis/session_manager.py'
        if not canonical_session_manager.exists():
            violations.append(SSotViolation(
                violation_type="MISSING_CANONICAL_SESSION_MANAGER",
                file_path=str(canonical_session_manager),
                line_number=None,
                description="Canonical Redis session manager is missing", 
                severity="CRITICAL",
                business_impact="No centralized session management"
            ))
        
        return violations
    
    def validate_tool_execution_consolidation(self) -> List[SSotViolation]:
        """
        Validate Tool Execution Engine consolidation - CRITICAL for agent functionality.
        
        BUSINESS IMPACT: Tool execution affects agent performance and WebSocket events.
        """
        violations = []
        
        # Look for duplicate tool execution implementations
        tool_execution_files = []
        for pattern in ['*tool_execution*', '*execution_engine*']:
            tool_execution_files.extend(self.project_root.rglob(pattern))
        
        # Filter to Python files only
        tool_execution_py_files = [f for f in tool_execution_files if f.suffix == '.py']
        
        # Check for specific forbidden duplicates
        forbidden_engines = [
            'netra_backend/app/agents/duplicate_tool_execution.py',
            'netra_backend/app/agents/legacy_execution_engine.py'
        ]
        
        for forbidden_engine in forbidden_engines:
            file_path = self.project_root / forbidden_engine
            if file_path.exists():
                violations.append(SSotViolation(
                    violation_type="DUPLICATE_TOOL_EXECUTION_ENGINE",
                    file_path=str(file_path),
                    line_number=None,
                    description=f"Forbidden duplicate tool execution engine: {forbidden_engine}",
                    severity="HIGH",
                    business_impact="Tool execution inconsistencies - agent performance issues"
                ))
        
        # Check for exact duplicate code in tool execution files
        if len(tool_execution_py_files) > 1:
            for i, file1 in enumerate(tool_execution_py_files):
                for file2 in tool_execution_py_files[i+1:]:
                    # Skip test files
                    if 'test' in file1.name.lower() or 'test' in file2.name.lower():
                        continue
                    
                    try:
                        with open(file1, 'r', encoding='utf-8') as f1:
                            content1 = f1.read()
                        with open(file2, 'r', encoding='utf-8') as f2:
                            content2 = f2.read()
                        
                        # Simple duplicate detection - check for exact function duplicates
                        if 'enhance_tool_with_ws_notifications' in content1 and 'enhance_tool_with_ws_notifications' in content2:
                            # Extract function for comparison
                            func_start = 'def enhance_tool_with_ws_notifications'
                            if func_start in content1 and func_start in content2:
                                violations.append(SSotViolation(
                                    violation_type="DUPLICATE_TOOL_EXECUTION_CODE",
                                    file_path=f"{file1} and {file2}",
                                    line_number=None,
                                    description="Duplicate tool execution code detected",
                                    severity="MEDIUM",
                                    business_impact="Code duplication maintenance burden"
                                ))
                                
                    except Exception:
                        continue
        
        return violations
    
    def validate_direct_os_environ_access(self) -> List[SSotViolation]:
        """
        Validate NO direct os.environ access - FORBIDDEN per CLAUDE.md.
        
        BUSINESS IMPACT: Direct os.environ access violates architecture principles.
        """
        violations = []
        
        # Search for direct os.environ access
        python_files = list(self.project_root.rglob('*.py'))
        for py_file in python_files:
            # Skip files that are allowed to access os.environ
            allowed_files = [
                'shared/isolated_environment.py',
                'test_framework/environment_isolation.py',
                # Skip our own test file
                'test_ssot_compliance_suite.py'
            ]
            
            if any(allowed_file in str(py_file) for allowed_file in allowed_files):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                forbidden_patterns = [
                    'os.environ[',
                    'env.get(',
                    'os.getenv(',
                    'environ['
                ]
                
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in forbidden_patterns:
                        if pattern in line and not line.strip().startswith('#'):
                            # Skip if it's in a comment or import statement
                            if 'import os' in line or '# ' in line.split(pattern)[0]:
                                continue
                            
                            violations.append(SSotViolation(
                                violation_type="DIRECT_OS_ENVIRON_ACCESS",
                                file_path=str(py_file),
                                line_number=line_num,
                                description=f"Forbidden direct os.environ access: {line.strip()}",
                                severity="MEDIUM",
                                business_impact="Violates IsolatedEnvironment architecture"
                            ))
                            
            except Exception:
                continue
        
        return violations
    
    def validate_websocket_events_functionality(self) -> bool:
        """
        Validate WebSocket agent events work end-to-end.
        
        BUSINESS IMPACT: Chat functionality depends on agent events reaching users.
        """
        try:
            # Try to run the mission critical WebSocket test
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', 
                 'tests/mission_critical/test_websocket_agent_events_suite.py', 
                 '-v', '--tb=short', '--timeout=60'],
                capture_output=True, text=True, cwd=self.project_root,
                timeout=120
            )
            
            # Check if tests passed
            return result.returncode == 0 and 'FAILED' not in result.stdout
            
        except Exception as e:
            print(f"WebSocket events validation failed: {e}")
            return False
    
    def run_comprehensive_validation(self) -> SSotComplianceResults:
        """
        Run comprehensive SSOT compliance validation.
        
        Returns complete validation results for all critical subsystems.
        """
        print("SSOT COMPLIANCE VALIDATION - MISSION CRITICAL")
        print("=" * 80)
        
        start_time = time.time()
        
        # 1. WebSocket Manager Consolidation
        print("\n1. WEBSOCKET MANAGER CONSOLIDATION")
        websocket_violations = self.validate_websocket_manager_consolidation()
        self.compliance_results.websocket_manager_violations = websocket_violations
        print(f"   Violations found: {len(websocket_violations)}")
        
        # 2. JWT Validation Security  
        print("\n2. JWT VALIDATION SECURITY")
        jwt_violations = self.validate_jwt_validation_security()
        self.compliance_results.jwt_validation_violations = jwt_violations
        print(f"   Violations found: {len(jwt_violations)}")
        
        # 3. Agent Registry Consolidation
        print("\n3. AGENT REGISTRY CONSOLIDATION") 
        agent_violations = self.validate_agent_registry_consolidation()
        self.compliance_results.agent_registry_violations = agent_violations
        print(f"   Violations found: {len(agent_violations)}")
        
        # 4. IsolatedEnvironment Consolidation
        print("\n4. ISOLATED ENVIRONMENT CONSOLIDATION")
        env_violations = self.validate_isolated_environment_consolidation()
        self.compliance_results.isolated_environment_violations = env_violations
        print(f"   Violations found: {len(env_violations)}")
        
        # 5. Session Management Consolidation
        print("\n5. SESSION MANAGEMENT CONSOLIDATION")
        session_violations = self.validate_session_management_consolidation() 
        self.compliance_results.session_management_violations = session_violations
        print(f"   Violations found: {len(session_violations)}")
        
        # 6. Tool Execution Consolidation
        print("\n6. TOOL EXECUTION CONSOLIDATION")
        tool_violations = self.validate_tool_execution_consolidation()
        self.compliance_results.tool_execution_violations = tool_violations
        print(f"   Violations found: {len(tool_violations)}")
        
        # 7. Direct os.environ Access
        print("\n7. DIRECT OS.ENVIRON ACCESS")
        os_violations = self.validate_direct_os_environ_access()
        self.compliance_results.direct_os_environ_violations = os_violations
        print(f"   Violations found: {len(os_violations)}")
        
        # 8. WebSocket Events Functionality
        print("\n8. WEBSOCKET EVENTS FUNCTIONALITY")
        websocket_events_working = self.validate_websocket_events_functionality()
        print(f"   WebSocket events working: {'YES' if websocket_events_working else 'NO'}")
        
        # Calculate overall results
        all_violations = (websocket_violations + jwt_violations + agent_violations + 
                         env_violations + session_violations + tool_violations + 
                         os_violations)
        
        # Count by severity
        critical_count = sum(1 for v in all_violations if v.severity == 'CRITICAL')
        high_count = sum(1 for v in all_violations if v.severity == 'HIGH') 
        
        self.compliance_results.total_violations = len(all_violations)
        self.compliance_results.critical_violations = critical_count
        self.compliance_results.high_violations = high_count
        
        # Calculate compliance score (0-100)
        # Weights: Critical=50, High=30, Medium=15, Low=5, WebSocket Events=20
        max_score = 100
        deductions = (critical_count * 50) + (high_count * 30) + \
                    (sum(1 for v in all_violations if v.severity == 'MEDIUM') * 15) + \
                    (sum(1 for v in all_violations if v.severity == 'LOW') * 5)
        
        if not websocket_events_working:
            deductions += 20  # Major deduction for WebSocket events not working
        
        compliance_score = max(0, max_score - deductions)
        self.compliance_results.overall_compliance_score = compliance_score
        
        # Generate recommendations
        recommendations = []
        if critical_count > 0:
            recommendations.append(f"URGENT: Fix {critical_count} critical SSOT violations immediately")
        if high_count > 0:
            recommendations.append(f"High priority: Address {high_count} high-severity violations")
        if len(websocket_violations) > 0:
            recommendations.append("Fix WebSocket manager consolidation to prevent chat failures")
        if len(jwt_violations) > 0:
            recommendations.append("Fix JWT validation security to prevent authentication bypass")
        if not websocket_events_working:
            recommendations.append("Fix WebSocket agent events - critical for chat functionality")
        
        self.compliance_results.recommendations = recommendations
        
        elapsed_time = time.time() - start_time
        print(f"\nValidation completed in {elapsed_time:.2f}s")
        print(f"Overall Compliance Score: {compliance_score:.1f}/100")
        
        return self.compliance_results


class TestSSotCompliance:
    """Test suite for SSOT compliance validation."""
    
    def test_ssot_compliance_comprehensive(self):
        """
        MISSION CRITICAL: Comprehensive SSOT compliance validation.
        
        This test validates ALL SSOT fixes and MUST PASS before deployment.
        Protects $1.8M+ ARR from SSOT violations causing system failures.
        """
        suite = SSotComplianceSuite()
        results = suite.run_comprehensive_validation()
        
        # Generate detailed report
        report = self._generate_ssot_compliance_report(results)
        
        # Save report
        report_path = suite.project_root / 'SSOT_COMPLIANCE_VALIDATION_REPORT.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nSSOT compliance report saved: {report_path}")
        
        # Determine pass/fail
        COMPLIANCE_THRESHOLD = 85.0  # 85% compliance required for deployment
        
        if results.overall_compliance_score >= COMPLIANCE_THRESHOLD:
            print(f"\nSSOT COMPLIANCE VALIDATION PASSED")
            print(f"   Compliance Score: {results.overall_compliance_score:.1f}/100")
            print(f"   Total Violations: {results.total_violations}")
            print(f"   Critical Violations: {results.critical_violations}")
        else:
            # Generate failure report
            failure_msg = f"\n{'='*80}\n"
            failure_msg += "SSOT COMPLIANCE VALIDATION FAILED\n"
            failure_msg += f"{'='*80}\n\n"
            failure_msg += f"Compliance Score: {results.overall_compliance_score:.1f}/100 "
            failure_msg += f"(NEED {COMPLIANCE_THRESHOLD}%)\n\n"
            
            failure_msg += "CRITICAL VIOLATIONS BY SUBSYSTEM:\n"
            failure_msg += f"  WebSocket Manager: {len(results.websocket_manager_violations)} violations\n"
            failure_msg += f"  JWT Validation: {len(results.jwt_validation_violations)} violations\n"
            failure_msg += f"  Agent Registry: {len(results.agent_registry_violations)} violations\n"  
            failure_msg += f"  IsolatedEnvironment: {len(results.isolated_environment_violations)} violations\n"
            failure_msg += f"  Session Management: {len(results.session_management_violations)} violations\n"
            failure_msg += f"  Tool Execution: {len(results.tool_execution_violations)} violations\n"
            failure_msg += f"  Direct os.environ: {len(results.direct_os_environ_violations)} violations\n\n"
            
            if results.recommendations:
                failure_msg += "REQUIRED ACTIONS:\n"
                for rec in results.recommendations:
                    failure_msg += f"  {rec}\n"
                failure_msg += "\n"
            
            # Show critical violations in detail
            all_violations = (results.websocket_manager_violations + 
                            results.jwt_validation_violations +
                            results.agent_registry_violations +
                            results.isolated_environment_violations +
                            results.session_management_violations +
                            results.tool_execution_violations +
                            results.direct_os_environ_violations)
            
            critical_violations = [v for v in all_violations if v.severity == 'CRITICAL']
            if critical_violations:
                failure_msg += "CRITICAL VIOLATIONS (MUST FIX IMMEDIATELY):\n"
                for violation in critical_violations[:10]:  # Show first 10
                    failure_msg += f"  {violation.description}\n"
                    failure_msg += f"     File: {violation.file_path}\n"
                    failure_msg += f"     Impact: {violation.business_impact}\n\n"
            
            failure_msg += f"{'='*80}\n"
            failure_msg += "SSOT COMPLIANCE MUST REACH 85%+ BEFORE DEPLOYMENT\n"
            failure_msg += f"{'='*80}\n"
            
            pytest.fail(failure_msg)
    
    def _generate_ssot_compliance_report(self, results: SSotComplianceResults) -> str:
        """Generate comprehensive SSOT compliance report."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# SSOT Compliance Validation Report - MISSION CRITICAL

**Generated:** {timestamp}
**Overall Compliance:** {results.overall_compliance_score:.1f}/100
**Status:** {'PASSED' if results.overall_compliance_score >= 85 else 'FAILED'}

## Executive Summary

This report validates ALL SSOT fixes made to protect $1.8M+ ARR from system failures
caused by duplicate implementations, security vulnerabilities, and architectural violations.

### Critical Subsystem Compliance

| Subsystem | Violations | Status | Business Impact |
|-----------|------------|--------|-----------------|
| WebSocket Manager | {len(results.websocket_manager_violations)} | {'OK' if len(results.websocket_manager_violations) == 0 else 'FAIL'} | Chat functionality - $500K ARR |
| JWT Validation | {len(results.jwt_validation_violations)} | {'OK' if len(results.jwt_validation_violations) == 0 else 'FAIL'} | Security - $1M ARR |
| Agent Registry | {len(results.agent_registry_violations)} | {'OK' if len(results.agent_registry_violations) == 0 else 'FAIL'} | Agent events - $500K ARR |
| IsolatedEnvironment | {len(results.isolated_environment_violations)} | {'OK' if len(results.isolated_environment_violations) == 0 else 'FAIL'} | Configuration drift |
| Session Management | {len(results.session_management_violations)} | {'OK' if len(results.session_management_violations) == 0 else 'FAIL'} | User experience |
| Tool Execution | {len(results.tool_execution_violations)} | {'OK' if len(results.tool_execution_violations) == 0 else 'FAIL'} | Agent performance |
| Direct os.environ | {len(results.direct_os_environ_violations)} | {'OK' if len(results.direct_os_environ_violations) == 0 else 'FAIL'} | Architecture compliance |

### Violation Summary

- **Total Violations:** {results.total_violations}
- **Critical Violations:** {results.critical_violations} (❌ MUST BE ZERO)
- **High Severity:** {results.high_violations}
- **Compliance Score:** {results.overall_compliance_score:.1f}/100

## Critical Issues
"""
        
        # Add critical violations
        all_violations = (results.websocket_manager_violations + 
                         results.jwt_validation_violations +
                         results.agent_registry_violations +
                         results.isolated_environment_violations +
                         results.session_management_violations +
                         results.tool_execution_violations +
                         results.direct_os_environ_violations)
        
        critical_violations = [v for v in all_violations if v.severity == 'CRITICAL']
        
        if critical_violations:
            for violation in critical_violations:
                report += f"\n### CRITICAL: {violation.violation_type}\n"
                report += f"- **File:** {violation.file_path}\n"
                if violation.line_number:
                    report += f"- **Line:** {violation.line_number}\n"
                report += f"- **Description:** {violation.description}\n"  
                report += f"- **Business Impact:** {violation.business_impact}\n"
        else:
            report += "\nNo critical violations detected\n"
        
        report += "\n## Recommendations\n"
        
        if results.recommendations:
            for rec in results.recommendations:
                report += f"- {rec}\n"
        else:
            report += "- System is SSOT compliant\n"
        
        report += f"""

## SSOT Fix Validation Summary

The following critical SSOT fixes have been validated:

1. **WebSocket Manager Consolidation** - {'FIXED' if len(results.websocket_manager_violations) == 0 else 'VIOLATIONS DETECTED'}
2. **JWT Validation Security** - {'FIXED' if len(results.jwt_validation_violations) == 0 else 'VIOLATIONS DETECTED'}
3. **Agent Registry Consolidation** - {'FIXED' if len(results.agent_registry_violations) == 0 else 'VIOLATIONS DETECTED'}
4. **IsolatedEnvironment Consolidation** - {'FIXED' if len(results.isolated_environment_violations) == 0 else 'VIOLATIONS DETECTED'}
5. **Session Management Consolidation** - {'FIXED' if len(results.session_management_violations) == 0 else 'VIOLATIONS DETECTED'}
6. **Tool Execution Engine Consolidation** - {'FIXED' if len(results.tool_execution_violations) == 0 else 'VIOLATIONS DETECTED'}

## Deployment Readiness

{'**READY FOR DEPLOYMENT** - All SSOT fixes validated and compliant' if results.overall_compliance_score >= 85 else '**NOT READY FOR DEPLOYMENT** - Critical SSOT violations must be fixed'}

### Business Value Protected

- **Revenue at Risk:** $1.8M ARR
- **System Stability:** {'Stable' if results.critical_violations == 0 else 'At Risk'}
- **Development Velocity:** {'Optimized' if results.total_violations < 10 else 'Impacted'}

---

*This report was generated by the SSOT Compliance Validation Suite - Mission Critical*
"""
        
        return report


if __name__ == '__main__':
    # Run comprehensive SSOT validation
    print("SSOT COMPLIANCE SUITE - MISSION CRITICAL")
    print("Validating all SSOT fixes to protect $1.8M+ ARR")
    
    suite = SSotComplianceSuite()
    results = suite.run_comprehensive_validation()
    
    if results.overall_compliance_score >= 85:
        print(f"\nSUCCESS: SSOT Compliance at {results.overall_compliance_score:.1f}%")
        exit(0)
    else:
        print(f"\nFAILURE: SSOT Compliance at {results.overall_compliance_score:.1f}% (need 85%+)")
        print(f"Critical violations: {results.critical_violations}")
        exit(1)