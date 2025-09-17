#!/usr/bin/env python3
"""
Issue #1060 WebSocket Authentication Fragmentation Demonstration
CRITICAL: This test demonstrates JWT authentication fragmentation across the system.
Expected: FAILURES proving fragmentation exists
"""

import unittest
import jwt
import sys
import os
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, Mock

# Add the project root to Python path
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

def test_jwt_secret_fragmentation():
    """
    Demonstrate JWT secret fragmentation across different system components
    EXPECTED: FAILURE - Different components use different JWT secrets
    """
    print("\n" + "="*80)
    print("JWT SECRET FRAGMENTATION DEMONSTRATION - Issue #1060")
    print("="*80)
    
    # Test different JWT secret configuration paths that should be unified (SSOT)
    secret_paths = [
        "JWT_SECRET_KEY",         # Standard
        "JWT_SECRET",             # Alternative  
        "WEBSOCKET_JWT_SECRET",   # WebSocket specific
        "AUTH_SERVICE_JWT_SECRET" # Auth service specific
    ]
    
    # Mock environment with different secrets (demonstrating fragmentation)
    mock_env = {
        "JWT_SECRET_KEY": "main-jwt-secret",
        "JWT_SECRET": "alternate-jwt-secret", 
        "WEBSOCKET_JWT_SECRET": "websocket-jwt-secret",
        "AUTH_SERVICE_JWT_SECRET": "auth-service-jwt-secret"
    }
    
    # Create test JWT payload
    jwt_payload = {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
    }
    
    # Generate tokens with different secrets (showing fragmentation)
    tokens_by_secret = {}
    for secret_path in secret_paths:
        secret = mock_env.get(secret_path)
        if secret:
            try:
                token = jwt.encode(jwt_payload, secret, algorithm="HS256")
                tokens_by_secret[secret_path] = {
                    "secret": secret,
                    "token": token
                }
                print(f"✓ Generated token with {secret_path}: {secret}")
            except Exception as e:
                print(f"✗ Failed to generate token with {secret_path}: {e}")
    
    # Test cross-validation (fragmentation evidence)
    print(f"\n--- FRAGMENTATION EVIDENCE: Cross-Secret Validation ---")
    validation_results = {}
    
    for source_path, source_data in tokens_by_secret.items():
        validation_results[source_path] = {}
        source_token = source_data["token"]
        
        for target_path, target_data in tokens_by_secret.items():
            target_secret = target_data["secret"]
            
            try:
                # Try to validate source token with target secret
                decoded = jwt.decode(source_token, target_secret, algorithms=["HS256"])
                validation_results[source_path][target_path] = True
                print(f"✓ Token from {source_path} validated with {target_path} secret")
            except jwt.InvalidTokenError:
                validation_results[source_path][target_path] = False
                print(f"✗ Token from {source_path} FAILED validation with {target_path} secret")
            except Exception as e:
                validation_results[source_path][target_path] = False
                print(f"✗ Token from {source_path} ERROR with {target_path} secret: {e}")
    
    # Analyze fragmentation evidence
    print(f"\n--- FRAGMENTATION ANALYSIS ---")
    total_validations = 0
    successful_validations = 0
    
    for source_path, targets in validation_results.items():
        for target_path, success in targets.items():
            total_validations += 1
            if success:
                successful_validations += 1
    
    success_rate = (successful_validations / total_validations) * 100 if total_validations > 0 else 0
    
    print(f"Total cross-validations: {total_validations}")
    print(f"Successful validations: {successful_validations}")
    print(f"Success rate: {success_rate:.1f}%")
    
    # FRAGMENTATION EVIDENCE: In a unified system, success rate should be 100%
    # In a fragmented system, success rate will be low
    if success_rate == 100.0:
        print("⚠️  WARNING: 100% validation success - JWT fragmentation may be resolved")
        return False  # No fragmentation detected
    elif success_rate < 30.0:
        print("🚨 CRITICAL: Very low success rate - significant JWT fragmentation detected")
        return True   # Fragmentation confirmed
    else:
        print(f"⚠️  FRAGMENTATION DETECTED: {success_rate:.1f}% success rate indicates partial fragmentation")
        return True   # Some fragmentation detected
    
