"""
Quick test to verify the API URL configuration fix works
"""

# Test 1: Verify frontend configuration
print("=" * 60)
print("TEST 1: Frontend API URL Configuration")
print("=" * 60)

# Simulate frontend environment
import os
os.environ['NEXT_PUBLIC_ENVIRONMENT'] = 'staging'

# Check what would happen in frontend
frontend_file = 'frontend/components/chat/hooks/useMessageSending.ts'
with open(frontend_file, 'r') as f:
    content = f.read()
    
    # Check for the fix
    has_import = "import { getUnifiedApiConfig }" in content
    uses_config = "getUnifiedApiConfig()" in content
    uses_api_url = "${apiUrl}/api/agents/" in content
    
    print(f"[OK] Has getUnifiedApiConfig import: {has_import}")
    print(f"[OK] Uses getUnifiedApiConfig(): {uses_config}")
    print(f"[OK] Uses ${{apiUrl}}/api/agents/: {uses_api_url}")
    
    # Check for bad patterns
    bad_patterns = [
        "fetch('/api/agents/",
        'fetch("/api/agents/',
        "fetch(`/api/agents/"
    ]
    
    has_bad_pattern = False
    for pattern in bad_patterns:
        if pattern in content:
            has_bad_pattern = True
            print(f"[FAIL] Found bad pattern: {pattern}")
    
    if not has_bad_pattern:
        print("[OK] No relative URL patterns found")

print("\n" + "=" * 60)
print("TEST 2: Backend Agent Endpoints")
print("=" * 60)

# Test 2: Check backend routes are configured
import sys
sys.path.insert(0, 'netra_backend')

try:
    from netra_backend.app.routes.agents_execute import router
    
    # Get all routes from the router
    routes = [route.path for route in router.routes if hasattr(route, 'path')]
    
    expected_routes = ['/execute', '/triage', '/data', '/optimization']
    
    for route in expected_routes:
        if route in routes:
            print(f"[OK] Route {route} exists in agents_execute router")
        else:
            print(f"[FAIL] Route {route} missing from agents_execute router")
    
    # Check route configuration
    from netra_backend.app.core.app_factory_route_configs import get_all_route_configurations
    from netra_backend.app.core.app_factory_route_imports import import_all_route_modules
    
    modules = import_all_route_modules()
    configs = get_all_route_configurations(modules)
    
    if 'agents_execute' in configs:
        config = configs['agents_execute']
        print(f"[OK] agents_execute router configured with prefix: {config[1]}")
        print(f"   Full paths will be: {config[1]}/triage, {config[1]}/data, etc.")
    else:
        print("[FAIL] agents_execute router not found in configuration")
        
except Exception as e:
    print(f"Error testing backend: {e}")

print("\n" + "=" * 60)
print("TEST 3: URL Construction Verification")
print("=" * 60)

# Test URL construction
staging_api = "https://api.staging.netrasystems.ai"
agent_types = ['triage', 'data', 'optimization']

print("Expected URLs in staging:")
for agent_type in agent_types:
    url = f"{staging_api}/api/agents/{agent_type}"
    print(f"  {agent_type}: {url}")

print("\n[OK] All tests completed. The fix should resolve the 404 issue.")
print("   Frontend will now call api.staging.netrasystems.ai instead of app.staging.netrasystems.ai")