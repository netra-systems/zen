import clickhouse_connect
from clickhouse_connect.driver.client import Client
from typing import List, Dict, Any

class ClickHouseDatabase:
    """
    A client for interacting with a ClickHouse database.
    It handles connection, disconnection, and data operations.
    """
    def __init__(self, host: str, port: int, database: str, user: str, password: str, secure: bool = False):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.secure = secure
        self.client: Client | None = None

        try:
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                secure=self.secure
            )
            self.client.ping()
        except Exception as e:
            self.client = None
            raise ConnectionError(f"Could not connect to ClickHouse: {e}") from e

    def insert_log(self, log_entry):
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.insert("logs", [log_entry.model_dump_json()])
        except Exception as e:
            # In a real application, you would have a more robust error handling mechanism
            print(f"Failed to insert log into ClickHouse: {e}")
