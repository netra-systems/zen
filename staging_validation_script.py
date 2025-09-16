#!/usr/bin/env python3
"""
Staging Infrastructure Validation Script
Direct validation of staging GCP services without test framework complications
"""

import asyncio
import time
import json
import ssl
import sys
from typing import Dict, Any, List

try:
    import requests
    import websockets
    DEPS_AVAILABLE = True
except ImportError:
    print("ERROR: Missing dependencies. Install with: pip install requests websockets")
    DEPS_AVAILABLE = False

class StagingValidator:
    """Direct staging infrastructure validation."""
    
    def __init__(self):
        self.results = {
            'http_services': {},
            'websocket_services': {},
            'performance_metrics': {},
            'overall_status': 'UNKNOWN'
        }
        
        # Staging URLs based on worklog configuration
        self.services = {
            'frontend': 'https://staging.netrasystems.ai',
            'api': 'https://api.staging.netrasystems.ai', 
            'auth': 'https://auth.staging.netrasystems.ai',
            'websocket': 'wss://api.staging.netrasystems.ai/ws'
        }
    
    def test_http_service(self, name: str, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Test HTTP service availability."""
        result = {
            'url': url,
            'status': 'UNKNOWN',
            'response_code': None,
            'response_time': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            response = requests.get(f"{url}/health", timeout=timeout)
            end_time = time.time()
            
            result.update({
                'status': 'AVAILABLE' if response.status_code == 200 else 'DEGRADED',
                'response_code': response.status_code,
                'response_time': round(end_time - start_time, 2)
            })
            
        except requests.exceptions.Timeout:
            result.update({
                'status': 'TIMEOUT',
                'error': f'Timeout after {timeout}s'
            })
        except requests.exceptions.ConnectionError as e:
            result.update({
                'status': 'UNAVAILABLE',
                'error': f'Connection error: {str(e)}'
            })
        except Exception as e:
            result.update({
                'status': 'ERROR',
                'error': str(e)
            })
        
        return result
    
    async def test_websocket_service(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """Test WebSocket service availability."""
        result = {
            'url': url,
            'status': 'UNKNOWN',
            'connection_time': None,
            'ping_time': None,
            'error': None
        }
        
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            start_time = time.time()
            async with websockets.connect(
                url, 
                ssl=ssl_context, 
                timeout=timeout,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                connection_time = time.time() - start_time
                
                # Test ping
                ping_start = time.time()
                pong_waiter = await websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
                ping_time = time.time() - ping_start
                
                result.update({
                    'status': 'AVAILABLE',
                    'connection_time': round(connection_time, 2),
                    'ping_time': round(ping_time, 2)
                })
                
        except asyncio.TimeoutError:
            result.update({
                'status': 'TIMEOUT',
                'error': f'Timeout after {timeout}s'
            })
        except ConnectionError as e:
            result.update({
                'status': 'UNAVAILABLE', 
                'error': f'Connection error: {str(e)}'
            })
        except Exception as e:
            result.update({
                'status': 'ERROR',
                'error': str(e)
            })
        
        return result
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run complete staging validation."""
        print("STAGING INFRASTRUCTURE VALIDATION")
        print("=" * 50)
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
        print()
        
        # Test HTTP services
        print("Testing HTTP Services...")
        for name, url in self.services.items():
            if name == 'websocket':
                continue
            
            print(f"  {name}: ", end="", flush=True)
            result = self.test_http_service(name, url)
            self.results['http_services'][name] = result
            
            if result['status'] == 'AVAILABLE':
                print(f"✅ {result['response_code']} ({result['response_time']}s)")
            elif result['status'] == 'TIMEOUT':
                print(f"⏰ TIMEOUT ({result['error']})")
            elif result['status'] == 'UNAVAILABLE':
                print(f"❌ UNAVAILABLE ({result['error']})")
            else:
                print(f"🟡 {result['status']} - {result['error']}")
        
        print()
        
        # Test WebSocket service
        print("Testing WebSocket Service...")
        ws_result = await self.test_websocket_service(self.services['websocket'])
        self.results['websocket_services']['primary'] = ws_result
        
        print(f"  websocket: ", end="", flush=True)
        if ws_result['status'] == 'AVAILABLE':
            print(f"✅ AVAILABLE (conn: {ws_result['connection_time']}s, ping: {ws_result['ping_time']}s)")
        elif ws_result['status'] == 'TIMEOUT':
            print(f"⏰ TIMEOUT ({ws_result['error']})")
        elif ws_result['status'] == 'UNAVAILABLE':
            print(f"❌ UNAVAILABLE ({ws_result['error']})")
        else:
            print(f"🟡 {ws_result['status']} - {ws_result['error']}")
        
        print()
        
        # Calculate overall status
        all_http_available = all(
            result['status'] == 'AVAILABLE' 
            for result in self.results['http_services'].values()
        )
        websocket_available = ws_result['status'] == 'AVAILABLE'
        
        if all_http_available and websocket_available:
            self.results['overall_status'] = 'HEALTHY'
            status_emoji = "✅"
        elif any(result['status'] == 'AVAILABLE' for result in self.results['http_services'].values()):
            self.results['overall_status'] = 'DEGRADED'
            status_emoji = "🟡"
        else:
            self.results['overall_status'] = 'CRITICAL'
            status_emoji = "❌"
        
        print(f"OVERALL STATUS: {status_emoji} {self.results['overall_status']}")
        print("=" * 50)
        
        return self.results

async def main():
    """Main validation function."""
    if not DEPS_AVAILABLE:
        return False
    
    validator = StagingValidator()
    results = await validator.run_validation()
    
    # Print JSON results for programmatic consumption
    print("\nJSON RESULTS:")
    print(json.dumps(results, indent=2))
    
    # Return success/failure for script exit code
    return results['overall_status'] in ['HEALTHY', 'DEGRADED']

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)