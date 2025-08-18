"""Analyze function complexity violations from agents directory."""
import json
from collections import defaultdict
from typing import Dict, List, Tuple

def load_violations(filepath: str) -> Dict:
    """Load violations JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def get_function_violations(data: Dict) -> List[Dict]:
    """Extract function complexity violations."""
    violations = []
    for v in data['violations']:
        if v['violation_type'] == 'function_complexity' and v['severity'] != 'low':
            violations.append(v)
    return violations

def group_by_file(violations: List[Dict]) -> Dict[str, List[Dict]]:
    """Group violations by file path."""
    grouped = defaultdict(list)
    for v in violations:
        grouped[v['file_path']].append(v)
    return dict(grouped)

def analyze_violations():
    """Main analysis function."""
    data = load_violations('agents_violations.json')
    
    # Get function violations
    func_violations = get_function_violations(data)
    print(f"Total function violations to fix: {len(func_violations)}")
    
    # Group by file
    by_file = group_by_file(func_violations)
    print(f"Files with violations: {len(by_file)}")
    
    # Sort files by number of violations
    sorted_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)
    
    print("\nTop 10 files with most violations:")
    for filepath, violations in sorted_files[:10]:
        print(f"  {filepath}: {len(violations)} violations")
        
    # Create sets of files for batch processing
    batch_size = 5
    batches = []
    for i in range(0, len(sorted_files), batch_size):
        batch = sorted_files[i:i+batch_size]
        batches.append(batch)
    
    print(f"\nCreated {len(batches)} batches for processing")
    
    # Save organized data
    output = {
        'total_violations': len(func_violations),
        'files_count': len(by_file),
        'batches': []
    }
    
    for i, batch in enumerate(batches):
        batch_data = {
            'batch_number': i + 1,
            'files': []
        }
        for filepath, violations in batch:
            file_data = {
                'filepath': filepath,
                'violations_count': len(violations),
                'violations': violations
            }
            batch_data['files'].append(file_data)
        output['batches'].append(batch_data)
    
    with open('agents_function_violations.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\nSaved organized violations to agents_function_violations.json")
    return output

if __name__ == "__main__":
    analyze_violations()