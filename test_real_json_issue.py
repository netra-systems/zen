#!/usr/bin/env python3
"""Test the exact JSON issue from the logs."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.utils import extract_json_from_response, extract_partial_json, fix_common_json_errors

# Simulate the exact error: line 26 column 83 (char 1595)
# Create a JSON with a missing comma at that position
def create_failing_json():
    lines = [
        '```json',
        '{',
        '    "action_plan_summary": "This action plan implements a three-phase strategy to introduce tiered, feature-based model routing and a caching layer. Phase 1 establishes baseline metrics and initial cache configuration. Phase 2 implements intelligent routing based on request characteristics. Phase 3 adds performance monitoring and continuous optimization.",',
        '    "total_estimated_time": "3-4 weeks",',
        '    "required_approvals": ["Technical Lead", "Infrastructure Team", "Security Review"],',
        '    "actions": [',
        '        {',
        '            "action_id": "act_001",',
        '            "action_type": "monitoring",',
        '            "name": "Establish Baseline Metrics",',
        '            "description": "Set up comprehensive monitoring to capture current system performance metrics including latency, throughput, cost per request, and error rates across all models",',
        '            "priority": "critical",',
        '            "dependencies": [],',
        '            "estimated_duration": "2 days",',
        '            "implementation_details": {',
        '                "target_component": "monitoring_system",',
        '                "commands": [',
        '                    "configure_prometheus_exporters",',
        '                    "setup_grafana_dashboards",',
        '                    "enable_distributed_tracing"',
        '                ],',
        '                "config_changes": {',
        '                    "prometheus.yml": "Add model-specific scrape targets",',
        '                    "grafana_dashboards": "Import performance dashboard templates"',
        '                }',
        '            }',  # This is line 26 - missing comma after this brace
        '            "validation_steps": ["Verify metrics collection", "Test dashboard access"]',
        '        },',
        '        {',
        '            "action_id": "act_002",',
        '            "action_type": "cache",',
        '            "name": "Implement Response Cache Layer",',
        '            "description": "Deploy Redis-based caching layer for frequently requested prompts"',
        '        }',
        '    ]',
        '}'
    ]
    
    json_str = '\n'.join(lines)
    
    # Check that char 1595 is around line 26
    chars_counted = 0
    for i, line in enumerate(lines):
        chars_counted += len(line) + 1  # +1 for newline
        if chars_counted >= 1595:
            print(f"Character 1595 is approximately at line {i+1}")
            print(f"Line content: {line}")
            break
    
    return json_str

# Test the failing JSON
response = create_failing_json()
print("Testing JSON with missing comma at line 26...")
print("="*60)

# Try direct parsing to see the error
try:
    json.loads(response.replace('```json', '').replace('```', '').strip())
    print("Direct parsing succeeded (unexpected!)")
except json.JSONDecodeError as e:
    print(f"Direct parsing failed as expected:")
    print(f"  Error: {e.msg}")
    print(f"  Line: {e.lineno}, Column: {e.colno}, Position: {e.pos}")

print("\n" + "="*60)

# Try our extraction function
result = extract_json_from_response(response)
if result:
    print("Full extraction succeeded!")
    if isinstance(result, dict):
        print(f"  Extracted {len(result)} top-level fields")
        print(f"  Actions extracted: {len(result.get('actions', []))}")
else:
    print("Full extraction failed, trying partial...")
    
    # Try partial extraction
    partial = extract_partial_json(response)
    if partial:
        print(f"Partial extraction succeeded with {len(partial)} fields")
        print("Fields extracted:")
        for key in sorted(partial.keys())[:10]:  # Show first 10 fields
            value_preview = str(partial[key])[:50]
            print(f"  - {key}: {value_preview}...")
    else:
        print("Partial extraction also failed")

print("\n" + "="*60)

# Test if the fix_common_json_errors function helps
print("Testing fix_common_json_errors function...")
json_content = response.replace('```json', '').replace('```', '').strip()
fixed = fix_common_json_errors(json_content)

try:
    result = json.loads(fixed)
    print("Fixed JSON parsed successfully!")
    if isinstance(result, dict):
        print(f"  Extracted {len(result)} top-level fields")
        print(f"  Actions extracted: {len(result.get('actions', []))}")
except json.JSONDecodeError as e:
    print(f"Fixed JSON still has errors:")
    print(f"  Error: {e.msg}")
    print(f"  Line: {e.lineno}, Column: {e.colno}")
    
    # Show the problematic area
    lines = fixed.split('\n')
    if e.lineno <= len(lines):
        print(f"\nProblematic line {e.lineno}:")
        print(f"  {lines[e.lineno - 1]}")
        if e.lineno < len(lines):
            print(f"Next line:")
            print(f"  {lines[e.lineno]}")