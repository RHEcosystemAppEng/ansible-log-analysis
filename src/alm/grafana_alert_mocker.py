import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.alm.models import GrafanaAlert
from src.alm.patterns.ingestion import (
    AAP_LOG_ERROR,
    AAP_LOG_FATAL,
    TESTING_LOG_ERROR,
    TESTING_LOG_FATAL,
    TESTING_LOG_FAILED,
)


def _filter_matches_end_with_ignoring(matches: list[re.Match]) -> list[re.Match]:
    """Filter matches that end with 'ignoring'."""
    return [
        match
        for match in matches
        if not match.groupdict().get("logmessage", "").endswith("ignoring")
    ]


def shrink_long_logs(log: str) -> str:
    """Shrink long logs."""
    # used for very long logs that have a lot of redundent data
    # This should be improve later to be more accurate
    # TODO: improve this
    # NOTE: see the 30_000 char trim
    return log.split(r'"properties": ')[0][:30_000] if len(log) > 30_000 else log


def grafana_alert_mock(path: str) -> Optional[GrafanaAlert]:
    """Mock the Grafana alerting system."""
    with open(path, "r") as file:
        content = file.read()
    matches = _filter_matches_end_with_ignoring(
        list(re.finditer(TESTING_LOG_ERROR, content, re.MULTILINE))
    )

    if not matches:
        matches = _filter_matches_end_with_ignoring(
            re.finditer(TESTING_LOG_FATAL, content, re.MULTILINE)
        )
        if not matches:
            if not matches:
                matches = _filter_matches_end_with_ignoring(
                    re.finditer(TESTING_LOG_FAILED, content, re.MULTILINE)
                )
            return None

    # Get the last match
    last_match = matches[-1]
    groups = last_match.groupdict()

    # Create GrafanaAlert instance with extracted data
    alert = GrafanaAlert(
        logTimestamp=(
            datetime.strptime(groups.get("timestamp"), "%A %d %B %Y  %H:%M:%S")
            if groups.get("timestamp")
            else datetime.now()
        ),
        logMessage=shrink_long_logs(
            groups.get("logmessage", "")
        ),  # Full matched text as the log message
        # logSummary=groups.get('logsummary', ''),
        # expertClassification=groups.get('expertClassification', ''),
        labels={
            "host": groups.get("host", "").strip(),
            "file_name": Path(path).name,
            # 'log_source': groups.get('host', '').strip(),
            # "task_name": groups.get("task_name", "").strip(),
        },
        # logLevel=groups.get('status', ''),  # Use status as log level (fatal/error)
        # logSource=pathlib.Path(path).name
    )

    return alert


def ingest_alerts(directory: str) -> list[GrafanaAlert]:
    """Ingest alerts from a directory."""
    alerts = []
    error_count = 0
    success_count = 0
    for file in os.listdir(directory):
        if file.endswith(".txt"):
            try:
                alerts.append(grafana_alert_mock(os.path.join(directory, file)))
                success_count += 1
            except Exception:
                error_count += 1
    print(f"{error_count} errors and {success_count} successes")
    print(f"alerts: {len(alerts)}")
    return alerts
