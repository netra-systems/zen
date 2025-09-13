"""Demo session manager for handling enterprise demonstration sessions."""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
    
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DemoSessionManager:
    """Manages demo sessions with PostgreSQL database persistence."""
    
    def __init__(self):
        self._pool = None
        self._in_memory_sessions = {}  # Fallback for when database is unavailable
        
    async def _get_connection(self):
        """Get database connection from pool."""
        # Try to import asyncpg only when needed
        try:
            import asyncpg
        except ImportError:
            logger.warning("asyncpg not available, using in-memory storage only")
            return None
            
        if not self._pool:
            # Get database configuration from environment
            database_url = os.environ.get("DATABASE_URL", "")
            
            if database_url:
                # Parse database URL
                if database_url.startswith("postgresql://"):
                    database_url = database_url.replace("postgresql://", "")
                elif database_url.startswith("postgres://"):
                    database_url = database_url.replace("postgres://", "")
                
                # Split and parse connection components
                if "@" in database_url:
                    auth, rest = database_url.split("@", 1)
                    if ":" in auth:
                        user, password = auth.split(":", 1)
                    else:
                        user = auth
                        password = None
                        
                    if "/" in rest:
                        host_port, database = rest.split("/", 1)
                        if ":" in host_port:
                            host, port = host_port.split(":", 1)
                            port = int(port)
                        else:
                            host = host_port
                            port = 5432
                    else:
                        host = rest
                        port = 5432
                        database = "netra"
                else:
                    # Invalid URL format, use defaults
                    host = "localhost"
                    port = 5432
                    user = "netra"
                    password = "netra"
                    database = "netra"
            else:
                # Fallback to individual environment variables
                host = os.environ.get("DB_HOST", "localhost")
                port = int(os.environ.get("DB_PORT", "5432"))
                user = os.environ.get("DB_USER", "netra")
                password = os.environ.get("DB_PASSWORD", "netra")
                database = os.environ.get("DB_NAME", "netra")
            
            try:
                self._pool = await asyncpg.create_pool(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
            except Exception as e:
                logger.error(f"Failed to create database pool: {str(e)}")
                # Return None to allow fallback behavior
                return None
                
        if self._pool:
            return await self._pool.acquire()
        return None
        
    async def _release_connection(self, conn):
        """Release connection back to pool."""
        if conn and self._pool:
            await self._pool.release(conn)
            
    async def get_demo_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get demo session by ID."""
        conn = None
        try:
            conn = await self._get_connection()
            if not conn:
                # Fallback to in-memory session
                logger.warning(f"Database unavailable, checking in-memory session for {session_id}")
                return self._in_memory_sessions.get(session_id)
                
            row = await conn.fetchrow(
                """
                SELECT id, user_id, industry, company_name, company_size, 
                       status, progress_percentage, started_at, completed_at, 
                       metadata, created_at, updated_at
                FROM demo_sessions 
                WHERE id = $1
                """,
                session_id
            )
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting demo session {session_id}: {str(e)}")
            return None
        finally:
            if conn:
                await self._release_connection(conn)
                
    async def create_demo_session(self, session_id: str, industry: str, 
                                  user_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new demo session."""
        conn = None
        try:
            # Generate UUID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                
            conn = await self._get_connection()
            if not conn:
                # Fallback to in-memory session
                logger.warning("Database unavailable, creating in-memory session")
                session_data = {
                    "id": session_id,
                    "industry": industry,
                    "user_id": str(user_id) if user_id else None,
                    "status": "active",
                    "progress_percentage": 0.0,
                    "started_at": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "messages": []  # Store messages in memory
                }
                self._in_memory_sessions[session_id] = session_data
                return session_data
                
            user_id_str = str(user_id) if user_id else None
            now = datetime.utcnow()
            
            row = await conn.fetchrow(
                """
                INSERT INTO demo_sessions 
                (id, user_id, industry, status, progress_percentage, 
                 started_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO UPDATE 
                SET updated_at = EXCLUDED.updated_at
                RETURNING *
                """,
                session_id, user_id_str, industry, "active", 0.0,
                now, now, now
            )
            
            return dict(row) if row else {
                "id": session_id,
                "industry": industry,
                "user_id": user_id_str,
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Error creating demo session: {str(e)}")
            # Return fallback in-memory session
            session_data = {
                "id": session_id,
                "industry": industry,
                "user_id": str(user_id) if user_id else None,
                "status": "active",
                "progress_percentage": 0.0,
                "started_at": datetime.utcnow().isoformat(),
                "messages": []
            }
            self._in_memory_sessions[session_id] = session_data
            return session_data
        finally:
            if conn:
                await self._release_connection(conn)
                
    async def add_demo_message(self, session_id: str, role: str, message: str,
                               agents: Optional[List[str]] = None,
                               metrics: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the demo session."""
        conn = None
        try:
            conn = await self._get_connection()
            if not conn:
                # Store in memory if database unavailable
                logger.warning(f"Database unavailable, storing message in memory for session {session_id}")
                if session_id in self._in_memory_sessions:
                    if "messages" not in self._in_memory_sessions[session_id]:
                        self._in_memory_sessions[session_id]["messages"] = []
                    self._in_memory_sessions[session_id]["messages"].append({
                        "role": role,
                        "message": message,
                        "agents": agents,
                        "metrics": metrics,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                return
                
            interaction_type = "user_message" if role == "user" else "assistant_response"
            
            await conn.execute(
                """
                INSERT INTO demo_interactions 
                (session_id, interaction_type, message, response, 
                 agents_involved, metrics, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                session_id,
                interaction_type,
                message if role == "user" else None,
                message if role == "assistant" else None,
                agents or [],
                json.dumps(metrics) if metrics else None,
                datetime.utcnow()
            )
            
            # Update session progress
            if role == "assistant":
                await conn.execute(
                    """
                    UPDATE demo_sessions 
                    SET progress_percentage = progress_percentage + 10,
                        updated_at = $2
                    WHERE id = $1 AND progress_percentage < 100
                    """,
                    session_id,
                    datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Error adding demo message: {str(e)}")
            # Continue without storing - don't break the chat flow
        finally:
            if conn:
                await self._release_connection(conn)
                
    async def get_demo_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a demo session."""
        conn = None
        try:
            conn = await self._get_connection()
            if not conn:
                # Check in-memory session
                if session_id in self._in_memory_sessions:
                    session = self._in_memory_sessions[session_id]
                    return {
                        "session_id": session_id,
                        "status": session.get("status", "active"),
                        "progress": session.get("progress_percentage", 0.0),
                        "interaction_count": len(session.get("messages", [])),
                        "created_at": session.get("created_at")
                    }
                return {
                    "session_id": session_id,
                    "status": "not_found",
                    "progress": 0.0
                }
                
            # Get session info
            session = await conn.fetchrow(
                """
                SELECT status, progress_percentage, created_at, updated_at
                FROM demo_sessions
                WHERE id = $1
                """,
                session_id
            )
            
            if not session:
                return {
                    "session_id": session_id,
                    "status": "not_found",
                    "progress": 0.0
                }
                
            # Get interaction count
            interaction_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM demo_interactions
                WHERE session_id = $1
                """,
                session_id
            )
            
            return {
                "session_id": session_id,
                "status": session["status"],
                "progress": float(session["progress_percentage"]),
                "interaction_count": interaction_count,
                "created_at": session["created_at"].isoformat() if session["created_at"] else None,
                "updated_at": session["updated_at"].isoformat() if session["updated_at"] else None
            }
            
        except Exception as e:
            logger.error(f"Error getting demo session status: {str(e)}")
            return {
                "session_id": session_id,
                "status": "error",
                "progress": 0.0
            }
        finally:
            if conn:
                await self._release_connection(conn)
                
    async def close(self):
        """Close database connections."""
        if self._pool:
            await self._pool.close()