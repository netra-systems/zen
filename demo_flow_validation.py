#!/usr/bin/env python3
"""
Demo Flow End-to-End Validation Script

This script validates the complete demo WebSocket flow from connection to AI response.
"""

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any

import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException


class DemoFlowValidator:
    """Validates the complete demo flow end-to-end"""
    
    def __init__(self, websocket_url: str = "ws://localhost:8000/api/demo/ws"):
        self.websocket_url = websocket_url
        self.events_received = []
        self.connection = None
        self.test_results = {}
        
    async def connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            print(f"🔗 Connecting to {self.websocket_url}...")
            self.connection = await websockets.connect(self.websocket_url, open_timeout=10)
            print("✅ WebSocket connection established")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def receive_events(self, timeout: float = 30.0) -> List[Dict]:
        """Receive WebSocket events with timeout"""
        events = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    # Wait for message with short timeout for periodic checks
                    message = await asyncio.wait_for(self.connection.recv(), timeout=2.0)
                    event = json.loads(message)
                    events.append(event)
                    print(f"📨 Received: {event.get('type', 'unknown')} - {event.get('message', '')[:100]}")
                    
                    # Stop on agent_completed or error
                    if event.get('type') in ['agent_completed', 'agent_error', 'error']:
                        break
                        
                except asyncio.TimeoutError:
                    continue  # Continue waiting for more events
                    
        except ConnectionClosedError:
            print("🔌 Connection closed while receiving events")
        except Exception as e:
            print(f"❌ Error receiving events: {e}")
            
        return events
    
    async def send_message(self, message: str) -> bool:
        """Send a chat message"""
        try:
            payload = {
                "type": "chat",
                "message": message
            }
            await self.connection.send(json.dumps(payload))
            print(f"📤 Sent message: {message[:100]}")
            return True
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False
    
    def validate_event_sequence(self, events: List[Dict]) -> Dict[str, Any]:
        """Validate the sequence and content of WebSocket events"""
        validation_result = {
            "required_events_present": {},
            "event_sequence_correct": False,
            "unique_content": False,
            "total_events": len(events),
            "errors": []
        }
        
        # Required events in expected order
        required_events = [
            "connection_established",
            "agent_started", 
            "agent_thinking",
            "tool_executing",
            "tool_completed", 
            "agent_completed"
        ]
        
        # Check if all required events are present
        event_types = [event.get('type') for event in events]
        for required_event in required_events:
            validation_result["required_events_present"][required_event] = required_event in event_types
        
        # Check sequence (some flexibility allowed)
        key_events = ["agent_started", "agent_thinking", "agent_completed"]
        key_event_indices = []
        for key_event in key_events:
            for i, event in enumerate(events):
                if event.get('type') == key_event:
                    key_event_indices.append(i)
                    break
        
        # Events should be in ascending order (with flexibility for interleaving)
        if len(key_event_indices) == len(key_events):
            validation_result["event_sequence_correct"] = all(
                key_event_indices[i] < key_event_indices[i+1] 
                for i in range(len(key_event_indices)-1)
            )
        
        # Check for unique content (not generic/canned responses)
        for event in events:
            if event.get('type') == 'agent_completed':
                message = event.get('message', '')
                # Look for signs of real AI processing (detailed responses, specifics, etc.)
                if len(message) > 200 and any(keyword in message.lower() for keyword in [
                    'optimization', 'analysis', 'recommendation', 'strategy', '$', '%', 'cost'
                ]):
                    validation_result["unique_content"] = True
                    break
        
        return validation_result
    
    async def test_scenario(self, scenario_name: str, test_message: str) -> Dict[str, Any]:
        """Test a specific scenario"""
        print(f"\n🧪 Testing Scenario: {scenario_name}")
        print(f"📝 Message: {test_message}")
        
        # Send message
        if not await self.send_message(test_message):
            return {"success": False, "error": "Failed to send message"}
        
        # Receive events
        events = await self.receive_events(timeout=45.0)  # Extended timeout for real AI processing
        
        # Validate results
        validation = self.validate_event_sequence(events)
        
        result = {
            "success": len(events) > 0,
            "scenario": scenario_name,
            "message": test_message,
            "events_received": len(events),
            "validation": validation,
            "events": events
        }
        
        return result
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of demo flow"""
        print("🚀 Starting Comprehensive Demo Flow Validation")
        print("=" * 60)
        
        # Test scenarios with different contexts to ensure unique responses
        test_scenarios = [
            ("Basic AI Query", "How can AI help optimize my business operations?"),
            ("Healthcare Focus", "I'm running a healthcare startup. How can AI reduce our operational costs?"),
            ("Finance Focus", "Our financial services company needs to optimize our trading algorithms. What AI solutions do you recommend?"),
            ("Manufacturing Query", "We manufacture consumer electronics. How can AI optimize our supply chain and reduce waste?"),
        ]
        
        results = {
            "overall_success": True,
            "scenarios_tested": len(test_scenarios),
            "scenarios_passed": 0,
            "connection_success": False,
            "scenario_results": [],
            "summary": {}
        }
        
        # Establish connection
        if not await self.connect():
            results["overall_success"] = False
            results["connection_success"] = False
            return results
        
        results["connection_success"] = True
        
        # Wait for initial connection message
        try:
            initial_events = await self.receive_events(timeout=5.0)
            print(f"📨 Received {len(initial_events)} initial events")
        except Exception as e:
            print(f"⚠️ Initial events error: {e}")
        
        # Test each scenario
        for scenario_name, test_message in test_scenarios:
            try:
                result = await self.test_scenario(scenario_name, test_message)
                results["scenario_results"].append(result)
                
                if result.get("success") and result.get("validation", {}).get("required_events_present", {}).get("agent_completed", False):
                    results["scenarios_passed"] += 1
                    print(f"✅ {scenario_name}: PASSED")
                else:
                    print(f"❌ {scenario_name}: FAILED")
                    results["overall_success"] = False
                
                # Wait between scenarios to avoid overwhelming the system
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ {scenario_name}: EXCEPTION - {e}")
                results["overall_success"] = False
                results["scenario_results"].append({
                    "success": False,
                    "scenario": scenario_name,
                    "error": str(e)
                })
        
        # Close connection
        if self.connection:
            await self.connection.close()
            print("🔌 Connection closed")
        
        # Generate summary
        results["summary"] = {
            "connection_established": results["connection_success"],
            "scenarios_passed": f"{results['scenarios_passed']}/{results['scenarios_tested']}",
            "overall_success": results["overall_success"]
        }
        
        return results
    
    def print_detailed_results(self, results: Dict[str, Any]):
        """Print detailed validation results"""
        print("\n" + "="*80)
        print("📊 DEMO FLOW VALIDATION RESULTS")
        print("="*80)
        
        print(f"🔗 Connection Success: {'✅' if results['connection_success'] else '❌'}")
        print(f"📈 Scenarios Passed: {results['scenarios_passed']}/{results['scenarios_tested']}")
        print(f"🎯 Overall Success: {'✅' if results['overall_success'] else '❌'}")
        
        print("\n📋 SCENARIO DETAILS:")
        print("-" * 40)
        
        for i, result in enumerate(results.get("scenario_results", []), 1):
            scenario = result.get("scenario", f"Scenario {i}")
            success = "✅" if result.get("success") else "❌"
            events_count = result.get("events_received", 0)
            
            print(f"\n{i}. {scenario} {success}")
            print(f"   Events Received: {events_count}")
            
            validation = result.get("validation", {})
            if validation:
                required_events = validation.get("required_events_present", {})
                print(f"   Required Events: {sum(required_events.values())}/{len(required_events)}")
                print(f"   Event Sequence: {'✅' if validation.get('event_sequence_correct') else '❌'}")
                print(f"   Unique Content: {'✅' if validation.get('unique_content') else '❌'}")
            
            if "error" in result:
                print(f"   Error: {result['error']}")
        
        print("\n" + "="*80)
        if results["overall_success"]:
            print("🎉 DEMO FLOW VALIDATION: SUCCESSFUL")
            print("✅ The demo is ready for production use!")
        else:
            print("⚠️ DEMO FLOW VALIDATION: ISSUES DETECTED")
            print("❌ Please review the issues above before going live.")
        print("="*80)


async def main():
    """Main validation function"""
    print("🚀 Demo Flow End-to-End Validation")
    print("🎯 Validating complete user journey from connection to AI response")
    print("")
    
    # Check if backend is running
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/demo/health") as response:
                if response.status == 200:
                    print("✅ Demo backend is running")
                else:
                    print("❌ Demo backend returned unexpected status:", response.status)
                    return
    except Exception as e:
        print(f"❌ Cannot reach demo backend: {e}")
        print("💡 Make sure the backend is running with: python -m uvicorn netra_backend.app.main:app --host 0.0.0.0 --port 8000")
        return
    
    # Run validation
    validator = DemoFlowValidator()
    results = await validator.run_comprehensive_validation()
    validator.print_detailed_results(results)
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_success"] else 1)


if __name__ == "__main__":
    asyncio.run(main())