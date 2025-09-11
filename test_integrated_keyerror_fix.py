#!/usr/bin/env python3
"""
Integrated test to verify the KeyError fix in the full logging system.
"""

import os
import sys
import subprocess

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

def test_with_real_logger():
    """Test with the real SSOT logger system."""
    
    # Create a simple test script that uses the SSOT logger in JSON mode
    test_script = '''
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

# Set environment for JSON logging
os.environ['K_SERVICE'] = 'test-service'  # Cloud Run marker
os.environ['ENVIRONMENT'] = 'staging'      # GCP environment

try:
    from shared.logging.unified_logging_ssot import get_logger
    
    # Get logger - this should trigger JSON logging setup
    logger = get_logger('test_module')
    
    # Log some messages that contain potential problem strings
    logger.info('Test message with "timestamp" and other JSON fields')
    logger.warning('Another message with "severity" and "service" fields')
    logger.error('Error message with "message" field referenced')
    
    print("SUCCESS: All logging completed without KeyError")
    
except KeyError as e:
    if '"timestamp"' in str(e):
        print(f"FAILED: KeyError still occurring: {e}")
        sys.exit(1)
    else:
        print(f"FAILED: Unexpected KeyError: {e}")
        sys.exit(1)
except Exception as e:
    print(f"FAILED: Unexpected error: {e}")
    sys.exit(1)
'''
    
    # Write the test script
    with open('temp_logging_test.py', 'w') as f:
        f.write(test_script)
    
    try:
        # Run the test script
        result = subprocess.run([sys.executable, 'temp_logging_test.py'], 
                              capture_output=True, text=True, timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        
        # Check if the test passed
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            return True
        else:
            return False
            
    except subprocess.TimeoutExpired:
        print("Test timed out")
        return False
    except Exception as e:
        print(f"Failed to run test: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists('temp_logging_test.py'):
            os.remove('temp_logging_test.py')

if __name__ == '__main__':
    print("Integrated KeyError Fix Test")
    print("=" * 30)
    
    success = test_with_real_logger()
    
    if success:
        print("\nSUCCESS: Integrated KeyError fix is working!")
    else:
        print("\nFAILED: Integrated KeyError fix is not working")