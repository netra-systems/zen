# Database Initialization Scripts

## Overview
This directory contains modular PostgreSQL initialization scripts that create all required tables for the Netra AI Optimization Platform. The approach uses direct CREATE TABLE commands instead of migrations for fresh database installations.

## Architecture Principles
- **Modular Design**: Each file is under 300 lines (per architecture requirements)
- **Single Responsibility**: Each module handles one domain area
- **Clear Dependencies**: Tables created in proper order to satisfy foreign keys
- **No Migrations for Fresh Installs**: Direct table creation is faster and clearer

## Files Structure

### Main Orchestrator
- `00-init-main.sql` - Main script that executes all modules in order

### Modular Scripts (executed in order)
1. `01-init-extensions.sql` - PostgreSQL extensions and configurations
2. `02-init-users-auth.sql` - User, authentication, and permission tables
3. `03-init-agents.sql` - AI agents, assistants, threads, and messages
4. `04-init-supply.sql` - Supply research and AI model catalog
5. `05-init-content.sql` - Content, corpus, and analysis tables
6. `06-init-demo.sql` - Demo session and interaction tables
7. `07-init-indexes.sql` - Performance indexes and constraints

### Utilities
- `validate_init.py` - Python script to validate database initialization
- `schema.sql` - Reference file showing complete schema
- `schema_old.sql` - Previous monolithic schema (backup)

## Fresh Database Setup

### Option 1: Using psql directly
```bash
# Connect to PostgreSQL and run main initialization
psql -U postgres -d netra_dev -f database_scripts/00-init-main.sql
```

### Option 2: From within psql
```sql
-- Connect to your database
\c netra_dev

-- Run the main initialization script
\i database_scripts/00-init-main.sql
```

### Option 3: Using Docker PostgreSQL
```bash
# Copy scripts to container
docker cp database_scripts postgres_container:/tmp/

# Execute initialization
docker exec -it postgres_container psql -U netra_app -d netra_dev -f /tmp/database_scripts/00-init-main.sql
```

## Validation

After initialization, validate the database structure:

```bash
# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=netra_dev
export DB_USER=netra_app
export DB_PASSWORD=changeme

# Run validation
python database_scripts/validate_init.py
```

Expected output:
```
✅ All required tables are present!
```

## Migration Strategy

### Fresh Installations
- Use the initialization scripts directly
- No Alembic migrations needed
- Faster and cleaner setup

### Existing Databases
- Continue using Alembic migrations
- Migrations handle schema evolution
- Never run init scripts on existing databases

### Development Workflow
1. Fresh setup: Run `00-init-main.sql`
2. Schema changes: Create Alembic migration
3. Deploy to existing: Run migrations only
4. Deploy to new: Run init scripts only

## Table Dependencies

The initialization order ensures all foreign key dependencies are satisfied:

```
1. Extensions (no dependencies)
2. userbase (no dependencies)
3. secrets, tool_usage_logs (depend on userbase)
4. assistants, threads (no dependencies)
5. runs (depends on threads, assistants)
6. messages (depends on threads, runs, assistants)
7. steps (depends on runs, threads, assistants)
8. supplies, supply_options (no dependencies)
9. ai_supply_items, research_sessions (no dependencies)
10. supply_update_logs (depends on ai_supply_items, research_sessions)
11. analyses, corpora (depend on userbase)
12. analysis_results (depends on analyses)
13. corpus_audit_logs (depends on userbase)
14. demo_* tables (depend on userbase)
```

## Performance Considerations

The initialization scripts include:
- Appropriate indexes for all foreign keys
- Composite indexes for common query patterns
- Partial indexes for filtered queries
- Statistics targets for frequently queried columns
- Check constraints for data integrity

## Troubleshooting

### Permission Denied
```bash
# Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE netra_dev TO netra_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO netra_app;
```

### Extension Not Available
Some extensions may not be available in all PostgreSQL installations:
- `pg_jsonschema` - Optional, for JSON validation
- `pg_stat_statements` - Optional, for query performance monitoring

### Foreign Key Violations
If you encounter foreign key violations:
1. Check the initialization order
2. Ensure all parent tables exist
3. Run validation script to identify issues

## Maintenance

### Adding New Tables
1. Determine appropriate module (or create new one)
2. Add CREATE TABLE statement to module
3. Ensure module stays under 300 lines
4. Add indexes and constraints to `07-init-indexes.sql`
5. Update validation script
6. Create Alembic migration for existing databases

### Modifying Existing Tables
1. **Never** modify initialization scripts for schema changes
2. Create Alembic migration instead
3. Document changes in migration file
4. Update SQLAlchemy models accordingly

## Benefits of This Approach

1. **Clarity**: Complete schema visible in SQL files
2. **Performance**: No migration overhead for fresh installs
3. **Modularity**: Each file has single responsibility
4. **Maintainability**: Easy to understand and modify
5. **Compliance**: Adheres to 450-line architecture limit
6. **Debugging**: Direct SQL is easier to troubleshoot

## Related Documentation
- [Database Initialization Findings](../docs/DATABASE_INITIALIZATION_FINDINGS.md)
- [SQLAlchemy Models](../app/db/models_*.py)
- [Alembic Migrations](../alembic/versions/)
- [Architecture Guidelines](../SPEC/conventions.xml)