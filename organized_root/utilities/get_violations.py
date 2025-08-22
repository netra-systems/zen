#!/usr/bin/env python
"""Get compliance violations for backend."""
import json
import os
import sys

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.compliance.analyzer import Analyzer
from scripts.compliance.orchestrator import ComplianceOrchestrator


def main():
    # Analyze backend
    orchestrator = ComplianceOrchestrator()
    results = orchestrator.check_directory('app')
    
    violations = {
        'file_violations': [],
        'function_violations': []
    }
    
    # Collect file violations
    for file_path, metrics in results['files'].items():
        if metrics['line_count'] > 300:
            violations['file_violations'].append({
                'file': file_path,
                'lines': metrics['line_count']
            })
    
    # Collect function violations
    for file_path, metrics in results['files'].items():
        for func in metrics.get('functions', []):
            if func['line_count'] > 8:
                violations['function_violations'].append({
                    'file': file_path,
                    'function': func['name'],
                    'lines': func['line_count'],
                    'start': func['start_line'],
                    'end': func['end_line']
                })
    
    # Save to JSON for processing
    with open('violations.json', 'w') as f:
        json.dump(violations, f, indent=2)
    
    print(f"File violations: {len(violations['file_violations'])}")
    print(f"Function violations: {len(violations['function_violations'])}")

if __name__ == '__main__':
    main()