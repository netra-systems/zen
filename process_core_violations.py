import json
import os
from collections import defaultdict

# Read the violations
with open('core_violations.json', 'r') as f:
    data = json.load(f)

# Group function violations by file
function_violations = defaultdict(list)
for violation in data['violations']:
    if violation['violation_type'] == 'function_complexity':
        file_path = violation['file_path'].replace('\\', '/')
        # Only process files in app/core
        if file_path.startswith('app/core'):
            function_violations[file_path].append({
                'function': violation['function_name'],
                'lines': violation['actual_value'],
                'line_number': violation['line_number']
            })

# Print summary
print(f'Total files with function violations in app/core: {len(function_violations)}')
print(f'Total function violations: {sum(len(v) for v in function_violations.values())}')
print()

# Show files with most violations
print('Files with most violations:')
for file_path, violations in sorted(function_violations.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
    print(f'  {file_path}: {len(violations)} violations')
    
# Create file groups for parallel processing
file_groups = []
files_list = sorted(function_violations.items())
for i in range(0, len(files_list), 5):
    group = files_list[i:i+5]
    file_groups.append(group)

print(f'\nCreated {len(file_groups)} groups for parallel processing')

# Export groups for processing
with open('violation_groups.json', 'w') as f:
    groups_data = []
    for i, group in enumerate(file_groups):
        group_data = {
            'group_id': i + 1,
            'files': []
        }
        for file_path, violations in group:
            group_data['files'].append({
                'path': file_path,
                'violations': violations
            })
        groups_data.append(group_data)
    json.dump(groups_data, f, indent=2)

print(f'Exported {len(file_groups)} groups to violation_groups.json')