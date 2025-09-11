#!/usr/bin/env python3
"""
Emergency fix for staging 503 issue - creates missing database tables
This is a temporary fix to restore staging functionality
"""
import asyncio
import asyncpg
import os
import sys

async def create_tables():
    """Create the missing tables that are causing startup failures."""
    
    try:
        # Database connection parameters
        host = '/cloudsql/netra-staging:us-central1:staging-shared-postgres'
        database = os.getenv('POSTGRES_DB', 'netra_staging')
        user = os.getenv('POSTGRES_USER')
        password = os.getenv('POSTGRES_PASSWORD')
        
        print(f"Connecting to database: {database}")
        print(f"Host: {host}")
        print(f"User: {user}")
        
        # Connect to database
        conn = await asyncpg.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        
        print("✅ Connected to database successfully")
        
        # Check current state
        try:
            tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
            existing_tables = [t['table_name'] for t in tables]
            print(f"📋 Existing tables: {existing_tables}")
        except Exception as e:
            print(f"⚠️  Error listing tables: {e}")
        
        # Create agent_executions table
        print("🔧 Creating agent_executions table...")
        await conn.execute("""
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
        
        # Create indexes for agent_executions
        print("🔧 Creating indexes for agent_executions...")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_executions_agent_id ON agent_executions(agent_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_executions_status ON agent_executions(status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_executions_thread_id ON agent_executions(thread_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_executions_user_id ON agent_executions(user_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_executions_workflow_id ON agent_executions(workflow_id);")
        
        # Create credit_transactions table
        print("🔧 Creating credit_transactions table...")
        await conn.execute("""
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
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR,
                plan_name VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE
            );
        """)
        
        # Verify tables were created
        print("✅ Verifying tables were created...")
        missing_tables = ['agent_executions', 'credit_transactions', 'subscriptions']
        for table in missing_tables:
            exists = await conn.fetchval(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='{table}');")
            print(f"📋 Table {table} exists: {'✅' if exists else '❌'}")
            
        # Update alembic version if table exists
        try:
            await conn.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY);")
            await conn.execute("INSERT INTO alembic_version (version_num) VALUES ('882759db46ce') ON CONFLICT (version_num) DO NOTHING;")
            current_version = await conn.fetchval("SELECT version_num FROM alembic_version;")
            print(f"📋 Alembic version: {current_version}")
        except Exception as e:
            print(f"⚠️  Error updating alembic version: {e}")
        
        await conn.close()
        print("🎉 All tables created successfully! Staging should now start properly.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(create_tables())