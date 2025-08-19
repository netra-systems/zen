"""Agent conversation test helpers for unified e2e testing."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime

@dataclass
class AgentConversationHelpers:
    """Helper class for agent conversation testing."""
    
    @staticmethod
    async def create_conversation_context(
        user_id: str,
        thread_id: str,
        agent_type: str = "assistant"
    ) -> Dict[str, Any]:
        """Create a conversation context for testing."""
        return {
            "user_id": user_id,
            "thread_id": thread_id,
            "agent_type": agent_type,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "context": {}
        }
    
    @staticmethod
    async def simulate_agent_execution(
        context: Dict[str, Any],
        message: str,
        delay: float = 0.1
    ) -> Dict[str, Any]:
        """Simulate agent execution with a message."""
        await asyncio.sleep(delay)
        
        response = {
            "run_id": f"run_{datetime.now().timestamp()}",
            "agent_name": context.get("agent_type", "assistant"),
            "message": message,
            "response": f"Processing: {message}",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to conversation history
        if "messages" in context:
            context["messages"].append({
                "role": "user",
                "content": message
            })
            context["messages"].append({
                "role": "assistant", 
                "content": response["response"]
            })
        
        return response
    
    @staticmethod
    def validate_conversation_state(
        context: Dict[str, Any],
        expected_messages: int = 0
    ) -> bool:
        """Validate the conversation state."""
        if "messages" not in context:
            return False
        
        if expected_messages > 0:
            return len(context["messages"]) >= expected_messages
        
        return True
    
    @staticmethod
    async def cleanup_conversation(context: Dict[str, Any]) -> None:
        """Clean up conversation resources."""
        context["messages"] = []
        context["context"] = {}
        await asyncio.sleep(0.01)  # Small delay for cleanup