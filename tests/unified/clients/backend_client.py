"""Test client for backend service with typed methods."""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class BackendTestClient:
    """Typed client for testing backend service endpoints."""
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        """Initialize backend test client.
        
        Args:
            base_url: Base URL of the backend service (e.g., http://localhost:8000)
            token: Optional JWT token for authenticated requests
        """
        self.base_url = base_url
        self.token = token
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        self.client = httpx.AsyncClient(
            base_url=base_url, 
            timeout=10.0,
            headers=headers
        )
        
    async def health_check(self) -> bool:
        """Check backend service health.
        
        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
            
    async def get_chat_history(self, thread_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get chat history for a thread.
        
        Args:
            thread_id: Optional thread ID, uses default if not provided
            
        Returns:
            List of chat messages
        """
        params = {}
        if thread_id:
            params["thread_id"] = thread_id
            
        response = await self.client.get("/api/chat/history", params=params)
        response.raise_for_status()
        return response.json()
        
    async def send_chat_message(self, message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message.
        
        Args:
            message: Message content
            thread_id: Optional thread ID
            
        Returns:
            Chat response
        """
        data = {"message": message}
        if thread_id:
            data["thread_id"] = thread_id
            
        response = await self.client.post("/api/chat/send", json=data)
        response.raise_for_status()
        return response.json()
        
    async def create_thread(self, name: str = "Test Thread") -> Dict[str, Any]:
        """Create a new chat thread.
        
        Args:
            name: Thread name
            
        Returns:
            Thread creation response
        """
        response = await self.client.post(
            "/api/threads/create",
            json={"name": name}
        )
        response.raise_for_status()
        return response.json()
        
    async def get_threads(self) -> List[Dict[str, Any]]:
        """Get all threads for the authenticated user.
        
        Returns:
            List of threads
        """
        response = await self.client.get("/api/threads")
        response.raise_for_status()
        return response.json()
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics.
        
        Returns:
            Metrics data
        """
        response = await self.client.get("/api/metrics")
        response.raise_for_status()
        return response.json()
        
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get agent system status.
        
        Returns:
            Agent status information
        """
        response = await self.client.get("/api/agents/status")
        response.raise_for_status()
        return response.json()
        
    async def execute_agent_task(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an agent task.
        
        Args:
            task_type: Type of agent task
            payload: Task payload
            
        Returns:
            Task execution result
        """
        response = await self.client.post(
            f"/api/agents/execute/{task_type}",
            json=payload
        )
        response.raise_for_status()
        return response.json()
        
    async def get_user_settings(self) -> Dict[str, Any]:
        """Get user settings.
        
        Returns:
            User settings data
        """
        response = await self.client.get("/api/user/settings")
        response.raise_for_status()
        return response.json()
        
    async def update_user_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update user settings.
        
        Args:
            settings: Settings to update
            
        Returns:
            Updated settings
        """
        response = await self.client.put("/api/user/settings", json=settings)
        response.raise_for_status()
        return response.json()
        
    async def get_websocket_info(self) -> Dict[str, Any]:
        """Get WebSocket connection information.
        
        Returns:
            WebSocket connection details
        """
        response = await self.client.get("/api/websocket/info")
        response.raise_for_status()
        return response.json()
        
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        
    def with_token(self, token: str) -> "BackendTestClient":
        """Create a new client with updated token.
        
        Args:
            token: New JWT token
            
        Returns:
            New BackendTestClient instance with token
        """
        return BackendTestClient(self.base_url, token)