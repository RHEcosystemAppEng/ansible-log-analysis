from pydantic import BaseModel, Field
from typing import Optional
from alm.models import LogEntry


class GrafanaAlertState(BaseModel):
    """State for the Grafana alert agent."""

    # Input field
    log_entry: LogEntry = Field(description="The log entry that triggered the alert")

    # Intermediate fields
    logSummary: Optional[str] = Field(
        default=None, description="Summary of the log message"
    )
    expertClassification: Optional[str] = Field(
        default=None, description="Classification of the log message"
    )
    logCluster: Optional[str] = Field(
        default=None, description="Cluster of the log message"
    )
    needMoreContext: Optional[bool] = Field(
        default=None, description="Is additional context needed to solve the problem"
    )
    stepByStepSolution: Optional[str] = Field(
        default=None, description="Step by step solution to the problem"
    )
    contextForStepByStepSolution: Optional[str] = Field(
        default=None, description="Context for the step by step solution"
    )
