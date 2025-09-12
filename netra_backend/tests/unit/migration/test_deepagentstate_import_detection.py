"""
DeepAgentState Import Detection Test - Migration Validation

This test is DESIGNED TO FAIL by detecting active DeepAgentState imports in production files.
When the migration to UserExecutionContext is complete, this test should PASS.

BUSINESS IMPACT: Issue #271 - User isolation vulnerability remediation
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import unittest

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestDeepAgentStateMigrationDetection(SSotAsyncTestCase):
    """
    Migration validation test for DeepAgentState  ->  UserExecutionContext
    
    This test FAILS until all DeepAgentState imports are removed from production files.
    Success = migration complete, security vulnerability resolved.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.netra_backend_root = Path(__file__).parent.parent.parent.parent
        self._setup_production_files()
        
    def _setup_production_files(self):
        """Initialize production files list with DeepAgentState usage"""
        # 43 production files identified as containing DeepAgentState usage
        self.production_files_with_deepagentstate = [
            "netra_backend/app/agents/supervisor/execution_engine.py",
            "netra_backend/app/agents/supervisor/mcp_execution_engine.py", 
            "netra_backend/app/agents/supervisor/pipeline_executor.py",
            "netra_backend/app/agents/supervisor/user_execution_engine.py",
            "netra_backend/app/agents/supervisor/workflow_orchestrator.py",
            "netra_backend/app/agents/supervisor/agent_execution_core.py",
            "netra_backend/app/agents/supervisor/agent_routing.py",
            "netra_backend/app/websocket_core/connection_executor.py",
            "netra_backend/app/websocket_core/unified_manager.py",
            # Additional files will be discovered during scan
        ]
        
    async def test_scan_for_active_deepagentstate_imports(self):
        """
        DESIGNED TO FAIL: Scan production files for active DeepAgentState imports
        
        This test fails if ANY production files contain:
        - from netra_backend.app.agents.state import DeepAgentState
        - DeepAgentState class usage in method signatures
        - DeepAgentState instantiation
        """
        violations = self._scan_deepagentstate_usage()
        
        # Build detailed failure message
        if violations:
            violation_summary = self._build_violation_summary(violations)
            self.fail(f"""
 ALERT:  MIGRATION REQUIRED: DeepAgentState still in use (Issue #271)

Active DeepAgentState imports detected in {len(violations)} production files:

{violation_summary}

SECURITY RISK: Cross-user contamination vulnerability exists until migration complete.
MIGRATION: Replace all DeepAgentState usage with UserExecutionContext pattern.

See: USER_CONTEXT_ARCHITECTURE.md for migration guide.
            """)
            
    async def test_verify_userexecutioncontext_adoption(self):
        """
        DESIGNED TO FAIL: Verify critical files have adopted UserExecutionContext
        
        This test checks that high-priority files are using the secure pattern.
        """
        critical_files = [
            "netra_backend/app/agents/supervisor/agent_execution_core.py",
            "netra_backend/app/agents/supervisor/agent_routing.py", 
            "netra_backend/app/agents/supervisor/workflow_orchestrator.py",
        ]
        
        missing_adoption = []
        
        for file_path in critical_files:
            full_path = self.netra_backend_root / file_path
            if full_path.exists():
                if not self._has_userexecutioncontext_import(full_path):
                    missing_adoption.append(file_path)
                    
        if missing_adoption:
            self.fail(f"""
 ALERT:  CRITICAL FILES MISSING UserExecutionContext ADOPTION

Files not yet migrated to secure pattern:
{chr(10).join(f'  - {f}' for f in missing_adoption)}

SECURITY IMPACT: User isolation not enforced in critical execution paths.
PRIORITY: P0 - Migrate these files first to protect $500K+ ARR.
            """)
            
    def _scan_deepagentstate_usage(self) -> Dict[str, List[str]]:
        """Scan for DeepAgentState usage across production files"""
        violations = {}
        
        # Scan known production files
        for file_path in self.production_files_with_deepagentstate:
            full_path = self.netra_backend_root / file_path
            if full_path.exists():
                usage_violations = self._analyze_file_for_deepagentstate(full_path)
                if usage_violations:
                    violations[file_path] = usage_violations
                    
        # Scan additional directories for unknown usage
        search_dirs = [
            "netra_backend/app/agents",
            "netra_backend/app/websocket_core",
            "netra_backend/app/services",
        ]
        
        for search_dir in search_dirs:
            violations.update(self._scan_directory_for_deepagentstate(search_dir))
            
        return violations
        
    def _analyze_file_for_deepagentstate(self, file_path: Path) -> List[str]:
        """Analyze single file for DeepAgentState usage patterns"""
        violations = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Check for import statements
            if 'from netra_backend.app.agents.state import DeepAgentState' in content:
                violations.append("Direct import: 'from netra_backend.app.agents.state import DeepAgentState'")
                
            if 'from netra_backend.app.agents.state import' in content and 'DeepAgentState' in content:
                violations.append("Indirect import: DeepAgentState imported via state module")
                
            # Check for usage in method signatures
            for i, line in enumerate(lines, 1):
                if 'DeepAgentState' in line and ('def ' in line or 'async def ' in line):
                    violations.append(f"Method signature usage at line {i}: {line.strip()}")
                    
                if 'state: DeepAgentState' in line or 'DeepAgentState(' in line:
                    violations.append(f"Direct usage at line {i}: {line.strip()}")
                    
        except Exception as e:
            violations.append(f"Scan error: {str(e)}")
            
        return violations
        
    def _scan_directory_for_deepagentstate(self, dir_path: str) -> Dict[str, List[str]]:
        """Recursively scan directory for DeepAgentState usage"""
        violations = {}
        search_path = self.netra_backend_root / dir_path
        
        if not search_path.exists():
            return violations
            
        for py_file in search_path.rglob("*.py"):
            # Skip test files and __pycache__
            if 'test_' in py_file.name or '__pycache__' in str(py_file):
                continue
                
            relative_path = py_file.relative_to(self.netra_backend_root)
            usage_violations = self._analyze_file_for_deepagentstate(py_file)
            
            if usage_violations:
                violations[str(relative_path)] = usage_violations
                
        return violations
        
    def _has_userexecutioncontext_import(self, file_path: Path) -> bool:
        """Check if file has adopted UserExecutionContext import"""
        try:
            content = file_path.read_text(encoding='utf-8')
            return 'from netra_backend.app.services.user_execution_context import UserExecutionContext' in content
        except Exception:
            return False
            
    def _build_violation_summary(self, violations: Dict[str, List[str]]) -> str:
        """Build formatted summary of violations for failure message"""
        summary_lines = []
        
        for file_path, file_violations in violations.items():
            summary_lines.append(f"[U+1F4C1] {file_path}:")
            for violation in file_violations:
                summary_lines.append(f"    ALERT:  {violation}")
            summary_lines.append("")
            
        return '\n'.join(summary_lines)


if __name__ == '__main__':
    unittest.main()