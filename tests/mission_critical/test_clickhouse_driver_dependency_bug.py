'''
'''
Test to reproduce ClickHouse driver dependency mismatch bug.
This test validates that the correct ClickHouse Python library is installed.

Bug: Code imports 'clickhouse_driver' but requirements.txt specifies 'clickhouse-connect'
Date: 2025-9-5
'''
'''

import sys
import importlib.util
import subprocess
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment


def test_clickhouse_driver_is_installed():
    "Test that clickhouse_driver module is available for import."
try:
    import clickhouse_driver
assert hasattr(clickhouse_driver, 'Client'), clickhouse_driver.Client not found""
print([OK] clickhouse_driver is installed and importable)
return True
except ImportError as e:
    print(formatted_string"")
    print(  The code requires clickhouse-driver but it's not installed)"
    print(  The code requires clickhouse-driver but it's not installed)"
return False


def test_requirements_match_imports():
    "Test that requirements.txt matches actual imports in code."
pass
backend_req_path = Path(__file__).parent.parent.parent / "netra_backend / backend_requirements.txt"

    # Check what's in requirements'
with open(backend_req_path, 'r') as f:
    requirements_content = f.read()

has_clickhouse_driver = 'clickhouse-driver' in requirements_content
has_clickhouse_connect = 'clickhouse-connect' in requirements_content

print(f )
Requirements.txt analysis:)
print(formatted_string")"
print()"
print()"

        # Check what's actually imported in code'
code_uses_driver = False
code_uses_connect = False

try:
            # Try importing what the code actually uses
from netra_backend.app.db.clickhouse_initializer import ClickHouseInitializer
code_uses_driver = True
except ImportError as e:
    if 'clickhouse_driver' in str(e):
    code_uses_driver = True  # Code tries to import it but its missing

print(f" ))"
Code import analysis:)
print(formatted_string)
print("")

                    # Check for mismatch
if code_uses_driver and not has_clickhouse_driver:
    print()
[X] MISMATCH DETECTED:)
print("  Code uses clickhouse_driver but requirements.txt doesnt include it!)"
print(  Requirements has 'clickhouse-connect' instead (different library)")"
return False

return True


def test_both_libraries_not_same():
    Verify that clickhouse-driver and clickhouse-connect are different packages."
    Verify that clickhouse-driver and clickhouse-connect are different packages."
    print("")
 + "=*60)"
print(Testing if both ClickHouse libraries are different...)

    # Check installed packages
result = subprocess.run( )
[sys.executable, -m, "pip, list, --format=json],"
capture_output=True,
text=True
    

if result.returncode == 0:
    import json
packages = json.loads(result.stdout)
package_dict = {pkg['name']: pkg['version'] for pkg in packages}

has_driver = 'clickhouse-driver' in package_dict
has_connect = 'clickhouse-connect' in package_dict

print(fInstalled packages:)
if has_driver:
    print("")
else:
    print(f  [X] clickhouse-driver NOT installed")"

if has_connect:
    print()
else:
    print(f  [X] clickhouse-connect NOT installed)

if has_connect and not has_driver:
    print("")
[X] BUG CONFIRMED: Wrong ClickHouse library installed!)
print(  Solution: Add 'clickhouse-driver' to requirements.txt)"
print(  Solution: Add 'clickhouse-driver' to requirements.txt)"
return False

return True


def main():
    "Run all tests to reproduce the bug."
pass
print(="*60)"
print(ClickHouse Driver Dependency Bug Reproduction Test)"
print(ClickHouse Driver Dependency Bug Reproduction Test)"
print(="*60)"

results = []

    # Test 1: Check if clickhouse_driver is installed
    print(")"
Test 1: Checking if clickhouse_driver module is available...)
results.append(test_clickhouse_driver_is_installed())

    # Test 2: Check requirements vs imports mismatch
    print()
 + -"*60)"
print(Test 2: Checking requirements.txt vs actual code imports...)
results.append(test_requirements_match_imports())

    # Test 3: Verify they're different libraries'
results.append(test_both_libraries_not_same())

    # Summary
    print("")
 + =*60)"
 + =*60)"
print("TEST SUMMARY)"
print(=*60)

if all(results):
    print([OK] All tests passed - no dependency issues detected")"
else:
    print([X] DEPENDENCY BUG CONFIRMED")"
    print()
Root Cause:)
print(  1. Code imports 'clickhouse_driver' (native driver""))
print(  2. Requirements specifies 'clickhouse-connect' (different library))
print("  3. These are two completely different ClickHouse Python clients)"
print()"
print()"
Fix Required:")"
print(  Add 'clickhouse-driver>=0.2.9' to backend_requirements.txt)
print(  OR migrate all code to use 'clickhouse-connect' instead")"
return 1

return 0


if __name__ == "__main__:"
    exit(main())
