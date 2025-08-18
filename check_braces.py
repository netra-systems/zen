with open('deploy-staging-automated.ps1', 'r') as f:
    lines = f.readlines()
    open_braces = 0
    for i, line in enumerate(lines, 1):
        open_braces += line.count('{') - line.count('}')
        if i >= 315 and i <= 390:
            print(f'Line {i}: braces={open_braces}, content={line.strip()[:60]}')