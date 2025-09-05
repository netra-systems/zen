#!/usr/bin/env python3
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_deployment_script_changes():
    print('Testing deployment script modifications...')
    
    script_path = project_root / 'scripts' / 'deploy_to_gcp.py'
    
    if not script_path.exists():
        print(f'   Deployment script not found: {script_path}')
        return False
    
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for our new methods
    checks = [
        ('retrieve_secret_value method', 'def retrieve_secret_value'),
        ('get_critical_env_vars_from_gsm method', 'def get_critical_env_vars_from_gsm'),
        ('GSM env var retrieval', 'gsm_env_vars = self.get_critical_env_vars_from_gsm'),
    ]
    
    all_present = True
    for check_name, search_string in checks:
        if search_string in content:
            print(f'   OK: {check_name} found')
        else:
            print(f'   FAIL: {check_name} missing')
            all_present = False
    
    return all_present

if __name__ == '__main__':
    print('STAGING CONFIGURATION FIX VALIDATION')
    print('=' * 40)
    if test_deployment_script_changes():
        print('\nSUCCESS: All deployment script changes are in place!')
        print('\nNext steps:')
        print('1. Run: python scripts/setup_staging_secrets.py --project netra-staging')
        print('2. Deploy: python scripts/deploy_to_gcp.py --project netra-staging --build-local')
    else:
        print('\nFAILED: Some changes are missing')

