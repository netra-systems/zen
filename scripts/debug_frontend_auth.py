#!/usr/bin/env python3
"""Debug script to check frontend auth behavior"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def debug_frontend_auth():
    """Debug frontend authentication behavior"""
    
    # Setup Chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Clear any existing auth and navigate to protected route
        driver.get("http://localhost:3001")
        driver.execute_script("localStorage.clear();")
        driver.get("http://localhost:3001/chat")
        
        # Wait longer and check multiple times like the test does
        max_wait_time = 10  # seconds
        check_interval = 1  # seconds
        start_time = time.time()
        
        print("Waiting for frontend to load...")
        while time.time() - start_time < max_wait_time:
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            print(f"After {int(time.time() - start_time)}s: {repr(page_text[:100])}")
            
            # Break if we see proper content
            if "sign in" in page_text or "login" in page_text:
                break
                
            time.sleep(check_interval)
        
        # Get current state
        current_url = driver.current_url
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        print(f"Current URL: {current_url}")
        print(f"Page text length: {len(page_text)}")
        print(f"First 500 characters of page text:")
        print(repr(page_text[:500]))
        print()
        
        # Check individual conditions
        redirect_happened = "/login" in current_url or "/auth" in current_url
        print(f"Redirect happened: {redirect_happened}")
        
        # Check for login content
        login_terms = ["login", "sign in", "authenticate", "dev login", "development"]
        found_terms = []
        for term in login_terms:
            if term in page_text:
                found_terms.append(term)
        
        print(f"Found login terms: {found_terms}")
        print(f"Login content shown: {len(found_terms) > 0}")
        
        auth_protection_working = redirect_happened or len(found_terms) > 0
        print(f"Auth protection working: {auth_protection_working}")
        
        return auth_protection_working
        
    finally:
        driver.quit()

if __name__ == "__main__":
    result = debug_frontend_auth()
    print(f"\nFinal result: {result}")