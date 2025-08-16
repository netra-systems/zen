import ast
import os
from pathlib import Path
from typing import List, Dict, Tuple

def count_function_lines(node: ast.FunctionDef) -> int:
    """Count actual lines in a function."""
    if not node.body:
        return 0
    start = node.body[0].lineno
    end = node.body[-1].end_lineno or node.body[-1].lineno
    return end - start + 1

def analyze_file(filepath: Path) -> List[Dict]:
    """Analyze a Python file for function violations."""
    violations = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content, str(filepath))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = count_function_lines(node)
                if lines > 8:
                    violations.append({
                        'file': str(filepath),
                        'function': node.name,
                        'lines': lines,
                        'start_line': node.lineno
                    })
    except Exception:
        pass
    return violations

def scan_codebase() -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Scan entire codebase for violations."""
    severe = []  # >20 lines
    moderate = []  # 9-20 lines
    all_violations = []
    
    # Scan app directory
    for root, _, files in os.walk('app'):
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                filepath = Path(root) / file
                violations = analyze_file(filepath)
                for v in violations:
                    all_violations.append(v)
                    if v['lines'] > 20:
                        severe.append(v)
                    elif v['lines'] > 8:
                        moderate.append(v)
    
    # Scan scripts directory  
    for root, _, files in os.walk('scripts'):
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                violations = analyze_file(filepath)
                for v in violations:
                    all_violations.append(v)
                    if v['lines'] > 20:
                        severe.append(v)
                    elif v['lines'] > 8:
                        moderate.append(v)
                        
    return severe, moderate, all_violations

if __name__ == "__main__":
    print("Scanning codebase for function violations...")
    severe, moderate, all_violations = scan_codebase()
    
    print(f"\nSEVERE VIOLATIONS (>20 lines): {len(severe)}")
    print(f"MODERATE VIOLATIONS (9-20 lines): {len(moderate)}")
    print(f"TOTAL VIOLATIONS (>8 lines): {len(all_violations)}")
    
    # Group by file for efficient agent assignment
    files_with_violations = {}
    for v in all_violations:
        if v['file'] not in files_with_violations:
            files_with_violations[v['file']] = []
        files_with_violations[v['file']].append(v)
    
    print(f"\nFiles with violations: {len(files_with_violations)}")
    
    # Show top severe violations
    print("\nTop 10 Most Severe Violations:")
    for v in sorted(severe, key=lambda x: x['lines'], reverse=True)[:10]:
        print(f"  {v['lines']:3d} lines: {v['function']:30s} in {v['file']}")
    
    # Save results for agent processing
    import json
    with open('violation_analysis.json', 'w') as f:
        json.dump({
            'severe': severe,
            'moderate': moderate, 
            'all': all_violations,
            'by_file': files_with_violations
        }, f, indent=2)
    
    print("\nResults saved to violation_analysis.json")