#!/usr/bin/env python3
"""Test script to verify demo chat with real agents."""

import asyncio
import json
from netra_backend.app.services.demo.demo_service import DemoService

async def test_demo_chat():
    """Test the demo chat with real agent invocation."""
    print("Initializing Demo Service...")
    demo_service = DemoService()
    
    # Test message
    test_message = "How can I optimize my AI costs for a healthcare application?"
    industry = "healthcare"
    session_id = "test-session-123"
    
    print(f"\nSending test message: {test_message}")
    print(f"Industry: {industry}")
    print(f"Session ID: {session_id}\n")
    
    try:
        # Process the message
        result = await demo_service.process_demo_chat(
            message=test_message,
            industry=industry,
            session_id=session_id,
            user_id=1
        )
        
        print("✅ Demo chat processed successfully!\n")
        print(f"Agents involved: {', '.join(result['agents'])}")
        print(f"\nResponse (first 500 chars):\n{result['response'][:500]}...")
        print(f"\nMetrics: {json.dumps(result['metrics'], indent=2)}")
        
    except Exception as e:
        print(f"❌ Error processing demo chat: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_demo_chat())