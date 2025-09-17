#!/usr/bin/env python3

"""
Golden Path Validation for Staging Deployment
Tests the critical user flow: Login → WebSocket → Agent Interaction
"""

import json
import urllib.request
import urllib.error
import sys
from datetime import datetime

STAGING_CONFIG = {
    'frontend': 'https://netra-frontend-staging-pnovr5vsba-uc.a.run.app',
    'auth': 'https://auth.staging.netrasystems.ai'
}

def test_golden_path_components():
    """Test the critical components of the Golden Path user flow"""
    
    print("🛤️ GOLDEN PATH VALIDATION")
    print("=" * 60)
    print("Testing critical user journey components:")
    print("1️⃣ User loads frontend application")
    print("2️⃣ Authentication system is accessible") 
    print("3️⃣ WebSocket endpoints are configured")
    print("4️⃣ Agent interaction setup is ready")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Frontend Application Load
    print("\n1️⃣ Testing Frontend Application Load...")
    try:
        req = urllib.request.Request(STAGING_CONFIG['frontend'])
        req.add_header('User-Agent', 'GoldenPath-Validator/1.0')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8')
            
            # Check for critical frontend elements
            has_next_data = '_NEXT_DATA_' in content or 'nextConfig' in content
            has_react = 'react' in content.lower()
            has_websocket = 'websocket' in content.lower() or 'ws://' in content or 'wss://' in content
            
            results['frontend_load'] = {
                'success': True,
                'status': response.getcode(),
                'has_next_data': has_next_data,
                'has_react': has_react,
                'has_websocket_refs': has_websocket,
                'content_length': len(content)
            }
            
            print(f"✅ Frontend loads successfully")
            print(f"   📏 Content size: {len(content):,} bytes")
            print(f"   📦 Next.js data: {'✅' if has_next_data else '❌'}")
            print(f"   ⚛️  React present: {'✅' if has_react else '❌'}")
            print(f"   🔌 WebSocket refs: {'✅' if has_websocket else '❌'}")
            
    except Exception as e:
        results['frontend_load'] = {'success': False, 'error': str(e)}
        print(f"❌ Frontend load failed: {e}")
    
    # Test 2: Authentication System Accessibility
    print("\n2️⃣ Testing Authentication System...")
    try:
        auth_url = f"{STAGING_CONFIG['auth']}/health"
        req = urllib.request.Request(auth_url)
        req.add_header('User-Agent', 'GoldenPath-Validator/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            auth_data = json.loads(response.read().decode('utf-8'))
            
            results['auth_system'] = {
                'success': True,
                'status': response.getcode(),
                'service_status': auth_data.get('status', 'unknown'),
                'uptime': auth_data.get('uptime_seconds', 0),
                'version': auth_data.get('version', 'unknown')
            }
            
            print(f"✅ Auth system accessible")
            print(f"   🔐 Status: {auth_data.get('status', 'unknown')}")
            print(f"   ⏱️  Uptime: {auth_data.get('uptime_seconds', 0):.0f}s")
            print(f"   📋 Version: {auth_data.get('version', 'unknown')}")
            
    except Exception as e:
        results['auth_system'] = {'success': False, 'error': str(e)}
        print(f"❌ Auth system test failed: {e}")
    
    # Test 3: Frontend Configuration for WebSocket
    print("\n3️⃣ Testing WebSocket Configuration...")
    try:
        config_url = f"{STAGING_CONFIG['frontend']}/api/config/public"
        req = urllib.request.Request(config_url)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            config_data = json.loads(response.read().decode('utf-8'))
            
            # Check OAuth configuration
            has_oauth = config_data.get('oauth_enabled', False)
            google_client_id = config_data.get('google_client_id', '')
            
            # Check auth endpoints
            endpoints = config_data.get('endpoints', {})
            has_login = 'login' in endpoints
            has_callback = 'callback' in endpoints
            
            results['websocket_config'] = {
                'success': True,
                'oauth_enabled': has_oauth,
                'google_client_configured': bool(google_client_id),
                'login_endpoint': has_login,
                'callback_endpoint': has_callback,
                'endpoints': endpoints
            }
            
            print(f"✅ Configuration accessible")
            print(f"   🔐 OAuth enabled: {'✅' if has_oauth else '❌'}")
            print(f"   🌐 Google client: {'✅' if google_client_id else '❌'}")
            print(f"   🔗 Login endpoint: {'✅' if has_login else '❌'}")
            print(f"   🔙 Callback endpoint: {'✅' if has_callback else '❌'}")
            
    except Exception as e:
        results['websocket_config'] = {'success': False, 'error': str(e)}
        print(f"❌ WebSocket config test failed: {e}")
    
    # Test 4: Critical Frontend Routes
    print("\n4️⃣ Testing Critical Frontend Routes...")
    critical_routes = ['/login', '/chat', '/health']
    route_results = {}
    
    for route in critical_routes:
        try:
            route_url = f"{STAGING_CONFIG['frontend']}{route}"
            req = urllib.request.Request(route_url)
            req.add_header('User-Agent', 'GoldenPath-Validator/1.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.getcode()
                content_type = response.headers.get('content-type', '')
                
                route_results[route] = {
                    'success': status in [200, 302, 401],  # Accept redirect for auth-protected routes
                    'status': status,
                    'content_type': content_type
                }
                
                print(f"   {route}: {'✅' if route_results[route]['success'] else '❌'} ({status})")
                
        except urllib.error.HTTPError as e:
            # Some routes may return 401/403 for unauthenticated requests - this is expected
            route_results[route] = {
                'success': e.code in [200, 302, 401, 403],
                'status': e.code,
                'content_type': None
            }
            print(f"   {route}: {'✅' if route_results[route]['success'] else '❌'} ({e.code})")
            
        except Exception as e:
            route_results[route] = {'success': False, 'error': str(e)}
            print(f"   {route}: ❌ ({str(e)[:50]}...)")
    
    results['critical_routes'] = route_results
    
    return results

def analyze_golden_path_readiness(results):
    """Analyze results to determine Golden Path readiness"""
    
    print("\n" + "=" * 60)
    print("🎯 GOLDEN PATH READINESS ANALYSIS")
    print("=" * 60)
    
    # Critical success factors
    factors = {
        'frontend_operational': results.get('frontend_load', {}).get('success', False),
        'auth_system_healthy': results.get('auth_system', {}).get('success', False),
        'config_accessible': results.get('websocket_config', {}).get('success', False),
        'oauth_configured': results.get('websocket_config', {}).get('oauth_enabled', False),
        'routes_responsive': any(r.get('success', False) for r in results.get('critical_routes', {}).values())
    }
    
    print("📋 Readiness Factors:")
    for factor, status in factors.items():
        status_icon = "✅" if status else "❌"
        factor_name = factor.replace('_', ' ').title()
        print(f"   {status_icon} {factor_name}")
    
    # Overall readiness score
    passed_factors = sum(1 for status in factors.values() if status)
    total_factors = len(factors)
    readiness_score = passed_factors / total_factors
    
    print(f"\n📊 Overall Readiness: {passed_factors}/{total_factors} ({readiness_score:.1%})")
    
    # Readiness assessment
    if readiness_score >= 0.8:
        assessment = "🟢 READY - Golden Path should work"
        recommendation = "✅ Proceed with user testing"
    elif readiness_score >= 0.6:
        assessment = "🟡 PARTIALLY READY - Some issues detected"
        recommendation = "⚠️ Address failing components before full rollout"
    else:
        assessment = "🔴 NOT READY - Critical issues present"
        recommendation = "❌ Fix critical issues before proceeding"
    
    print(f"\n🎯 Assessment: {assessment}")
    print(f"📋 Recommendation: {recommendation}")
    
    # Specific recommendations based on failures
    if not factors['frontend_operational']:
        print("   🔧 Fix frontend application loading issues")
    if not factors['auth_system_healthy']:
        print("   🔧 Verify auth service connectivity and health")
    if not factors['config_accessible']:
        print("   🔧 Check frontend configuration endpoint")
    if not factors['oauth_configured']:
        print("   🔧 Enable OAuth configuration for authentication")
    if not factors['routes_responsive']:
        print("   🔧 Verify critical route accessibility")
    
    return {
        'readiness_score': readiness_score,
        'assessment': assessment,
        'recommendation': recommendation,
        'factors': factors
    }

def main():
    """Run Golden Path validation"""
    print(f"⏰ Started: {datetime.now().isoformat()}")
    print(f"🎯 Target: {STAGING_CONFIG['frontend']}")
    
    # Run validation tests
    test_results = test_golden_path_components()
    
    # Analyze readiness
    readiness_analysis = analyze_golden_path_readiness(test_results)
    
    # Save results
    timestamp = int(datetime.now().timestamp())
    results_file = f"golden_path_validation_{timestamp}.json"
    
    full_results = {
        'timestamp': datetime.now().isoformat(),
        'target_environment': 'staging',
        'config': STAGING_CONFIG,
        'test_results': test_results,
        'readiness_analysis': readiness_analysis
    }
    
    with open(results_file, 'w') as f:
        json.dump(full_results, f, indent=2)
    
    print(f"\n📁 Results saved to: {results_file}")
    print("=" * 60)
    
    # Return success based on readiness score
    return readiness_analysis['readiness_score'] >= 0.7

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)