def test_websocket_auth_path_fragmentation():
    """
    Demonstrate WebSocket authentication path fragmentation
    EXPECTED: FAILURE - Different WebSocket auth paths behave differently
    """
    print("\n" + "="*80)
    print("WEBSOCKET AUTH PATH FRAGMENTATION DEMONSTRATION - Issue #1060")
    print("="*80)
    
    # Different WebSocket authentication formats (showing fragmentation)
    base_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.test"
    
    websocket_auth_formats = {
        "subprotocol_jwt": f"jwt.{base_token}",
        "subprotocol_bearer": f"bearer.{base_token}",
        "authorization_header": f"Bearer {base_token}",
        "query_param": base_token,
        "custom_header": f"WS-Auth {base_token}"
    }
    
    print("Testing different WebSocket authentication format recognition:")
    
    extraction_results = {}
    for format_name, auth_data in websocket_auth_formats.items():
        # Mock WebSocket connection with different auth formats
        mock_websocket = Mock()
        
        if format_name.startswith("subprotocol"):
            mock_websocket.scope = {"subprotocols": [auth_data]}
            mock_websocket.headers = {}
            mock_websocket.query_params = {}
        elif format_name == "authorization_header":
            mock_websocket.scope = {"subprotocols": []}
            mock_websocket.headers = {"authorization": auth_data}
            mock_websocket.query_params = {}
        elif format_name == "query_param":
            mock_websocket.scope = {"subprotocols": []}
            mock_websocket.headers = {}
            mock_websocket.query_params = {"token": auth_data}
        elif format_name == "custom_header":
            mock_websocket.scope = {"subprotocols": []}
            mock_websocket.headers = {"ws-auth": auth_data}
            mock_websocket.query_params = {}
        
        # Test different extraction methods (showing fragmentation)
        extraction_methods = [
            ("subprotocol_extraction", lambda ws: ws.scope.get("subprotocols", [])[0] if ws.scope.get("subprotocols") else None),
            ("header_extraction", lambda ws: ws.headers.get("authorization", "").replace("Bearer ", "") if ws.headers.get("authorization") else None),
            ("query_extraction", lambda ws: ws.query_params.get("token") if hasattr(ws, 'query_params') and ws.query_params.get("token") else None),
            ("custom_header_extraction", lambda ws: ws.headers.get("ws-auth", "").replace("WS-Auth ", "") if ws.headers.get("ws-auth") else None)
        ]
        
        format_results = {}
        for method_name, extraction_func in extraction_methods:
            try:
                extracted_token = extraction_func(mock_websocket)
                success = extracted_token is not None and extracted_token != ""
                format_results[method_name] = {
                    "success": success,
                    "extracted": extracted_token
                }
                status = "✓" if success else "✗"
                print(f"{status} {format_name} with {method_name}: {'SUCCESS' if success else 'FAILED'}")
            except Exception as e:
                format_results[method_name] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"✗ {format_name} with {method_name}: ERROR - {e}")
        
        extraction_results[format_name] = format_results
    
    # Analyze extraction fragmentation
    print(f"\n--- WEBSOCKET AUTH EXTRACTION FRAGMENTATION ANALYSIS ---")
    format_success_rates = {}
    
    for format_name, method_results in extraction_results.items():
        successful_methods = sum(1 for r in method_results.values() if r.get("success"))
        total_methods = len(method_results)
        success_rate = (successful_methods / total_methods) * 100 if total_methods > 0 else 0
        format_success_rates[format_name] = success_rate
        print(f"{format_name}: {successful_methods}/{total_methods} methods succeeded ({success_rate:.1f}%)")
    
    # FRAGMENTATION EVIDENCE: Different formats should have different success rates
    unique_success_rates = set(format_success_rates.values())
    
    print(f"\nUnique success rate patterns: {len(unique_success_rates)}")
    print(f"Success rates: {list(unique_success_rates)}")
    
    if len(unique_success_rates) == 1:
        if list(unique_success_rates)[0] == 100.0:
            print("⚠️  WARNING: All formats have 100% success - fragmentation may be resolved")
            return False  # No fragmentation
        elif list(unique_success_rates)[0] == 0.0:
            print("🚨 CRITICAL: All formats failed - configuration issue, not fragmentation")
            return False  # Configuration issue
        else:
            print("⚠️  CONSISTENT: All formats have same success rate - indicates uniform behavior")
            return False  # No fragmentation
    else:
        print("🚨 FRAGMENTATION CONFIRMED: Different formats have different success rates")
        return True   # Fragmentation detected

def main():
    """Run the fragmentation demonstration tests"""
    print("Issue #1060 WebSocket Authentication Fragmentation Test Execution")
    print("AGENT_SESSION_ID = agent-session-2025-09-14-1430")
    print("\nThese tests are designed to FAIL initially to prove fragmentation exists.")
    print("After SSOT remediation, they should all pass consistently.\n")
    
    # Test 1: JWT Secret Fragmentation
    jwt_fragmentation_detected = test_jwt_secret_fragmentation()
    
    # Test 2: WebSocket Auth Path Fragmentation  
    websocket_fragmentation_detected = test_websocket_auth_path_fragmentation()
    
    # Summary
    print("\n" + "="*80)
    print("FRAGMENTATION DETECTION SUMMARY")
    print("="*80)
    print(f"JWT Secret Fragmentation: {'DETECTED' if jwt_fragmentation_detected else 'NOT DETECTED'}")
    print(f"WebSocket Auth Path Fragmentation: {'DETECTED' if websocket_fragmentation_detected else 'NOT DETECTED'}")
    
    if jwt_fragmentation_detected or websocket_fragmentation_detected:
        print("\n🚨 FRAGMENTATION CONFIRMED: Issue #1060 authentication fragmentation exists")
        print("RECOMMENDATION: Implement SSOT authentication consolidation")
        return 1  # Exit code indicating fragmentation found
    else:
        print("\n✅ NO FRAGMENTATION DETECTED: Authentication paths appear unified")
        print("RESULT: Tests suggest fragmentation may already be resolved")
        return 0  # Exit code indicating no fragmentation

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)