# fast_mcp_consolidated.py
#
# This file contains the complete, consolidated code for the Fast-MCP 2.0 system
# with Netra integration. All modules have been combined into this single file
# for easy portability and execution.

import logging
import sys
import socket
import json
import os
import importlib
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

# ==============================================================================
# Section 1: Logger (from fast_mcp/logger.py)
# ==============================================================================

def setup_logger(name, level='INFO'):
    """
    Sets up a logger with a specified name and level.

    Args:
        name (str): The name of the logger.
        level (str): The logging level (e.g., 'INFO', 'DEBUG').

    Returns:
        logging.Logger: The configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding multiple handlers to the same logger
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# ==============================================================================
# Section 2: Tool Manager (from fast_mcp/tool_manager.py)
# ==============================================================================

class BaseTool(ABC):
    """
    Abstract base class for all tools.
    """

    @property
    @abstractmethod
    def name(self):
        """The name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self):
        """A brief description of what the tool does."""
        pass

    @abstractmethod
    def execute(self, params):
        """
        The main execution logic of the tool.

        Args:
            params (dict): The parameters for the tool.

        Returns:
            dict: The result of the tool's execution.
        """
        pass

class ToolManager:
    """
    Manages the loading and execution of tools.
    """

    def __init__(self):
        """
        Initializes the ToolManager.
        """
        self.tools = {}
        self.logger = setup_logger(__name__, 'INFO')

    def register_tool(self, tool):
        """
        Registers a new tool.

        Args:
            tool (BaseTool): The tool instance to register.
        """
        if not isinstance(tool, BaseTool):
            raise TypeError("Provided tool must be an instance of BaseTool")

        if tool.name in self.tools:
            self.logger.warning(f"Tool '{tool.name}' is being overwritten.")
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name):
        """
        Retrieves a tool by name.

        Args:
            name (str): The name of the tool.

        Returns:
            BaseTool: The tool instance, or None if not found.
        """
        return self.tools.get(name)

# ==============================================================================
# Section 3: Placeholder Services for NetraTool
# These are dummy classes since the full implementation was not provided.
# ==============================================================================

class AnalysisRunner:
    def __init__(self, config):
        pass
    def get_system_recommendations(self, app_id):
        return {"status": "success", "recommendations": f"Recommendations for {app_id}"}

class SupplyCatalogService:
    def __init__(self, config):
        pass

class SecurityService:
    def __init__(self, config):
        pass

# ==============================================================================
# Section 4: Tools (from tools/ and fast_mcp/tools/)
# ==============================================================================

class ExampleTool(BaseTool):
    """
    An example tool that demonstrates the basic structure.
    """
    @property
    def name(self):
        return "example_tool"

    @property
    def description(self):
        return "An example tool that returns a simple message."

    def execute(self, params):
        name = params.get('name', 'World')
        return {'message': f'Hello, {name}!'}

class NetraTool(BaseTool):
    """
    A tool that integrates with the Netra Core Generation 1 services.
    """
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger(__name__, self.config.get('log_level', 'INFO'))
        self.analysis_runner = AnalysisRunner(self.config)
        self.supply_catalog = SupplyCatalogService(self.config)
        self.security_service = SecurityService(self.config)
        self.logger.info("NetraTool initialized.")

    @property
    def name(self):
        return "netra"

    @property
    def description(self):
        return "Interfaces with the Netra Core Generation 1 services."

    def execute(self, params):
        sub_tool = params.get('sub_tool')
        if not sub_tool:
            raise ValueError("Missing 'sub_tool' parameter.")

        if sub_tool == 'getSystemRecommendations':
            return self._get_system_recommendations(params)
        elif sub_tool == 'applySystemRecommendations':
            return self._apply_system_recommendations(params)
        elif sub_tool == 'findModelCalls':
            return self._find_model_calls(params)
        elif sub_tool == 'refactorForMiddleware':
            return self._refactor_for_middleware(params)
        else:
            raise ValueError(f"Unknown sub-tool: {sub_tool}")

    def _get_system_recommendations(self, params):
        app_id = params.get('appId')
        if not app_id:
            raise ValueError("Missing 'appId' parameter.")
        return self.analysis_runner.get_system_recommendations(app_id)

    def _apply_system_recommendations(self, params):
        app_id = params.get('appId')
        if not app_id:
            raise ValueError("Missing 'appId' parameter.")
        return {"status": "success", "message": f"Applied recommendations for {app_id}"}

    def _find_model_calls(self, params):
        code_context = params.get('codeContext')
        if not code_context:
            raise ValueError("Missing 'codeContext' parameter.")
        return {"model_calls": ["openai.chat.completions.create"]}

    def _refactor_for_middleware(self, params):
        code = params.get('code')
        intent = params.get('intent')
        if not code or not intent:
            raise ValueError("Missing 'code' or 'intent' parameter.")
        return {"refactored_code": "refactored code snippet"}

