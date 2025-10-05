from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import JSON
from sqlmodel import Column, Field, SQLModel


class GrafanaAlert(SQLModel, table=True):
    """Grafana alert payload for Loki log alerts."""

    # # Optional ID field
    id: Optional[int] = Field(default=None, primary_key=True)

    # Grouping information
    logTimestamp: Optional[datetime] = Field(
        default_factory=datetime.now, description="Timestamp of the log message"
    )
    logMessage: str = Field(description="Original log message that triggered the alert")
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
    labels: Dict[str, str] = Field(
        default={},
        description="Labels used for grouping alerts",
        sa_column=Column(JSON),
    )

    # # Loki-specific fields that might be extracted from log content
    # logLevel: Optional[str] = None  # Log level from Loki logs (info, warn, error, etc.)
    # # logStream: Optional[str] = None  # Loki log stream identifier
    # logSource: Optional[str] = None  # Source of the log (e.g., service name, pod name)

    # log_type: Optional[str] = None
    # task_name: Optional[str] = None
