import sys
import os

print(f"sys.executable: {sys.executable}")
print(f"sys.path: {sys.path}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")

# Add the site-packages directory to the Python path
site_packages = r"C:\Users\antho\miniconda3\Lib\site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pydantic_to_typescript import generate_typescript_defs
except Exception as e:
    print(e)
    sys.exit(1)

from app import schemas

def main():
    """Generate TypeScript definitions from Pydantic schemas."""
    schema_list = [
        schemas.WebSocketMessage,
        schemas.SubAgentLifecycle,
        schemas.AgentState,
        schemas.Todo,
        schemas.DeepAgentState,
        schemas.SubAgentState,
        schemas.AgentStarted,
        schemas.AgentCompleted,
        schemas.AgentErrorMessage,
        schemas.SubAgentUpdate,
        schemas.SubAgentStatus,
        schemas.GoogleUser,
        schemas.DevUser,
        schemas.DevLoginRequest,
        schemas.AuthEndpoints,
        schemas.AuthConfigResponse,
        schemas.ClickHouseCredentials,
        schemas.SecretReference,
        schemas.SECRET_CONFIG,
        schemas.GoogleCloudConfig,
        schemas.OAuthConfig,
        schemas.ClickHouseNativeConfig,
        schemas.ClickHouseHTTPSConfig,
        schemas.ClickHouseHTTPSDevConfig,
        schemas.ClickHouseLoggingConfig,
        schemas.LogTableSettings,
        schemas.TimePeriodSettings,
        schemas.DefaultLogTableSettings,
        schemas.LangfuseConfig,
        schemas.LLMConfig,
        schemas.AppConfig,
        schemas.DevelopmentConfig,
        schemas.ProductionConfig,
        schemas.TestingConfig,
        schemas.CorpusBase,
        schemas.CorpusCreate,
        schemas.CorpusUpdate,
        schemas.CorpusInDBBase,
        schemas.Corpus,
        schemas.ContentCorpus,
        schemas.ContentGenParams,
        schemas.LogGenParams,
        schemas.SyntheticDataGenParams,
        schemas.DataIngestionParams,
        schemas.ContentCorpusGenParams,
        schemas.EventMetadata,
        schemas.TraceContext,
        schemas.MessageType,
        schemas.Message,
        schemas.Performance,
        schemas.FinOps,
        schemas.CostComparison,
        schemas.EnrichedMetrics,
        schemas.BaselineMetrics,
        schemas.UnifiedLogEntry,
        schemas.DiscoveredPattern,
        schemas.LearnedPolicy,
        schemas.PredictedOutcome,
        schemas.AnalysisResult,
        schemas.Settings,
        schemas.DataSource,
        schemas.TimeRange,
        schemas.Workload,
        schemas.RequestModel,
        schemas.Response,
        schemas.StartAgentPayload,
        schemas.StartAgentMessage,
        schemas.RunComplete,
        schemas.ModelIdentifier,
        schemas.SupplyOptionBase,
        schemas.SupplyOptionCreate,
        schemas.SupplyOptionUpdate,
        schemas.SupplyOptionInDBBase,
        schemas.SupplyOption,
        schemas.SupplyOptionInDB,
        schemas.Token,
        schemas.TokenPayload,
        schemas.ToolStatus,
        schemas.ToolInput,
        schemas.ToolResult,
        schemas.ToolInvocation,
        schemas.ToolStarted,
        schemas.ToolCompleted,
        schemas.UserBase,
        schemas.UserCreate,
        schemas.UserUpdate,
        schemas.UserInDBBase,
        schemas.User,
        schemas.UserInDB,
        schemas.WebSocketError,
        schemas.MessageToUser,
        schemas.AnalysisRequest,
        schemas.UserMessage,
        schemas.AgentMessage,
        schemas.StopAgent,
        schemas.StreamEvent,
        schemas.ReferenceGetResponse,
        schemas.ReferenceItem,
        schemas.ReferenceCreateRequest,
        schemas.ReferenceUpdateRequest,
    ]
    ts_defs = generate_typescript_defs(
        ["app.schemas"],
        schema_list
    )
    with open("frontend/types/backend_schema_auto_generated.ts", "w") as f:
        f.write(ts_defs)


if __name__ == "__main__":
    main()