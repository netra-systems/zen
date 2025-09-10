#!/usr/bin/env python3
"""Emergency database table creation for staging 503 fix"""
import asyncio
import os
import sys

# Add the app directory to Python path to use existing database utilities
sys.path.insert(0, '/app')

from netra_backend.app.db.database_manager import DatabaseManager

async def fix_staging_tables():
    """Create missing tables directly using existing database manager."""
    try:
        print("🚀 Starting emergency table creation for staging...")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get async engine
        engine = db_manager.get_async_engine()
        
        async with engine.begin() as conn:
            print("✅ Connected to database")
            
            # Create agent_executions table
            print("🔧 Creating agent_executions table...")
            await conn.execute_raw("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    agent_id VARCHAR(100) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_time TIMESTAMP WITH TIME ZONE,
                    duration_seconds FLOAT,
                    input_data JSON,
                    output_data JSON,
                    error_message TEXT,
                    tokens_used INTEGER,
                    api_calls_made INTEGER,
                    cost_cents INTEGER,
                    thread_id VARCHAR(50),
                    workflow_id VARCHAR(50),
                    execution_context JSON,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS ix_agent_executions_agent_id ON agent_executions(agent_id);",
                "CREATE INDEX IF NOT EXISTS ix_agent_executions_status ON agent_executions(status);",
                "CREATE INDEX IF NOT EXISTS ix_agent_executions_thread_id ON agent_executions(thread_id);", 
                "CREATE INDEX IF NOT EXISTS ix_agent_executions_user_id ON agent_executions(user_id);",
                "CREATE INDEX IF NOT EXISTS ix_agent_executions_workflow_id ON agent_executions(workflow_id);"
            ]
            for index_sql in indexes:
                await conn.execute_raw(index_sql)
            
            # Create credit_transactions table
            print("🔧 Creating credit_transactions table...")
            await conn.execute_raw("""
                CREATE TABLE IF NOT EXISTS credit_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR,
                    amount FLOAT NOT NULL,
                    transaction_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Create subscriptions table
            print("🔧 Creating subscriptions table...")
            await conn.execute_raw("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR,
                    plan_name VARCHAR(100) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE
                );
            """)
            
            # Verify tables exist
            print("✅ Verifying table creation...")
            result = await conn.execute_raw("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema='public' 
                AND table_name IN ('agent_executions', 'credit_transactions', 'subscriptions')
                ORDER BY table_name;
            """)
            tables = await result.fetchall() if hasattr(result, 'fetchall') else []
            print(f"📋 Created tables: {[t[0] if hasattr(t, '__getitem__') else str(t) for t in tables]}")
            
            # Update alembic version
            try:
                await conn.execute_raw("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY);")
                await conn.execute_raw("INSERT INTO alembic_version (version_num) VALUES ('882759db46ce') ON CONFLICT (version_num) DO NOTHING;")
                print("✅ Updated alembic version")
            except Exception as e:
                print(f"⚠️  Could not update alembic version: {e}")
        
        print("🎉 Emergency table creation completed successfully!")
        print("🔄 Backend services should now start properly!")
        
    except Exception as e:
        print(f"❌ Emergency fix failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(fix_staging_tables())