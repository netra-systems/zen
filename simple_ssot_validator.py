#!/usr/bin/env python3
"""
Simple SSOT WebSocket Factory Violation Validator

Scans for deprecated factory usage and canonical patterns.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

def scan_file_for_patterns(file_path: Path, patterns: List[str]) -> List[Tuple[int, str]]:
    """Scan file for matching patterns and return line numbers and matches."""
    matches = []
    if not file_path.exists() or not file_path.is_file():
        return matches
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        matches.append((line_num, line.strip()))
    except Exception as e:
        # Skip files that can't be read
        pass
        
    return matches

def scan_directory_for_patterns(directory: Path, patterns: List[str]) -> Dict[str, List[Tuple[int, str]]]:
    """Recursively scan directory for pattern matches."""
    matches = {}
    
    if not directory.exists():
        return matches
        
    for file_path in directory.rglob('*.py'):
        if file_path.is_file():
            file_matches = scan_file_for_patterns(file_path, patterns)
            if file_matches:
                relative_path = str(file_path.relative_to(directory.parent))
                matches[relative_path] = file_matches
                
    return matches

def main():
    """Main validation logic."""
    print("SSOT WebSocket Factory Deprecation Violation Validator")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    netra_backend_root = project_root / "netra_backend"
    
    # Deprecated factory patterns (SHOULD BE ELIMINATED)
    deprecated_patterns = [
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import\s+get_websocket_manager_factory",
        r"get_websocket_manager_factory\s*\(\s*\)",
        r"import.*get_websocket_manager_factory",
        r"websocket_manager_factory\.get_websocket_manager_factory",
    ]
    
    # Canonical SSOT patterns (SHOULD BE USED)
    canonical_patterns = [
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+WebSocketManager",
        r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+get_websocket_manager",
        r"WebSocketManager\s*\(",
        r"get_websocket_manager\s*\(\s*\)",
    ]
    
    print("SCANNING FOR VIOLATIONS...")
    
    # Scan for deprecated patterns
    print("\nSCANNING FOR DEPRECATED FACTORY PATTERNS:")
    deprecated_violations = scan_directory_for_patterns(project_root, deprecated_patterns)
    
    # Scan for canonical patterns
    print("SCANNING FOR CANONICAL SSOT PATTERNS:")
    canonical_usage = scan_directory_for_patterns(netra_backend_root, canonical_patterns)
    
    # Calculate metrics
    total_violation_files = len(deprecated_violations)
    total_violation_instances = sum(len(matches) for matches in deprecated_violations.values())
    total_canonical_files = len(canonical_usage)
    total_canonical_instances = sum(len(matches) for matches in canonical_usage.values())
    
    print(f"\nSSOT COMPLIANCE METRICS:")
    print(f"-" * 40)
    print(f"Deprecated Factory Usage:")
    print(f"   Files with violations: {total_violation_files}")
    print(f"   Total violation instances: {total_violation_instances}")
    
    print(f"\nCanonical SSOT Usage:")
    print(f"   Files with canonical patterns: {total_canonical_files}")
    print(f"   Total canonical instances: {total_canonical_instances}")
    
    # Calculate SSOT compliance ratio
    total_usage = total_violation_instances + total_canonical_instances
    if total_usage > 0:
        ssot_compliance_ratio = (total_canonical_instances / total_usage) * 100
        print(f"\nSSOT COMPLIANCE RATIO: {ssot_compliance_ratio:.1f}%")
    else:
        ssot_compliance_ratio = 0.0
        print(f"\nSSOT COMPLIANCE RATIO: 0.0% (No WebSocket usage detected)")
    
    print(f"\nDETAILED VIOLATIONS:")
    print(f"-" * 40)
    
    if deprecated_violations:
        print("DEPRECATED FACTORY VIOLATIONS FOUND:")
        for file_path, matches in deprecated_violations.items():
            print(f"\nFile: {file_path}:")
            for line_num, match_text in matches[:3]:  # Show first 3 matches per file
                print(f"   Line {line_num}: {match_text}")
            if len(matches) > 3:
                print(f"   ... and {len(matches) - 3} more violations")
    else:
        print("NO DEPRECATED FACTORY VIOLATIONS DETECTED!")
    
    print(f"\nCANONICAL USAGE EXAMPLES:")
    print(f"-" * 40)
    
    if canonical_usage:
        print("CANONICAL SSOT PATTERNS FOUND:")
        # Show examples from first few files
        shown_files = 0
        for file_path, matches in canonical_usage.items():
            if shown_files >= 3:  # Show first 3 files
                break
            print(f"\nFile: {file_path}:")
            for line_num, match_text in matches[:2]:  # Show first 2 matches per file
                print(f"   Line {line_num}: {match_text}")
            shown_files += 1
        
        if len(canonical_usage) > 3:
            print(f"\n   ... and {len(canonical_usage) - 3} more files with canonical usage")
    else:
        print("WARNING: NO CANONICAL WEBSOCKET USAGE DETECTED")
    
    # Phase 1 Success Assessment
    print(f"\nPHASE 1 REMEDIATION ASSESSMENT:")
    print(f"-" * 40)
    
    if total_violation_instances == 0:
        print("SUCCESS: Phase 1 COMPLETE - Zero deprecated factory violations!")
        print("WebSocket factory deprecation violations eliminated")
        print("Ready for Phase 2 expansion")
    elif total_violation_instances < 10:
        print(f"PROGRESS: Phase 1 PARTIAL - {total_violation_instances} violations remain")
        print("Continue Phase 1 remediation to eliminate remaining violations")
    else:
        print(f"VIOLATIONS: Phase 1 IN PROGRESS - {total_violation_instances} violations detected")
        print("Phase 1 remediation needed to eliminate deprecated factory usage")
    
    # Business Impact Assessment
    print(f"\nBUSINESS IMPACT VALIDATION:")
    print(f"-" * 40)
    
    if ssot_compliance_ratio >= 95.0:
        print("GOLDEN PATH PROTECTED: High SSOT compliance protects $500K+ ARR")
        print("WebSocket architecture stability maintained")
    elif ssot_compliance_ratio >= 75.0:
        print("GOLDEN PATH STABLE: Moderate SSOT compliance, continue improvement")
        print("Continue remediation to ensure full business value protection")
    else:
        print("GOLDEN PATH RISK: Low SSOT compliance may impact revenue")
        print("URGENT: Complete SSOT remediation to protect business functionality")
    
    return total_violation_instances == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)