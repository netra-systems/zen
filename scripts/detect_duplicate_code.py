#!/usr/bin/env python3
"""
Duplicate Code Detection Script
Prevents regression of duplicate code patterns identified in WebSocket consolidation

Usage:
    python scripts/detect_duplicate_code.py [--threshold 0.8] [--report-only]
    
This script detects:
- Duplicate class names across files
- Similar function implementations
- Multiple wrappers for same functionality
- Parallel implementations of same feature
"""

import ast
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple
import difflib
import json
import argparse


class DuplicateCodeDetector:
    """Detects duplicate code patterns in the codebase."""
    
    def __init__(self, root_path: str = ".", threshold: float = 0.8):
        self.root_path = Path(root_path)
        self.threshold = threshold
        self.classes = defaultdict(list)
        self.functions = defaultdict(list)
        self.managers = defaultdict(list)
        self.services = defaultdict(list)
        self.handlers = defaultdict(list)
        self.issues = []
        
    def scan_codebase(self) -> None:
        """Scan all Python files in the codebase."""
        python_files = list(self.root_path.rglob("*.py"))
        
        # Exclude virtual environments and cache
        python_files = [
            f for f in python_files 
            if not any(p in str(f) for p in ['.venv', '__pycache__', 'migrations', 'site-packages'])
        ]
        
        print(f"Scanning {len(python_files)} Python files...")
        
        for file_path in python_files:
            self._analyze_file(file_path)
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for duplicate patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._record_class(node.name, file_path)
                elif isinstance(node, ast.FunctionDef):
                    self._record_function(node.name, file_path, node)
                    
        except Exception as e:
            # Skip files that can't be parsed
            pass
    
    def _record_class(self, class_name: str, file_path: Path) -> None:
        """Record class definition and categorize by type."""
        self.classes[class_name].append(str(file_path))
        
        # Categorize by suffix patterns
        if class_name.endswith('Manager'):
            self.managers[class_name].append(str(file_path))
        elif class_name.endswith('Service'):
            self.services[class_name].append(str(file_path))
        elif class_name.endswith('Handler'):
            self.handlers[class_name].append(str(file_path))
    
    def _record_function(self, func_name: str, file_path: Path, node: ast.FunctionDef) -> None:
        """Record function definition with basic signature."""
        params = [arg.arg for arg in node.args.args]
        signature = f"{func_name}({', '.join(params)})"
        self.functions[signature].append(str(file_path))
    
    def detect_duplicates(self) -> List[Dict]:
        """Detect various types of duplicates."""
        issues = []
        
        # Detect duplicate classes
        for class_name, files in self.classes.items():
            if len(files) > 1:
                issues.append({
                    'type': 'duplicate_class',
                    'severity': 'critical',
                    'name': class_name,
                    'files': files,
                    'count': len(files),
                    'message': f"Class '{class_name}' defined in {len(files)} files"
                })
        
        # Detect WebSocket pattern duplicates (specific to our case)
        self._detect_websocket_duplicates(issues)
        
        # Detect manager/service/handler duplicates
        self._detect_component_duplicates(issues)
        
        # Detect wrapper patterns
        self._detect_wrapper_patterns(issues)
        
        return issues
    
    def _detect_websocket_duplicates(self, issues: List[Dict]) -> None:
        """Detect WebSocket-specific duplicate patterns."""
        websocket_patterns = [
            ('heartbeat', r'heartbeat|ping.*pong|keep.*alive'),
            ('lifecycle', r'lifecycle|connection.*manager|conn.*pool'),
            ('message_queue', r'message.*queue|queue.*message'),
            ('event_handler', r'event.*handler|handle.*event'),
        ]
        
        for feature, pattern in websocket_patterns:
            matching_files = []
            for class_name, files in self.classes.items():
                if re.search(pattern, class_name, re.IGNORECASE):
                    matching_files.extend(files)
            
            if len(set(matching_files)) > 3:  # More than 3 unique files
                issues.append({
                    'type': 'feature_duplication',
                    'severity': 'high',
                    'feature': feature,
                    'files': list(set(matching_files)),
                    'count': len(set(matching_files)),
                    'message': f"Feature '{feature}' has {len(set(matching_files))} implementations"
                })
    
    def _detect_component_duplicates(self, issues: List[Dict]) -> None:
        """Detect duplicate managers, services, and handlers."""
        components = [
            ('Manager', self.managers),
            ('Service', self.services),
            ('Handler', self.handlers),
        ]
        
        for component_type, component_dict in components:
            # Look for similar names (e.g., WebSocketManager vs WSManager)
            names = list(component_dict.keys())
            for i, name1 in enumerate(names):
                for name2 in names[i+1:]:
                    similarity = difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
                    if similarity > self.threshold and name1 != name2:
                        files1 = component_dict[name1]
                        files2 = component_dict[name2]
                        issues.append({
                            'type': 'similar_components',
                            'severity': 'medium',
                            'component_type': component_type,
                            'names': [name1, name2],
                            'files': files1 + files2,
                            'similarity': round(similarity, 2),
                            'message': f"Similar {component_type}s: '{name1}' and '{name2}' (similarity: {similarity:.0%})"
                        })
    
    def _detect_wrapper_patterns(self, issues: List[Dict]) -> None:
        """Detect wrapper/delegation patterns that might indicate duplication."""
        # Look for files with similar imports that might be wrappers
        import_patterns = defaultdict(set)
        
        for file_path in self.root_path.rglob("*.py"):
            if any(p in str(file_path) for p in ['.venv', '__pycache__']):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find imports that look like internal delegations
                imports = re.findall(r'from\s+(\S+)\s+import\s+(\w+Manager|\w+Service|\w+Handler)', content)
                for module, imported in imports:
                    if 'netra_backend' in module:
                        import_patterns[imported].add(str(file_path))
            except:
                pass
        
        # Flag when same class is imported in many places (potential wrappers)
        for imported_class, files in import_patterns.items():
            if len(files) > 5:  # Imported in more than 5 files
                issues.append({
                    'type': 'potential_wrapper_pattern',
                    'severity': 'low',
                    'class': imported_class,
                    'import_count': len(files),
                    'sample_files': list(files)[:5],
                    'message': f"Class '{imported_class}' imported in {len(files)} files - check for wrapper duplication"
                })
    
    def generate_report(self, issues: List[Dict]) -> str:
        """Generate a formatted report of duplicate code issues."""
        if not issues:
            return "✅ No duplicate code patterns detected!"
        
        report = []
        report.append("=" * 80)
        report.append("DUPLICATE CODE DETECTION REPORT")
        report.append("=" * 80)
        report.append(f"\nTotal issues found: {len(issues)}\n")
        
        # Group by severity
        by_severity = defaultdict(list)
        for issue in issues:
            by_severity[issue['severity']].append(issue)
        
        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                report.append(f"\n{severity.upper()} SEVERITY ISSUES ({len(by_severity[severity])})")
                report.append("-" * 40)
                
                for issue in by_severity[severity]:
                    report.append(f"\n❌ {issue['message']}")
                    report.append(f"   Type: {issue['type']}")
                    
                    if 'files' in issue and len(issue['files']) <= 10:
                        for file in issue['files']:
                            report.append(f"   - {file}")
                    elif 'files' in issue:
                        report.append(f"   - {len(issue['files'])} files affected")
                    
                    if 'similarity' in issue:
                        report.append(f"   Similarity: {issue['similarity']:.0%}")
        
        report.append("\n" + "=" * 80)
        report.append("RECOMMENDATIONS")
        report.append("=" * 80)
        
        if any(i['severity'] == 'critical' for i in issues):
            report.append("\n⚠️  CRITICAL: Immediate consolidation required!")
            report.append("   Run: python scripts/fix_websocket_imports.py")
        
        if any(i['type'] == 'feature_duplication' for i in issues):
            report.append("\n⚠️  Multiple implementations of same features detected.")
            report.append("   Review SPEC/learnings/websocket_consolidation.xml for consolidation strategy.")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)
    
    def save_json_report(self, issues: List[Dict], output_file: str = "duplicate_code_report.json") -> None:
        """Save detailed report as JSON for further analysis."""
        report = {
            'timestamp': str(Path.cwd()),
            'threshold': self.threshold,
            'total_issues': len(issues),
            'by_severity': {
                'critical': len([i for i in issues if i['severity'] == 'critical']),
                'high': len([i for i in issues if i['severity'] == 'high']),
                'medium': len([i for i in issues if i['severity'] == 'medium']),
                'low': len([i for i in issues if i['severity'] == 'low']),
            },
            'issues': issues
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Detailed report saved to: {output_file}")


def main():
    """Main entry point for duplicate detection."""
    parser = argparse.ArgumentParser(description='Detect duplicate code patterns')
    parser.add_argument('--threshold', type=float, default=0.8,
                       help='Similarity threshold for detection (0.0-1.0)')
    parser.add_argument('--report-only', action='store_true',
                       help='Only generate report without failing')
    parser.add_argument('--json', action='store_true',
                       help='Save detailed JSON report')
    parser.add_argument('--path', default='.',
                       help='Root path to scan')
    
    args = parser.parse_args()
    
    detector = DuplicateCodeDetector(args.path, args.threshold)
    
    print("🔍 Scanning for duplicate code patterns...")
    detector.scan_codebase()
    
    print("🔎 Analyzing for duplicates...")
    issues = detector.detect_duplicates()
    
    # Generate and print report
    report = detector.generate_report(issues)
    print(report)
    
    # Save JSON report if requested
    if args.json:
        detector.save_json_report(issues)
    
    # Exit with error if critical issues found (unless report-only mode)
    if not args.report_only:
        critical_count = len([i for i in issues if i['severity'] == 'critical'])
        if critical_count > 0:
            print(f"\n❌ Found {critical_count} critical duplicate code issues!")
            print("Fix these issues before committing.")
            sys.exit(1)
        elif len(issues) > 10:
            print(f"\n⚠️  Found {len(issues)} duplicate code issues.")
            print("Consider consolidation to improve maintainability.")
            sys.exit(1)
    
    print("\n✅ Duplicate detection complete.")
    return 0


if __name__ == "__main__":
    main()