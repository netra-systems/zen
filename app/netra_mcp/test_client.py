"""
MCP Test Client

Test client for the Netra MCP server using the MCP SDK.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.logging_config import CentralLogger

logger = CentralLogger()


class NetraMCPTestClient:
    """Test client for Netra MCP server"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        
    async def connect_stdio(self, server_script_path: str):
        """Connect to MCP server via stdio transport"""
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()
                logger.info("Connected to MCP server via stdio")
                return session
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        if not self.session:
            raise Exception("Not connected to server")
            
        result = await self.session.list_tools()
        logger.info(f"Available tools: {len(result.tools)}")
        return result
    
    async def list_resources(self) -> Dict[str, Any]:
        """List available resources"""
        if not self.session:
            raise Exception("Not connected to server")
            
        result = await self.session.list_resources()
        logger.info(f"Available resources: {len(result.resources)}")
        return result
    
    async def list_prompts(self) -> Dict[str, Any]:
        """List available prompts"""
        if not self.session:
            raise Exception("Not connected to server")
            
        result = await self.session.list_prompts()
        logger.info(f"Available prompts: {len(result.prompts)}")
        return result
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool"""
        if not self.session:
            raise Exception("Not connected to server")
            
        result = await self.session.call_tool(tool_name, arguments)
        return result
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource"""
        if not self.session:
            raise Exception("Not connected to server")
            
        result = await self.session.read_resource(uri)
        return result
    
    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> Any:
        """Get a prompt"""
        if not self.session:
            raise Exception("Not connected to server")
            
        result = await self.session.get_prompt(prompt_name, arguments)
        return result


async def test_netra_mcp_server():
    """Test the Netra MCP server"""
    client = NetraMCPTestClient()
    
    try:
        # Connect to server
        server_path = "app/mcp/run_server.py"
        session = await client.connect_stdio(server_path)
        
        # Test listing capabilities
        print("\n=== Testing MCP Server Capabilities ===\n")
        
        # List tools
        tools = await client.list_tools()
        print(f"Tools ({len(tools.tools)}):")
        for tool in tools.tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # List resources
        resources = await client.list_resources()
        print(f"\nResources ({len(resources.resources)}):")
        for resource in resources.resources:
            print(f"  - {resource.uri}: {resource.name}")
        
        # List prompts
        prompts = await client.list_prompts()
        print(f"\nPrompts ({len(prompts.prompts)}):")
        for prompt in prompts.prompts:
            print(f"  - {prompt.name}: {prompt.description}")
        
        # Test tool calls
        print("\n=== Testing Tool Calls ===\n")
        
        # Test list_agents
        print("Testing list_agents tool...")
        result = await client.call_tool("list_agents", {})
        print(f"Result: {json.dumps(json.loads(result.content[0].text), indent=2)}")
        
        # Test analyze_workload
        print("\nTesting analyze_workload tool...")
        result = await client.call_tool("analyze_workload", {
            "workload_data": {
                "prompts_per_day": 1000,
                "average_tokens": 500,
                "models_used": ["claude-3-opus", "gpt-4"]
            },
            "metrics": ["cost", "latency"]
        })
        print(f"Result: {result.content[0].text}")
        
        # Test resources
        print("\n=== Testing Resources ===\n")
        
        # Read optimization history
        print("Reading optimization history...")
        result = await client.read_resource("netra://optimization/history")
        print(f"Result: {json.dumps(json.loads(result.contents[0].text), indent=2)}")
        
        # Test prompts
        print("\n=== Testing Prompts ===\n")
        
        # Get optimization request prompt
        print("Getting optimization request prompt...")
        result = await client.get_prompt("optimization_request", {
            "workload_description": "Daily AI chatbot serving 10k users",
            "monthly_budget": 5000.0,
            "quality_requirements": "high"
        })
        print(f"Messages: {json.dumps(result.messages, indent=2)}")
        
        print("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


async def test_direct_server():
    """Test the server directly without stdio"""
    from app.mcp.netra_mcp_server import NetraMCPServer
    
    print("\n=== Testing Direct Server Access ===\n")
    
    # Create server
    server = NetraMCPServer()
    app = server.get_app()
    
    # The FastMCP app provides direct access to tools
    print("Server initialized successfully")
    print(f"Server name: {app.name}")
    print(f"Server version: {app.version}")
    
    # List available tools via the app's tool registry
    print("\nRegistered tools:")
    for tool_name in app._tool_manager.tools:
        print(f"  - {tool_name}")
    
    print("\nRegistered resources:")
    for resource_uri in app._resource_manager.resources:
        print(f"  - {resource_uri}")
    
    print("\nRegistered prompts:")
    for prompt_name in app._prompt_manager.prompts:
        print(f"  - {prompt_name}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        # Test direct server access
        asyncio.run(test_direct_server())
    else:
        # Test via MCP client
        asyncio.run(test_netra_mcp_server())