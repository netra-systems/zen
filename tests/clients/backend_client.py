"""Test client for backend service with typed methods."""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Alias for compatibility
BackendClient = None  # Will be set after class definition


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
    
    async def detailed_health_check(self) -> Dict[str, Any]:
        """Perform detailed health check with diagnostic information.
        
        Returns:
            Dictionary with health status and diagnostic information
        """
        import time
        start_time = time.time()
        
        try:
            response = await self.client.get("/health")
            response_time_ms = (time.time() - start_time) * 1000
            
            return {
                "available": response.status_code == 200,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "url": f"{self.base_url}/health",
                "service_type": "backend",
                "response_data": response.json() if response.status_code == 200 else None,
                "error": None
            }
            
        except httpx.ConnectError as e:
            return {
                "available": False,
                "status_code": None,
                "response_time_ms": (time.time() - start_time) * 1000,
                "url": f"{self.base_url}/health",
                "service_type": "backend",
                "response_data": None,
                "error": f"Connection failed: {str(e)}"
            }
        except httpx.TimeoutException as e:
            return {
                "available": False,
                "status_code": None,
                "response_time_ms": (time.time() - start_time) * 1000,
                "url": f"{self.base_url}/health",
                "service_type": "backend",
                "response_data": None,
                "error": f"Timeout: {str(e)}"
            }
        except Exception as e:
            return {
                "available": False,
                "status_code": None,
                "response_time_ms": (time.time() - start_time) * 1000,
                "url": f"{self.base_url}/health",
                "service_type": "backend", 
                "response_data": None,
                "error": f"Unexpected error: {str(e)}"
            }
            
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
        
    async def get_user_profile(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Get user profile information.
        
        Args:
            token: Optional token override
            
        Returns:
            User profile data
        """
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        response = await self.client.get("/api/user/profile", headers=headers)
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
        
    async def update_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile.
        
        Args:
            profile_data: Profile data to update
            
        Returns:
            Updated profile
        """
        response = await self.client.put("/api/user/profile", json=profile_data)
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
        
    async def check_permission(self, token: str, permission: str) -> bool:
        """Check if user has specific permission.
        
        Args:
            token: JWT token
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        try:
            response = await self.client.get(
                f"/auth/check-permission/{permission}",
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Generic GET request method.
        
        Args:
            url: URL path to request
            params: Optional query parameters
            headers: Optional additional headers
            
        Returns:
            HTTP response
        """
        request_headers = {}
        if headers:
            request_headers.update(headers)
        return await self.client.get(url, params=params, headers=request_headers)
    
    async def post(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Any] = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Generic POST request method.
        
        Args:
            url: URL path to request
            json: Optional JSON payload
            data: Optional form data
            headers: Optional additional headers
            
        Returns:
            HTTP response
        """
        request_headers = {}
        if headers:
            request_headers.update(headers)
        return await self.client.post(url, json=json, data=data, headers=request_headers)
    
    async def put(self, url: str, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Generic PUT request method.
        
        Args:
            url: URL path to request
            json: Optional JSON payload
            headers: Optional additional headers
            
        Returns:
            HTTP response
        """
        request_headers = {}
        if headers:
            request_headers.update(headers)
        return await self.client.put(url, json=json, headers=request_headers)
    
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Generic DELETE request method.
        
        Args:
            url: URL path to request
            headers: Optional additional headers
            
        Returns:
            HTTP response
        """
        request_headers = {}
        if headers:
            request_headers.update(headers)
        return await self.client.delete(url, headers=request_headers)

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


# Create alias for backward compatibility
BackendClient = BackendTestClient