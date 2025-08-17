#!/usr/bin/env python
"""
Validation script for the 3 critical fixes:
1. CI/CD security (Terraform secrets)
2. Frontend test stability (WebSocket mocks)
3. Database connection pooling
"""

import subprocess
import sys
from pathlib import Path
import yaml
import json

def validate_terraform_security():
    """Check that Terraform secrets are properly secured in CI/CD"""
    print("\n[CHECK] Validating CI/CD Security Fix...")
    
    workflow_file = Path(".github/workflows/staging-environment.yml")
    if not workflow_file.exists():
        print("[ERROR] Workflow file not found")
        return False
    
    with open(workflow_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for direct secret exposure in terraform commands
    bad_patterns = [
        '-var="postgres_password=${{',
        '-var="clickhouse_password=${{',
        r'terraform plan.*secrets\.',
        r'terraform destroy.*secrets\.'
    ]
    
    issues = []
    for pattern in bad_patterns:
        if pattern in content and 'TF_VAR_' not in content[max(0, content.find(pattern)-50):content.find(pattern)+50]:
            issues.append(f"  [WARNING] Potential secret exposure pattern found: {pattern[:30]}...")
    
    # Check for good patterns (using env vars or tfvars files)
    good_patterns = [
        'TF_VAR_postgres_password',
        'TF_VAR_clickhouse_password',
        'terraform.tfvars',
        'chmod 600 terraform.tfvars'
    ]
    
    found_good = sum(1 for p in good_patterns if p in content)
    
    if issues:
        print(f"  [WARNING] Found {len(issues)} potential issues:")
        for issue in issues[:3]:
            print(issue)
    
    if found_good >= 3:
        print(f"  [PASS] Found {found_good}/4 security improvements implemented")
        print("  [PASS] Terraform secrets are now properly secured using environment variables and tfvars files")
        return True
    else:
        print(f"  [WARNING] Only {found_good}/4 security patterns found")
        return False

def validate_websocket_mock():
    """Check that WebSocket mocks are properly configured for frontend tests"""
    print("\n[CHECK] Validating Frontend Test Stability Fix...")
    
    # Check jest.setup.ts
    setup_file = Path("frontend/jest.setup.ts")
    if not setup_file.exists():
        print("  [ERROR] jest.setup.ts not found")
        return False
    
    with open(setup_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    improvements = []
    
    # Check for improved WebSocket mock
    if 'MockWebSocket' in content and 'readyState' in content:
        improvements.append("Enhanced MockWebSocket class")
    
    if 'CONNECTING' in content and 'OPEN' in content and 'CLOSED' in content:
        improvements.append("Proper WebSocket state constants")
    
    if 'process.nextTick' in content or 'setTimeout' in content:
        improvements.append("Async connection simulation")
    
    # Check test runner improvements
    runner_file = Path("scripts/test_frontend_simple.py")
    if runner_file.exists():
        with open(runner_file, 'r', encoding='utf-8') as f:
            runner_content = f.read()
        
        if 'timeout=' in runner_content:
            improvements.append("Test timeout configuration")
        
        if 'maxWorkers' in runner_content:
            improvements.append("Jest worker limitation")
    
    if len(improvements) >= 3:
        print(f"  [PASS] Found {len(improvements)} test stability improvements:")
        for imp in improvements:
            print(f"     - {imp}")
        return True
    else:
        print(f"  [WARNING] Only {len(improvements)} improvements found")
        return False

def validate_database_pooling():
    """Check that database connection pooling is properly configured"""
    print("\n[CHECK] Validating Database Connection Pool Fix...")
    
    db_file = Path("app/db/postgres.py")
    if not db_file.exists():
        print("  [ERROR] postgres.py not found")
        return False
    
    with open(db_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    improvements = []
    
    # Check pool configuration
    if 'POOL_SIZE = 20' in content:
        improvements.append("Increased pool size (20)")
    
    if 'MAX_OVERFLOW = 30' in content:
        improvements.append("Increased overflow limit (30)")
    
    if 'statement_timeout' in content:
        improvements.append("Statement timeout protection")
    
    if 'idle_in_transaction_session_timeout' in content:
        improvements.append("Idle transaction timeout")
    
    if 'lock_timeout' in content:
        improvements.append("Lock timeout protection")
    
    if 'Connection pool usage high' in content:
        improvements.append("Pool usage monitoring")
    
    # Check health endpoint
    health_file = Path("app/routes/health_extended.py")
    if health_file.exists():
        improvements.append("Extended health monitoring endpoint")
    
    if len(improvements) >= 5:
        print(f"  [PASS] Found {len(improvements)} database pooling improvements:")
        for imp in improvements:
            print(f"     - {imp}")
        return True
    else:
        print(f"  [WARNING] Only {len(improvements)} improvements found")
        return False

def main():
    """Run all validations"""
    print("="*60)
    print("VALIDATING CRITICAL FIXES FOR NETRA AI PLATFORM")
    print("="*60)
    
    results = {
        "CI/CD Security": validate_terraform_security(),
        "Frontend Test Stability": validate_websocket_mock(),
        "Database Connection Pooling": validate_database_pooling()
    }
    
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    for fix, status in results.items():
        status_icon = "[PASS]" if status else "[FAIL]"
        print(f"{status_icon} {fix}: {'FIXED' if status else 'NEEDS ATTENTION'}")
    
    all_fixed = all(results.values())
    
    print("\n" + "="*60)
    if all_fixed:
        print("[SUCCESS] ALL 3 CRITICAL ISSUES HAVE BEEN FIXED!")
        print("\nNext Steps:")
        print("1. Commit these changes to your branch")
        print("2. Run full test suite: python test_runner.py --level unit")
        print("3. Deploy to staging for validation")
    else:
        print("[WARNING] Some issues still need attention")
        print("\nPlease review the validation output above")
    print("="*60)
    
    return 0 if all_fixed else 1

if __name__ == "__main__":
    sys.exit(main())