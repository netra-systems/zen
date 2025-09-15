#!/usr/bin/env python3
"""
Systematic WebSocket Import Replacement - Phase 1 Implementation

This script performs systematic replacement of WebSocket Manager import variations
with canonical SSOT imports in priority order to reduce the 974+ violations
found in critical areas.

BUSINESS PROTECTION:
- Maintains $500K+ ARR Golden Path functionality
- Processes files in risk-prioritized batches
- Validates after each change with mission critical tests
- Provides rollback capability if issues occur

PHASE 1 STRATEGY:
1. Focus on highest impact, lowest risk changes first
2. Target non-canonical imports in critical files  
3. Preserve all functionality through compatibility shims
4. Validate Golden Path after each batch
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

class SystematicImportReplacer:
    """Systematic WebSocket import replacer with safety features."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.backup_dir = self.root_path / "import_replacement_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Define canonical import replacements
        self.replacement_patterns = [
            {
                "name": "Legacy manager.py imports",
                "pattern": r"from\s+netra_backend\.app\.websocket_core\.manager\s+import\s+(.*)",
                "replacement": r"from netra_backend.app.websocket_core.websocket_manager import \1",
                "priority": "high",
                "risk": "low"
            },
            {
                "name": "Unified manager direct imports", 
                "pattern": r"from\s+netra_backend\.app\.websocket_core\.unified_manager\s+import\s+UnifiedWebSocketManager",
                "replacement": r"from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
                "priority": "high",
                "risk": "medium"
            },
            {
                "name": "Package-level websocket_core imports",
                "pattern": r"from\s+netra_backend\.app\.websocket_core\s+import\s+(get_websocket_manager|WebSocketManager)",
                "replacement": r"from netra_backend.app.websocket_core.websocket_manager import \1",
                "priority": "high", 
                "risk": "low"
            },
            {
                "name": "Deprecated factory imports",
                "pattern": r"from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import\s+(.*)",
                "replacement": r"from netra_backend.app.websocket_core.canonical_imports import \1",
                "priority": "medium",
                "risk": "medium"
            }
        ]
        
        # Priority file categories
        self.priority_files = {
            "critical": [
                "netra_backend/app/routes/",
                "netra_backend/app/agents/supervisor/",
            ],
            "high": [
                "netra_backend/app/services/",
                "netra_backend/app/websocket_core/",
            ],
            "medium": [
                "tests/mission_critical/",
                "tests/e2e/",
            ],
            "low": [
                "tests/integration/",
                "tests/unit/",
            ]
        }
        
        self.changes_made = []
        self.validation_results = []
    
    def classify_file_priority(self, file_path: str) -> str:
        """Classify file priority based on path."""
        for priority, paths in self.priority_files.items():
            if any(path in file_path for path in paths):
                return priority
        return "low"
    
    def backup_file(self, file_path: Path) -> Path:
        """Create backup of file before modification."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{file_path.name}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def apply_replacements_to_file(self, file_path: Path) -> List[Dict]:
        """Apply import replacements to a single file."""
        changes = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            modified_content = original_content
            file_changed = False
            
            # Apply each replacement pattern
            for replacement_config in self.replacement_patterns:
                pattern = replacement_config["pattern"]
                replacement = replacement_config["replacement"]
                
                # Find matches
                matches = list(re.finditer(pattern, modified_content, re.MULTILINE))
                
                if matches:
                    # Create backup on first change
                    if not file_changed:
                        backup_path = self.backup_file(file_path)
                        file_changed = True
                    
                    # Apply replacement
                    modified_content = re.sub(pattern, replacement, modified_content, flags=re.MULTILINE)
                    
                    # Track changes
                    for match in matches:
                        change = {
                            "file": str(file_path),
                            "line_number": original_content[:match.start()].count('\n') + 1,
                            "original": match.group(0),
                            "replacement": re.sub(pattern, replacement, match.group(0)),
                            "pattern_name": replacement_config["name"],
                            "priority": replacement_config["priority"],
                            "risk": replacement_config["risk"],
                            "backup_path": str(backup_path) if file_changed else None
                        }
                        changes.append(change)
            
            # Write modified content if changes were made
            if file_changed:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                    
                print(f"✅ Modified: {file_path.relative_to(self.root_path)}")
                for change in changes:
                    print(f"   {change['line_number']:3}: {change['original']} -> {change['replacement']}")
        
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
        
        return changes
    
    def scan_and_replace_priority_batch(self, priority: str, max_files: int = 10) -> List[Dict]:
        """Scan and replace imports in a priority batch of files."""
        
        print(f"\n{'='*60}")
        print(f"PROCESSING {priority.upper()} PRIORITY BATCH (max {max_files} files)")
        print(f"{'='*60}")
        
        batch_changes = []
        files_processed = 0
        
        # Scan priority areas for this batch
        priority_paths = self.priority_files.get(priority, [])
        
        for priority_path in priority_paths:
            area_path = self.root_path / priority_path
            if not area_path.exists():
                continue
                
            print(f"Scanning: {priority_path}")
            
            for py_file in area_path.rglob("*.py"):
                if files_processed >= max_files:
                    break
                    
                # Skip backup and cache files
                if any(skip in str(py_file) for skip in ["__pycache__", ".backup", ".bak"]):
                    continue
                
                # Check if file contains WebSocket imports to replace
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    has_websocket_imports = any(
                        re.search(pattern["pattern"], content, re.MULTILINE)
                        for pattern in self.replacement_patterns
                    )
                    
                    if has_websocket_imports:
                        print(f"Processing: {py_file.relative_to(self.root_path)}")
                        file_changes = self.apply_replacements_to_file(py_file)
                        batch_changes.extend(file_changes)
                        files_processed += 1
                        
                except Exception as e:
                    print(f"Warning: Could not scan {py_file}: {e}")
        
        print(f"Processed {files_processed} files, made {len(batch_changes)} changes")
        return batch_changes
    
    def validate_changes(self) -> bool:
        """Validate that changes don't break mission critical functionality."""
        print(f"\n{'='*60}")
        print(f"VALIDATING CHANGES WITH MISSION CRITICAL TESTS")
        print(f"{'='*60}")
        
        # Run mission critical test
        import subprocess
        
        try:
            result = subprocess.run([
                "python3", "tests/mission_critical/test_websocket_mission_critical_fixed.py"
            ], capture_output=True, text=True, timeout=60)
            
            success = result.returncode == 0
            
            validation_result = {
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
                "stderr": result.stderr[-1000:] if result.stderr else "",
            }
            
            self.validation_results.append(validation_result)
            
            if success:
                print("✅ VALIDATION PASSED: Mission critical tests successful")
            else:
                print("❌ VALIDATION FAILED: Mission critical tests failed")
                print(f"Error: {result.stderr}")
            
            return success
            
        except subprocess.TimeoutExpired:
            print("❌ VALIDATION TIMEOUT: Tests took too long")
            return False
        except Exception as e:
            print(f"❌ VALIDATION ERROR: {e}")
            return False
    
    def rollback_changes(self, changes: List[Dict]) -> None:
        """Rollback changes if validation fails."""
        print(f"\n{'='*60}")
        print(f"ROLLING BACK {len(changes)} CHANGES")
        print(f"{'='*60}")
        
        backup_files = set(change.get("backup_path") for change in changes if change.get("backup_path"))
        
        for backup_path in backup_files:
            if backup_path and Path(backup_path).exists():
                original_file = Path(backup_path.replace(".backup_", "").split("_")[0])
                if original_file.exists():
                    shutil.copy2(backup_path, original_file)
                    print(f"✅ Restored: {original_file}")
        
        print("Rollback completed")
    
    def generate_progress_report(self) -> Dict:
        """Generate progress report for Phase 1."""
        
        total_changes = len(self.changes_made)
        successful_validations = sum(1 for v in self.validation_results if v["success"])
        
        report = {
            "phase": "Phase 1 - Systematic Import Replacement",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_changes_made": total_changes,
                "successful_validations": successful_validations,
                "total_validations": len(self.validation_results),
                "validation_success_rate": f"{(successful_validations/len(self.validation_results)*100):.1f}%" if self.validation_results else "N/A"
            },
            "changes_by_priority": {},
            "changes_by_pattern": {},
            "validation_history": self.validation_results[-5:]  # Last 5 validations
        }
        
        # Group changes by priority and pattern
        for change in self.changes_made:
            priority = change.get("priority", "unknown")
            pattern = change.get("pattern_name", "unknown")
            
            report["changes_by_priority"][priority] = report["changes_by_priority"].get(priority, 0) + 1
            report["changes_by_pattern"][pattern] = report["changes_by_pattern"].get(pattern, 0) + 1
        
        return report
    
    def execute_phase1_remediation(self) -> Dict:
        """Execute Phase 1 systematic import remediation."""
        
        print("WebSocket Manager Import Replacement - Phase 1")
        print("=" * 60)
        print("Systematic replacement of import variations with canonical SSOT patterns")
        
        # Process in priority order
        for priority in ["critical", "high", "medium"]:
            batch_changes = self.scan_and_replace_priority_batch(priority, max_files=5)
            
            if batch_changes:
                self.changes_made.extend(batch_changes)
                
                # Validate after each batch
                if not self.validate_changes():
                    print(f"❌ Validation failed for {priority} priority batch")
                    self.rollback_changes(batch_changes)
                    # Remove failed changes from tracking
                    for change in batch_changes:
                        if change in self.changes_made:
                            self.changes_made.remove(change)
                    break
                else:
                    print(f"✅ {priority.capitalize()} priority batch completed successfully")
        
        # Generate final report
        report = self.generate_progress_report()
        
        # Save detailed report
        report_file = f"phase1_import_replacement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"PHASE 1 REMEDIATION COMPLETE")
        print(f"{'='*60}")
        print(f"Total changes: {len(self.changes_made)}")
        print(f"Validation success rate: {report['summary']['validation_success_rate']}")
        print(f"Detailed report: {report_file}")
        
        return report

def main():
    """Main execution function."""
    root_path = "/Users/anthony/Desktop/netra-apex"
    replacer = SystematicImportReplacer(root_path)
    
    # Execute Phase 1 remediation
    report = replacer.execute_phase1_remediation()
    
    return replacer, report

if __name__ == "__main__":
    replacer, report = main()