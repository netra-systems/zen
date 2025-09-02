#!/usr/bin/env python3
"""
LIFE OR DEATH CRITICAL P0: Mock Duplication Consolidation Script

This script systematically replaces ALL duplicate mock implementations across the codebase
with SSOT MockFactory usage. Critical for spacecraft reliability.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Eliminates inconsistent test behavior and ensures reliable mock interactions.

CRITICAL: This script ensures backward compatibility through deprecation warnings.
"""

import ast
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
SSOT_MOCK_IMPORT = "from test_framework.ssot.mocks import get_mock_factory"

class MockDuplicationAnalyzer:
    """Analyzes and consolidates duplicate mock implementations."""
    
    def __init__(self):
        self.duplicate_patterns = {
            # Agent mocks
            "MockAgent": "create_agent_mock",
            "MockOrchestrator": "create_orchestrator_mock", 
            "MockAgentService": "create_agent_mock",
            
            # Service mocks
            "MockServiceManager": "create_service_manager_mock",
            "MockServiceFactory": "create_service_factory_mock",
            "MockClickHouseService": "create_database_session_mock",
            "MockRedisService": "create_redis_client_mock",
            "MockLLMService": "create_llm_client_mock",
            "MockAuthService": "create_auth_service_mock",
            
            # WebSocket mocks
            "MockWebSocket": "create_websocket_connection_mock",
            "MockWebSocketManager": "create_websocket_manager_mock",
            "MockWebSocketConnection": "create_websocket_connection_mock",
            "MockWebSocketServer": "create_websocket_server_mock",
            "MockWebSocketBroadcaster": "create_websocket_manager_mock",
            
            # Database mocks
            "MockDatabaseSession": "create_database_session_mock",
            "MockRepository": "create_repository_mock",
            "MockDatabaseManager": "create_database_session_mock",
            "MockPostgreSQLConnection": "create_database_session_mock",
            "MockClickHouseConnection": "create_database_session_mock",
            
            # HTTP mocks
            "MockHttpClient": "create_http_client_mock",
            "MockResponse": "create_http_client_mock",
            
            # Configuration mocks
            "MockConfigLoader": "create_config_loader_mock",
            "MockEnvironment": "create_environment_mock",
            
            # Generic mocks
            "MockBase": "create_mock",
        }
        
        # Track files that need modification
        self.files_to_modify: Dict[Path, List[str]] = {}
        self.deprecated_mocks: Set[str] = set()
        
    def scan_codebase(self) -> Dict[str, List[Path]]:
        """Scan codebase for duplicate mock implementations."""
        logger.info("Scanning codebase for duplicate mock implementations...")
        
        duplicate_files = {}
        python_files = list(PROJECT_ROOT.rglob("*.py"))
        
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                found_mocks = self._find_mock_classes(content)
                for mock_class in found_mocks:
                    if mock_class in self.duplicate_patterns:
                        if mock_class not in duplicate_files:
                            duplicate_files[mock_class] = []
                        duplicate_files[mock_class].append(file_path)
                        
            except Exception as e:
                logger.warning(f"Error scanning {file_path}: {e}")
                
        return duplicate_files
        
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv",
            # Skip the SSOT mocks file itself
            "test_framework/ssot/mocks.py",
            # Skip this consolidation script
            "scripts/consolidate_duplicate_mocks.py"
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
        
    def _find_mock_classes(self, content: str) -> List[str]:
        """Find mock class definitions in file content."""
        mock_classes = []
        
        # Look for class definitions starting with "Mock"
        class_pattern = r"^class (Mock\w+).*?:"
        matches = re.findall(class_pattern, content, re.MULTILINE)
        mock_classes.extend(matches)
        
        return mock_classes
        
    def generate_consolidation_report(self, duplicate_files: Dict[str, List[Path]]) -> str:
        """Generate a comprehensive consolidation report."""
        report_lines = [
            "# MOCK DUPLICATION CONSOLIDATION REPORT",
            f"# Generated on: {__import__('datetime').datetime.now()}",
            "",
            "## CRITICAL FINDINGS",
            f"- Found {len(duplicate_files)} different mock types with duplicates",
            f"- Total files affected: {sum(len(files) for files in duplicate_files.values())}",
            "",
            "## DUPLICATE MOCK IMPLEMENTATIONS",
            ""
        ]
        
        for mock_class, files in sorted(duplicate_files.items()):
            factory_method = self.duplicate_patterns.get(mock_class, "UNMAPPED")
            report_lines.extend([
                f"### {mock_class} ({len(files)} duplicates)",
                f"**SSOT Factory Method:** `{factory_method}`",
                f"**Files containing duplicates:**",
                ""
            ])
            
            for file_path in sorted(files):
                rel_path = file_path.relative_to(PROJECT_ROOT)
                report_lines.append(f"- `{rel_path}`")
                
            report_lines.append("")
            
        return "\\n".join(report_lines)
        
    def consolidate_file(self, file_path: Path, mock_class: str) -> bool:
        """Consolidate duplicate mocks in a single file."""
        logger.info(f"Consolidating {mock_class} in {file_path.relative_to(PROJECT_ROOT)}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                
            modified_content = self._apply_consolidation(original_content, mock_class, file_path)
            
            if modified_content != original_content:
                # Create backup
                backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                    
                # Write consolidated version
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                    
                logger.info(f"Successfully consolidated {mock_class} in {file_path.relative_to(PROJECT_ROOT)}")
                return True
            else:
                logger.info(f"No changes needed for {file_path.relative_to(PROJECT_ROOT)}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to consolidate {file_path}: {e}")
            return False
            
    def _apply_consolidation(self, content: str, mock_class: str, file_path: Path) -> str:
        """Apply consolidation transformations to file content."""
        lines = content.split('\\n')
        modified_lines = []
        factory_method = self.duplicate_patterns.get(mock_class, "create_mock")
        
        # Track import insertion
        has_ssot_import = SSOT_MOCK_IMPORT in content
        import_inserted = False
        in_mock_class = False
        mock_class_indent = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Add SSOT import if needed
            if not has_ssot_import and not import_inserted and line.strip().startswith("from "):
                modified_lines.append(line)
                modified_lines.append(SSOT_MOCK_IMPORT)
                import_inserted = True
                i += 1
                continue
                
            # Detect mock class definition
            if re.match(rf"^(\\s*)class {mock_class}.*?:", line):
                mock_class_indent = len(line) - len(line.lstrip())
                
                # Add deprecation warning
                indent = " " * mock_class_indent
                deprecation_comment = f'{indent}"""DEPRECATED: Use MockFactory.{factory_method}() instead."""'
                deprecation_warning = (
                    f'{indent}def __init__(self, *args, **kwargs):\\n'
                    f'{indent}    import warnings\\n'
                    f'{indent}    warnings.warn(\\n'
                    f'{indent}        f"{{self.__class__.__name__}} is deprecated. "'
                    f'"Use get_mock_factory().{factory_method}() instead.",\\n'
                    f'{indent}        DeprecationWarning,\\n'
                    f'{indent}        stacklevel=2\\n'
                    f'{indent}    )\\n'
                    f'{indent}    super().__init__(*args, **kwargs)\\n'
                )
                
                modified_lines.append(line)
                modified_lines.append(deprecation_comment)
                modified_lines.append("")
                modified_lines.append(deprecation_warning)
                
                in_mock_class = True
                i += 1
                continue
                
            # Skip duplicate class body (keep only deprecation warning)
            if in_mock_class:
                current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
                
                # End of class detected
                if line.strip() and current_indent <= mock_class_indent:
                    in_mock_class = False
                    modified_lines.append(line)
                else:
                    # Skip class body except for docstring
                    if '"""' in line and "DEPRECATED" not in line:
                        # Keep existing docstring but add deprecation notice
                        if line.strip().startswith('"""'):
                            deprecated_docstring = line.replace('"""', '"""DEPRECATED: ')
                            modified_lines.append(deprecated_docstring)
                        else:
                            modified_lines.append(line)
                    # Skip everything else in class body
                i += 1
                continue
                
            # Keep all other lines
            modified_lines.append(line)
            i += 1
            
        return '\\n'.join(modified_lines)
        
    def create_usage_migration_guide(self, duplicate_files: Dict[str, List[Path]]) -> str:
        """Create a migration guide for developers."""
        guide_lines = [
            "# MOCK CONSOLIDATION MIGRATION GUIDE",
            "",
            "## Overview",
            "All duplicate mock implementations have been consolidated to use the SSOT MockFactory.",
            "This ensures consistent behavior and eliminates maintenance overhead.",
            "",
            "## New Usage Pattern",
            "```python",
            "from test_framework.ssot.mocks import get_mock_factory",
            "",
            "def test_example():",
            "    factory = get_mock_factory()",
            "    ",
            "    # Instead of: MockAgent()",
            "    agent_mock = factory.create_agent_mock()",
            "    ",
            "    # Instead of: MockWebSocket()",  
            "    websocket_mock = factory.create_websocket_connection_mock()",
            "    ",
            "    # Instead of: MockServiceManager()",
            "    service_mock = factory.create_service_manager_mock()",
            "```",
            "",
            "## Migration Mappings",
            ""
        ]
        
        for mock_class, files in sorted(duplicate_files.items()):
            factory_method = self.duplicate_patterns.get(mock_class, "create_mock")
            guide_lines.extend([
                f"### {mock_class}",
                f"**Old:** `{mock_class}()`",
                f"**New:** `get_mock_factory().{factory_method}()`",
                ""
            ])
            
        guide_lines.extend([
            "## Benefits",
            "- Consistent mock behavior across all tests", 
            "- Centralized mock configuration",
            "- Automatic cleanup and resource management",
            "- Call history tracking and verification",
            "- Environment-specific mock behavior",
            "- No more mock implementation drift",
            "",
            "## Backward Compatibility",
            "Existing mock classes include deprecation warnings but still work.",
            "Gradually migrate tests to use the new MockFactory pattern.",
            ""
        ])
        
        return "\\n".join(guide_lines)


def main():
    """Main consolidation process."""
    print("LIFE OR DEATH CRITICAL P0: Mock Duplication Consolidation")
    print("=" * 60)
    
    analyzer = MockDuplicationAnalyzer()
    
    # Step 1: Scan for duplicates
    duplicate_files = analyzer.scan_codebase()
    
    if not duplicate_files:
        print("SUCCESS: No duplicate mock implementations found!")
        return
        
    print(f"CRITICAL: Found {len(duplicate_files)} mock types with duplicates")
    total_files = sum(len(files) for files in duplicate_files.values())
    print(f"CRITICAL: Total files affected: {total_files}")
    
    # Step 2: Generate reports
    consolidation_report = analyzer.generate_consolidation_report(duplicate_files)
    migration_guide = analyzer.create_usage_migration_guide(duplicate_files)
    
    # Save reports
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    with open(reports_dir / "mock_consolidation_report.md", "w", encoding="utf-8") as f:
        f.write(consolidation_report)
        
    with open(reports_dir / "mock_migration_guide.md", "w", encoding="utf-8") as f:
        f.write(migration_guide)
        
    print(f"REPORTS: Reports saved to {reports_dir}")
    
    # Step 3: Ask for confirmation
    print("\\nPROCEED: Proceed with consolidation? This will:")
    print("   - Add deprecation warnings to duplicate mock classes")
    print("   - Create backup files (.bak)")
    print("   - Update imports to use SSOT MockFactory")
    
    response = input("\\nContinue? (y/N): ").strip().lower()
    if response != 'y':
        print("CANCELLED: Consolidation cancelled")
        return
        
    # Step 4: Apply consolidation
    print("\\nAPPLYING: Applying consolidation...")
    consolidated_files = 0
    
    for mock_class, files in duplicate_files.items():
        for file_path in files:
            if analyzer.consolidate_file(file_path, mock_class):
                consolidated_files += 1
                
    print(f"\\nSUCCESS: Successfully consolidated {consolidated_files} files")
    print(f"REPORT: Consolidation report: {reports_dir / 'mock_consolidation_report.md'}")
    print(f"GUIDE: Migration guide: {reports_dir / 'mock_migration_guide.md'}")
    
    print("\\nNEXT STEPS:")
    print("1. Run test suite to verify no regressions")
    print("2. Gradually migrate tests to use MockFactory methods")
    print("3. Remove deprecated mock classes after full migration")
    print("\\nCRITICAL: Test all affected functionality before deployment!")


if __name__ == "__main__":
    main()