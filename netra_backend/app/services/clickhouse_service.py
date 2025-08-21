from netra_backend.app.db.clickhouse import get_clickhouse_client

async def list_corpus_tables():
    async with get_clickhouse_client() as client:
        tables = await client.fetch("SHOW TABLES LIKE 'netra_content_corpus_%'")
        return [table['name'] for table in tables]
