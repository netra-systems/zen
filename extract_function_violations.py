import json
import sys
from collections import defaultdict

# Read the violations JSON
with open('agents_violations.json', 'r') as f:
    data = json.load(f)

# Extract function violations
all_violations = data.get('violations', [])

# Group by file - only function violations in app/agents
violations_by_file = defaultdict(list)

for violation in all_violations:
    if violation.get('violation_type') == 'function_complexity':
        file_path = violation['file_path']
        if 'app\\agents\\' in file_path or 'app/agents/' in file_path:
            violations_by_file[file_path].append({
                'function': violation.get('function_name', 'unknown'),
                'lines': violation.get('actual_value', 0),
                'location': violation.get('location', '')
            })

# Sort by number of violations per file (descending)
sorted_files = sorted(violations_by_file.items(), key=lambda x: len(x[1]), reverse=True)

# Print summary
print(f"Total files with violations: {len(violations_by_file)}")
print(f"Total function violations: {sum(len(v) for v in violations_by_file.values())}")
print("\nFiles with most violations:")

for file_path, violations in sorted_files[:10]:
    print(f"\n{file_path}: {len(violations)} violations")
    for v in violations[:3]:  # Show first 3 violations per file
        print(f"  - {v['function']}: {v['lines']} lines")
    if len(violations) > 3:
        print(f"  ... and {len(violations) - 3} more")

# Save grouped violations
with open('agents_function_violations_grouped.json', 'w') as f:
    json.dump(dict(violations_by_file), f, indent=2)

print("\nGrouped violations saved to: agents_function_violations_grouped.json")