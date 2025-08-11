"""
MCP Request Handler

Processes JSON-RPC 2.0 requests and routes them to appropriate handlers.
"""

import json
from typing import Dict, Any, Optional, Union
from datetime import datetime
import traceback

from app.logging_config import CentralLogger
from app.core.exceptions import NetraException

logger = CentralLogger()


class RequestHandler:
    """
    Handles JSON-RPC 2.0 request processing for MCP
    """
    
    def __init__(self, server):
        self.server = server
        
    async def process_request(self, raw_request: Union[str, Dict], session_id: Optional[str] = None) -> Union[str, Dict]:
        """
        Process a raw request (string or dict) and return response
        
        Args:
            raw_request: JSON string or dict representing the request
            session_id: Optional session identifier
            
        Returns:
            JSON string or dict response
        """
        try:
            # Parse request if string
            if isinstance(raw_request, str):
                try:
                    request = json.loads(raw_request)
                    return_as_string = True
                except json.JSONDecodeError as e:
                    error_response = self._parse_error(str(e))
                    return json.dumps(error_response)
            else:
                request = raw_request
                return_as_string = False
                
            # Handle batch requests
            if isinstance(request, list):
                responses = []
                for single_request in request:
                    response = await self._process_single_request(single_request, session_id)
                    if response is not None:  # Notifications don't get responses
                        responses.append(response)
                        
                result = responses if responses else None
            else:
                result = await self._process_single_request(request, session_id)
                
            # Return in same format as received
            if return_as_string and result is not None:
                return json.dumps(result)
            return result
            
        except Exception as e:
            logger.error(f"Error processing MCP request: {e}", exc_info=True)
            error_response = self._internal_error(str(e))
            if isinstance(raw_request, str):
                return json.dumps(error_response)
            return error_response
            
    async def _process_single_request(self, request: Dict, session_id: Optional[str] = None) -> Optional[Dict]:
        """Process a single JSON-RPC request"""
        try:
            # Validate request structure
            if not isinstance(request, dict):
                return self._invalid_request("Request must be an object")
                
            # Check JSON-RPC version
            if request.get("jsonrpc") != "2.0":
                return self._invalid_request("Invalid or missing jsonrpc version")
                
            # Get method
            method = request.get("method")
            if not method or not isinstance(method, str):
                return self._invalid_request("Invalid or missing method")
                
            # Get params (optional)
            params = request.get("params", {})
            if not isinstance(params, (dict, list)):
                return self._invalid_params("Params must be object or array")
                
            # Get id (optional for notifications)
            request_id = request.get("id")
            is_notification = "id" not in request
            
            # Log request
            logger.debug(f"MCP Request: method={method}, session={session_id}, notification={is_notification}")
            
            # Process through server
            response = await self.server.handle_request(request, session_id)
            
            # Don't return response for notifications
            if is_notification:
                return None
                
            return response
            
        except NetraException as e:
            logger.warning(f"Business error in MCP request: {e}")
            return self._error_response(-32000, str(e), request.get("id"))
        except Exception as e:
            logger.error(f"Unexpected error in MCP request: {e}", exc_info=True)
            return self._internal_error(str(e), request.get("id"))
            
    def validate_request(self, request: Dict) -> Optional[Dict]:
        """
        Validate JSON-RPC 2.0 request structure
        
        Returns error response if invalid, None if valid
        """
        # Check required fields
        if "jsonrpc" not in request:
            return self._invalid_request("Missing jsonrpc field")
            
        if request["jsonrpc"] != "2.0":
            return self._invalid_request(f"Invalid jsonrpc version: {request['jsonrpc']}")
            
        if "method" not in request:
            return self._invalid_request("Missing method field")
            
        if not isinstance(request["method"], str):
            return self._invalid_request("Method must be a string")
            
        # Check optional fields
        if "params" in request:
            if not isinstance(request["params"], (dict, list)):
                return self._invalid_params("Params must be object or array")
                
        if "id" in request:
            if not isinstance(request["id"], (str, int, type(None))):
                return self._invalid_request("Invalid id type")
                
        return None
        
    def _parse_error(self, message: str = "Parse error", request_id: Any = None) -> Dict:
        """Create parse error response"""
        return self._error_response(-32700, message, request_id)
        
    def _invalid_request(self, message: str = "Invalid Request", request_id: Any = None) -> Dict:
        """Create invalid request error response"""
        return self._error_response(-32600, message, request_id)
        
    def _method_not_found(self, method: str, request_id: Any = None) -> Dict:
        """Create method not found error response"""
        return self._error_response(-32601, f"Method not found: {method}", request_id)
        
    def _invalid_params(self, message: str = "Invalid params", request_id: Any = None) -> Dict:
        """Create invalid params error response"""
        return self._error_response(-32602, message, request_id)
        
    def _internal_error(self, message: str = "Internal error", request_id: Any = None) -> Dict:
        """Create internal error response"""
        return self._error_response(-32603, message, request_id)
        
    def _error_response(self, code: int, message: str, request_id: Any = None, data: Any = None) -> Dict:
        """Create standard error response"""
        error = {
            "code": code,
            "message": message
        }
        
        if data is not None:
            error["data"] = data
            
        response = {
            "jsonrpc": "2.0",
            "error": error
        }
        
        if request_id is not None:
            response["id"] = request_id
            
        return response