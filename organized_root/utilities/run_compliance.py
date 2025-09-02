from shared.isolated_environment import get_env
#!/usr/bin/env python
"""Run compliance checker and capture output."""
import os
import sys

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Import and run the compliance checker
from scripts.compliance.analyzer import Analyzer
from scripts.compliance.collector import ViolationCollector
from scripts.compliance.reporter import ComplianceReporter


def main():
    analyzer = Analyzer()
    results = analyzer.analyze_codebase('app')
    
    # Collect violations by category
    collector = ViolationCollector()
    violations = collector.collect_violations(results)
    
    print("\nARCHITECTURE COMPLIANCE REPORT")
    print("=" * 80)
    
    # File violations
    file_violations = violations.get('file_violations', [])
    if file_violations:
        print(f"\nFILE SIZE VIOLATIONS (>300 lines): {len(file_violations)} files")
        print("-" * 40)
        for v in sorted(file_violations, key=lambda x: x['lines'], reverse=True)[:10]:
            print(f"  {v['lines']:4d} lines: {v['file']}")
    
    # Function violations  
    func_violations = violations.get('function_violations', [])
    if func_violations:
        print(f"\nFUNCTION SIZE VIOLATIONS (>8 lines): {len(func_violations)} functions")
        print("-" * 40)
        for v in sorted(func_violations, key=lambda x: x['lines'], reverse=True)[:10]:
            print(f"  {v['lines']:4d} lines: {v['function']} in {v['file']}")
    
    print("\nSUMMARY:")
    print(f"  Total file violations: {len(file_violations)}")
    print(f"  Total function violations: {len(func_violations)}")

if __name__ == '__main__':
    main()
