"""
Test Deprecated Import Pattern Elimination - Issue #1100

Business Value Justification (BVJ):
- Segment: Platform/Internal Infrastructure
- Business Goal: Eliminate SSOT violations threatening WebSocket reliability  
- Value Impact: Prevents race conditions affecting $500K+ ARR chat functionality
- Strategic Impact: Ensures long-term maintainability of WebSocket infrastructure

This test module validates the elimination of deprecated `websocket_manager_factory` 
imports across 25+ identified files and ensures proper SSOT consolidation.

CRITICAL: These tests are designed to FAIL initially with current fragmented imports
and PASS after SSOT import migration is complete.
"""

import os
import re
import ast
import pytest
from pathlib import Path
from typing import List, Dict, Set
from test_framework.base_integration_test import BaseIntegrationTest
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestDeprecatedImportElimination(BaseIntegrationTest):
    """Test elimination of deprecated websocket_manager_factory imports."""
    
    # Priority files that MUST be migrated to SSOT imports
    PRIORITY_FILES = [
        "netra_backend/app/agents/supervisor/agent_instance_factory.py",
        "netra_backend/app/agents/tool_executor_factory.py", 
        "netra_backend/app/services/agent_websocket_bridge.py",
        "netra_backend/app/websocket_core/migration_adapter.py",
        "netra_backend/app/core/supervisor_factory.py",
        "netra_backend/app/core/interfaces_data.py",
        "netra_backend/app/agents/synthetic_data_progress_tracker.py",
        "netra_backend/app/agents/example_message_processor.py",
        "netra_backend/app/websocket_core/unified_init.py",
        "netra_backend/app/websocket_core/protocols.py",
        "netra_backend/app/websocket_core/canonical_imports.py",
        "netra_backend/app/websocket_core/__init__.py",
        "netra_backend/app/websocket_core/utils.py"
    ]
    
    # Deprecated import patterns that should be eliminated
    DEPRECATED_PATTERNS = [
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import\s+create_websocket_manager",
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import\s+WebSocketManagerFactory", 
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import\s+get_websocket_manager_factory",
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import\s+create_websocket_manager_sync",
        r"import\s+netra_backend\.app\.websocket_core\.websocket_manager_factory",
        r"websocket_manager_factory\.",  # Any usage of factory module
    ]
    
    # Canonical SSOT import patterns that should be used instead
    CANONICAL_PATTERNS = [
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+WebSocketManager",
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+get_websocket_manager",
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+WebSocketManagerMode",
    ]
    
    @pytest.fixture(scope="class")
    def project_root(self) -> Path:
        """Get project root directory."""
        current_dir = Path(__file__).parent
        # Navigate up to find netra-apex root
        while current_dir.name != "netra-apex" and current_dir.parent != current_dir:
            current_dir = current_dir.parent
        return current_dir
    
    def _scan_file_for_patterns(self, file_path: Path, patterns: List[str]) -> List[Dict[str, any]]:
        """
        Scan a file for specific import patterns.
        
        Args:
            file_path: Path to the file to scan
            patterns: List of regex patterns to search for
            
        Returns:
            List of pattern matches with line numbers and content
        """
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            for line_num, line in enumerate(lines, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        matches.append({
                            'file': str(file_path),
                            'line_number': line_num,
                            'line_content': line.strip(),
                            'pattern': pattern,
                            'match_type': 'deprecated' if pattern in self.DEPRECATED_PATTERNS else 'canonical'
                        })
        except (UnicodeDecodeError, FileNotFoundError) as e:
            logger.warning(f"Could not scan file {file_path}: {e}")
        
        return matches
    
    def _get_all_python_files(self, project_root: Path) -> List[Path]:
        """Get all Python files in the netra_backend app directory."""
        app_dir = project_root / "netra_backend" / "app"
        if not app_dir.exists():
            pytest.skip(f"netra_backend/app directory not found at {app_dir}")
            
        python_files = []
        for py_file in app_dir.rglob("*.py"):
            # Skip __pycache__ and test files
            if "__pycache__" not in str(py_file) and "test_" not in py_file.name:
                python_files.append(py_file)
                
        return python_files
    
    @pytest.mark.unit
    def test_no_deprecated_websocket_factory_imports_in_production_code(self, project_root):
        """
        SHOULD FAIL: Detect deprecated websocket_manager_factory imports in production files.
        
        This test is designed to FAIL initially, detecting the 25+ files using
        deprecated import patterns. It will PASS after SSOT import migration.
        """
        logger.info("Scanning for deprecated websocket_manager_factory imports in production code")
        
        python_files = self._get_all_python_files(project_root)
        deprecated_imports_found = []
        
        for py_file in python_files:
            matches = self._scan_file_for_patterns(py_file, self.DEPRECATED_PATTERNS)
            deprecated_imports_found.extend(matches)
        
        # Log findings for debugging
        if deprecated_imports_found:
            logger.error(f"Found {len(deprecated_imports_found)} deprecated imports:")
            for match in deprecated_imports_found:
                logger.error(f"  {match['file']}:{match['line_number']} - {match['line_content']}")
        
        # This assertion should FAIL initially with current fragmented imports
        assert len(deprecated_imports_found) == 0, (
            f"Found {len(deprecated_imports_found)} deprecated websocket_manager_factory imports. "
            f"These must be migrated to SSOT patterns:\n" +
            "\n".join([f"  {m['file']}:{m['line_number']} - {m['line_content']}" 
                      for m in deprecated_imports_found])
        )
    
    @pytest.mark.unit  
    def test_agent_factory_files_use_ssot_imports(self, project_root):
        """
        SHOULD FAIL: Validate agent factory files use SSOT WebSocket imports.
        
        Specifically targets agent_instance_factory.py and tool_executor_factory.py
        which are critical for agent execution pipeline.
        """
        logger.info("Validating agent factory files use SSOT WebSocket imports")
        
        agent_factory_files = [
            project_root / "netra_backend/app/agents/supervisor/agent_instance_factory.py",
            project_root / "netra_backend/app/agents/tool_executor_factory.py"
        ]
        
        violations = []
        missing_canonical = []
        
        for file_path in agent_factory_files:
            if not file_path.exists():
                logger.warning(f"Agent factory file not found: {file_path}")
                continue
                
            # Check for deprecated patterns
            deprecated_matches = self._scan_file_for_patterns(file_path, self.DEPRECATED_PATTERNS)
            violations.extend(deprecated_matches)
            
            # Check for canonical patterns  
            canonical_matches = self._scan_file_for_patterns(file_path, self.CANONICAL_PATTERNS)
            
            # If file contains WebSocket-related imports, it should use canonical patterns
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'websocket' in content.lower() and not canonical_matches:
                    missing_canonical.append(str(file_path))
        
        # This assertion should FAIL initially 
        assert len(violations) == 0, (
            f"Agent factory files contain {len(violations)} deprecated imports:\n" +
            "\n".join([f"  {v['file']}:{v['line_number']} - {v['line_content']}" 
                      for v in violations])
        )
        
        # Validate canonical patterns are used
        if missing_canonical:
            pytest.fail(
                f"Agent factory files with WebSocket usage missing canonical imports: "
                f"{', '.join(missing_canonical)}"
            )
    
    @pytest.mark.unit
    def test_websocket_bridge_uses_canonical_import(self, project_root):
        """
        SHOULD FAIL: Validate agent_websocket_bridge uses canonical imports.
        
        The AgentWebSocketBridge is critical infrastructure connecting agents
        to WebSocket functionality and must use SSOT patterns.
        """
        logger.info("Validating agent_websocket_bridge uses canonical WebSocket imports")
        
        bridge_file = project_root / "netra_backend/app/services/agent_websocket_bridge.py"
        
        if not bridge_file.exists():
            pytest.skip(f"AgentWebSocketBridge file not found: {bridge_file}")
        
        # Check for deprecated patterns
        deprecated_matches = self._scan_file_for_patterns(bridge_file, self.DEPRECATED_PATTERNS)
        
        # Check for canonical patterns
        canonical_matches = self._scan_file_for_patterns(bridge_file, self.CANONICAL_PATTERNS)
        
        # This assertion should FAIL initially if deprecated imports exist
        assert len(deprecated_matches) == 0, (
            f"AgentWebSocketBridge contains {len(deprecated_matches)} deprecated imports:\n" +
            "\n".join([f"  Line {m['line_number']}: {m['line_content']}" 
                      for m in deprecated_matches])
        )
        
        # Validate canonical patterns are present
        assert len(canonical_matches) > 0, (
            "AgentWebSocketBridge should use canonical WebSocket imports. "
            "Expected patterns like: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager"
        )
    
    @pytest.mark.unit
    def test_migration_adapter_elimination(self, project_root):
        """
        SHOULD FAIL: Validate migration_adapter.py removed or uses SSOT.
        
        The migration_adapter.py file was created as temporary compatibility
        and should be eliminated as part of SSOT consolidation.
        """
        logger.info("Validating migration_adapter elimination or SSOT compliance")
        
        adapter_file = project_root / "netra_backend/app/websocket_core/migration_adapter.py"
        
        if not adapter_file.exists():
            # File eliminated - this is the preferred outcome
            logger.info("migration_adapter.py successfully eliminated")
            return
        
        # If file still exists, it should not contain deprecated patterns
        deprecated_matches = self._scan_file_for_patterns(adapter_file, self.DEPRECATED_PATTERNS)
        
        # This assertion should FAIL initially if deprecated patterns exist
        assert len(deprecated_matches) == 0, (
            f"migration_adapter.py contains {len(deprecated_matches)} deprecated imports "
            "and should either be eliminated or use SSOT patterns:\n" +
            "\n".join([f"  Line {m['line_number']}: {m['line_content']}" 
                      for m in deprecated_matches])
        )
    
    @pytest.mark.unit
    def test_websocket_core_module_ssot_compliance(self, project_root):
        """
        SHOULD FAIL: Validate websocket_core module files use SSOT patterns.
        
        Files in websocket_core module should be exemplars of SSOT compliance
        since they define the canonical implementation.
        """
        logger.info("Validating websocket_core module SSOT compliance")
        
        websocket_core_dir = project_root / "netra_backend/app/websocket_core"
        
        if not websocket_core_dir.exists():
            pytest.skip(f"websocket_core directory not found: {websocket_core_dir}")
        
        violations = []
        websocket_files = []
        
        for py_file in websocket_core_dir.glob("*.py"):
            if py_file.name.startswith("test_") or py_file.name == "__pycache__":
                continue
                
            websocket_files.append(py_file)
            deprecated_matches = self._scan_file_for_patterns(py_file, self.DEPRECATED_PATTERNS)
            violations.extend(deprecated_matches)
        
        logger.info(f"Scanned {len(websocket_files)} websocket_core files")
        
        # This assertion should FAIL initially if any websocket_core files use deprecated patterns
        assert len(violations) == 0, (
            f"websocket_core module files contain {len(violations)} deprecated imports:\n" +
            "\n".join([f"  {v['file']}:{v['line_number']} - {v['line_content']}" 
                      for v in violations])
        )
    
    @pytest.mark.unit
    def test_priority_files_import_migration_status(self, project_root):
        """
        SHOULD FAIL: Validate all priority files have completed import migration.
        
        Tracks migration progress across the highest priority files identified
        in Issue #1100 analysis.
        """
        logger.info("Validating priority files import migration status")
        
        migration_status = {
            'completed': [],
            'pending': [],
            'violations': []
        }
        
        for priority_file in self.PRIORITY_FILES:
            file_path = project_root / priority_file
            
            if not file_path.exists():
                logger.warning(f"Priority file not found: {file_path}")
                continue
            
            # Check for deprecated patterns
            deprecated_matches = self._scan_file_for_patterns(file_path, self.DEPRECATED_PATTERNS)
            
            if deprecated_matches:
                migration_status['pending'].append(priority_file)
                migration_status['violations'].extend(deprecated_matches)
            else:
                # Check if file contains WebSocket imports at all
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'websocket' in content.lower():
                        # File has WebSocket usage - check for canonical patterns
                        canonical_matches = self._scan_file_for_patterns(file_path, self.CANONICAL_PATTERNS)
                        if canonical_matches:
                            migration_status['completed'].append(priority_file)
                        else:
                            migration_status['pending'].append(priority_file)
                    else:
                        # File doesn't use WebSocket - not applicable
                        pass
        
        # Log migration status
        logger.info(f"Migration Status: {len(migration_status['completed'])} completed, "
                   f"{len(migration_status['pending'])} pending")
        
        if migration_status['violations']:
            logger.error("Priority files with violations:")
            for violation in migration_status['violations']:
                logger.error(f"  {violation['file']}:{violation['line_number']} - {violation['line_content']}")
        
        # This assertion should FAIL initially with pending migrations
        assert len(migration_status['pending']) == 0, (
            f"{len(migration_status['pending'])} priority files still pending migration:\n" +
            "\n".join([f"  {f}" for f in migration_status['pending']]) +
            f"\n\nFound {len(migration_status['violations'])} deprecated imports to fix."
        )


class TestSSotImportPathConsistency(BaseIntegrationTest):
    """Test consistency of SSOT import paths across the codebase."""
    
    @pytest.mark.unit
    def test_websocket_manager_import_path_consistency(self, project_root):
        """
        SHOULD FAIL: Validate consistent import paths for WebSocketManager across all modules.
        
        All files importing WebSocketManager should use the same canonical import path
        to prevent confusion and ensure SSOT compliance.
        """
        logger.info("Validating WebSocketManager import path consistency")
        
        websocket_manager_imports = []
        python_files = self._get_all_python_files(project_root)
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if 'WebSocketManager' in line and ('import' in line or 'from' in line):
                        websocket_manager_imports.append({
                            'file': str(py_file),
                            'line_number': line_num,
                            'import_statement': line.strip()
                        })
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Group imports by pattern
        import_patterns = {}
        for import_info in websocket_manager_imports:
            pattern = import_info['import_statement']
            if pattern not in import_patterns:
                import_patterns[pattern] = []
            import_patterns[pattern].append(import_info)
        
        logger.info(f"Found {len(import_patterns)} different WebSocketManager import patterns")
        for pattern, usages in import_patterns.items():
            logger.info(f"  Pattern: {pattern} (used in {len(usages)} files)")
        
        # Should have only one canonical pattern for WebSocketManager imports
        canonical_pattern = "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager"
        
        non_canonical_imports = []
        for pattern, usages in import_patterns.items():
            if pattern != canonical_pattern and 'WebSocketManager' in pattern:
                non_canonical_imports.extend(usages)
        
        # This assertion should FAIL initially with multiple import patterns
        assert len(non_canonical_imports) == 0, (
            f"Found {len(non_canonical_imports)} non-canonical WebSocketManager imports. "
            f"All should use: {canonical_pattern}\n" +
            "\n".join([f"  {imp['file']}:{imp['line_number']} - {imp['import_statement']}" 
                      for imp in non_canonical_imports])
        )
    
    def _get_all_python_files(self, project_root: Path) -> List[Path]:
        """Get all Python files in the netra_backend app directory."""
        app_dir = project_root / "netra_backend" / "app"
        if not app_dir.exists():
            return []
            
        python_files = []
        for py_file in app_dir.rglob("*.py"):
            if "__pycache__" not in str(py_file) and "test_" not in py_file.name:
                python_files.append(py_file)
                
        return python_files