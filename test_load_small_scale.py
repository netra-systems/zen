"""
Small Scale Load Test - 5 users for validation before full 100-user test.
"""

import asyncio
import time
import json
from test_unified_load import UnifiedLoadTester, TestUnifiedLoad

class SmallScaleLoadTester(UnifiedLoadTester):
    """Small scale version for initial validation."""
    
    async def run_small_scale_test(self, num_users=5, messages_per_user=3) -> dict:
        """Run small scale test with configurable parameters."""
        print(f"Starting small scale test: {num_users} users, {messages_per_user} messages each")
        
        self.start_resource_monitoring()
        
        # Create fewer user tasks
        tasks = []
        for i in range(num_users):
            user_id = self.generate_test_user_id()
            session_data = {'user_index': i, 'start_time': time.time()}
            
            # Override messages per user for this test
            original_messages = globals().get('MESSAGES_PER_USER', 10)
            globals()['MESSAGES_PER_USER'] = messages_per_user
            
            task = asyncio.create_task(self.simulate_user_session(user_id, session_data))
            tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Restore original value
        globals()['MESSAGES_PER_USER'] = original_messages
        
        self.stop_resource_monitoring()
        
        # Compile results
        final_results = self._compile_final_results(results)
        final_results['scale'] = 'small'
        final_results['configured_users'] = num_users
        final_results['configured_messages_per_user'] = messages_per_user
        
        return final_results

async def main():
    """Run small scale load test."""
    tester = SmallScaleLoadTester()
    
    # Test with 5 users first
    print("="*60)
    print("SMALL SCALE LOAD TEST - SYSTEM VALIDATION")
    print("="*60)
    
    try:
        results = await tester.run_small_scale_test(num_users=5, messages_per_user=3)
        
        print("\nSmall Scale Test Results:")
        print(f"Users: {results['configured_users']}")
        print(f"Messages per user: {results['configured_messages_per_user']}")
        print(f"Success rate: {results['success_rate']:.1f}%")
        print(f"Average response time: {results['avg_response_time']:.3f}s")
        print(f"P95 response time: {results['p95_response_time']:.3f}s")
        print(f"Total messages: {results['total_messages']}")
        print(f"Connections established: {results['connections_established']}")
        print(f"Errors: {results['errors_total']}")
        
        # Determine if ready for full scale test
        if results['success_rate'] >= 80 and results['p95_response_time'] < 10:
            print("\n[READY] System appears ready for full 100-user load test")
            return True
        else:
            print("\n[NOT READY] System needs optimization before 100-user test")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Small scale test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)