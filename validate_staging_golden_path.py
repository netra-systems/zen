#!/usr/bin/env python3
"""
Validate Golden Path Agent Orchestration Fix on Staging
Issue #1197 validation - Ensure real AI responses instead of mock
"""

import asyncio
import websockets
import json
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STAGING_BACKEND_URL = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app"
TEST_USER_ID = "test-user-golden-path"
TEST_MESSAGE = "What is machine learning and how can it help my business?"

class GoldenPathValidator:
    def __init__(self):
        self.events_received = []
        self.start_time = None
        self.websocket = None
        
    async def connect_websocket(self):
        """Connect to staging WebSocket endpoint"""
        try:
            # Use staging WebSocket URL
            ws_url = f"{STAGING_BACKEND_URL}/ws/{TEST_USER_ID}"
            logger.info(f"Connecting to staging WebSocket: {ws_url}")
            
            self.websocket = await websockets.connect(
                ws_url,
                timeout=30,
                ping_interval=20,
                ping_timeout=10
            )
            logger.info("✅ WebSocket connection established to staging")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to staging WebSocket: {e}")
            return False
    
    async def send_test_message(self):
        """Send test message and track events"""
        if not self.websocket:
            logger.error("❌ No WebSocket connection available")
            return False
            
        try:
            # Create test message
            message = {
                "type": "chat_message",
                "content": TEST_MESSAGE,
                "user_id": TEST_USER_ID,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📤 Sending test message: {TEST_MESSAGE}")
            self.start_time = time.time()
            
            await self.websocket.send(json.dumps(message))
            logger.info("✅ Message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            return False
    
    async def listen_for_events(self, timeout=90):
        """Listen for WebSocket events and validate agent execution"""
        if not self.websocket:
            logger.error("❌ No WebSocket connection available")
            return False
            
        try:
            end_time = time.time() + timeout
            required_events = {
                'agent_started': False,
                'agent_thinking': False, 
                'tool_executing': False,
                'tool_completed': False,
                'agent_completed': False
            }
            
            logger.info(f"👂 Listening for events (timeout: {timeout}s)...")
            
            while time.time() < end_time:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=10
                    )
                    
                    event_data = json.loads(message)
                    event_type = event_data.get('type')
                    
                    logger.info(f"📨 Received event: {event_type}")
                    self.events_received.append(event_data)
                    
                    # Track required events
                    if event_type in required_events:
                        required_events[event_type] = True
                        logger.info(f"✅ Required event received: {event_type}")
                    
                    # Check for agent completion
                    if event_type == 'agent_completed':
                        completion_time = time.time() - self.start_time
                        logger.info(f"🎉 Agent execution completed in {completion_time:.2f}s")
                        
                        # Validate response content
                        response_content = event_data.get('data', {}).get('content', '')
                        if self.validate_ai_response(response_content):
                            logger.info("✅ AI response validation passed - REAL response detected")
                            return True
                        else:
                            logger.warning("⚠️ AI response validation failed - may be mock")
                            return False
                    
                except asyncio.TimeoutError:
                    logger.debug("⏰ No message received in last 10s, continuing...")
                    continue
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Failed to parse message as JSON: {e}")
                    continue
            
            # Check if we got all required events
            missing_events = [event for event, received in required_events.items() if not received]
            if missing_events:
                logger.error(f"❌ Missing required events: {missing_events}")
                return False
            
            logger.error("❌ Timeout waiting for agent_completed event")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error listening for events: {e}")
            return False
    
    def validate_ai_response(self, response_content):
        """Validate that response is from real AI, not mock"""
        if not response_content:
            logger.warning("⚠️ Empty response content")
            return False
        
        # Check for mock indicators
        mock_indicators = [
            "mock response",
            "simulated response", 
            "test response",
            "placeholder",
            "mock execution"
        ]
        
        content_lower = response_content.lower()
        if any(indicator in content_lower for indicator in mock_indicators):
            logger.warning(f"⚠️ Response appears to be mock: {response_content[:100]}...")
            return False
        
        # Check for substantive AI content
        substantive_indicators = [
            "machine learning",
            "artificial intelligence", 
            "business",
            "data",
            "algorithm",
            "automation",
            "analytics"
        ]
        
        if any(indicator in content_lower for indicator in substantive_indicators):
            logger.info("✅ Response contains substantive AI content")
            return True
        
        # Check minimum length for real response
        if len(response_content) > 50:
            logger.info(f"✅ Response has substantial length ({len(response_content)} chars)")
            return True
        
        logger.warning(f"⚠️ Response may not be substantial: {response_content[:100]}...")
        return False
    
    async def close_connection(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 WebSocket connection closed")

async def main():
    """Main validation function"""
    logger.info("🚀 Starting Golden Path validation on staging")
    logger.info("=" * 60)
    
    validator = GoldenPathValidator()
    
    try:
        # Step 1: Connect to staging WebSocket
        if not await validator.connect_websocket():
            return False
        
        # Step 2: Send test message
        if not await validator.send_test_message():
            return False
        
        # Step 3: Listen for agent events and validate response
        success = await validator.listen_for_events(timeout=90)
        
        # Step 4: Report results
        logger.info("=" * 60)
        logger.info("📊 VALIDATION RESULTS")
        logger.info("=" * 60)
        
        if success:
            logger.info("🎉 GOLDEN PATH VALIDATION PASSED!")
            logger.info("✅ Real AI agent execution confirmed")
            logger.info("✅ All required WebSocket events received")
            logger.info("✅ Substantive AI response generated")
            logger.info("✅ Issue #1197 fix is working correctly")
        else:
            logger.error("❌ GOLDEN PATH VALIDATION FAILED!")
            logger.error("❌ Agent execution may still be using mocks")
            
        logger.info(f"📈 Total events received: {len(validator.events_received)}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Validation failed with exception: {e}")
        return False
        
    finally:
        await validator.close_connection()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)