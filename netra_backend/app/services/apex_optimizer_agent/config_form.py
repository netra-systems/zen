from typing import List, Optional

from pydantic import BaseModel, Field


class AdditionalTable(BaseModel):
    name: str = Field(..., description="The name of the additional table.")
    context: str = Field(..., description="The context in which this table should be used.")
    time_period: str = Field(..., description="The default time period for this table.")

class ConfigForm(BaseModel):
    default_log_table: str = Field(..., description="The default log table to pull from.")
    default_time_range: str = Field(default="7d", description="The default time period to pull logs from.")
    additional_tables: Optional[List[AdditionalTable]] = Field(default=None, description="A list of additional default tables.")
