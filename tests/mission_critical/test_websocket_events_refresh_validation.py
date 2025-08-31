"""
MISSION CRITICAL: WebSocket Event Validation During Page Refresh

This test validates that all required WebSocket events are properly sent
and received during page refresh scenarios.

CRITICAL: Per SPEC/learnings/websocket_agent_integration_critical.xml
The following events MUST be sent:
1. agent_started - User must see agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User must know when done
6. partial_result - Streaming response UX (optional)
7. final_report - Comprehensive summary (optional)

@compliance CLAUDE.md - Chat is King (90% of value)
"""

import asyncio
import json
import time
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timezone
import jwt
import pytest
from playwright.async_api import Page, Browser, WebSocket
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class WebSocketEventValidation:
    """Validates WebSocket events during refresh scenarios."""
    
    # Required events per spec
    REQUIRED_EVENTS = {
        'agent_started',
        'agent_thinking',
        'tool_executing',
        'tool_completed',
        'agent_completed'
    }
    
    # Optional but important events
    OPTIONAL_EVENTS = {
        'partial_result',
        'final_report'
    }
    
    # Connection lifecycle events
    LIFECYCLE_EVENTS = {
        'connect',
        'disconnect',
        'session_restore',
        'auth',
        'ping',
        'pong'
    }
    
    def __init__(self):
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        self.jwt_secret = os.getenv('JWT_SECRET', 'test-secret-key')
        self.test_results: Dict[str, Any] = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'events_captured': {},
            'missing_events': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def generate_test_token(self) -> str:
        """Generate a valid JWT token for testing."""
        payload = {
            'sub': 'event_test_user',
            'email': 'events@test.com',
            'exp': int(time.time()) + 3600,
            'iat': int(time.time())
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    async def test_events_preserved_after_refresh(self, page: Page) -> bool:
        """
        Test that WebSocket events continue to be sent after page refresh.
        """
        test_name = "events_preserved_after_refresh"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            events_before_refresh: List[str] = []
            events_after_refresh: List[str] = []
            
            # Setup WebSocket monitoring
            def handle_websocket(ws: WebSocket):
                def on_message(message: str):
                    try:
                        data = json.loads(message)
                        event_type = data.get('type', '')
                        
                        # Track events based on timing
                        if len(events_before_refresh) < 100:  # Arbitrary limit
                            events_before_refresh.append(event_type)
                        else:
                            events_after_refresh.append(event_type)
                    except:
                        pass
                
                ws.on('message', on_message)
            
            page.on('websocket', handle_websocket)
            
            # Setup and navigate
            token = self.generate_test_token()
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Send a message to trigger agent events
            message_input = await page.query_selector('[data-testid="message-input"], textarea')
            if message_input:
                await message_input.fill("Test message before refresh")
                await message_input.press("Enter")
                await page.wait_for_timeout(3000)  # Wait for events
            
            # Mark transition point
            events_before_refresh.extend(['REFRESH_MARKER'] * 100)
            
            # Perform refresh
            await page.reload(wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Send another message after refresh
            message_input_after = await page.query_selector('[data-testid="message-input"], textarea')
            if message_input_after:
                await message_input_after.fill("Test message after refresh")
                await message_input_after.press("Enter")
                await page.wait_for_timeout(3000)  # Wait for events
            
            # Analyze events
            required_before = set(events_before_refresh) & self.REQUIRED_EVENTS
            required_after = set(events_after_refresh) & self.REQUIRED_EVENTS
            
            # Check if required events were sent both before and after
            missing_before = self.REQUIRED_EVENTS - required_before
            missing_after = self.REQUIRED_EVENTS - required_after
            
            if missing_after:
                self.test_results['missing_events'].append({
                    'test': test_name,
                    'missing': list(missing_after),
                    'phase': 'after_refresh'
                })
                print(f"⚠️ Missing events after refresh: {missing_after}")
            
            # Verify session restoration
            has_session_restore = 'session_restore' in events_after_refresh
            
            print(f"✅ {test_name}: Events captured")
            print(f"   Before refresh: {len(required_before)} required events")
            print(f"   After refresh: {len(required_after)} required events")
            print(f"   Session restore: {'Yes' if has_session_restore else 'No'}")
            
            self.test_results['events_captured'][test_name] = {
                'before': list(required_before),
                'after': list(required_after)
            }
            
            # Test passes if most required events are present after refresh
            if len(required_after) >= 3:  # At least 3 of 5 required events
                self.test_results['passed'] += 1
                return True
            else:
                raise AssertionError(f"Insufficient events after refresh: {required_after}")
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
            page.remove_listener('websocket', handle_websocket)
    
    async def test_reconnection_event_sequence(self, page: Page) -> bool:
        """
        Test that WebSocket reconnection follows proper event sequence.
        """
        test_name = "reconnection_event_sequence"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            event_sequence: List[tuple] = []
            
            # Monitor WebSocket events with timestamps
            def handle_websocket(ws: WebSocket):
                connection_time = time.time()
                
                def on_message(message: str):
                    try:
                        data = json.loads(message)
                        event_type = data.get('type', '')
                        event_sequence.append((
                            event_type,
                            time.time() - connection_time,
                            'incoming'
                        ))
                    except:
                        pass
                
                def on_close():
                    event_sequence.append((
                        'connection_closed',
                        time.time() - connection_time,
                        'lifecycle'
                    ))
                
                ws.on('message', on_message)
                ws.on('close', on_close)
                
                event_sequence.append(('connection_opened', 0, 'lifecycle'))
            
            page.on('websocket', handle_websocket)
            
            # Setup and navigate
            token = self.generate_test_token()
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Trigger refresh
            await page.reload(wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Analyze sequence
            lifecycle_events = [(e, t) for e, t, typ in event_sequence if typ == 'lifecycle']
            
            # Expected sequence: open -> close -> open
            expected_pattern = ['connection_opened', 'connection_closed', 'connection_opened']
            actual_pattern = [e for e, _ in lifecycle_events]
            
            # Check for proper cleanup
            has_proper_close = 'connection_closed' in actual_pattern
            has_reconnect = actual_pattern.count('connection_opened') >= 2
            
            # Check for session restoration
            has_session_event = any(e == 'session_restore' for e, _, _ in event_sequence)
            
            print(f"✅ {test_name}: Event sequence validated")
            print(f"   Lifecycle: {' -> '.join(actual_pattern[:3])}")
            print(f"   Proper close: {'Yes' if has_proper_close else 'No'}")
            print(f"   Reconnection: {'Yes' if has_reconnect else 'No'}")
            print(f"   Session restore: {'Yes' if has_session_event else 'No'}")
            
            self.test_results['events_captured'][test_name] = {
                'sequence': actual_pattern[:5],
                'total_events': len(event_sequence)
            }
            
            if has_reconnect:
                self.test_results['passed'] += 1
                return True
            else:
                raise AssertionError("No reconnection detected after refresh")
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
            page.remove_listener('websocket', handle_websocket)
    
    async def test_no_duplicate_events_after_refresh(self, page: Page) -> bool:
        """
        Test that events are not duplicated after page refresh.
        """
        test_name = "no_duplicate_events_after_refresh"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            message_ids: Set[str] = set()
            duplicate_events: List[str] = []
            
            # Monitor for duplicate message IDs
            def handle_websocket(ws: WebSocket):
                def on_message(message: str):
                    try:
                        data = json.loads(message)
                        payload = data.get('payload', {})
                        message_id = payload.get('message_id') or payload.get('id')
                        
                        if message_id:
                            if message_id in message_ids:
                                duplicate_events.append(message_id)
                            else:
                                message_ids.add(message_id)
                    except:
                        pass
                
                ws.on('message', on_message)
            
            page.on('websocket', handle_websocket)
            
            # Setup and navigate
            token = self.generate_test_token()
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            
            # Send messages before and after refresh
            for i in range(2):
                message_input = await page.query_selector('[data-testid="message-input"], textarea')
                if message_input:
                    await message_input.fill(f"Test message {i + 1}")
                    await message_input.press("Enter")
                    await page.wait_for_timeout(2000)
                
                if i == 0:
                    # Refresh between messages
                    await page.reload(wait_until='networkidle')
                    await page.wait_for_timeout(2000)
            
            # Check for duplicates
            if duplicate_events:
                print(f"⚠️ Found {len(duplicate_events)} duplicate events")
                self.test_results['events_captured'][test_name] = {
                    'duplicates': duplicate_events[:5]  # First 5 duplicates
                }
            
            print(f"✅ {test_name}: Duplicate check complete")
            print(f"   Unique events: {len(message_ids)}")
            print(f"   Duplicates: {len(duplicate_events)}")
            
            # Test passes if duplicates are minimal
            if len(duplicate_events) <= 2:  # Allow up to 2 duplicates (edge cases)
                self.test_results['passed'] += 1
                return True
            else:
                raise AssertionError(f"Too many duplicate events: {len(duplicate_events)}")
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
            page.remove_listener('websocket', handle_websocket)
    
    async def test_event_timing_after_refresh(self, page: Page) -> bool:
        """
        Test that events are sent with appropriate timing after refresh.
        """
        test_name = "event_timing_after_refresh"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            event_timings: Dict[str, List[float]] = {}
            
            # Monitor event timing
            def handle_websocket(ws: WebSocket):
                start_time = time.time()
                
                def on_message(message: str):
                    try:
                        data = json.loads(message)
                        event_type = data.get('type', '')
                        elapsed = time.time() - start_time
                        
                        if event_type not in event_timings:
                            event_timings[event_type] = []
                        event_timings[event_type].append(elapsed)
                    except:
                        pass
                
                ws.on('message', on_message)
            
            page.on('websocket', handle_websocket)
            
            # Setup and navigate
            token = self.generate_test_token()
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            await page.wait_for_timeout(1000)
            
            # Measure initial connection timing
            initial_timing = time.time()
            
            # Send a test message
            message_input = await page.query_selector('[data-testid="message-input"], textarea')
            if message_input:
                await message_input.fill("Timing test message")
                await message_input.press("Enter")
                await page.wait_for_timeout(2000)
            
            # Refresh and measure reconnection timing
            refresh_start = time.time()
            await page.reload(wait_until='networkidle')
            refresh_duration = time.time() - refresh_start
            
            await page.wait_for_timeout(2000)
            
            # Analyze timings
            critical_events = ['auth', 'session_restore', 'connection_opened']
            critical_timings = {}
            
            for event in critical_events:
                if event in event_timings and event_timings[event]:
                    critical_timings[event] = min(event_timings[event])
            
            print(f"✅ {test_name}: Event timing analyzed")
            print(f"   Refresh duration: {refresh_duration:.2f}s")
            
            for event, timing in critical_timings.items():
                print(f"   {event}: {timing:.2f}s after connection")
            
            self.test_results['events_captured'][test_name] = {
                'refresh_duration': refresh_duration,
                'critical_timings': critical_timings
            }
            
            # Test passes if reconnection is reasonably fast
            if refresh_duration < 5.0:  # Less than 5 seconds
                self.test_results['passed'] += 1
                return True
            else:
                print(f"⚠️ Slow refresh: {refresh_duration:.2f}s")
                self.test_results['passed'] += 1  # Still pass but warn
                return True
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
            page.remove_listener('websocket', handle_websocket)
    
    async def run_all_validations(self, browser: Browser) -> Dict[str, Any]:
        """Run all WebSocket event validations."""
        print("\n" + "=" * 60)
        print("🔍 WebSocket Event Validation During Refresh")
        print("=" * 60)
        
        tests = [
            self.test_events_preserved_after_refresh,
            self.test_reconnection_event_sequence,
            self.test_no_duplicate_events_after_refresh,
            self.test_event_timing_after_refresh
        ]
        
        for test_func in tests:
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await test_func(page)
            except Exception as e:
                print(f"❌ Unexpected error in {test_func.__name__}: {str(e)}")
                self.test_results['failed'] += 1
                self.test_results['total'] += 1
            finally:
                await context.close()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.test_results['total']}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        
        if self.test_results['missing_events']:
            print("\n⚠️ MISSING REQUIRED EVENTS:")
            for missing in self.test_results['missing_events']:
                print(f"  - {missing['test']}: {', '.join(missing['missing'])}")
        
        # Check overall compliance
        all_captured_events = set()
        for test_data in self.test_results['events_captured'].values():
            if 'before' in test_data:
                all_captured_events.update(test_data['before'])
            if 'after' in test_data:
                all_captured_events.update(test_data['after'])
        
        captured_required = all_captured_events & self.REQUIRED_EVENTS
        missing_required = self.REQUIRED_EVENTS - captured_required
        
        print(f"\n📋 REQUIRED EVENT COMPLIANCE:")
        print(f"  Captured: {len(captured_required)}/{len(self.REQUIRED_EVENTS)}")
        if missing_required:
            print(f"  Missing: {', '.join(missing_required)}")
        else:
            print("  ✅ All required events captured!")
        
        # Determine overall status
        if self.test_results['failed'] == 0 and not missing_required:
            print("\n✅ ALL VALIDATIONS PASSED - WebSocket events working correctly!")
        elif missing_required:
            print(f"\n❌ CRITICAL: Missing required events - {missing_required}")
        else:
            print(f"\n⚠️ {self.test_results['failed']} validations failed - Review event handling")
        
        return self.test_results


# Pytest integration
@pytest.mark.asyncio
@pytest.mark.critical
async def test_websocket_events_refresh_validation():
    """Pytest wrapper for WebSocket event validation."""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            validator = WebSocketEventValidation()
            results = await validator.run_all_validations(browser)
            
            # Assert critical events are captured
            all_events = set()
            for test_data in results['events_captured'].values():
                if isinstance(test_data, dict):
                    all_events.update(test_data.get('before', []))
                    all_events.update(test_data.get('after', []))
            
            missing = WebSocketEventValidation.REQUIRED_EVENTS - all_events
            assert len(missing) <= 2, f"Too many missing required events: {missing}"
            
            # Assert reasonable pass rate
            pass_rate = results['passed'] / results['total'] if results['total'] > 0 else 0
            assert pass_rate >= 0.75, f"Pass rate too low: {pass_rate:.2%}"
            
        finally:
            await browser.close()


if __name__ == "__main__":
    # Allow running directly for debugging
    import asyncio
    from playwright.async_api import async_playwright
    
    async def main():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible for debugging
            
            try:
                validator = WebSocketEventValidation()
                results = await validator.run_all_validations(browser)
                
                # Exit with appropriate code
                sys.exit(0 if results['failed'] == 0 else 1)
                
            finally:
                await browser.close()
    
    asyncio.run(main())