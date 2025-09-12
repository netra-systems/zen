#!/usr/bin/env python3
"""
Validate CSP fix for worker creation and external API connections.
Tests that the CSP configuration allows blob: URLs for workers and external domains.
"""

import requests
import sys
import io
from typing import List, Tuple

# Set UTF-8 encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_csp_headers(url: str) -> Tuple[bool, List[str]]:
    """Check if CSP headers are correctly configured."""
    try:
        response = requests.head(url, timeout=10)
        csp_header = response.headers.get('content-security-policy', '')
        
        if not csp_header:
            return False, ["No CSP header found"]
        
        issues = []
        successes = []
        
        # Check for blob: in script-src
        if 'script-src' in csp_header and 'blob:' in csp_header:
            successes.append(" PASS:  blob: found in script-src")
        else:
            issues.append(" FAIL:  blob: not found in script-src")
        
        # Check for worker-src directive
        if 'worker-src' in csp_header:
            if 'blob:' in csp_header.split('worker-src')[1].split(';')[0]:
                successes.append(" PASS:  worker-src includes blob:")
            else:
                issues.append(" FAIL:  worker-src exists but doesn't include blob:")
        else:
            issues.append(" WARNING: [U+FE0F]  No explicit worker-src directive (will fallback to script-src)")
        
        # Check for external domains in connect-src
        connect_src_section = csp_header.split('connect-src')[1].split(';')[0] if 'connect-src' in csp_header else ''
        
        if 'featureassets.org' in connect_src_section:
            successes.append(" PASS:  featureassets.org in connect-src")
        else:
            issues.append(" FAIL:  featureassets.org not in connect-src")
        
        if 'cloudflare-dns.com' in connect_src_section:
            successes.append(" PASS:  cloudflare-dns.com in connect-src")
        else:
            issues.append(" FAIL:  cloudflare-dns.com not in connect-src")
        
        # Print results
        print(f"\n SEARCH:  CSP Validation for {url}")
        print("=" * 60)
        
        if successes:
            print("\n PASS:  Successful checks:")
            for success in successes:
                print(f"  {success}")
        
        if issues:
            print("\n FAIL:  Issues found:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("\n CELEBRATION:  All CSP checks passed!")
        
        print("\n[U+1F4CB] Full CSP Header:")
        print("-" * 60)
        # Pretty print the CSP header
        csp_parts = csp_header.split('; ')
        for part in csp_parts:
            print(f"  {part}")
        
        return len(issues) == 0, issues
        
    except requests.RequestException as e:
        return False, [f"Failed to fetch headers: {e}"]

def main():
    """Main validation function."""
    environments = [
        ("Staging", "https://app.staging.netrasystems.ai"),
    ]
    
    all_passed = True
    
    for env_name, url in environments:
        passed, issues = check_csp_headers(url)
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print(" PASS:  CSP VALIDATION SUCCESSFUL - All environments configured correctly!")
        print("\nThe CSP fixes have been successfully applied:")
        print("[U+2022] Web Workers can now be created from blob: URLs")
        print("[U+2022] External API connections to featureassets.org and cloudflare-dns.com are allowed")
        return 0
    else:
        print(" FAIL:  CSP VALIDATION FAILED - Some issues need attention")
        print("\nPlease review the issues above and update the CSP configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())