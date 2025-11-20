from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from google.cloud.firestore import Client

from agency_service.firestore import add_timestamps


def generate_plan(
    client: Client,
    *,
    agency_id: str,
    date: str,
    plan_version: str,
) -> Dict[str, str]:
    """Placeholder algoritmo VRP.

    Per ora assegna i lavori pending della data indicata senza ottimizzazione avanzata.
    """
    jobs_query = (
        client.collection("cleaningJobs")
        .where("agencyId", "==", agency_id)
        .where("scheduledDate", "==", date)
    )
    jobs = list(jobs_query.stream())

    assignments = []
    for job in jobs:
        assignments.append(
            {
                "jobId": job.id,
                "staffId": None,
                "startTime": None,
                "endTime": None,
                "travelMinutes": None,
            }
        )

    payload = {
        "agencyId": agency_id,
        "date": date,
        "status": "draft",
        "solverVersion": plan_version,
        "inputJobs": [job.id for job in jobs],
        "assignments": assignments,
        "metrics": {"totalJobs": len(jobs)},
    }

    plan_ref = client.collection("cleaningPlans").document()
    plan_ref.set(add_timestamps(payload))

    # Aggiorna i job con il riferimento al nuovo piano
    for job in jobs:
        job.reference.update({"planId": plan_ref.id, "updatedAt": datetime.now(timezone.utc)})

    return {"planId": plan_ref.id, "status": payload["status"], "date": date}

