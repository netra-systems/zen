#!/usr/bin/env python3
"""
WebSocket Manager Import Scanner - Phase 1 of Issue #1196 Remediation

This script comprehensively scans for WebSocket Manager import variations
across the entire codebase to establish baseline metrics and identify
priority files for systematic import consolidation.

BUSINESS CONTEXT:
- 1,772 import variations threaten $500K+ ARR Golden Path functionality 
- WebSocket Manager delivers 90% of platform value (chat functionality)
- Import race conditions causing Cloud Run initialization failures

PURPOSE:
1. Identify all WebSocket Manager import patterns and variations
2. Categorize imports by priority (Golden Path vs. tests vs. utilities)
3. Generate systematic remediation plan with risk assessment
4. Track progress toward single canonical SSOT import path

CANONICAL TARGET:
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
"""

import os
import re
import ast
import json
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class ImportViolation:
    """Represents a WebSocket Manager import variation violation."""
    file_path: str
    line_number: int
    import_statement: str
    import_type: str  # "from_import", "direct_import", "factory_import", etc.
    priority: str     # "critical", "high", "medium", "low"
    category: str     # "routes", "core", "tests", "utilities", etc.

class WebSocketImportScanner:
    """Comprehensive scanner for WebSocket Manager import variations."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.violations: List[ImportViolation] = []
        
        # Define canonical SSOT import patterns
        self.canonical_patterns = {
            "websocket_manager": "from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
            "unified_manager": "from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation",
            "canonical_imports": "from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager",
        }
        
        # Define import patterns to find and consolidate
        self.websocket_patterns = [
            # WebSocket Manager imports
            r'from\s+netra_backend\.app\.websocket_core\.manager\s+import.*WebSocketManager',
            r'from\s+netra_backend\.app\.websocket_core\.unified_manager\s+import.*WebSocketManager',
            r'from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import.*WebSocketManager',
            r'from\s+netra_backend\.app\.websocket_core\s+import.*WebSocketManager',
            
            # Factory imports
            r'from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import',
            r'from\s+netra_backend\.app\.websocket_core\.canonical_imports\s+import.*create_websocket_manager',
            
            # Unified manager imports
            r'from\s+netra_backend\.app\.websocket_core\.unified_manager\s+import.*UnifiedWebSocketManager',
            r'import.*UnifiedWebSocketManager',
            
            # Bridge and service imports
            r'from\s+netra_backend\.app\.services\.agent_websocket_bridge\s+import',
            r'from\s+netra_backend\.app\.services\.websocket',
            
            # Legacy patterns
            r'from\s+netra_backend\.app\.websocket_core\s+import.*get_websocket_manager',
            r'import.*get_websocket_manager',
            
            # Core component imports
            r'from\s+netra_backend\.app\.websocket_core\..*\s+import',
        ]
        
        # Priority classification
        self.priority_paths = {
            "critical": [
                "netra_backend/app/routes/",
                "netra_backend/app/agents/supervisor/",
                "netra_backend/app/services/",
            ],
            "high": [
                "netra_backend/app/websocket_core/",
                "netra_backend/app/core/",
                "tests/mission_critical/",
                "tests/e2e/",
            ],
            "medium": [
                "tests/integration/",
                "netra_backend/tests/",
            ],
            "low": [
                "tests/unit/",
                "tests/stress/",
                "frontend/",
            ],
        }
    
    def classify_priority(self, file_path: str) -> str:
        """Classify the priority of a file based on its path."""
        for priority, paths in self.priority_paths.items():
            if any(path in file_path for path in paths):
                return priority
        return "low"
    
    def classify_category(self, file_path: str) -> str:
        """Classify the category of a file."""
        if "/routes/" in file_path:
            return "routes"
        elif "/agents/" in file_path:
            return "agents"
        elif "/services/" in file_path:
            return "services"
        elif "/websocket_core/" in file_path:
            return "websocket_core"
        elif "/mission_critical/" in file_path:
            return "mission_critical_tests"
        elif "/e2e/" in file_path:
            return "e2e_tests"
        elif "/integration/" in file_path:
            return "integration_tests"
        elif "/unit/" in file_path:
            return "unit_tests"
        elif "/frontend/" in file_path:
            return "frontend"
        else:
            return "other"
    
    def scan_file(self, file_path: Path) -> List[ImportViolation]:
        """Scan a single file for WebSocket Manager import violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Skip comments and empty lines
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # Check each WebSocket pattern
                for pattern in self.websocket_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violation = ImportViolation(
                            file_path=str(file_path),
                            line_number=line_num,
                            import_statement=line_stripped,
                            import_type=self._classify_import_type(line_stripped),
                            priority=self.classify_priority(str(file_path)),
                            category=self.classify_category(str(file_path))
                        )
                        violations.append(violation)
                        break  # Only count one violation per line
                        
        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")
            
        return violations
    
    def _classify_import_type(self, import_statement: str) -> str:
        """Classify the type of import statement."""
        if "WebSocketManager" in import_statement:
            if "from netra_backend.app.websocket_core.websocket_manager" in import_statement:
                return "canonical_manager"
            elif "from netra_backend.app.websocket_core.manager" in import_statement:
                return "legacy_manager"
            elif "UnifiedWebSocketManager" in import_statement:
                return "unified_manager"
            else:
                return "manager_variant"
        elif "create_websocket_manager" in import_statement:
            return "factory_function"
        elif "get_websocket_manager" in import_statement:
            return "legacy_function"
        elif "agent_websocket_bridge" in import_statement:
            return "bridge_service"
        elif "websocket_core" in import_statement:
            return "core_component"
        else:
            return "other_websocket"
    
    def scan_directory(self, directory: Path) -> None:
        """Recursively scan a directory for WebSocket imports."""
        for item in directory.rglob("*.py"):
            if item.is_file():
                # Skip certain directories/files
                skip_patterns = [
                    "__pycache__",
                    ".git",
                    "node_modules",
                    ".backup",
                    ".bak",
                ]
                
                if any(pattern in str(item) for pattern in skip_patterns):
                    continue
                
                violations = self.scan_file(item)
                self.violations.extend(violations)
    
    def generate_statistics(self) -> Dict:
        """Generate comprehensive statistics about import violations."""
        stats = {
            "total_violations": len(self.violations),
            "scan_timestamp": datetime.now().isoformat(),
            "by_priority": Counter(v.priority for v in self.violations),
            "by_category": Counter(v.category for v in self.violations),
            "by_import_type": Counter(v.import_type for v in self.violations),
            "critical_files": [],
            "high_priority_files": [],
            "canonical_compliance": {
                "total_files_scanned": 0,
                "files_with_violations": len(set(v.file_path for v in self.violations)),
                "canonical_usage": sum(1 for v in self.violations if v.import_type == "canonical_manager"),
                "compliance_percentage": 0.0,
            }
        }
        
        # Identify critical and high priority files
        critical_files = [v for v in self.violations if v.priority == "critical"]
        high_priority_files = [v for v in self.violations if v.priority == "high"]
        
        stats["critical_files"] = [
            {"file": v.file_path, "line": v.line_number, "import": v.import_statement}
            for v in critical_files
        ]
        
        stats["high_priority_files"] = [
            {"file": v.file_path, "line": v.line_number, "import": v.import_statement}
            for v in high_priority_files
        ]
        
        # Calculate compliance percentage
        total_websocket_imports = len(self.violations)
        canonical_imports = stats["canonical_compliance"]["canonical_usage"]
        if total_websocket_imports > 0:
            stats["canonical_compliance"]["compliance_percentage"] = (
                canonical_imports / total_websocket_imports * 100
            )
        
        return stats
    
    def generate_remediation_plan(self) -> Dict:
        """Generate systematic remediation plan for Phase 1."""
        plan = {
            "phase_1_scope": "WebSocket Manager Import Consolidation",
            "target_canonical_import": self.canonical_patterns["websocket_manager"],
            "priority_batches": {
                "batch_1_critical": [],
                "batch_2_high": [],
                "batch_3_medium": [],
                "batch_4_low": [],
            },
            "risk_assessment": {
                "golden_path_files": 0,
                "mission_critical_files": 0,
                "breaking_change_risk": "medium",
                "rollback_strategy": "compatibility_shims"
            },
            "compatibility_shims_needed": [],
            "success_metrics": {
                "target_reduction": "reduce from 1,772 to <100 variations",
                "golden_path_protection": "maintain 100% functionality",
                "compliance_target": ">95% canonical imports"
            }
        }
        
        # Group violations by priority for batched remediation
        for violation in self.violations:
            batch_key = f"batch_1_{violation.priority}" if violation.priority == "critical" else \
                       f"batch_2_{violation.priority}" if violation.priority == "high" else \
                       f"batch_3_{violation.priority}" if violation.priority == "medium" else \
                       f"batch_4_{violation.priority}"
            
            file_info = {
                "file": violation.file_path,
                "line": violation.line_number,
                "current_import": violation.import_statement,
                "target_import": self._get_target_import(violation),
                "category": violation.category
            }
            
            if batch_key in plan["priority_batches"]:
                plan["priority_batches"][batch_key].append(file_info)
        
        # Assess risk
        plan["risk_assessment"]["golden_path_files"] = len([
            v for v in self.violations if "routes" in v.category or "agents" in v.category
        ])
        plan["risk_assessment"]["mission_critical_files"] = len([
            v for v in self.violations if "mission_critical" in v.category
        ])
        
        # Identify compatibility shims needed
        unique_imports = set(v.import_statement for v in self.violations)
        plan["compatibility_shims_needed"] = list(unique_imports)
        
        return plan
    
    def _get_target_import(self, violation: ImportViolation) -> str:
        """Get the target canonical import for a violation."""
        if "WebSocketManager" in violation.import_statement:
            return self.canonical_patterns["websocket_manager"]
        elif "create_websocket_manager" in violation.import_statement:
            return self.canonical_patterns["canonical_imports"]
        else:
            return self.canonical_patterns["websocket_manager"]  # Default
    
    def save_results(self, output_file: str) -> None:
        """Save scan results to JSON file."""
        results = {
            "scan_metadata": {
                "root_path": str(self.root_path),
                "scan_timestamp": datetime.now().isoformat(),
                "total_violations": len(self.violations),
                "scanner_version": "1.0.0"
            },
            "violations": [asdict(v) for v in self.violations],
            "statistics": self.generate_statistics(),
            "remediation_plan": self.generate_remediation_plan()
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Scan results saved to: {output_file}")
    
    def print_summary(self) -> None:
        """Print a summary of scan results."""
        stats = self.generate_statistics()
        
        print("\n" + "="*80)
        print("WEBSOCKET MANAGER IMPORT SCANNER - PHASE 1 RESULTS")
        print("="*80)
        print(f"Total WebSocket Import Variations Found: {stats['total_violations']}")
        print(f"Scan Timestamp: {stats['scan_timestamp']}")
        
        print(f"\nPRIORITY BREAKDOWN:")
        for priority, count in stats['by_priority'].items():
            print(f"  {priority.upper():12}: {count:4} violations")
        
        print(f"\nCATEGORY BREAKDOWN:")
        for category, count in stats['by_category'].items():
            print(f"  {category:20}: {count:4} violations")
        
        print(f"\nIMPORT TYPE BREAKDOWN:")
        for import_type, count in stats['by_import_type'].items():
            print(f"  {import_type:20}: {count:4} violations")
        
        print(f"\nCANONICAL COMPLIANCE:")
        compliance = stats['canonical_compliance']
        print(f"  Files with violations: {compliance['files_with_violations']}")
        print(f"  Canonical usage: {compliance['canonical_usage']}")
        print(f"  Compliance percentage: {compliance['compliance_percentage']:.1f}%")
        
        print(f"\nCRITICAL FILES (Golden Path Risk):")
        for i, file_info in enumerate(stats['critical_files'][:10]):  # Show top 10
            print(f"  {i+1:2}. {file_info['file']}:{file_info['line']}")
        
        if len(stats['critical_files']) > 10:
            print(f"  ... and {len(stats['critical_files']) - 10} more critical files")
        
        print("\n" + "="*80)

def main():
    """Main execution function."""
    print("WebSocket Manager Import Scanner - Phase 1")
    print("Scanning for import variations blocking Golden Path...")
    
    # Initialize scanner
    root_path = "/Users/anthony/Desktop/netra-apex"
    scanner = WebSocketImportScanner(root_path)
    
    # Run comprehensive scan
    print(f"Scanning directory: {root_path}")
    scanner.scan_directory(scanner.root_path)
    
    # Generate and display results
    scanner.print_summary()
    
    # Save detailed results
    output_file = f"websocket_import_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    scanner.save_results(output_file)
    
    # Generate actionable recommendations
    plan = scanner.generate_remediation_plan()
    print(f"\nREMEDIATION PLAN:")
    print(f"Target: {plan['target_canonical_import']}")
    print(f"Critical files to fix: {len(plan['priority_batches']['batch_1_critical'])}")
    print(f"High priority files: {len(plan['priority_batches']['batch_2_high'])}")
    print(f"Golden Path risk files: {plan['risk_assessment']['golden_path_files']}")
    
    return scanner

if __name__ == "__main__":
    scanner = main()