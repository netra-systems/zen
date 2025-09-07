"""
Test to verify SERVICE_ID does not contain timestamp suffix
"""
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_service_id_no_timestamp():
    """Verify that SERVICE_ID in deployment script does not contain timestamp"""
    deploy_script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts", "deploy_to_gcp.py"
    )
    
    with open(deploy_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the old pattern with timestamp
    timestamp_pattern = r'"service-id-staging":\s*f"netra-auth-staging-\{int\(time\.time\(\)\)\}"'
    if re.search(timestamp_pattern, content):
        assert False, "SERVICE_ID still contains timestamp suffix! Should be 'netra-auth-staging' without timestamp"
    
    # Check for the correct pattern without timestamp
    correct_pattern = r'"service-id-staging":\s*"netra-auth-staging"'
    assert re.search(correct_pattern, content), "SERVICE_ID should be set to 'netra-auth-staging' without timestamp"
    
    print("[PASS] SERVICE_ID correctly set to 'netra-auth-staging' without timestamp suffix")

if __name__ == "__main__":
    test_service_id_no_timestamp()
    print("Test passed!")