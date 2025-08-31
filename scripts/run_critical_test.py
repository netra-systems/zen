#!/usr/bin/env python
"""Script to run critical agent pipeline test with proper environment configuration."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file with override to ensure our values take precedence
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path, override=True)

# Ensure GEMINI_API_KEY is set from .env
gemini_key = os.getenv('GEMINI_API_KEY')
if not os.getenv('GEMINI_API_KEY'):
    os.environ['GEMINI_API_KEY'] = gemini_key
    print(f"Set GEMINI_API_KEY directly")

# Set all possible API key environment variables that might be needed
os.environ['TEST_GOOGLE_API_KEY'] = gemini_key
os.environ['TEST_GEMINI_API_KEY'] = gemini_key
os.environ['GOOGLE_API_KEY'] = gemini_key  # Some code might look for this

print(f"Set all Google/Gemini API key variants")

# Enable real LLM testing
os.environ['ENABLE_REAL_LLM_TESTING'] = 'true'
os.environ['TEST_LLM_MODE'] = 'real'
os.environ['USE_REAL_LLM'] = 'true'
os.environ['TEST_USE_REAL_LLM'] = 'true'

# Set environment to testing to ensure config loads properly
os.environ['ENVIRONMENT'] = 'testing'

# Print configuration
print("\nEnvironment configuration:")
print(f"  ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
print(f"  GEMINI_API_KEY: {'Set' if os.getenv('GEMINI_API_KEY') else 'Not set'}")
print(f"  GOOGLE_API_KEY: {'Set' if os.getenv('GOOGLE_API_KEY') else 'Not set'}")
print(f"  TEST_GOOGLE_API_KEY: {'Set' if os.getenv('TEST_GOOGLE_API_KEY') else 'Not set'}")
print(f"  TEST_GEMINI_API_KEY: {'Set' if os.getenv('TEST_GEMINI_API_KEY') else 'Not set'}")
print(f"  ENABLE_REAL_LLM_TESTING: {os.getenv('ENABLE_REAL_LLM_TESTING')}")
print(f"  TEST_LLM_MODE: {os.getenv('TEST_LLM_MODE')}")
print()

# Run pytest with the critical test
import pytest
sys.exit(pytest.main([
    'tests/e2e/test_agent_pipeline_critical.py',
    '-v',
    '--tb=short'
]))