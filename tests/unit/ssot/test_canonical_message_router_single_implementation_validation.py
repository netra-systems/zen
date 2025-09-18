#!/usr/bin/env python3
"""
SSOT Validation Test: Canonical Message Router Single Implementation
==================================================================

BUSINESS CRITICAL: This test protects the $500K+ ARR Golden Path where users login and get AI responses.

PURPOSE:
- Validates exactly ONE CanonicalMessageRouter implementation exists
- Prevents message routing fragmentation that breaks chat functionality
- Ensures WebSocket message routing follows SSOT patterns
- Currently FAILS (multiple implementations exist) - will pass after SSOT consolidation

GOLDEN PATH IMPACT:
- Chat functionality is 90% of platform value
- Message routing failures break user -> AI response flow
- Multiple routers cause race conditions and silent failures
- SSOT compliance ensures reliable message delivery

BUSINESS VALUE:
- Protects primary revenue stream (chat functionality)
- Prevents customer churn from broken AI interactions
- Ensures WebSocket reliability for real-time chat experience
- Maintains system stability for Enterprise customers

TEST STRATEGY:
1. Scan entire codebase for message router class definitions
2. Validate exactly one canonical implementation exists
3. Check for related router classes that should be consolidated
4. Verify canonical location follows architecture standards
5. Provide detailed failure analysis for SSOT violations

Created: 2025-01-17
Author: Claude Code (Netra Systems SSOT Validation)
"""

