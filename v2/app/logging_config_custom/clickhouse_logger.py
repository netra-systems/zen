import logging
from app.db.clickhouse import ClickHouseClient
from app.logging.logger import Log

class ClickHouseLogHandler(logging.Handler):
    def __init__(self, client: ClickHouseClient):
        super().__init__()
        self.client = client

    def emit(self, record: logging.LogRecord):
        # This handler will be triggered by logger calls.
        # We re-create a Log Pydantic model from the record.
        log_entry = Log(
            level=record.levelname,
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line_no=record.lineno,
            process_name=record.processName,
            thread_name=record.threadName,
        )
        self.client.insert_log(log_entry)