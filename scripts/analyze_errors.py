import json

with open('test_reports/test_report_20250824_090437.json') as f:
    data = json.load(f)

# Find syntax errors in unit tests
unit_output = data['categories']['unit']['output']
lines = unit_output.split('\n')

print("=== Syntax Errors Found ===")
for i, line in enumerate(lines):
    if 'SyntaxError' in line:
        # Print context around syntax error
        start = max(0, i-2)
        end = min(len(lines), i+3)
        for j in range(start, end):
            print(lines[j])
        print("-" * 40)

print("\n=== Indentation Errors Found ===")
for i, line in enumerate(lines):
    if 'IndentationError' in line:
        # Print context around indentation error
        start = max(0, i-2)
        end = min(len(lines), i+3)
        for j in range(start, end):
            print(lines[j])
        print("-" * 40)