import ast
import os
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TestCanonicalMessageRouterSSOTValidation(unittest.TestCase):
    """
    MISSION CRITICAL: Validates WebSocket message routing SSOT compliance.
    
    This test ensures the Golden Path (users login -> get AI responses) works reliably
    by preventing message router fragmentation that breaks chat functionality.
    """
    
    def setUp(self):
        """Initialize test with project root discovery."""
        self.project_root = self._find_project_root()
        self.canonical_location = "netra_backend/app/websocket_core/canonical_message_router.py"
        
        # Known router class patterns that should be consolidated
        self.router_class_patterns = [
            "CanonicalMessageRouter",
            "MessageRouter", 
            "QualityMessageRouter",
            "WebSocketMessageRouter",
            "ChatMessageRouter",
            "AgentMessageRouter"
        ]
        
        # Directories to skip during scan
        self.skip_dirs = {
            ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
            "node_modules", ".mypy_cache", ".tox", "build", "dist",
            ".idea", ".vscode", "backups", "backup",
            ".test_venv", "test_venv", "google-cloud-sdk"
        }
        
        # File patterns to skip
        self.skip_file_patterns = {
            ".backup", ".bak", ".old", ".tmp", ".swp", "~"
        }

    def _find_project_root(self) -> Path:
        """Find the project root directory containing CLAUDE.md."""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "CLAUDE.md").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not find project root with CLAUDE.md")

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scan."""
        # Skip backup files and temporary files
        for pattern in self.skip_file_patterns:
            if pattern in str(file_path):
                return True
        
        # Skip non-Python files
        if file_path.suffix != ".py":
            return True
            
        return False

    def _should_skip_directory(self, dir_path: Path) -> bool:
        """Check if directory should be skipped during scan."""
        return dir_path.name in self.skip_dirs

    def _extract_class_definitions(self, file_path: Path) -> List[Tuple[str, int]]:
        """
        Extract class definitions from Python file using AST parsing.
        
        Returns:
            List of (class_name, line_number) tuples
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append((node.name, node.lineno))
            
            return classes
            
        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            # Skip files that can't be parsed
            return []

    def _scan_for_router_classes(self) -> Dict[str, List[Tuple[Path, int]]]:
        """
        Scan entire codebase for message router class definitions.
        
        Returns:
            Dictionary mapping class names to list of (file_path, line_number) tuples
        """
        router_implementations = {}
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if not self._should_skip_directory(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                
                if self._should_skip_file(file_path):
                    continue
                
                classes = self._extract_class_definitions(file_path)
                
                for class_name, line_num in classes:
                    # Check if this class matches any router pattern
                    for pattern in self.router_class_patterns:
                        if pattern in class_name or class_name in pattern:
                            if class_name not in router_implementations:
                                router_implementations[class_name] = []
                            
                            relative_path = file_path.relative_to(self.project_root)
                            router_implementations[class_name].append((relative_path, line_num))
                            break
        
        return router_implementations

    def _validate_canonical_implementation(self, implementations: Dict[str, List[Tuple[Path, int]]]) -> Tuple[bool, str]:
        """
        Validate that exactly one canonical implementation exists.
        
        Returns:
            (is_valid, error_message) tuple
        """
        canonical_implementations = implementations.get("CanonicalMessageRouter", [])
        
        if len(canonical_implementations) == 0:
            return False, "X CRITICAL: No CanonicalMessageRouter implementation found!"
        
        if len(canonical_implementations) > 1:
            locations = [f"{path}:{line}" for path, line in canonical_implementations]
            return False, f"X CRITICAL: Multiple CanonicalMessageRouter implementations found: {locations}"
        
        # Check if canonical implementation is in the expected location
        canonical_path, _ = canonical_implementations[0]
        expected_path = Path(self.canonical_location)
        
        if canonical_path != expected_path:
            return False, (
                f"X CRITICAL: CanonicalMessageRouter found at {canonical_path} "
                f"but should be at {expected_path}"
            )
        
        return True, "CHECK Single canonical implementation found in correct location"

    def _analyze_consolidation_opportunities(self, implementations: Dict[str, List[Tuple[Path, int]]]) -> str:
        """Analyze which router classes should be consolidated."""
        analysis = []
        total_implementations = 0
        
        for class_name, locations in implementations.items():
            if class_name != "CanonicalMessageRouter":
                total_implementations += len(locations)
                for path, line in locations:
                    analysis.append(f"  • {class_name} at {path}:{line}")
        
        if total_implementations == 0:
            return "CHECK No duplicate router implementations found"
        
        return (
            f"X CONSOLIDATION REQUIRED: {total_implementations} duplicate/alternative router implementations:\n" +
            "\n".join(analysis)
        )

    def test_single_canonical_message_router_implementation(self):
        """
        MISSION CRITICAL: Validate exactly one CanonicalMessageRouter exists.
        
        BUSINESS IMPACT:
        - Chat functionality is 90% of platform value
        - Multiple routers cause message routing failures
        - Silent failures break user -> AI response Golden Path
        - $500K+ ARR depends on reliable WebSocket message routing
        
        EXPECTED BEHAVIOR:
        - Currently FAILS (multiple implementations exist)
        - Will PASS after SSOT consolidation is complete
        """
        print("\n" + "="*80)
        print("🚨 EXECUTING MISSION CRITICAL SSOT VALIDATION")
        print("   WebSocket Message Router Single Implementation Test")
        print("="*80)
        
        # Scan entire codebase for router implementations
        print("🔍 Scanning codebase for message router implementations...")
        router_implementations = self._scan_for_router_classes()
        
        # Print discovery summary
        total_classes = sum(len(locations) for locations in router_implementations.values())
        print(f"📊 Discovery: Found {total_classes} router-related class implementations")
        
        # Validate canonical implementation
        is_canonical_valid, canonical_message = self._validate_canonical_implementation(router_implementations)
        print(f"🎯 Canonical Validation: {canonical_message}")
        
        # Analyze consolidation opportunities
        consolidation_analysis = self._analyze_consolidation_opportunities(router_implementations)
        print(f"🔧 Consolidation Analysis:\n{consolidation_analysis}")
        
        # Generate detailed failure report
        if not is_canonical_valid or "CONSOLIDATION REQUIRED" in consolidation_analysis:
            failure_report = self._generate_failure_report(router_implementations)
            print("\n" + "="*80)
            print("X SSOT VALIDATION FAILED - GOLDEN PATH AT RISK")
            print("="*80)
            print(failure_report)
            print("="*80)
            
            # Fail the test with comprehensive business impact message
            self.fail(
                f"CRITICAL SSOT VIOLATION: WebSocket message routing not consolidated.\n\n"
                f"BUSINESS IMPACT:\n"
                f"• Chat functionality (90% of platform value) at risk\n"
                f"• Multiple routers cause race conditions and silent failures\n"
                f"• Golden Path broken: users login but don't get AI responses\n"
                f"• $500K+ ARR threatened by unreliable message routing\n\n"
                f"TECHNICAL DETAILS:\n"
                f"• {canonical_message}\n"
                f"• {consolidation_analysis}\n\n"
                f"REQUIRED ACTION:\n"
                f"1. Consolidate all router implementations into single CanonicalMessageRouter\n"
                f"2. Update all imports to use canonical implementation\n"
                f"3. Remove duplicate/alternative router classes\n"
                f"4. Re-run this test to verify SSOT compliance\n\n"
                f"See test output above for detailed implementation locations."
            )
        
        print("\nCHECK SSOT VALIDATION PASSED - WebSocket routing properly consolidated")
        print("🎉 Golden Path protected: Single message router implementation confirmed")

    def _generate_failure_report(self, implementations: Dict[str, List[Tuple[Path, int]]]) -> str:
        """Generate detailed failure report for SSOT violations."""
        report = []
        report.append("DETAILED VIOLATION ANALYSIS:")
        report.append("")
        
        # Canonical implementation status
        canonical_impls = implementations.get("CanonicalMessageRouter", [])
        report.append(f"📍 CANONICAL IMPLEMENTATION STATUS:")
        if len(canonical_impls) == 0:
            report.append(f"   X No CanonicalMessageRouter found")
        elif len(canonical_impls) == 1:
            path, line = canonical_impls[0]
            expected_path = Path(self.canonical_location)
            if path == expected_path:
                report.append(f"   CHECK Found at correct location: {path}:{line}")
            else:
                report.append(f"   WARNING️  Found at {path}:{line} (should be {expected_path})")
        else:
            report.append(f"   X Multiple implementations found:")
            for path, line in canonical_impls:
                report.append(f"      • {path}:{line}")
        
        report.append("")
        
        # Alternative/duplicate implementations
        duplicates = {k: v for k, v in implementations.items() if k != "CanonicalMessageRouter"}
        if duplicates:
            report.append("🔄 DUPLICATE/ALTERNATIVE IMPLEMENTATIONS TO CONSOLIDATE:")
            for class_name, locations in duplicates.items():
                report.append(f"   📋 {class_name} ({len(locations)} implementation{'s' if len(locations) > 1 else ''}):")
                for path, line in locations:
                    report.append(f"      • {path}:{line}")
                report.append("")
        
        # Consolidation impact
        total_violations = sum(len(locations) for class_name, locations in duplicates.items())
        if total_violations > 0:
            report.append(f"💥 BUSINESS IMPACT: {total_violations} router implementations threaten system stability")
            report.append("   • Message routing race conditions")
            report.append("   • Silent WebSocket failures")
            report.append("   • Broken user -> AI response flow")
            report.append("   • Chat functionality degradation")
        
        return "\n".join(report)

    def test_websocket_message_routing_architecture_compliance(self):
        """
        Validate WebSocket message routing follows established architecture patterns.
        
        This supplementary test ensures the message router implementation
        follows SSOT patterns and integrates properly with the WebSocket system.
        """
        print("\n🏗️  Validating WebSocket message routing architecture compliance...")
        
        canonical_path = self.project_root / self.canonical_location
        
        if not canonical_path.exists():
            self.skipTest(f"Canonical implementation not found at {canonical_path}")
        
        # Validate file contains expected patterns
        try:
            with open(canonical_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for essential architectural patterns
            required_patterns = [
                "class CanonicalMessageRouter",
                "async def route_message",
                "WebSocketManager",
                "AgentRegistry"
            ]
            
            missing_patterns = []
            for pattern in required_patterns:
                if pattern not in content:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                self.fail(
                    f"Canonical implementation missing required patterns: {missing_patterns}\n"
                    f"This indicates incomplete SSOT consolidation."
                )
            
            print("CHECK Architecture compliance validated")
            
        except Exception as e:
            self.fail(f"Could not validate canonical implementation: {e}")


if __name__ == "__main__":
    # Run the test with verbose output
    unittest.main(verbosity=2, buffer=False)