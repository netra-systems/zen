"""
SSOT Agent-WebSocket Direct Import Violations Test Suite - Issue #1070 Phase 1

This test suite creates FAILING tests that reproduce SSOT agent-websocket bridge violations.
These tests will FAIL initially to prove the violations exist, then PASS after proper SSOT 
bridge implementation.

TARGET VIOLATIONS TO REPRODUCE:
- Direct WebSocketManager imports in agent files (lines 43, 13, 30)
- Multi-user isolation failures due to shared state
- Missing WebSocket events due to bridge bypass

Business Value: Platform Infrastructure - Protects $500K+ ARR Golden Path functionality
through proper SSOT bridge patterns that ensure multi-user isolation and event delivery.

CRITICAL: These tests are designed to FAIL initially to validate violation reproduction.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestAgentWebSocketDirectImportViolations(SSotBaseTestCase):
    """
    Test suite for detecting direct WebSocketManager imports in agent files.
    
    These tests use AST parsing to detect SSOT violations where agent files 
    directly import WebSocketManager instead of using the proper SSOT bridge pattern.
    
    EXPECTED BEHAVIOR: These tests should FAIL initially to prove violations exist.
    """

    def setup_method(self, method=None):
        """Setup test environment for SSOT violation detection."""
        super().setup_method(method)
        
        # Define paths to examine for violations
        self.backend_root = Path("/Users/anthony/Desktop/netra-apex/netra_backend")
        self.agent_paths = [
            self.backend_root / "app" / "agents",
            self.backend_root / "app" / "agents" / "supervisor",
        ]
        
        # Known violation targets from Issue #1070
        self.known_violations = {
            "registry.py": 43,  # Expected line (approximate)
            "mcp_execution_engine.py": 13,  # Expected line (exact)
            "pipeline_executor.py": 30,  # Expected line (exact)
        }
        
        self.logger.info(f"Initialized SSOT violation detection for {len(self.agent_paths)} agent directories")
    
    @pytest.mark.ssot_violation
    @pytest.mark.priority_p1
    def test_detect_direct_websocket_manager_imports(self):
        """
        FAILING TEST: Detect direct WebSocketManager imports in agent files.
        
        This test will FAIL initially because the violations exist.
        It should PASS after SSOT bridge implementation removes direct imports.
        """
        violations_found = {}
        
        for agent_dir in self.agent_paths:
            if not agent_dir.exists():
                continue
                
            for py_file in agent_dir.rglob("*.py"):
                try:
                    violations = self._check_file_for_direct_websocket_imports(py_file)
                    if violations:
                        violations_found[str(py_file.relative_to(self.backend_root))] = violations
                except Exception as e:
                    self.logger.warning(f"Failed to parse {py_file}: {e}")
        
        # Record metrics for tracking
        self.record_metric("direct_import_violations_found", len(violations_found))
        self.record_metric("files_with_violations", list(violations_found.keys()))
        
        # Log detailed findings
        if violations_found:
            self.logger.error("SSOT VIOLATION: Found direct WebSocketManager imports:")
            for file_path, violations in violations_found.items():
                self.logger.error(f"  {file_path}: {violations}")
        
        # EXPECTED FAILURE: This assertion should fail initially to prove violations exist
        assert not violations_found, (
            f"SSOT VIOLATION: Found {len(violations_found)} files with direct WebSocketManager imports. "
            f"Files must use SSOT bridge pattern instead. Violations: {violations_found}"
        )
    
    @pytest.mark.ssot_violation
    @pytest.mark.priority_p1
    def test_verify_known_violation_locations(self):
        """
        FAILING TEST: Verify specific known violation locations from Issue #1070.
        
        This test checks the exact files and lines mentioned in Issue #1070.
        It will FAIL initially because these violations are documented to exist.
        """
        verified_violations = {}
        
        for filename, expected_line in self.known_violations.items():
            # Find the file in agent directories
            file_found = False
            for agent_dir in self.agent_paths:
                candidate_file = agent_dir / filename
                if candidate_file.exists():
                    file_found = True
                    violations = self._check_file_for_direct_websocket_imports(candidate_file)
                    if violations:
                        # Check if violation is near expected line
                        line_matches = any(
                            abs(line - expected_line) <= 5  # Allow 5-line tolerance
                            for line in violations
                        )
                        if line_matches:
                            verified_violations[filename] = {
                                "expected_line": expected_line,
                                "actual_lines": violations,
                                "file_path": str(candidate_file.relative_to(self.backend_root))
                            }
                    break
            
            if not file_found:
                self.logger.warning(f"Known violation file not found: {filename}")
        
        # Record metrics
        self.record_metric("known_violations_verified", len(verified_violations))
        self.record_metric("verified_violations_details", verified_violations)
        
        # EXPECTED FAILURE: This should fail initially because known violations exist
        assert not verified_violations, (
            f"SSOT VIOLATION: Verified {len(verified_violations)} known violation locations. "
            f"These files must be refactored to use SSOT bridge pattern. "
            f"Verified violations: {verified_violations}"
        )
    
    @pytest.mark.ssot_violation
    @pytest.mark.priority_p1
    def test_detect_websocket_singleton_patterns(self):
        """
        FAILING TEST: Detect singleton WebSocket patterns that violate multi-user isolation.
        
        This test identifies code patterns that could cause multi-user contamination
        by using shared WebSocket instances instead of user-isolated factories.
        """
        singleton_violations = {}
        
        # Patterns that suggest singleton usage
        singleton_patterns = [
            "WebSocketManager(",  # Direct instantiation
            ".websocket_manager = ",  # Instance assignment
            "global websocket",  # Global variables
            "_websocket_instance",  # Private singleton instances
        ]
        
        for agent_dir in self.agent_paths:
            if not agent_dir.exists():
                continue
                
            for py_file in agent_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.splitlines()
                        
                    violations = []
                    for i, line in enumerate(lines, 1):
                        for pattern in singleton_patterns:
                            if pattern in line and "WebSocket" in line:
                                violations.append({
                                    "line": i,
                                    "pattern": pattern,
                                    "content": line.strip()
                                })
                    
                    if violations:
                        singleton_violations[str(py_file.relative_to(self.backend_root))] = violations
                        
                except Exception as e:
                    self.logger.warning(f"Failed to scan {py_file} for singleton patterns: {e}")
        
        # Record findings
        self.record_metric("singleton_pattern_violations", len(singleton_violations))
        
        # EXPECTED FAILURE: Should fail if singleton patterns are found
        assert not singleton_violations, (
            f"SSOT VIOLATION: Found {len(singleton_violations)} files with potential singleton WebSocket patterns. "
            f"These patterns may cause multi-user isolation failures. Violations: {singleton_violations}"
        )
    
    @pytest.mark.ssot_violation  
    @pytest.mark.priority_p1
    def test_websocket_bridge_interface_compliance(self):
        """
        FAILING TEST: Verify that agent files use proper SSOT bridge interfaces.
        
        This test checks whether agent files are using the correct SSOT bridge pattern
        instead of direct WebSocket manager access.
        """
        non_compliant_files = {}
        
        # Expected SSOT bridge patterns
        expected_patterns = [
            "from netra_backend.app.websocket_core.bridge",
            "WebSocketBridge",
            "websocket_bridge",
        ]
        
        # Prohibited direct access patterns  
        prohibited_patterns = [
            "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
            "from netra_backend.app.websocket_core.manager import",
            "WebSocketManager(",
        ]
        
        for agent_dir in self.agent_paths:
            if not agent_dir.exists():
                continue
                
            for py_file in agent_dir.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue  # Skip __init__.py etc.
                    
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for prohibited patterns
                    has_prohibited = any(pattern in content for pattern in prohibited_patterns)
                    has_expected = any(pattern in content for pattern in expected_patterns)
                    
                    # Files with WebSocket usage should use bridge pattern
                    has_websocket_usage = "websocket" in content.lower() and "WebSocket" in content
                    
                    if has_websocket_usage and (has_prohibited or not has_expected):
                        non_compliant_files[str(py_file.relative_to(self.backend_root))] = {
                            "has_prohibited_patterns": has_prohibited,
                            "has_expected_patterns": has_expected,
                            "websocket_usage": has_websocket_usage,
                        }
                        
                except Exception as e:
                    self.logger.warning(f"Failed to check bridge compliance for {py_file}: {e}")
        
        # Record metrics
        self.record_metric("bridge_non_compliant_files", len(non_compliant_files))
        
        # EXPECTED FAILURE: Should fail if files don't use proper bridge pattern
        assert not non_compliant_files, (
            f"SSOT VIOLATION: Found {len(non_compliant_files)} files not using proper WebSocket bridge pattern. "
            f"Agent files with WebSocket usage must use SSOT bridge pattern. "
            f"Non-compliant files: {non_compliant_files}"
        )

    def _check_file_for_direct_websocket_imports(self, file_path: Path) -> List[int]:
        """
        Use AST parsing to find direct WebSocketManager imports.
        
        Args:
            file_path: Path to Python file to analyze
            
        Returns:
            List of line numbers with direct WebSocketManager imports
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the AST
            tree = ast.parse(content, filename=str(file_path))
            
            # Check all import statements
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    # Check for direct websocket_manager imports
                    if (node.module and 
                        "websocket_manager" in node.module and 
                        any(alias.name == "WebSocketManager" for alias in node.names or [])):
                        violations.append(node.lineno)
                        
                elif isinstance(node, ast.Import):
                    # Check for direct websocket imports
                    for alias in node.names:
                        if "websocket_manager" in alias.name:
                            violations.append(node.lineno)
                            
        except SyntaxError as e:
            self.logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
            
        return violations