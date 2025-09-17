import sys
sys.path.insert(0, '.')

# Quick connectivity check
try:
    import requests
    response = requests.get('https://api.staging.netrasystems.ai/health', timeout=10)
    print(f"Backend health: {response.status_code}")
except Exception as e:
    print(f"Backend error: {e}")

try:
    import requests
    response = requests.get('https://auth.staging.netrasystems.ai/health', timeout=10)
    print(f"Auth health: {response.status_code}")
except Exception as e:
    print(f"Auth error: {e}")

# Quick import check
try:
    from tests.e2e.staging_config import StagingTestConfig
    config = StagingTestConfig()
    print(f"Config loaded: {config.get_backend_base_url()}")
except Exception as e:
    print(f"Config error: {e}")