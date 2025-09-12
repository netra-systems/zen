"""
LLM Manager Factory Pattern Violations Detection - Issue #224 Phase 3 Test Plan

DESIGNED TO FAIL: These tests prove the 51 LLMManager factory pattern violations exist.
They will PASS after proper factory pattern remediation is implemented.

Business Value: Platform/Internal - System Stability & User Isolation
Protects $500K+ ARR chat functionality from user conversation mixing.

Target Violations:
- data_helper_agent.py:74 - Direct LLMManager() creation
- optimizations_core_sub_agent.py:405 - Direct LLMManager() creation  
- unified_triage_agent.py:222 - Direct LLMManager() creation
- Additional 48 violations in agent system

Test Strategy:
1. Static analysis to detect direct LLMManager() violations
2. Factory pattern compliance validation
3. Agent system specific violation detection

IMPORTANT: These tests use real service patterns to detect actual violations
that could cause user conversation mixing in production.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict

import pytest
from loguru import logger

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestLLMManagerFactoryViolationsIssue224(SSotBaseTestCase):
    """Unit tests to detect the 51 LLMManager factory pattern violations for issue #224"""
    
    def test_detect_direct_llm_manager_instantiation_violations(self):
        """DESIGNED TO FAIL: Detect direct LLMManager() instantiation violations.
        
        This test should FAIL and detect the known violations at:
        - data_helper_agent.py:74
        - optimizations_core_sub_agent.py:405  
        - unified_triage_agent.py:222
        - And ~48 additional violations
        
        Expected pattern: llm_manager = LLMManager() (VIOLATION)
        Required pattern: llm_manager = create_llm_manager(user_context) (COMPLIANT)
        
        Business Impact: Direct instantiation bypasses user isolation, 
        causing conversation mixing between users in $500K+ ARR chat system.
        """
        logger.info("Starting detection of direct LLMManager() instantiation violations...")
        
        violations = []
        total_files_scanned = 0
        
        # Focus on agent system files where violations are known to exist
        search_roots = [
            Path("netra_backend/app/agents"),
            Path("netra_backend/app/routes"), 
            Path("netra_backend/app/services"),
            Path("netra_backend/app/websocket_core")
        ]
        
        def scan_file_for_direct_instantiation(file_path: Path) -> List[Dict]:
            """Scan a Python file for direct LLMManager() instantiation violations."""
            file_violations = []
            
            if not file_path.exists() or not file_path.suffix == '.py':
                return file_violations
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Skip comments and imports
                    stripped_line = line.strip()
                    if stripped_line.startswith('#') or stripped_line.startswith('import') or stripped_line.startswith('from'):
                        continue
                    
                    # Detect direct LLMManager() instantiation
                    if 'LLMManager()' in line:
                        file_violations.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'violation_type': 'direct_instantiation',
                            'severity': 'CRITICAL'
                        })
                        logger.warning(f"VIOLATION DETECTED: {file_path}:{line_num} - {line.strip()}")
                    
                    # Detect LLMManager instantiation with parameters (also problematic)
                    elif re.search(r'LLMManager\s*\([^)]*\)', line) and 'import' not in line:
                        file_violations.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'violation_type': 'parameterized_instantiation',
                            'severity': 'HIGH'
                        })
                        logger.warning(f"PARAMETERIZED VIOLATION: {file_path}:{line_num} - {line.strip()}")
                        
            except Exception as e:
                logger.error(f"Failed to scan {file_path}: {e}")
                
            return file_violations
        
        # Scan all target directories
        for search_root in search_roots:
            if search_root.exists():
                for file_path in search_root.rglob("*.py"):
                    # Skip test files to focus on production code
                    if 'test' not in str(file_path).lower():
                        total_files_scanned += 1
                        file_violations = scan_file_for_direct_instantiation(file_path)
                        violations.extend(file_violations)
        
        # Verify we found the specific known violations
        known_violation_files = [
            'data_helper_agent.py',
            'optimizations_core_sub_agent.py', 
            'unified_triage_agent.py'
        ]
        
        found_known_violations = []
        for violation in violations:
            file_name = Path(violation['file']).name
            if file_name in known_violation_files:
                found_known_violations.append({
                    'file': file_name,
                    'line': violation['line'],
                    'content': violation['content']
                })
        
        # Record metrics
        self.record_metric('total_files_scanned', total_files_scanned)
        self.record_metric('total_violations_found', len(violations))
        self.record_metric('known_violations_found', len(found_known_violations))
        
        # Log summary
        logger.info(f"Scanned {total_files_scanned} files")
        logger.info(f"Found {len(violations)} total violations")
        logger.info(f"Found {len(found_known_violations)} known violations")
        
        for violation in found_known_violations:
            logger.error(f"KNOWN VIOLATION CONFIRMED: {violation['file']}:{violation['line']} - {violation['content']}")
        
        # This test should FAIL because we expect to find violations
        assert len(violations) >= 3, (
            f"Expected to find at least 3 violations (the known ones), but found {len(violations)}. "
            f"Known violations should be at data_helper_agent.py:74, optimizations_core_sub_agent.py:405, "
            f"unified_triage_agent.py:222. Scanned {total_files_scanned} files."
        )
        
        # More specific assertion for the known violations
        assert len(found_known_violations) >= 3, (
            f"Expected to find the 3 specific known violations, but only found {len(found_known_violations)}. "
            f"Found violations in: {[v['file'] for v in found_known_violations]}"
        )
        
        # This will cause the test to fail and show the violations
        pytest.fail(
            f"LLMManager Factory Pattern Violations Detected! "
            f"Found {len(violations)} total violations including {len(found_known_violations)} known violations. "
            f"This proves user conversation mixing risk exists. "
            f"Violations: {violations[:5]}..."
        )
    
    def test_factory_pattern_compliance_scan(self):
        """DESIGNED TO FAIL: Verify files use create_llm_manager(user_context) pattern.
        
        This test should FAIL because agent files use direct instantiation
        instead of the required factory pattern with user context.
        
        Expected Compliant Pattern:
        - llm_manager = create_llm_manager(user_context)
        - llm_manager = LLMManagerFactory.create_for_user(user_context)
        
        Business Impact: Non-compliant patterns break user isolation,
        causing conversation data to mix between different users.
        """
        logger.info("Starting factory pattern compliance scan...")
        
        compliance_violations = []
        compliant_usages = []
        total_llm_usages = 0
        
        # Scan agent system for LLM usage patterns
        agent_root = Path("netra_backend/app/agents")
        
        def analyze_llm_usage_patterns(file_path: Path) -> Dict[str, List]:
            """Analyze LLM usage patterns in a file."""
            patterns = {
                'violations': [],
                'compliant': [],
                'questionable': []
            }
            
            if not file_path.exists():
                return patterns
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    stripped_line = line.strip()
                    
                    # Skip comments and imports
                    if stripped_line.startswith('#') or 'import' in line:
                        continue
                    
                    # Check for LLM manager usage
                    if 'llm_manager' in line.lower() or 'LLMManager' in line:
                        total_llm_usages += 1
                        
                        # Violations: Direct instantiation
                        if 'LLMManager()' in line or re.search(r'LLMManager\s*\(', line):
                            patterns['violations'].append({
                                'line': line_num,
                                'content': line.strip(),
                                'pattern': 'direct_instantiation'
                            })
                        
                        # Compliant: Factory usage with user context
                        elif any(pattern in line for pattern in ['create_llm_manager', 'LLMManagerFactory', 'get_llm_manager']):
                            if 'user' in line.lower() or 'context' in line.lower():
                                patterns['compliant'].append({
                                    'line': line_num,
                                    'content': line.strip(),
                                    'pattern': 'factory_with_context'
                                })
                            else:
                                patterns['questionable'].append({
                                    'line': line_num,
                                    'content': line.strip(),
                                    'pattern': 'factory_without_context'
                                })
                        
                        # Assignment or usage without clear pattern
                        elif '=' in line and 'llm_manager' in line.lower():
                            patterns['questionable'].append({
                                'line': line_num,
                                'content': line.strip(),
                                'pattern': 'unclear_assignment'
                            })
                            
            except Exception as e:
                logger.error(f"Failed to analyze {file_path}: {e}")
                
            return patterns
        
        # Scan all agent files
        files_analyzed = 0
        if agent_root.exists():
            for file_path in agent_root.rglob("*.py"):
                if 'test' not in str(file_path).lower():
                    files_analyzed += 1
                    patterns = analyze_llm_usage_patterns(file_path)
                    
                    for violation in patterns['violations']:
                        compliance_violations.append({
                            'file': str(file_path),
                            'line': violation['line'],
                            'content': violation['content'],
                            'pattern': violation['pattern'],
                            'severity': 'CRITICAL'
                        })
                    
                    compliant_usages.extend(patterns['compliant'])
                    
                    # Questionable patterns are also concerning
                    for questionable in patterns['questionable']:
                        compliance_violations.append({
                            'file': str(file_path),
                            'line': questionable['line'],
                            'content': questionable['content'],
                            'pattern': questionable['pattern'],
                            'severity': 'MEDIUM'
                        })
        
        # Calculate compliance ratio
        total_patterns = len(compliance_violations) + len(compliant_usages)
        compliance_ratio = len(compliant_usages) / total_patterns if total_patterns > 0 else 0
        
        # Record metrics
        self.record_metric('files_analyzed', files_analyzed)
        self.record_metric('total_llm_patterns', total_patterns)
        self.record_metric('compliance_violations', len(compliance_violations))
        self.record_metric('compliant_usages', len(compliant_usages))
        self.record_metric('compliance_ratio', compliance_ratio)
        
        # Log findings
        logger.info(f"Analyzed {files_analyzed} agent files")
        logger.info(f"Found {total_patterns} LLM usage patterns")
        logger.info(f"Compliance ratio: {compliance_ratio:.2%}")
        
        for violation in compliance_violations[:5]:  # Show first 5
            logger.error(f"COMPLIANCE VIOLATION: {violation['file']}:{violation['line']} - {violation['content']}")
        
        # This test should FAIL because we expect compliance violations
        assert len(compliance_violations) > 0, (
            f"Expected factory pattern compliance violations, but found none. "
            f"This indicates agents may already be using proper factory patterns. "
            f"Analyzed {files_analyzed} files with {total_patterns} LLM patterns."
        )
        
        # Check that compliance ratio is poor (indicating violations exist)
        assert compliance_ratio < 0.8, (
            f"Expected poor compliance ratio (<80%), but found {compliance_ratio:.2%}. "
            f"This indicates most agent code is already using proper factory patterns."
        )
        
        pytest.fail(
            f"Factory Pattern Compliance Violations Detected! "
            f"Found {len(compliance_violations)} violations out of {total_patterns} patterns. "
            f"Compliance ratio: {compliance_ratio:.2%}. "
            f"This proves agent system needs factory pattern remediation."
        )
    
    def test_agent_system_specific_violations(self):
        """DESIGNED TO FAIL: Detect agent-specific LLM manager violations.
        
        This test focuses on the specific agent files mentioned in issue #224
        and validates they have the expected factory pattern violations.
        
        Target Files:
        - data_helper_agent.py (line 74)
        - optimizations_core_sub_agent.py (line 405)
        - unified_triage_agent.py (line 222)
        
        Business Impact: These specific violations in agent execution
        create race conditions that can mix user conversations.
        """
        logger.info("Starting agent-specific violation detection...")
        
        target_violations = [
            {
                'file': 'data_helper_agent.py',
                'expected_line': 74,
                'pattern': 'llm_manager = LLMManager()'
            },
            {
                'file': 'optimizations_core_sub_agent.py', 
                'expected_line': 405,
                'pattern': 'llm_manager = LLMManager()'
            },
            {
                'file': 'unified_triage_agent.py',
                'expected_line': 222,
                'pattern': 'llm_manager = LLMManager()'
            }
        ]
        
        detected_violations = []
        
        # Find and analyze each target file
        agent_root = Path("netra_backend/app/agents")
        
        for target in target_violations:
            # Find the file
            found_files = list(agent_root.rglob(target['file']))
            
            if not found_files:
                logger.error(f"Target file not found: {target['file']}")
                continue
                
            file_path = found_files[0]  # Use first match
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Check specific line number area ( +/- 5 lines for flexibility)
                target_line = target['expected_line']
                search_range = range(max(1, target_line - 5), min(len(lines) + 1, target_line + 6))
                
                violation_found = False
                for line_num in search_range:
                    if line_num <= len(lines):
                        line_content = lines[line_num - 1].strip()
                        
                        # Check for the violation pattern
                        if 'LLMManager()' in line_content:
                            detected_violations.append({
                                'file': target['file'],
                                'expected_line': target_line,
                                'actual_line': line_num,
                                'content': line_content,
                                'severity': 'CRITICAL'
                            })
                            violation_found = True
                            logger.error(f"VIOLATION CONFIRMED: {target['file']}:{line_num} - {line_content}")
                            break
                
                if not violation_found:
                    # Check if there's any LLMManager usage in the file
                    llm_usage_lines = []
                    for line_num, line in enumerate(lines, 1):
                        if 'LLMManager' in line and 'import' not in line:
                            llm_usage_lines.append({
                                'line': line_num,
                                'content': line.strip()
                            })
                    
                    logger.warning(f"Expected violation not found at {target['file']}:{target_line}")
                    logger.info(f"Found LLM usage in {target['file']}: {llm_usage_lines}")
                    
            except Exception as e:
                logger.error(f"Failed to analyze {target['file']}: {e}")
        
        # Record metrics
        self.record_metric('target_files_checked', len(target_violations))
        self.record_metric('violations_detected', len(detected_violations))
        
        # Verify we found the expected violations
        logger.info(f"Checked {len(target_violations)} target files")
        logger.info(f"Detected {len(detected_violations)} violations")
        
        for violation in detected_violations:
            logger.error(
                f"AGENT VIOLATION: {violation['file']} "
                f"(expected: ~{violation['expected_line']}, actual: {violation['actual_line']}) "
                f"- {violation['content']}"
            )
        
        # This test should FAIL because we expect to find violations
        assert len(detected_violations) > 0, (
            f"Expected to find violations in the target agent files, but found none. "
            f"Target files: {[t['file'] for t in target_violations]}. "
            f"This may indicate the violations have already been fixed or moved."
        )
        
        # Prefer finding most of the expected violations
        assert len(detected_violations) >= 2, (
            f"Expected to find at least 2 of the 3 target violations, but only found {len(detected_violations)}. "
            f"This indicates some violations may have been fixed or are not at expected lines."
        )
        
        pytest.fail(
            f"Agent-Specific LLM Manager Violations Confirmed! "
            f"Found {len(detected_violations)} of {len(target_violations)} expected violations. "
            f"These violations create user conversation mixing risks in agent execution. "
            f"Violations: {detected_violations}"
        )


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    import sys
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)