"""
MCP Resource Manager

Manages resource registration, discovery, and access.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from app.logging_config import CentralLogger
from app.core.exceptions import NetraException

logger = CentralLogger()


class Resource(BaseModel):
    """Represents an MCP resource"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: str = "application/json"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    requires_auth: bool = True
    permissions: List[str] = Field(default_factory=list)


class ResourceAccess(BaseModel):
    """Records resource access details"""
    resource_uri: str
    session_id: Optional[str]
    access_type: str = "read"  # read, write, delete
    success: bool = True
    error: Optional[str] = None
    accessed_at: datetime = Field(default_factory=datetime.utcnow)


class ResourceManager:
    """
    Manager for MCP resources
    
    Provides access to Netra platform resources like threads, agents,
    corpus data, metrics, etc.
    """
    
    def __init__(self):
        self.resources: Dict[str, Resource] = {}
        self.access_log: List[ResourceAccess] = []
        self._initialize_builtin_resources()
        
    def _initialize_builtin_resources(self):
        """Initialize built-in Netra resources"""
        # Thread resources
        self.register_resource(Resource(
            uri="netra://threads",
            name="Conversation Threads",
            description="Access to conversation threads",
            mimeType="application/json"
        ))
        
        self.register_resource(Resource(
            uri="netra://threads/{thread_id}",
            name="Thread Details",
            description="Access to specific thread details and messages",
            mimeType="application/json"
        ))
        
        # Agent resources
        self.register_resource(Resource(
            uri="netra://agents",
            name="Agent Configurations",
            description="Available agent configurations and capabilities",
            mimeType="application/json"
        ))
        
        self.register_resource(Resource(
            uri="netra://agents/{agent_name}/state",
            name="Agent State",
            description="Current state of a specific agent",
            mimeType="application/json"
        ))
        
        # Corpus resources
        self.register_resource(Resource(
            uri="netra://corpus",
            name="Document Corpus",
            description="Access to document corpus and embeddings",
            mimeType="application/json"
        ))
        
        self.register_resource(Resource(
            uri="netra://corpus/search",
            name="Corpus Search",
            description="Search interface for document corpus",
            mimeType="application/json"
        ))
        
        # Metrics resources
        self.register_resource(Resource(
            uri="netra://metrics/workload",
            name="Workload Metrics",
            description="AI workload performance metrics",
            mimeType="application/json"
        ))
        
        self.register_resource(Resource(
            uri="netra://metrics/optimization",
            name="Optimization Metrics",
            description="Optimization results and recommendations",
            mimeType="application/json"
        ))
        
        # Synthetic data resources
        self.register_resource(Resource(
            uri="netra://synthetic-data/schemas",
            name="Synthetic Data Schemas",
            description="Available schemas for synthetic data generation",
            mimeType="application/json"
        ))
        
        self.register_resource(Resource(
            uri="netra://synthetic-data/generated",
            name="Generated Synthetic Data",
            description="Previously generated synthetic datasets",
            mimeType="application/json"
        ))
        
        # Supply catalog resources
        self.register_resource(Resource(
            uri="netra://supply/models",
            name="Model Catalog",
            description="Available LLM models and their specifications",
            mimeType="application/json"
        ))
        
        self.register_resource(Resource(
            uri="netra://supply/providers",
            name="Provider Catalog",
            description="LLM provider configurations",
            mimeType="application/json"
        ))
        
    def register_resource(self, resource: Resource):
        """Register a new resource"""
        if resource.uri in self.resources:
            logger.warning(f"Overwriting existing resource: {resource.uri}")
        self.resources[resource.uri] = resource
        logger.info(f"Registered resource: {resource.uri}")
        
    def unregister_resource(self, resource_uri: str):
        """Unregister a resource"""
        if resource_uri in self.resources:
            del self.resources[resource_uri]
            logger.info(f"Unregistered resource: {resource_uri}")
            
    async def list_resources(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available resources for a session"""
        # TODO: Filter resources based on session permissions
        resources_list = []
        for resource in self.resources.values():
            resource_dict = {
                "uri": resource.uri,
                "name": resource.name,
                "mimeType": resource.mimeType
            }
            if resource.description:
                resource_dict["description"] = resource.description
            resources_list.append(resource_dict)
        return resources_list
        
    async def read_resource(self, uri: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read resource content"""
        # Log access
        access = ResourceAccess(
            resource_uri=uri,
            session_id=session_id,
            access_type="read"
        )
        
        try:
            # Parse URI
            parsed = urlparse(uri)
            
            if parsed.scheme != "netra":
                raise NetraException(f"Invalid resource scheme: {parsed.scheme}")
                
            path = parsed.path.lstrip("/")
            
            # Route to appropriate handler
            if path.startswith("threads"):
                content = await self._read_threads_resource(path, session_id)
            elif path.startswith("agents"):
                content = await self._read_agents_resource(path, session_id)
            elif path.startswith("corpus"):
                content = await self._read_corpus_resource(path, session_id)
            elif path.startswith("metrics"):
                content = await self._read_metrics_resource(path, session_id)
            elif path.startswith("synthetic-data"):
                content = await self._read_synthetic_data_resource(path, session_id)
            elif path.startswith("supply"):
                content = await self._read_supply_resource(path, session_id)
            else:
                raise NetraException(f"Unknown resource path: {path}")
                
            access.success = True
            return content
            
        except Exception as e:
            access.success = False
            access.error = str(e)
            logger.error(f"Resource read failed: {uri} - {e}", exc_info=True)
            raise
        finally:
            self.access_log.append(access)
            
    async def _read_threads_resource(self, path: str, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """Read thread resources"""
        parts = path.split("/")
        
        if len(parts) == 1:  # netra://threads
            # TODO: Get actual threads from database
            logger.info(f"Fetching threads list for session {session_id}")
            return [{
                "type": "text",
                "text": json.dumps([
                    {"id": "thread1", "title": "Optimization Discussion", "created_at": "2025-01-11T10:00:00Z"},
                    {"id": "thread2", "title": "Performance Analysis", "created_at": "2025-01-11T09:00:00Z"}
                ], indent=2)
            }]
        elif len(parts) == 2:  # netra://threads/{thread_id}
            thread_id = parts[1]
            # TODO: Get actual thread messages
            logger.info(f"Fetching messages for thread {thread_id}, session {session_id}")
            return [{
                "type": "text",
                "text": f"Thread {thread_id} messages would be here"
            }]
        else:
            raise NetraException(f"Invalid threads resource path: {path}")
            
    async def _read_agents_resource(self, path: str, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """Read agent resources"""
        parts = path.split("/")
        
        if len(parts) == 1:  # netra://agents
            # TODO: Get actual agent configurations
            logger.info(f"Fetching agent configurations for session {session_id}")
            return [{
                "type": "text",
                "text": json.dumps({
                    "agents": [
                        {"name": "TriageSubAgent", "status": "available"},
                        {"name": "DataSubAgent", "status": "available"},
                        {"name": "OptimizationsCoreSubAgent", "status": "available"}
                    ]
                }, indent=2)
            }]
        elif len(parts) == 3 and parts[2] == "state":  # netra://agents/{agent_name}/state
            agent_name = parts[1]
            # TODO: Get actual agent state
            return [{
                "type": "text",
                "text": f"Agent {agent_name} state would be here"
            }]
        else:
            raise NetraException(f"Invalid agents resource path: {path}")
            
    async def _read_corpus_resource(self, path: str, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """Read corpus resources"""
        parts = path.split("/")
        
        if len(parts) == 1:  # netra://corpus
            # TODO: Get corpus overview
            return [{
                "type": "text",
                "text": "Corpus overview: 1000 documents, 50MB embeddings"
            }]
        elif parts[1] == "search":  # netra://corpus/search
            # TODO: Implement corpus search
            return [{
                "type": "text",
                "text": "Corpus search interface"
            }]
        else:
            raise NetraException(f"Invalid corpus resource path: {path}")
            
    async def _read_metrics_resource(self, path: str, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """Read metrics resources"""
        parts = path.split("/")
        
        if len(parts) < 2:
            raise NetraException(f"Invalid metrics resource path: {path}")
            
        metric_type = parts[1]
        
        if metric_type == "workload":
            # TODO: Get actual workload metrics from ClickHouse
            return [{
                "type": "text",
                "text": json.dumps({
                    "avg_latency_ms": 250,
                    "p99_latency_ms": 1200,
                    "requests_per_second": 45.2,
                    "error_rate": 0.02
                }, indent=2)
            }]
        elif metric_type == "optimization":
            # TODO: Get optimization metrics
            return [{
                "type": "text",
                "text": json.dumps({
                    "cost_reduction": "35%",
                    "latency_improvement": "42%",
                    "throughput_increase": "2.5x"
                }, indent=2)
            }]
        else:
            raise NetraException(f"Unknown metric type: {metric_type}")
            
    async def _read_synthetic_data_resource(self, path: str, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """Read synthetic data resources"""
        parts = path.split("/")
        
        if len(parts) < 2:
            raise NetraException(f"Invalid synthetic-data resource path: {path}")
            
        data_type = parts[1]
        
        if data_type == "schemas":
            # TODO: Get available schemas
            return [{
                "type": "text",
                "text": json.dumps({
                    "schemas": ["user_profile", "transaction", "product", "review"]
                }, indent=2)
            }]
        elif data_type == "generated":
            # TODO: Get generated datasets
            return [{
                "type": "text",
                "text": "List of generated synthetic datasets"
            }]
        else:
            raise NetraException(f"Unknown synthetic data type: {data_type}")
            
    async def _read_supply_resource(self, path: str, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """Read supply catalog resources"""
        parts = path.split("/")
        
        if len(parts) < 2:
            raise NetraException(f"Invalid supply resource path: {path}")
            
        catalog_type = parts[1]
        
        if catalog_type == "models":
            # TODO: Get actual model catalog
            return [{
                "type": "text",
                "text": json.dumps({
                    "models": [
                        {"name": "claude-3-opus", "provider": "anthropic", "cost_per_1k": 0.015},
                        {"name": "gpt-4", "provider": "openai", "cost_per_1k": 0.03},
                        {"name": "gemini-pro", "provider": "google", "cost_per_1k": 0.001}
                    ]
                }, indent=2)
            }]
        elif catalog_type == "providers":
            # TODO: Get provider catalog
            return [{
                "type": "text",
                "text": json.dumps({
                    "providers": ["anthropic", "openai", "google", "azure"]
                }, indent=2)
            }]
        else:
            raise NetraException(f"Unknown catalog type: {catalog_type}")
            
    async def shutdown(self):
        """Clean up resources"""
        self.resources.clear()
        self.access_log.clear()