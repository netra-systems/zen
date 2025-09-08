"""
Factory Interface Contract Specifications and Templates

This module defines the official interface contracts for all factory patterns
in the Netra platform. These contracts serve as the canonical specification
for parameter names, method signatures, and interface compatibility.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Eliminate systematic factory interface drift
- Value Impact: Standardized factory interfaces prevent integration failures
- Revenue Impact: Reduces downtime from parameter mismatch bugs

Key Contracts:
- UserExecutionContextContract: Defines the canonical UserExecutionContext interface
- WebSocketManagerFactoryContract: Defines WebSocket manager factory interface
- SupervisorFactoryContract: Defines supervisor creation interface
- DataAccessFactoryContract: Defines data access factory interface

These contracts are used by the validation framework to ensure implementations
match expected interfaces and prevent parameter naming mismatches.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from shared.lifecycle.contract_validation_framework import (
    ParameterInfo,
    MethodContract,
    InterfaceContract
)


# ============================================================================
# USER EXECUTION CONTEXT CONTRACT - CRITICAL FOR FACTORY COMPATIBILITY
# ============================================================================

def create_user_execution_context_contract() -> InterfaceContract:
    """
    Create the canonical UserExecutionContext interface contract.
    
    This contract defines the OFFICIAL parameter names and signatures that
    ALL factory patterns must use when creating UserExecutionContext instances.
    
    CRITICAL: The websocket parameter MUST be named 'websocket_client_id',
    NOT 'websocket_connection_id'. This prevents the parameter mismatch that
    caused the supervisor factory bug.
    
    Returns:
        InterfaceContract defining the canonical UserExecutionContext interface
    """
    
    # Constructor contract - this is where parameter mismatches occur
    constructor_params = [
        ParameterInfo("user_id", annotation="str", is_required=True, position=0),
        ParameterInfo("thread_id", annotation="str", is_required=True, position=1),
        ParameterInfo("run_id", annotation="str", is_required=True, position=2),
        ParameterInfo("request_id", annotation="str", is_required=False, position=3, 
                     default_value="field(default_factory=lambda: str(uuid.uuid4()))"),
        ParameterInfo("db_session", annotation="Optional[AsyncSession]", is_required=False, position=4,
                     default_value="field(default=None, repr=False, compare=False)"),
        # CRITICAL: This parameter MUST be named 'websocket_client_id'
        ParameterInfo("websocket_client_id", annotation="Optional[str]", is_required=False, position=5,
                     default_value="field(default=None)"),
        ParameterInfo("created_at", annotation="datetime", is_required=False, position=6,
                     default_value="field(default_factory=lambda: datetime.now(timezone.utc))"),
        ParameterInfo("agent_context", annotation="Dict[str, Any]", is_required=False, position=7,
                     default_value="field(default_factory=dict)"),
        ParameterInfo("audit_metadata", annotation="Dict[str, Any]", is_required=False, position=8,
                     default_value="field(default_factory=dict)"),
        ParameterInfo("operation_depth", annotation="int", is_required=False, position=9,
                     default_value="field(default=0)"),
        ParameterInfo("parent_request_id", annotation="Optional[str]", is_required=False, position=10,
                     default_value="field(default=None)"),
    ]
    
    constructor_contract = MethodContract(
        method_name="__init__",
        parameters=constructor_params,
        return_annotation="None",
        docstring="Initialize UserExecutionContext with proper user isolation.",
        is_async=False
    )
    
    # Factory method contracts
    from_request_params = [
        ParameterInfo("user_id", annotation="str", is_required=True, position=0),
        ParameterInfo("thread_id", annotation="str", is_required=True, position=1),
        ParameterInfo("run_id", annotation="str", is_required=True, position=2),
        ParameterInfo("request_id", annotation="Optional[str]", is_required=False, position=3),
        ParameterInfo("db_session", annotation="Optional[AsyncSession]", is_required=False, position=4),
        # CRITICAL: Factory methods must also use consistent parameter names
        ParameterInfo("websocket_client_id", annotation="Optional[str]", is_required=False, position=5),
        ParameterInfo("agent_context", annotation="Optional[Dict[str, Any]]", is_required=False, position=6),
        ParameterInfo("audit_metadata", annotation="Optional[Dict[str, Any]]", is_required=False, position=7),
    ]
    
    from_request_contract = MethodContract(
        method_name="from_request",
        parameters=from_request_params,
        return_annotation="UserExecutionContext",
        docstring="Factory method to create context from request parameters.",
        is_async=False
    )
    
    # Backward compatibility method (supervisor pattern)
    from_request_supervisor_params = [
        ParameterInfo("user_id", annotation="str", is_required=True, position=0),
        ParameterInfo("thread_id", annotation="str", is_required=True, position=1),
        ParameterInfo("run_id", annotation="str", is_required=True, position=2),
        ParameterInfo("request_id", annotation="Optional[str]", is_required=False, position=3),
        ParameterInfo("db_session", annotation="Optional[AsyncSession]", is_required=False, position=4),
        # IMPORTANT: This method accepts websocket_connection_id for backward compatibility
        # but maps it internally to websocket_client_id
        ParameterInfo("websocket_connection_id", annotation="Optional[str]", is_required=False, position=5),
        ParameterInfo("metadata", annotation="Optional[Dict[str, Any]]", is_required=False, position=6),
    ]
    
    from_request_supervisor_contract = MethodContract(
        method_name="from_request_supervisor",
        parameters=from_request_supervisor_params,
        return_annotation="UserExecutionContext",
        docstring="Supervisor-compatible factory method with legacy parameter names.",
        is_async=False
    )
    
    # Property contracts (backward compatibility)
    websocket_connection_id_property = MethodContract(
        method_name="websocket_connection_id",
        parameters=[],  # Property has no parameters
        return_annotation="Optional[str]",
        docstring="Backward compatibility property mapping to websocket_client_id.",
        is_async=False
    )
    
    # Create the complete interface contract
    contract = InterfaceContract(
        interface_name="UserExecutionContext",
        version="2.0",  # Version 2.0 includes backward compatibility
        class_docstring="Comprehensive immutable context for complete request isolation."
    )
    
    contract.methods = [
        constructor_contract,
        from_request_contract, 
        from_request_supervisor_contract,
        websocket_connection_id_property
    ]
    
    return contract


# ============================================================================
# WEBSOCKET MANAGER FACTORY CONTRACT
# ============================================================================

def create_websocket_manager_factory_contract() -> InterfaceContract:
    """
    Create the WebSocketManagerFactory interface contract.
    
    This contract ensures factory methods use consistent parameter names
    for user context creation.
    
    Returns:
        InterfaceContract for WebSocketManagerFactory
    """
    
    # Constructor contract
    constructor_params = [
        ParameterInfo("max_managers_per_user", annotation="int", is_required=False, position=0,
                     default_value="5"),
        ParameterInfo("connection_timeout_seconds", annotation="int", is_required=False, position=1,
                     default_value="1800"),
    ]
    
    constructor_contract = MethodContract(
        method_name="__init__",
        parameters=constructor_params,
        return_annotation="None",
        docstring="Initialize the WebSocket manager factory.",
        is_async=False
    )
    
    # create_manager contract - CRITICAL interface
    create_manager_params = [
        # CRITICAL: Must accept UserExecutionContext with correct interface
        ParameterInfo("user_context", annotation="UserExecutionContext", is_required=True, position=0),
    ]
    
    create_manager_contract = MethodContract(
        method_name="create_manager",
        parameters=create_manager_params,
        return_annotation="IsolatedWebSocketManager",
        docstring="Create an isolated WebSocket manager for a user context.",
        is_async=False
    )
    
    # get_manager contract
    get_manager_params = [
        ParameterInfo("isolation_key", annotation="str", is_required=True, position=0),
    ]
    
    get_manager_contract = MethodContract(
        method_name="get_manager",
        parameters=get_manager_params,
        return_annotation="Optional[IsolatedWebSocketManager]",
        docstring="Get an existing manager by isolation key.",
        is_async=False
    )
    
    # cleanup_manager contract
    cleanup_manager_params = [
        ParameterInfo("isolation_key", annotation="str", is_required=True, position=0),
    ]
    
    cleanup_manager_contract = MethodContract(
        method_name="cleanup_manager",
        parameters=cleanup_manager_params,
        return_annotation="bool",
        docstring="Clean up a specific manager by isolation key.",
        is_async=True
    )
    
    contract = InterfaceContract(
        interface_name="WebSocketManagerFactory",
        version="1.0",
        class_docstring="Factory for creating isolated WebSocket manager instances per user connection."
    )
    
    contract.methods = [
        constructor_contract,
        create_manager_contract,
        get_manager_contract,
        cleanup_manager_contract
    ]
    
    return contract


# ============================================================================
# SUPERVISOR FACTORY CONTRACT
# ============================================================================

def create_supervisor_factory_contract() -> InterfaceContract:
    """
    Create the supervisor factory interface contract.
    
    This contract defines the standard interface for supervisor creation
    that prevents parameter mismatches.
    
    Returns:
        InterfaceContract for supervisor factory functions
    """
    
    # create_supervisor_core contract - the core factory function
    create_supervisor_core_params = [
        ParameterInfo("user_id", annotation="str", is_required=True, position=0),
        ParameterInfo("thread_id", annotation="str", is_required=True, position=1),
        ParameterInfo("run_id", annotation="str", is_required=True, position=2),
        ParameterInfo("db_session", annotation="AsyncSession", is_required=True, position=3),
        # CRITICAL: Must use websocket_client_id, not websocket_connection_id
        ParameterInfo("websocket_client_id", annotation="Optional[str]", is_required=False, position=4),
        ParameterInfo("llm_client", annotation="Optional[ResilientLLMClient]", is_required=False, position=5),
        ParameterInfo("websocket_bridge", annotation="Any", is_required=False, position=6),
        ParameterInfo("tool_dispatcher", annotation="Any", is_required=False, position=7),
        ParameterInfo("tool_classes", annotation="Any", is_required=False, position=8),
    ]
    
    create_supervisor_core_contract = MethodContract(
        method_name="create_supervisor_core",
        parameters=create_supervisor_core_params,
        return_annotation="SupervisorAgent",
        docstring="Core supervisor creation logic - protocol agnostic.",
        is_async=True
    )
    
    # get_websocket_scoped_supervisor contract - WebSocket-specific wrapper
    get_websocket_scoped_supervisor_params = [
        ParameterInfo("context", annotation="WebSocketContext", is_required=True, position=0),
        ParameterInfo("db_session", annotation="AsyncSession", is_required=True, position=1),
        ParameterInfo("app_state", annotation="Any", is_required=False, position=2),
    ]
    
    get_websocket_scoped_supervisor_contract = MethodContract(
        method_name="get_websocket_scoped_supervisor",
        parameters=get_websocket_scoped_supervisor_params,
        return_annotation="SupervisorAgent",
        docstring="Create supervisor specifically for WebSocket connections.",
        is_async=True
    )
    
    contract = InterfaceContract(
        interface_name="SupervisorFactory",
        version="1.0",
        class_docstring="Factory pattern for creating SupervisorAgent instances."
    )
    
    contract.methods = [
        create_supervisor_core_contract,
        get_websocket_scoped_supervisor_contract
    ]
    
    return contract


# ============================================================================
# ISOLATED WEBSOCKET MANAGER CONTRACT
# ============================================================================

def create_isolated_websocket_manager_contract() -> InterfaceContract:
    """
    Create the IsolatedWebSocketManager interface contract.
    
    This contract ensures consistent interface for user-isolated WebSocket managers.
    
    Returns:
        InterfaceContract for IsolatedWebSocketManager
    """
    
    # Constructor contract
    constructor_params = [
        # CRITICAL: Must accept UserExecutionContext with correct interface
        ParameterInfo("user_context", annotation="UserExecutionContext", is_required=True, position=0),
    ]
    
    constructor_contract = MethodContract(
        method_name="__init__",
        parameters=constructor_params,
        return_annotation="None",
        docstring="Initialize isolated WebSocket manager for a specific user.",
        is_async=False
    )
    
    # add_connection contract
    add_connection_params = [
        ParameterInfo("connection", annotation="WebSocketConnection", is_required=True, position=0),
    ]
    
    add_connection_contract = MethodContract(
        method_name="add_connection",
        parameters=add_connection_params,
        return_annotation="None",
        docstring="Add a WebSocket connection to this isolated manager.",
        is_async=True
    )
    
    # send_to_user contract
    send_to_user_params = [
        ParameterInfo("message", annotation="Dict[str, Any]", is_required=True, position=0),
    ]
    
    send_to_user_contract = MethodContract(
        method_name="send_to_user",
        parameters=send_to_user_params,
        return_annotation="None",
        docstring="Send a message to all connections for this user.",
        is_async=True
    )
    
    # is_connection_active contract
    is_connection_active_params = [
        ParameterInfo("user_id", annotation="str", is_required=True, position=0),
    ]
    
    is_connection_active_contract = MethodContract(
        method_name="is_connection_active",
        parameters=is_connection_active_params,
        return_annotation="bool",
        docstring="Check if user has active WebSocket connections.",
        is_async=False
    )
    
    contract = InterfaceContract(
        interface_name="IsolatedWebSocketManager",
        version="1.0",
        class_docstring="User-isolated WebSocket manager with completely private state."
    )
    
    contract.methods = [
        constructor_contract,
        add_connection_contract,
        send_to_user_contract,
        is_connection_active_contract
    ]
    
    return contract


# ============================================================================
# CONTRACT REGISTRY AND FACTORY FUNCTIONS
# ============================================================================

def get_all_factory_contracts() -> Dict[str, InterfaceContract]:
    """
    Get all official factory interface contracts.
    
    This function returns the complete set of interface contracts that
    define the standard interfaces for all factory patterns in the system.
    
    Returns:
        Dictionary mapping interface names to their contracts
    """
    
    contracts = {}
    
    # Core contracts
    contracts["UserExecutionContext"] = create_user_execution_context_contract()
    contracts["WebSocketManagerFactory"] = create_websocket_manager_factory_contract()
    contracts["SupervisorFactory"] = create_supervisor_factory_contract()
    contracts["IsolatedWebSocketManager"] = create_isolated_websocket_manager_contract()
    
    return contracts


def register_factory_contracts_with_validator(validator) -> None:
    """
    Register all factory contracts with a contract validator.
    
    Args:
        validator: ContractValidator instance to register contracts with
    """
    
    contracts = get_all_factory_contracts()
    
    for contract_name, contract in contracts.items():
        validator.register_contract(contract)
    
    print(f"Registered {len(contracts)} factory contracts")


@dataclass
class ContractTemplate:
    """Template for creating new factory interface contracts."""
    
    interface_name: str
    description: str
    required_methods: List[str]
    parameter_naming_rules: Dict[str, str]
    examples: List[str]


def create_factory_contract_template(interface_name: str) -> ContractTemplate:
    """
    Create a template for defining new factory interface contracts.
    
    Args:
        interface_name: Name of the interface to create template for
        
    Returns:
        ContractTemplate with standard factory pattern structure
    """
    
    return ContractTemplate(
        interface_name=interface_name,
        description=f"Interface contract for {interface_name} factory pattern",
        required_methods=[
            "__init__",  # Constructor
            "create_*",  # Factory creation method
            "get_*",     # Retrieval method 
            "cleanup_*"  # Cleanup method
        ],
        parameter_naming_rules={
            "user_context": "Must be UserExecutionContext type",
            "websocket_client_id": "Use client_id, NOT connection_id for WebSocket parameters",
            "db_session": "Must be AsyncSession for database operations",
            "user_id": "String user identifier",
            "thread_id": "String thread identifier",
            "run_id": "String run identifier"
        },
        examples=[
            "def create_manager(self, user_context: UserExecutionContext) -> Manager:",
            "async def cleanup_manager(self, manager_id: str) -> bool:",
            "def get_manager_stats(self) -> Dict[str, Any]:"
        ]
    )


# Export all factory contracts and utilities
__all__ = [
    "create_user_execution_context_contract",
    "create_websocket_manager_factory_contract", 
    "create_supervisor_factory_contract",
    "create_isolated_websocket_manager_contract",
    "get_all_factory_contracts",
    "register_factory_contracts_with_validator",
    "ContractTemplate",
    "create_factory_contract_template"
]