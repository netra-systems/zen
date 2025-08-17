import json
from collections import defaultdict

with open('function_violations_top1000.json', 'r') as f:
    data = json.load(f)

# Analyze by module
modules = defaultdict(list)
for v in data['top_1000']:
    parts = v['file'].split('\\')
    if len(parts) > 1:
        module = parts[1]
    else:
        module = 'root'
    modules[module].append(v)

# Print summary
print(f"Total violations in top 1000: {len(data['top_1000'])}")
print(f"Total violations overall: {data['total_violations']}")
print("\nViolations by module:")
for module, violations in sorted(modules.items(), key=lambda x: len(x[1]), reverse=True):
    critical_count = sum(1 for v in violations if v.get('is_critical'))
    avg_lines = sum(v['lines'] for v in violations) / len(violations)
    print(f"  {module}: {len(violations)} violations (critical: {critical_count}, avg lines: {avg_lines:.1f})")
    if len(violations) <= 5:
        for v in violations:
            print(f"    - {v['file'].split('\\')[-1]}::{v['function']} ({v['lines']} lines)")

# Group for agent assignment
print("\nAgent assignment strategy:")
agent_groups = []
for module, violations in sorted(modules.items(), key=lambda x: len(x[1]), reverse=True):
    if len(violations) >= 10:
        agent_groups.append(f"agent_{module}")
        print(f"  agent_{module}: Handle {len(violations)} violations in {module}/")

print(f"\nTotal agents needed: {len(agent_groups)}")