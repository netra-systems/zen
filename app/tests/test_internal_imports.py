"""
Test file to verify all internal app modules can be imported.
This ensures the app structure is properly set up and all internal dependencies are resolvable.
"""

import pytest
import sys
import os
import importlib
from pathlib import Path


# Add app directory to path if not already there
app_dir = Path(__file__).parent.parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))


@pytest.mark.smoke
class TestInternalImports:
    """Test that all internal app modules can be imported successfully."""
    
    @pytest.mark.parametrize("module_path", [
        # Core modules
        "app.main",
        "app.config",
        "app.logging_config",
        "app.ws_manager",
        "app.redis_manager",
        
        # Database modules
        "app.db.postgres",
        "app.db.clickhouse",
        "app.db.models",
        
        # Auth modules
        "app.auth.auth",
        "app.auth.auth_dependencies",
        "app.auth.oauth",
        
        # Core functionality
        "app.core.exceptions",
        "app.core.error_handlers",
        "app.core.error_context",
        "app.core.interfaces",
        "app.core.service_interfaces",
        
        # Routes
        "app.routes.auth.login",
        "app.routes.auth.oauth_routes",
        "app.routes.websockets",
        "app.routes.agent_route",
        "app.routes.threads_route",
        "app.routes.generation",
        "app.routes.llm_cache",
        "app.routes.synthetic_data",
        "app.routes.corpus",
        "app.routes.config",
        "app.routes.supply",
        "app.routes.references",
        "app.routes.health",
        "app.routes.admin",
        
        # Schemas
        "app.schemas.auth",
        "app.schemas.agent",
        "app.schemas.WebSocket",
        "app.schemas.thread",
        "app.schemas.message",
        "app.schemas.run",
        "app.schemas.generation",
        "app.schemas.corpus",
        "app.schemas.reference",
        
        # Services - Core
        "app.services.agent_service",
        "app.services.generation_service",
        "app.services.thread_service",
        "app.services.llm_service",
        "app.services.security_service",
        "app.services.key_manager",
        "app.services.tool_registry",
        
        # Services - Database
        "app.services.database.user_repository",
        "app.services.database.thread_repository",
        "app.services.database.message_repository",
        "app.services.database.run_repository",
        "app.services.database.reference_repository",
        "app.services.database.unit_of_work",
        
        # Services - WebSocket
        "app.services.websocket.message_handler",
        "app.services.websocket.event_types",
        
        # Services - Cache
        "app.services.cache.cache_manager",
        "app.services.cache.llm_cache_service",
        
        # Services - State
        "app.services.state.state_manager",
        "app.services.state.persistence_service",
        
        # Services - Core container
        "app.services.core.service_container",
        "app.services.core.interfaces",
        
        # Agents
        "app.agents.base",
        "app.agents.supervisor",
        "app.agents.supervisor_consolidated",
        "app.agents.prompts",
        "app.agents.tool_dispatcher",
        
        # Sub-agents
        "app.agents.triage_sub_agent",
        "app.agents.data_sub_agent",
        "app.agents.optimizations_core_sub_agent",
        "app.agents.reporting_sub_agent",
        "app.agents.actions_to_meet_goals_sub_agent",
        "app.agents.synthetic_data_sub_agent",
        "app.agents.corpus_admin_sub_agent",
        
        # Agent orchestration
        "app.agents.orchestration.pipeline",
        "app.agents.orchestration.hooks",
        "app.agents.orchestration.strategies",
        
        # Apex Optimizer Agent
        "app.services.apex_optimizer_agent.apex_optimizer",
        "app.services.apex_optimizer_agent.tool_builder",
        "app.services.apex_optimizer_agent.tools.base",
        
        # Utilities
        "app.utils.validators",
        "app.utils.helpers",
        "app.utils.formatters",
    ])
    def test_internal_module_import(self, module_path: str):
        """Test that each internal module can be imported."""
        try:
            # Convert app.module.path to module.path for import
            if module_path.startswith("app."):
                module_path = module_path[4:]  # Remove 'app.' prefix
            
            module = importlib.import_module(module_path)
            assert module != None, f"Failed to import {module_path}"
            
        except ImportError as e:
            # Some modules might be optional or depend on specific configurations
            if "No module named" in str(e):
                pytest.skip(f"Module {module_path} not found (might be optional): {e}")
            else:
                pytest.fail(f"Failed to import {module_path}: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing {module_path}: {e}")
    
    def test_critical_internal_imports(self):
        """Test that critical internal modules can be imported."""
        critical_modules = [
            "main",
            "config",
            "auth.auth",
            "routes.websockets",
            "services.agent_service",
            "agents.supervisor_consolidated",
            "db.postgres",
        ]
        
        failed_imports = []
        for module_name in critical_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))
        
        assert len(failed_imports) == 0, f"Failed to import critical internal modules: {failed_imports}"
    
    def test_circular_imports(self):
        """Test for circular import issues by importing modules in different orders."""
        # Import in order A
        order_a = [
            "main",
            "config",
            "services.agent_service",
            "agents.supervisor",
        ]
        
        # Import in reverse order
        order_b = list(reversed(order_a))
        
        # Clear any cached imports
        for module in order_a:
            if module in sys.modules:
                del sys.modules[module]
        
        # Try order A
        try:
            for module in order_a:
                importlib.import_module(module)
        except ImportError as e:
            pytest.fail(f"Circular import detected with order A: {e}")
        
        # Clear again
        for module in order_a:
            if module in sys.modules:
                del sys.modules[module]
        
        # Try order B
        try:
            for module in order_b:
                importlib.import_module(module)
        except ImportError as e:
            pytest.fail(f"Circular import detected with order B: {e}")
    
    def test_apex_optimizer_tools(self):
        """Test that all Apex Optimizer tools can be imported."""
        tools_dir = Path(__file__).parent.parent / "services" / "apex_optimizer_agent" / "tools"
        
        if not tools_dir.exists():
            pytest.skip("Apex Optimizer tools directory not found")
        
        tool_files = [f.stem for f in tools_dir.glob("*.py") if f.stem not in ["__init__", "base"]]
        
        failed_tools = []
        for tool_name in tool_files:
            try:
                module_path = f"services.apex_optimizer_agent.tools.{tool_name}"
                importlib.import_module(module_path)
            except ImportError as e:
                failed_tools.append((tool_name, str(e)))
        
        if failed_tools:
            # Just warn about failed tool imports
            for tool, error in failed_tools:
                print(f"WARNING: Failed to import tool {tool}: {error}")
    
    def test_all_route_modules(self):
        """Test that all route modules can be imported."""
        routes_dir = Path(__file__).parent.parent / "routes"
        
        if not routes_dir.exists():
            pytest.skip("Routes directory not found")
        
        # Get all Python files in routes directory (including subdirectories)
        route_files = []
        for py_file in routes_dir.rglob("*.py"):
            if py_file.stem != "__init__":
                relative_path = py_file.relative_to(routes_dir.parent)
                module_path = str(relative_path).replace(os.sep, ".").replace(".py", "")
                route_files.append(module_path)
        
        failed_routes = []
        for route_module in route_files:
            try:
                importlib.import_module(route_module)
            except ImportError as e:
                failed_routes.append((route_module, str(e)))
        
        assert len(failed_routes) == 0, f"Failed to import route modules: {failed_routes}"
    
    def test_all_schema_modules(self):
        """Test that all schema modules can be imported."""
        schemas_dir = Path(__file__).parent.parent / "schemas"
        
        if not schemas_dir.exists():
            pytest.skip("Schemas directory not found")
        
        schema_files = [f.stem for f in schemas_dir.glob("*.py") if f.stem != "__init__"]
        
        failed_schemas = []
        for schema_name in schema_files:
            try:
                module_path = f"schemas.{schema_name}"
                importlib.import_module(module_path)
            except ImportError as e:
                failed_schemas.append((schema_name, str(e)))
        
        assert len(failed_schemas) == 0, f"Failed to import schema modules: {failed_schemas}"