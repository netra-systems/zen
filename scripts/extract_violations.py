import json
from collections import defaultdict
from pathlib import Path


def extract_violations():
    """Extract and organize all function violations for systematic fixing."""
    
    # Load compliance report
    with open('test_compliance.json', 'r') as f:
        data = json.load(f)
    
    # Extract medium severity function violations (critical)
    medium_funcs = [
        v for v in data['violations'] 
        if v['violation_type'] == 'function_complexity' 
        and v.get('severity') == 'medium'
    ]
    
    # Group by file
    files_to_fix = defaultdict(list)
    for v in medium_funcs:
        files_to_fix[v['file_path']].append({
            'function': v['function_name'],
            'lines': v['actual_value'],
            'line_num': v.get('line_number', 0)
        })
    
    # Categorize files by violation count
    high_violation_files = []  # 10+ violations
    medium_violation_files = []  # 5-9 violations
    low_violation_files = []  # 2-4 violations
    single_violation_files = []  # 1 violation
    
    for file_path, violations in files_to_fix.items():
        violation_count = len(violations)
        file_info = {
            'path': file_path,
            'violations': violations,
            'count': violation_count
        }
        
        if violation_count >= 10:
            high_violation_files.append(file_info)
        elif violation_count >= 5:
            medium_violation_files.append(file_info)
        elif violation_count >= 2:
            low_violation_files.append(file_info)
        else:
            single_violation_files.append(file_info)
    
    # Sort each category by violation count
    high_violation_files.sort(key=lambda x: x['count'], reverse=True)
    medium_violation_files.sort(key=lambda x: x['count'], reverse=True)
    low_violation_files.sort(key=lambda x: x['count'], reverse=True)
    
    return {
        'high': high_violation_files,
        'medium': medium_violation_files,
        'low': low_violation_files,
        'single': single_violation_files,
        'total_files': len(files_to_fix),
        'total_violations': len(medium_funcs)
    }

if __name__ == '__main__':
    violations = extract_violations()
    
    print(f"Total files to fix: {violations['total_files']}")
    print(f"Total violations: {violations['total_violations']}")
    print(f"\nHigh violation files (10+): {len(violations['high'])}")
    print(f"Medium violation files (5-9): {len(violations['medium'])}")
    print(f"Low violation files (2-4): {len(violations['low'])}")
    print(f"Single violation files: {len(violations['single'])}")
    
    # Save organized violations
    with open('organized_violations.json', 'w') as f:
        json.dump(violations, f, indent=2)
    
    print("\nViolations saved to organized_violations.json")