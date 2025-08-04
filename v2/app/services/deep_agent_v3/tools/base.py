
class BaseTool:
    def __init__(self, llm_connector=None, db_session=None):
        self.llm_connector = llm_connector
        self.db_session = db_session
