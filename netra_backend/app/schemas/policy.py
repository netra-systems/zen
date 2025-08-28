from pydantic import BaseModel, Field


class LearnedPolicy(BaseModel):
    pattern_name: str = Field(..., description="The name of the pattern.")
    optimal_supply_option_name: str = Field(..., description="The name of the optimal supply option.")

class PredictedOutcome(BaseModel):
    supply_option_name: str = Field(..., description="The name of the supply option.")
    explanation: str = Field(..., description="The explanation of the outcome.")
