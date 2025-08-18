import json
import os

with open('function_violations.json', 'r') as f:
    violations = json.load(f)

# Categorize by module type
categories = {
    'core': [],
    'agents': [],
    'services': [],
    'routes': [],
    'websocket': [],
    'db': [],
    'llm': [],
    'auth': [],
    'middleware': [],
    'schemas': [],
    'startup': [],
    'mcp': [],
    'clients': [],
    'config': [],
    'security': [],
    'monitoring': [],
    'data': [],
    'alembic': [],
    'netra_mcp': [],
    'other': []
}

for filepath, funcs in violations.items():
    path = filepath.replace('\', '/').replace('./', '')
    
    if path.startswith('core/'):
        categories['core'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('agents/'):
        categories['agents'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('services/'):
        categories['services'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('routes/'):
        categories['routes'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('websocket/'):
        categories['websocket'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('db/'):
        categories['db'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('llm/'):
        categories['llm'].extend([{**f, 'file': filepath} for f in funcs])
    elif 'auth' in path:
        categories['auth'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('middleware/'):
        categories['middleware'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('schemas/'):
        categories['schemas'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('startup'):
        categories['startup'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('mcp_client/'):
        categories['mcp'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('clients/'):
        categories['clients'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('config'):
        categories['config'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('security/'):
        categories['security'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('monitoring/'):
        categories['monitoring'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('data/'):
        categories['data'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('alembic/'):
        categories['alembic'].extend([{**f, 'file': filepath} for f in funcs])
    elif path.startswith('netra_mcp/'):
        categories['netra_mcp'].extend([{**f, 'file': filepath} for f in funcs])
    else:
        categories['other'].extend([{**f, 'file': filepath} for f in funcs])

# Print summary
print('VIOLATIONS BY CATEGORY:')
print('-' * 40)
total = 0
for cat, violations in sorted(categories.items(), key=lambda x: -len(x[1])):
    if violations:
        files = len(set(v['file'] for v in violations))
        print(f'{cat:12} {len(violations):4} violations in {files:3} files')
        total += len(violations)
print(f'\nTOTAL: {total} violations')

# Save categorized violations
for cat, violations in categories.items():
    if violations:
        with open(f'{cat}_violations.json', 'w') as f:
            json.dump(violations, f, indent=2)
