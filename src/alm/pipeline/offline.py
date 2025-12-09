import asyncio
import time
from typing import List, Dict, Tuple
from alm.database import convert_grafana_alert_to_grafana_alert_state, get_session
from alm.alert_mocker import ingest_alerts
from alm.agents.graph import graph_without_clustering
from alm.agents.node import train_embed_and_cluster_logs
from alm.models import GrafanaAlert
from sqlmodel import select
from alm.database import convert_state_to_grafana_alert
from alm.database import init_tables
from alm.utils.logger import get_logger

logger = get_logger(__name__)


async def _add_or_update_alert(alert):
    async with get_session() as db:
        db.add(alert)
        await db.commit()
        await db.refresh(alert)


def cluster_logs(
    alerts: List[GrafanaAlert],
) -> Tuple[List[str], Dict[str, GrafanaAlert]]:
    """Cluster logs and return unique alerts per cluster."""
    cluster_labels = train_embed_and_cluster_logs(
        [alert.logMessage for alert in alerts]
    )

    unique_cluster = {label: alert for alert, label in zip(alerts, cluster_labels)}
    return cluster_labels, unique_cluster


async def load_alerts(load_alerts_from_db):
    if not load_alerts_from_db:
        alerts = [
            alert for alert in ingest_alerts("data/logs/failed") if alert is not None
        ]
        logger.info("alerts ingested %d", len(alerts))
    else:
        async with get_session() as db:
            alerts = await db.exec(select(GrafanaAlert))
            alerts = alerts.all()
            logger.info("alerts loaded from db %d", len(alerts))
    return alerts


async def _process_alert(label: str, alert: GrafanaAlert) -> Tuple[str, GrafanaAlert]:
    """Process a single alert through the graph without clustering and return (label, result)."""
    state = convert_grafana_alert_to_grafana_alert_state(alert)
    result_state = await graph_without_clustering().ainvoke(state)
    return label, convert_state_to_grafana_alert(result_state)


async def training_pipeline(restart_db=True, load_alerts_from_db=False):
    if restart_db:
        await init_tables(delete_tables=True)

    # Load alerts
    alerts = await load_alerts(load_alerts_from_db=load_alerts_from_db)

    # Cluster logs
    cluster_labels, unique_cluster = cluster_logs(alerts)

    # Process all unique cluster alerts in parallel
    results = await asyncio.gather(
        *[_process_alert(label, alert) for label, alert in unique_cluster.items()]
    )
    updated_alerts: Dict[str, GrafanaAlert] = dict(results)

    # update alerts fields by label
    for label, alert in zip(cluster_labels, alerts):
        candidate_alert = updated_alerts[label]
        # All the intermediate steps of the agent
        alert.logSummary = candidate_alert.logSummary
        alert.expertClassification = candidate_alert.expertClassification
        alert.logCluster = str(label)
        alert.needMoreContext = candidate_alert.needMoreContext
        alert.stepByStepSolution = candidate_alert.stepByStepSolution
        alert.contextForStepByStepSolution = (
            candidate_alert.contextForStepByStepSolution
        )

    # update database
    start_time = time.time()
    await asyncio.gather(*[_add_or_update_alert(alert) for alert in alerts])
    elapsed_time = time.time() - start_time
    logger.info("database alerts added - Time: %.2fs", elapsed_time)
