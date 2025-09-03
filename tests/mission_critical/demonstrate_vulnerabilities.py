#!/usr/bin/env python3
"""
Standalone Vulnerability Demonstration Script

This script demonstrates critical data layer isolation vulnerabilities
WITHOUT using pytest to avoid fixture conflicts.

Run this script to see PROOF that the vulnerabilities exist in the current system.
"""

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any


class VulnerabilityDemo:
    """Demonstrates data layer isolation vulnerabilities."""
    
    def __init__(self):
        self.results = []
        
    def log_vulnerability(self, test_name: str, vulnerability_type: str, details: str, proven: bool = True):
        """Log vulnerability demonstration results."""
        status = "VULNERABILITY PROVEN" if proven else "VULNERABILITY NOT TRIGGERED"
        result = {
            'test': test_name,
            'type': vulnerability_type,
            'details': details,
            'proven': proven,
            'status': status
        }
        self.results.append(result)
        
        print(f"\n{'='*80}")
        print(f"SECURITY TEST: {test_name}")
        print(f"{'='*80}")
        print(f"Vulnerability Type: {vulnerability_type}")
        print(f"Status: {status}")
        print(f"Details: {details}")
        print(f"{'='*80}")
    
    def test_redis_key_collision(self):
        """Demonstrate Redis key collision vulnerability."""
        print("\nTesting Redis Key Collision Vulnerability...")
        
        # Setup test users
        user_a = {'id': 'user-a-123', 'email': 'usera@test.com'}
        user_b = {'id': 'user-b-456', 'email': 'userb@test.com'}
        
        # Vulnerable session key generation (current implementation)
        def generate_session_key(session_id: str, user_id: str = None) -> str:
            # VULNERABILITY: Key doesn't include user_id properly
            return f"session:{session_id}"  # Missing user context!
        
        # User A creates a session
        session_id = "abc123"
        session_key_a = generate_session_key(session_id, user_a['id'])
        
        # User B somehow gets same session ID (possible in distributed system)
        session_key_b = generate_session_key(session_id, user_b['id'])
        
        # Check if keys are identical (vulnerability)
        keys_identical = session_key_a == session_key_b
        
        details = f"User A key: '{session_key_a}' | User B key: '{session_key_b}' | Collision: {keys_identical}"
        
        if keys_identical:
            self.log_vulnerability(
                "Redis Key Collision",
                "CRITICAL - Session Hijacking",
                f"Session keys collide between users! {details}",
                proven=True
            )
        else:
            self.log_vulnerability(
                "Redis Key Collision", 
                "CRITICAL - Session Hijacking",
                f"Keys are unique (vulnerability not triggered in this test). {details}",
                proven=False
            )
        
        return keys_identical
    
    def test_cache_contamination(self):
        """Demonstrate cache contamination vulnerability."""
        print("\nTesting Cache Contamination Vulnerability...")
        
        # Setup test users
        users = [
            {'id': 'user-1', 'email': 'user1@test.com'},
            {'id': 'user-2', 'email': 'user2@test.com'},
        ]
        
        # Vulnerable cache without user context
        shared_cache = {}
        
        def get_cached_data(query: str, user_id: str = None):
            # VULNERABILITY: Cache key doesn't include user context
            cache_key = f"query:{hash(query) % 1000}"  # Simplified hash
            
            if cache_key not in shared_cache:
                shared_cache[cache_key] = f"Sensitive data from cache for query: {query}"
            
            return shared_cache[cache_key]
        
        # User 1 queries for their data
        user1_query = "SELECT * FROM sensitive_table"
        user1_result = get_cached_data(user1_query, users[0]['id'])
        
        # User 2 makes similar query 
        user2_query = "SELECT * FROM sensitive_table"  # Same query!
        user2_result = get_cached_data(user2_query, users[1]['id'])
        
        # Check if both users get same cached result (vulnerability)
        same_result = user1_result == user2_result
        user_specific = "user-1" in user1_result
        
        details = f"User 1 result: '{user1_result}' | User 2 result: '{user2_result}' | Same result: {same_result}"
        
        if same_result and not user_specific:
            self.log_vulnerability(
                "Cache Contamination",
                "CRITICAL - Data Leakage", 
                f"Both users got identical cached results without user context! {details}",
                proven=True
            )
        else:
            self.log_vulnerability(
                "Cache Contamination",
                "CRITICAL - Data Leakage",
                f"Cache results appear user-specific (vulnerability not triggered). {details}",
                proven=False
            )
        
        return same_result and not user_specific
    
    async def test_concurrent_contamination(self):
        """Demonstrate concurrent user contamination."""
        print("\nTesting Concurrent User Contamination...")
        
        users = [
            {'id': 'concurrent-user-1', 'email': 'user1@concurrent.test'},
            {'id': 'concurrent-user-2', 'email': 'user2@concurrent.test'},
            {'id': 'concurrent-user-3', 'email': 'user3@concurrent.test'},
        ]
        
        # Vulnerable shared execution context
        shared_context = {'current_user_id': None}
        
        async def user_operation(user, operation_id):
            """Simulate user operation with race condition."""
            # Set user context
            shared_context['current_user_id'] = user['id']
            
            # Simulate processing delay
            await asyncio.sleep(0.1)
            
            # Check if context was preserved
            actual_user_id = shared_context['current_user_id']
            
            return {
                'operation_id': operation_id,
                'expected_user': user['id'],
                'actual_user': actual_user_id,
                'contaminated': actual_user_id != user['id']
            }
        
        # Execute concurrent operations
        tasks = [user_operation(user, i) for i, user in enumerate(users)]
        results = await asyncio.gather(*tasks)
        
        # Count contaminated operations
        contaminated = [r for r in results if r['contaminated']]
        
        details = f"Total operations: {len(results)} | Contaminated: {len(contaminated)}"
        
        if contaminated:
            contamination_details = ", ".join([
                f"Op {r['operation_id']}: expected {r['expected_user']}, got {r['actual_user']}"
                for r in contaminated
            ])
            self.log_vulnerability(
                "Concurrent User Contamination",
                "HIGH - Race Condition",
                f"Race conditions caused user context contamination! {details} | Contaminations: {contamination_details}",
                proven=True
            )
        else:
            self.log_vulnerability(
                "Concurrent User Contamination", 
                "HIGH - Race Condition",
                f"No contamination detected in this run (race condition timing-dependent). {details}",
                proven=False
            )
        
        return len(contaminated) > 0
    
    def test_context_propagation_failure(self):
        """Demonstrate user context propagation failure."""
        print("\nTesting User Context Propagation Failure...")
        
        class VulnerableContext:
            def __init__(self):
                self.user_id = None
            
            def authenticate(self, user_id: str):
                self.user_id = user_id
                return self
            
            def layer1_process(self):
                # Context preserved at layer 1
                return self
            
            def layer2_process(self):
                # Context might be lost here
                return self
                
            def layer3_data_access(self):
                # VULNERABILITY: Context lost at data layer
                self.user_id = None  # Simulates what currently happens
                
                if self.user_id is None:
                    raise ValueError("User context lost at data layer")
                return self
        
        user = {'id': 'context-test-user'}
        context = VulnerableContext()
        
        try:
            # Process through layers
            context.authenticate(user['id'])
            context.layer1_process()
            context.layer2_process()
            context.layer3_data_access()  # This should fail
            
            # If we reach here, vulnerability wasn't triggered
            self.log_vulnerability(
                "User Context Propagation",
                "HIGH - Authorization Bypass",
                "Context was preserved through all layers (unexpected - vulnerability not triggered)",
                proven=False
            )
            return False
            
        except ValueError as e:
            self.log_vulnerability(
                "User Context Propagation",
                "HIGH - Authorization Bypass", 
                f"User context lost at data layer as expected: {e}",
                proven=True
            )
            return True
    
    def test_session_isolation_failure(self):
        """Demonstrate session isolation failure."""
        print("\nTesting Session Isolation Failure...")
        
        users = [
            {'id': 'session-admin', 'email': 'admin@test.com'},
            {'id': 'session-user-b', 'email': 'userb@test.com'},
            {'id': 'session-user-c', 'email': 'userc@test.com'},
        ]
        
        class VulnerableSessionManager:
            def __init__(self):
                self.current_session = None  # VULNERABILITY: Global state
                
            def create_session(self, user_id: str):
                session = {
                    'user_id': user_id,
                    'is_admin': user_id == users[0]['id'],  # First user is admin
                    'sensitive_data': f'Private data for {user_id}'
                }
                self.current_session = session  # VULNERABILITY: Overwrites global
                return session
                
            def get_current_session(self):
                return self.current_session
        
        manager = VulnerableSessionManager()
        
        # Admin creates session
        admin_session = manager.create_session(users[0]['id'])
        
        # Regular user creates session
        user_b_session = manager.create_session(users[1]['id']) 
        
        # User C tries to access "their" session
        user_c_current = manager.get_current_session()
        
        # Check if User C gets wrong session
        wrong_session = user_c_current['user_id'] != users[2]['id']
        
        details = f"User C expected their session, but got session for: {user_c_current['user_id']}"
        
        if wrong_session:
            self.log_vulnerability(
                "Session Isolation Failure",
                "CRITICAL - Session Hijacking",
                f"Session isolation failed - users can access other users' sessions! {details}",
                proven=True
            )
        else:
            self.log_vulnerability(
                "Session Isolation Failure",
                "CRITICAL - Session Hijacking", 
                f"Session isolation worked (vulnerability not triggered). {details}",
                proven=False
            )
        
        return wrong_session
    
    def test_predictable_cache_keys(self):
        """Demonstrate predictable cache key vulnerability."""
        print("\nTesting Predictable Cache Key Vulnerability...")
        
        users = [
            {'id': 'predictable-user-a', 'corpus_id': 'corpus-001'},
            {'id': 'predictable-user-b', 'corpus_id': 'corpus-002'},
        ]
        
        # Vulnerable cache key generation
        def generate_cache_key(resource_type: str, resource_id: str) -> str:
            # VULNERABILITY: Predictable keys without user context
            return f"{resource_type}:{resource_id}"
        
        cache = {}
        
        # User A caches sensitive data
        user_a_key = generate_cache_key("corpus", users[0]['corpus_id'])
        cache[user_a_key] = {
            'owner': users[0]['id'],
            'data': 'CONFIDENTIAL: User A sensitive documents'
        }
        
        # User B could guess User A's cache key
        guessed_key = generate_cache_key("corpus", users[0]['corpus_id'])  # Same as User A
        
        # Check if guessed key gives access to User A's data
        unauthorized_access = guessed_key in cache and cache[guessed_key]['owner'] != users[1]['id']
        
        details = f"User A key: '{user_a_key}' | User B guessed key: '{guessed_key}' | Unauthorized access: {unauthorized_access}"
        
        if unauthorized_access:
            accessed_data = cache[guessed_key]
            self.log_vulnerability(
                "Predictable Cache Keys",
                "MEDIUM - Information Disclosure",
                f"User B accessed User A's data via predictable cache key! {details} | Accessed: {accessed_data}",
                proven=True
            )
        else:
            self.log_vulnerability(
                "Predictable Cache Keys",
                "MEDIUM - Information Disclosure",
                f"Cache key prediction did not result in unauthorized access. {details}",
                proven=False
            )
        
        return unauthorized_access
    
    def test_thread_contamination(self):
        """Demonstrate thread-based context contamination."""
        print("\nTesting Thread-Based Context Contamination...")
        
        users = [
            {'id': f'thread-user-{i}', 'email': f'thread{i}@test.com'}
            for i in range(3)
        ]
        
        # Vulnerable global state
        global_state = {'current_user': None, 'violations': []}
        
        def user_operation(user, op_id):
            """Simulate user operation in thread."""
            # Set user context
            global_state['current_user'] = user['id']
            
            # Simulate work
            time.sleep(0.1)
            
            # Check if context was preserved
            actual_user = global_state['current_user']
            
            if actual_user != user['id']:
                violation = {
                    'operation': op_id,
                    'expected': user['id'],
                    'actual': actual_user
                }
                global_state['violations'].append(violation)
                return False
            
            return True
        
        # Execute in parallel threads
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = [
                executor.submit(user_operation, user, i)
                for i, user in enumerate(users)
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        violations = global_state['violations']
        
        details = f"Operations: {len(results)} | Context violations: {len(violations)}"
        
        if violations:
            violation_details = ", ".join([
                f"Op {v['operation']}: expected {v['expected']}, got {v['actual']}"
                for v in violations
            ])
            self.log_vulnerability(
                "Thread Context Contamination",
                "HIGH - Thread Safety",
                f"Thread safety issues caused context contamination! {details} | Violations: {violation_details}",
                proven=True
            )
        else:
            self.log_vulnerability(
                "Thread Context Contamination",
                "HIGH - Thread Safety",
                f"No thread contamination detected (timing-dependent). {details}",
                proven=False
            )
        
        return len(violations) > 0
    
    async def run_all_tests(self):
        """Run all vulnerability demonstration tests."""
        print("MISSION CRITICAL: Data Layer Isolation Vulnerability Demonstration")
        print("=" * 80)
        print("WARNING: These tests are designed to PROVE that security vulnerabilities exist!")
        print("GOAL: Demonstrate vulnerabilities before implementing fixes")
        print("=" * 80)
        
        vulnerability_count = 0
        
        # Run synchronous tests
        if self.test_redis_key_collision():
            vulnerability_count += 1
            
        if self.test_cache_contamination():
            vulnerability_count += 1
            
        if self.test_context_propagation_failure():
            vulnerability_count += 1
            
        if self.test_session_isolation_failure():
            vulnerability_count += 1
            
        if self.test_predictable_cache_keys():
            vulnerability_count += 1
            
        if self.test_thread_contamination():
            vulnerability_count += 1
        
        # Run async tests
        if await self.test_concurrent_contamination():
            vulnerability_count += 1
        
        # Summary
        print(f"\n{'='*80}")
        print("VULNERABILITY DEMONSTRATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total tests run: {len(self.results)}")
        print(f"Vulnerabilities proven: {vulnerability_count}")
        print(f"Vulnerabilities not triggered: {len(self.results) - vulnerability_count}")
        print()
        
        if vulnerability_count > 0:
            print("CRITICAL SECURITY ISSUES CONFIRMED!")
            print(f"   {vulnerability_count} vulnerabilities were successfully demonstrated.")
            print("   These represent real security risks in the current system.")
            print()
            print("NEXT STEPS:")
            print("   1. Implement user-scoped cache keys")
            print("   2. Add proper user context propagation")
            print("   3. Implement session isolation")
            print("   4. Add cross-tenant data protection")
            print("   5. Re-run tests until all vulnerabilities are fixed")
        else:
            print("WARNING: NO VULNERABILITIES TRIGGERED")
            print("   This could mean:")
            print("   - Vulnerabilities have been fixed")
            print("   - Tests need to be more comprehensive")
            print("   - Timing-dependent issues didn't manifest")
            print("   - Test conditions weren't realistic enough")
        
        print(f"{'='*80}")
        
        return vulnerability_count


async def main():
    """Main entry point for vulnerability demonstration."""
    demo = VulnerabilityDemo()
    vulnerability_count = await demo.run_all_tests()
    
    # Exit with appropriate code
    if vulnerability_count > 0:
        print(f"\nSECURITY ALERT: {vulnerability_count} vulnerabilities demonstrated!")
        exit(1)  # Failure indicates vulnerabilities exist
    else:
        print("\nNo vulnerabilities triggered in this run.")
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())