# ==============================================================================
# Section 5: Request Handler (from fast_mcp/request_handler.py)
# ==============================================================================

class RequestHandler:
    """
    Handles individual client requests in a separate thread.
    """
    def __init__(self, client_socket, address, tool_manager, config):
        self.client_socket = client_socket
        self.address = address
        self.tool_manager = tool_manager
        self.config = config
        self.logger = setup_logger(__name__, self.config.get('log_level', 'INFO'))

    def handle_request(self):
        try:
            request_data = self.client_socket.recv(4096).decode('utf-8')
            if not request_data:
                return

            self.logger.info(f"Received request from {self.address}: {request_data}")
            request = json.loads(request_data)

            tool_name = request.get('tool')
            params = request.get('params', {})

            if not tool_name:
                self.send_error("Missing 'tool' in request.")
                return

            tool = self.tool_manager.get_tool(tool_name)
            if not tool:
                self.send_error(f"Tool '{tool_name}' not found.")
                return

            try:
                result = tool.execute(params)
                self.send_response(result)
            except Exception as e:
                self.logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                self.send_error(f"Error executing tool: {e}")

        except json.JSONDecodeError:
            self.logger.error("Invalid JSON received.")
            self.send_error("Invalid JSON format.")
        except Exception as e:
            self.logger.error(f"An error occurred while handling request: {e}", exc_info=True)
            self.send_error("An internal server error occurred.")
        finally:
            self.client_socket.close()
            self.logger.info(f"Connection from {self.address} closed.")

    def send_response(self, data):
        response = json.dumps({'status': 'success', 'data': data})
        self.client_socket.sendall(response.encode('utf-8'))

    def send_error(self, message):
        response = json.dumps({'status': 'error', 'message': message})
        self.client_socket.sendall(response.encode('utf-8'))

# ==============================================================================
# Section 6: Server (from fast_mcp/server.py)
# ==============================================================================

class FastMCPServer:
    """
    The core server class that manages the Fast-MCP application.
    """
    def __init__(self, config):
        self.config = config
        self.host = self.config.get('host', '127.0.0.1')
        self.port = self.config.get('port', 8080)
        self.logger = setup_logger(__name__, self.config.get('log_level', 'INFO'))
        self.tool_manager = ToolManager()
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=self.config.get('max_workers', 10))
        self.server_socket = None
        self.logger.info("FastMCPServer initialized.")

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.is_running = True
        self.logger.info(f"Server started on {self.host}:{self.port}")

        while self.is_running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.logger.info(f"Accepted connection from {addr}")
                handler = RequestHandler(client_socket, addr, self.tool_manager, self.config)
                self.executor.submit(handler.handle_request)
            except OSError:
                if self.is_running:
                    self.logger.error("Error accepting connection.", exc_info=True)
                break
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"An unexpected error occurred in the main server loop: {e}", exc_info=True)

    def stop(self):
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()
        self.executor.shutdown(wait=True)
        self.logger.info("Server has been stopped.")

# ==============================================================================
# Section 7: Main Application (from fast_mcp/main.py and config.py)
# ==============================================================================

def get_config():
    """
    Retrieves the application configuration.
    For this consolidated file, it returns a default dictionary.
    """
    return {
        'host': '127.0.0.1',
        'port': 8080,
        'log_level': 'INFO',
        'max_workers': 10
    }

class MainApp:
    """
    The main application class that orchestrates the Fast-MCP server.
    """
    def __init__(self):
        self.config = get_config()
        self.logger = setup_logger(__name__, self.config.get('log_level', 'INFO'))
        self.server = FastMCPServer(self.config)
        self.logger.info("Fast-MCP 2.0 MainApp initialized.")
        self._register_tools()

    def _register_tools(self):
        """
        Registers all available tools with the server's tool manager.
        """
        self.server.tool_manager.register_tool(ExampleTool())
        self.server.tool_manager.register_tool(NetraTool(self.config))

    def run(self):
        """
        Starts the Fast-MCP server and begins listening for requests.
        """
        self.logger.info("Starting Fast-MCP 2.0 server.")
        try:
            self.server.start()
        except KeyboardInterrupt:
            self.logger.info("Server shutting down.")
            self.server.stop()
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            self.server.stop()

# ==============================================================================
# Section 8: Entry Point
# ==============================================================================

if __name__ == '__main__':
    app = MainApp()
    app.run()
