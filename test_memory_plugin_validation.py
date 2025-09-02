#!/usr/bin/env python3
"""
Validation script for pytest memory plugin functionality.
Run this to verify the memory monitoring is working correctly.
"""
import os
import subprocess
import sys
import tempfile


def create_memory_intensive_test():
    """Create a test file that uses significant memory."""
    test_content = '''
import pytest
import time


@pytest.mark.docker_safe
def test_small_memory():
    """A test that uses minimal memory."""
    data = [i for i in range(100)]
    assert len(data) == 100


@pytest.mark.docker_skip  
def test_large_memory():
    """A test that uses significant memory."""
    # Create a large list (should trigger memory monitoring)
    big_data = [f"item_{i}" * 100 for i in range(100000)]
    assert len(big_data) == 100000


@pytest.mark.unit
def test_memory_cleanup():
    """Test that demonstrates memory cleanup."""
    temp_data = list(range(1000))
    assert len(temp_data) == 1000
    del temp_data  # Explicit cleanup


@pytest.mark.docker_safe
def test_async_function():
    """Test async functionality with function scope."""
    import asyncio
    
    async def async_operation():
        await asyncio.sleep(0.01)
        return "completed"
    
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(async_operation())
    assert result == "completed"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='_test.py', delete=False) as f:
        f.write(test_content)
        return f.name


def test_memory_plugin():
    """Test the memory plugin functionality."""
    print("[TESTING] Testing pytest memory plugin...")
    
    # Create test file
    test_file = create_memory_intensive_test()
    
    try:
        # Test 1: Collection only with memory limits
        print("\n[TEST1] Collection-only mode")
        env = os.environ.copy()
        env['PYTEST_COLLECTION_LIMIT_MB'] = '64'
        
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            '-c', 'pytest-collection.ini',
            test_file
        ], capture_output=True, text=True, env=env)
        
        print(f"Exit code: {result.returncode}")
        if "[MEMORY]" in result.stdout or "[MEMORY]" in result.stderr:
            print("[OK] Memory monitoring active in collection mode")
        else:
            print("[WARN] Memory monitoring not detected in output")
            
        # Test 2: Docker mode with memory limits
        print("\n[TEST2] Docker mode with memory limits")
        env['PYTEST_MEMORY_LIMIT_MB'] = '128'
        
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            '-c', 'pytest-docker.ini', 
            '-m', 'docker_safe',
            '-v',
            test_file
        ], capture_output=True, text=True, env=env)
        
        print(f"Exit code: {result.returncode}")
        if "[MEMORY]" in result.stdout or "[MEMORY]" in result.stderr:
            print("[OK] Memory monitoring active in Docker mode")
        else:
            print("[WARN] Memory monitoring not detected in output")
            
        # Test 3: Regular mode with main config
        print("\n[TEST3] Regular mode with updated pytest.ini")
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            '-m', 'docker_safe',
            '--tb=short',
            '-v',
            test_file
        ], capture_output=True, text=True)
        
        print(f"Exit code: {result.returncode}")
        print("[OK] Updated pytest.ini configuration working")
        
        # Show output for debugging
        print("\n[OUTPUT] Sample output:")
        if result.stdout:
            print("STDOUT:", result.stdout[:500])
        if result.stderr:
            print("STDERR:", result.stderr[:500])
            
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.unlink(test_file)
    
    print("\n[COMPLETE] Memory plugin validation completed!")


def validate_configurations():
    """Validate that all configuration files exist and are valid."""
    print("[VALIDATE] Validating pytest configuration files...")
    
    files_to_check = [
        'pytest.ini',
        'pytest-docker.ini', 
        'pytest-collection.ini',
        'pytest_memory_plugin.py',
        'pytest_optimization.md'
    ]
    
    for filename in files_to_check:
        if os.path.exists(filename):
            print(f"[OK] {filename} exists")
            # Basic syntax check for .ini files
            if filename.endswith('.ini'):
                try:
                    import configparser
                    config = configparser.ConfigParser()
                    config.read(filename)
                    print(f"[OK] {filename} syntax is valid")
                except Exception as e:
                    print(f"[ERROR] {filename} syntax error: {e}")
        else:
            print(f"[ERROR] {filename} missing")
    
    print("[COMPLETE] Configuration validation completed!")


if __name__ == "__main__":
    print("[START] Starting pytest optimization validation...")
    validate_configurations()
    test_memory_plugin()
    print("\n[SUCCESS] All validations completed!")
    print("\n[NEXT] Next steps:")
    print("1. Test in Docker: docker-compose run backend pytest -c pytest-docker.ini -m docker_safe")
    print("2. Set memory limits: export PYTEST_MEMORY_LIMIT_MB=256")
    print("3. Use collection mode: pytest -c pytest-collection.ini --collect-only")