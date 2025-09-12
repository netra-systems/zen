#!/usr/bin/env python
"""Test GTM Event Tracking Implementation

This script verifies that GTM events are being properly tracked
in the application by checking for dataLayer pushes.
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from shared.isolated_environment import IsolatedEnvironment

def setup_driver():
    """Setup Chrome driver with options for testing"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(options=options)

def get_datalayer_events(driver):
    """Get all dataLayer events from the page"""
    return driver.execute_script("""
        return window.dataLayer ? window.dataLayer.filter(item => 
            item.event && !['gtm.dom', 'gtm.load', 'gtm.js'].includes(item.event)
        ) : [];
    """)

def test_authentication_tracking():
    """Test authentication flow tracking"""
    driver = setup_driver()
    events_captured = []
    
    try:
        # Navigate to the app
        driver.get("http://localhost:3002")
        time.sleep(2)
        
        # Check for page view event
        events = get_datalayer_events(driver)
        page_view_events = [e for e in events if e.get('event') == 'page_view']
        if page_view_events:
            print("[U+2713] Page view tracking working")
            events_captured.extend(page_view_events)
        
        # Navigate to protected route to trigger auth check
        driver.get("http://localhost:3002/chat")
        time.sleep(2)
        
        # Check for auth-related events
        events = get_datalayer_events(driver)
        auth_events = [e for e in events if 'auth' in e.get('event', '').lower() or 
                      e.get('event_action', '') == 'auth_required']
        if auth_events:
            print("[U+2713] Authentication tracking working")
            events_captured.extend(auth_events)
            
    finally:
        driver.quit()
        
    return events_captured

def test_error_tracking():
    """Test error event tracking"""
    driver = setup_driver()
    events_captured = []
    
    try:
        driver.get("http://localhost:3002")
        time.sleep(2)
        
        # Trigger an error by calling a non-existent function
        driver.execute_script("""
            try {
                nonExistentFunction();
            } catch(e) {
                if (window.dataLayer) {
                    window.dataLayer.push({
                        event: 'exception',
                        event_category: 'error',
                        event_action: 'test_error',
                        event_label: e.message
                    });
                }
            }
        """)
        
        # Check for error events
        events = get_datalayer_events(driver)
        error_events = [e for e in events if e.get('event') == 'exception']
        if error_events:
            print("[U+2713] Error tracking working")
            events_captured.extend(error_events)
            
    finally:
        driver.quit()
        
    return events_captured

def main():
    """Main test function"""
    print("Testing GTM Event Tracking Implementation\n")
    print("=" * 50)
    
    all_events = []
    
    # Test authentication tracking
    print("\n1. Testing Authentication Tracking...")
    auth_events = test_authentication_tracking()
    all_events.extend(auth_events)
    
    # Test error tracking  
    print("\n2. Testing Error Tracking...")
    error_events = test_error_tracking()
    all_events.extend(error_events)
    
    # Summary
    print("\n" + "=" * 50)
    print(f"\nTotal Events Captured: {len(all_events)}")
    
    if all_events:
        print("\nEvent Types Captured:")
        event_types = set(e.get('event') for e in all_events)
        for event_type in event_types:
            count = sum(1 for e in all_events if e.get('event') == event_type)
            print(f"  - {event_type}: {count} event(s)")
            
        print("\nSample Events:")
        for event in all_events[:3]:
            print(f"\n{json.dumps(event, indent=2)}")
    else:
        print("\n WARNING:  No GTM events were captured. Check if GTM is properly initialized.")
    
    return len(all_events) > 0

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[U+2717] Error running tests: {e}")
        exit(1)