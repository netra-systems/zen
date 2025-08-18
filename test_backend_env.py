#!/usr/bin/env python
"""Test script to check if GEMINI_API_KEY is in backend environment."""

import os
import sys

print(f"[ENV_TEST] Python: {sys.executable}", file=sys.stderr)
print(f"[ENV_TEST] Total env vars: {len(os.environ)}", file=sys.stderr)
print(f"[ENV_TEST] GEMINI_API_KEY exists: {'GEMINI_API_KEY' in os.environ}", file=sys.stderr)

if 'GEMINI_API_KEY' in os.environ:
    value = os.environ['GEMINI_API_KEY']
    print(f"[ENV_TEST] GEMINI_API_KEY value starts with: {value[:10]}...", file=sys.stderr)
    print(f"[ENV_TEST] GEMINI_API_KEY length: {len(value)}", file=sys.stderr)
else:
    print(f"[ENV_TEST] Looking for keys with 'GEMINI' in name:", file=sys.stderr)
    for key in os.environ:
        if 'GEMINI' in key.upper():
            print(f"[ENV_TEST]   Found: {key}", file=sys.stderr)
    
    print(f"[ENV_TEST] Looking for keys with 'API' in name:", file=sys.stderr)
    api_keys = [k for k in os.environ if 'API' in k.upper()]
    print(f"[ENV_TEST]   Found {len(api_keys)} keys with 'API'", file=sys.stderr)
    for key in api_keys[:5]:  # Show first 5
        print(f"[ENV_TEST]     - {key}", file=sys.stderr)

# Now test importing the config
print(f"\n[ENV_TEST] Testing config import...", file=sys.stderr)
try:
    from app.core.configuration.secrets import SecretManager
    sm = SecretManager()
    print(f"[ENV_TEST] SecretManager created successfully", file=sys.stderr)
    
    # Force load from environment
    sm._load_from_environment_variables()
    print(f"[ENV_TEST] Loaded secrets count: {sm.get_loaded_secrets_count()}", file=sys.stderr)
    
    # Check cache
    if 'gemini-api-key' in sm._secret_cache:
        print(f"[ENV_TEST] SUCCESS: gemini-api-key found in cache!", file=sys.stderr)
    else:
        print(f"[ENV_TEST] FAIL: gemini-api-key NOT in cache", file=sys.stderr)
        print(f"[ENV_TEST] Cache keys: {list(sm._secret_cache.keys())}", file=sys.stderr)
        
except Exception as e:
    print(f"[ENV_TEST] Error testing config: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)

print(f"[ENV_TEST] Test complete.", file=sys.stderr)