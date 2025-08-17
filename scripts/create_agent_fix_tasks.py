#!/usr/bin/env python3
"""Create agent tasks for fixing function violations"""
import json
from pathlib import Path

def create_agent_tasks():
    # Load violations data
    with open('function_violations_top1000.json', 'r') as f:
        data = json.load(f)
    
    files_to_fix = data['files_to_fix']
    file_violations = data['file_violations']
    
    # Group files by directory for logical batching
    file_groups = {}
    for file_path in files_to_fix:
        parts = file_path.split('\\')
        if len(parts) >= 2:
            key = '\\'.join(parts[:2])  # Group by app\module
        else:
            key = parts[0]
        if key not in file_groups:
            file_groups[key] = []
        file_groups[key].append(file_path)
    
    # Create batches (2-3 files per agent)
    agent_tasks = []
    batch_size = 2
    
    for group_key, files in file_groups.items():
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            task = {
                'id': len(agent_tasks) + 1,
                'files': batch,
                'total_violations': sum(len(file_violations[f]) for f in batch),
                'priority': 'critical' if any('agents' in f or 'llm' in f or 'core' in f for f in batch) else 'normal'
            }
            agent_tasks.append(task)
            if len(agent_tasks) >= 100:  # Limit to 100 agents
                break
        if len(agent_tasks) >= 100:
            break
    
    # Save agent tasks
    with open('agent_fix_tasks.json', 'w') as f:
        json.dump(agent_tasks, f, indent=2)
    
    print(f"Created {len(agent_tasks)} agent tasks")
    print(f"Critical tasks: {sum(1 for t in agent_tasks if t['priority'] == 'critical')}")
    
    # Show first 5 tasks
    print("\nFirst 5 agent tasks:")
    for task in agent_tasks[:5]:
        print(f"Task {task['id']}: {task['total_violations']} violations in {len(task['files'])} files")
        for f in task['files']:
            print(f"  - {f}")

if __name__ == "__main__":
    create_agent_tasks()