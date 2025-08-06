import logging

logging.getLogger("faker").setLevel(logging.WARNING)

import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth, supply, generation, google_auth, apex_optimizer_agent_route, websocket, streaming_agent_route, admin
from app.db.postgres import async_session_factory
from app.config import settings
from app.logging_config import central_logger
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.supervisor import NetraOptimizerAgentSupervisor
from app.services.streaming_agent.supervisor import StreamingAgentSupervisor
from app.services.key_manager import KeyManager
from app.services.security_service import SecurityService
from app.websocket import manager as websocket_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # Startup
    logger = central_logger.get_logger(__name__)
    logger.info("Application startup...")

    key_manager = KeyManager.load_from_settings(settings)
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)

    # Initialize LLMManager
    app.state.llm_manager = LLMManager(settings)

    # The ClickHouse client is now managed by the central_logger
    app.state.clickhouse_client = central_logger.clickhouse_db

    # Initialize Postgres
    app.state.db_session_factory = async_session_factory

    # Initialize the agent supervisor
    app.state.agent_supervisor = NetraOptimizerAgentSupervisor(app.state.db_session_factory, app.state.llm_manager)
    app.state.streaming_agent_supervisor = StreamingAgentSupervisor(app.state.db_session_factory, app.state.llm_manager, websocket_manager)

    yield
    
    # Shutdown
    logger.info("Application shutdown...")



from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(supply.router, prefix="/api/v3/supply", tags=["supply"])
app.include_router(generation.router, prefix="/api/v3/generation", tags=["generation"])
app.include_router(google_auth.router, tags=["google_auth"])
app.include_router(apex_optimizer_agent_route.router, prefix="/api/v3/apex/chat", tags=["apex/chat"])
app.include_router(streaming_agent_route.router, prefix="/api/v3/streaming_agent", tags=["streaming_agent"])
app.include_router(websocket.router, prefix="/ws", tags=["websockets"])
app.include_router(admin.router, prefix="/api/v3", tags=["admin"])

# Add a new websocket route for development that bypasses authentication
from app.auth_dependencies import ActiveUserWsDep
if settings.app_env == "development":
    @app.websocket("/ws/dev/{client_id}")
    async def dev_websocket_endpoint(websocket: WebSocket, client_id: str, current_user: ActiveUserWsDep):
        print(f"DEBUG: Dev WebSocket endpoint hit for client_id: {client_id}")
        await websocket_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await websocket_manager.send_personal_message(f"You wrote: {data}", websocket)
                await websocket_manager.broadcast(f"Client #{client_id} says: {data}")
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket)
            await websocket_manager.broadcast(f"Client #{client_id} left the chat")



@app.get("/")
def read_root():
    logger.info("Root endpoint was hit.")
    return {"message": "Welcome to Netra API v2"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if "pytest" in sys.modules:
    from app.db.postgres import async_session_factory
    from app.llm.llm_manager import LLMManager
    from app.services.apex_optimizer_agent.supervisor import NetraOptimizerAgentSupervisor
    from app.services.streaming_agent.supervisor import StreamingAgentSupervisor
    from app.websocket import manager as websocket_manager

    llm_manager = LLMManager(settings)
    app.state.agent_supervisor = NetraOptimizerAgentSupervisor(async_session_factory, llm_manager)
    app.state.streaming_agent_supervisor = StreamingAgentSupervisor(async_session_factory, llm_manager, websocket_manager)