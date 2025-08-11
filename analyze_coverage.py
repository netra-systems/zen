import json

# Load coverage data
with open('reports/coverage/coverage.json') as f:
    data = json.load(f)

# Extract file coverage
files = []
for filename, filedata in data['files'].items():
    summary = filedata.get('summary', {})
    if summary.get('num_statements', 0) > 0:
        files.append({
            'file': filename.replace('\\', '/'),
            'percent': summary.get('percent_covered', 0),
            'missing': summary.get('missing_lines', 0),
            'total': summary.get('num_statements', 0),
            'covered': summary.get('covered_lines', 0)
        })

# Sort by missing lines (most missing first)
files.sort(key=lambda x: x['missing'], reverse=True)

print('Top 20 Files with Most Missing Coverage:')
print('=' * 80)
for i, f in enumerate(files[:20], 1):
    print(f"{i:2}. {f['file']:<60} Missing: {f['missing']:4} ({f['percent']:5.1f}% covered)")

print('\n\nTop 20 Files by Lowest Coverage Percentage (min 50 lines):')
print('=' * 80)
# Filter files with at least 50 lines and sort by percentage
significant_files = [f for f in files if f['total'] >= 50]
significant_files.sort(key=lambda x: x['percent'])
for i, f in enumerate(significant_files[:20], 1):
    print(f"{i:2}. {f['file']:<60} {f['percent']:5.1f}% ({f['covered']}/{f['total']} lines)")