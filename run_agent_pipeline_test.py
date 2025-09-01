#!/usr/bin/env python3
"""
Test runner script for the agent pipeline real test.
Loads development environment and runs the test with proper configuration.
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def setup_test_environment():
    """Setup test environment with development configuration."""
    project_root = Path(__file__).parent
    
    # Load development environment
    env_file = project_root / ".env.development"
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        load_dotenv(env_file)
    else:
        print(f"Warning: {env_file} not found")
    
    # Set essential test environment variables
    essential_vars = {
        'USE_REAL_LLM': 'true',
        'TEST_USE_REAL_LLM': 'true', 
        'NETRA_REAL_LLM_ENABLED': 'true',
        'ENABLE_REAL_LLM_TESTING': 'true',
        'TEST_LLM_MODE': 'real',
        'JWT_SECRET_KEY': 'rsWwwvq8X6mCSuNv-TMXHDCfb96Xc-Dbay9MZy6EDCU',
        'ENVIRONMENT': 'testing',
        'TESTING': '1',
        'E2E_TESTING': 'true',
        'NO_MOCK_FALLBACK': 'true',
        'FORCE_REAL_SERVICES': 'true',
        'DATABASE_URL': 'sqlite+aiosqlite:///:memory:',  # Use in-memory SQLite for testing
        'TEST_SERVICE_MODE': 'local',
        'SKIP_DOCKER_CHECK': 'true'
    }
    
    for key, value in essential_vars.items():
        os.environ[key] = value
        print(f"Set {key}={value}")
    
    # Check API key availability
    api_keys = {
        'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY'),
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY'),
        'GOOGLE_API_KEY': os.environ.get('GOOGLE_API_KEY')
    }
    
    available_keys = {k: v for k, v in api_keys.items() if v}
    print(f"\nAvailable API keys: {list(available_keys.keys())}")
    
    if not available_keys:
        print("ERROR: No LLM API keys found!")
        return False
    
    return True

def run_test():
    """Run the agent pipeline test."""
    if not setup_test_environment():
        return 1
    
    print(f"\n{'='*60}")
    print("RUNNING AGENT PIPELINE REAL TEST")
    print(f"{'='*60}")
    
    # Build test command
    test_file = "tests/e2e/integration/test_agent_pipeline_real.py"
    cmd = [
        sys.executable, '-m', 'pytest', 
        test_file,
        '-v',                    # Verbose output
        '--tb=short',           # Short traceback format
        '--no-cov',             # Disable coverage for speed
        '-s',                   # Don't capture output
        '--timeout=300'         # 5 minute timeout per test
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.executable}")
    
    try:
        # Run the test
        result = subprocess.run(cmd, timeout=600)  # 10 minute overall timeout
        return result.returncode
    except subprocess.TimeoutExpired:
        print("ERROR: Test execution timed out after 10 minutes")
        return 1
    except KeyboardInterrupt:
        print("Test execution interrupted by user")
        return 1
    except Exception as e:
        print(f"ERROR: Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_test()
    print(f"\nTest completed with exit code: {exit_code}")
    sys.exit(exit_code)