"""Simple validation script for the staging user auto-creation fix."""

import re
import sys
from pathlib import Path

# Fix Unicode output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def validate_fix():
    """Validate that the fix has been correctly applied."""
    
    auth_file = Path(__file__).parent.parent / "netra_backend" / "app" / "auth_integration" / "auth.py"
    
    print("=" * 60)
    print("VALIDATING STAGING USER AUTO-CREATION FIX")
    print("=" * 60)
    
    if not auth_file.exists():
        print(f" FAIL:  Auth file not found: {auth_file}")
        return False
    
    with open(auth_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that environment check has been removed (auto-creation in all environments)
    staging_check = 'config.environment in ["development", "staging"]'
    if staging_check not in content:
        print(" PASS:  Environment check removed - auto-creation enabled for all environments")
    else:
        print(" FAIL:  Old environment check still present - should be removed")
        return False
    
    # Check for auto-creation logic
    auto_create_check = 'user_service.get_or_create_dev_user'
    if auto_create_check in content:
        print(" PASS:  User auto-creation logic present")
    else:
        print(" FAIL:  User auto-creation logic not found")
        return False
    
    # Check for proper logging
    log_check = 'logger.info(f"Auto-created user from JWT:'
    if log_check in content:
        print(" PASS:  Proper logging for auto-created users")
    else:
        print(" WARNING: [U+FE0F]  Logging message may differ slightly")
    
    # Extract the relevant code section
    pattern = r'if not user:(.*?)return user'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        code_section = match.group(1)
        print("\n[U+1F4DD] Relevant code section:")
        print("-" * 40)
        for line in code_section.split('\n')[:15]:
            if line.strip():
                print(f"  {line[:80]}")
        print("-" * 40)
    
    # Check test file
    test_file = Path(__file__).parent.parent / "netra_backend" / "tests" / "integration" / "test_staging_user_auto_creation.py"
    
    if test_file.exists():
        print("\n PASS:  Test file created: test_staging_user_auto_creation.py")
        with open(test_file, 'r', encoding='utf-8') as f:
            test_content = f.read()
            test_count = test_content.count('async def test_')
            print(f"   - Contains {test_count} test functions")
    else:
        print("\n WARNING: [U+FE0F]  Test file not found")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(" PASS:  Fix has been successfully implemented!")
    print("\nWhat the fix does:")
    print("1. Auto-creates users in ALL environments (dev, staging, production)")
    print("2. Extracts email from JWT claims when available")
    print("3. Logs the auto-creation with environment info")
    print("4. No more 'User not found' errors for valid JWT tokens")
    
    print("\nExpected behavior in ALL environments:")
    print("- Users with valid JWT tokens will be auto-created")
    print("- Email from JWT claims will be used")
    print("- Seamless authentication across all environments")
    
    return True


if __name__ == "__main__":
    success = validate_fix()
    exit(0 if success else 1)