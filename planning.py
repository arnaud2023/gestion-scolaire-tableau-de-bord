from __future__ import annotations

from datetime import time
from typing import Any, Iterable


RESOURCE_FIELDS = {
    "classe_id": "la classe",
    "enseignant_id": "l'enseignant",
    "salle_id": "la salle",
}


def has_time_conflict(
    candidate: dict[str, Any],
    sessions: Iterable[dict[str, Any]],
    ignore_id: int | None = None,
) -> str | None:
    """Return a French conflict message, or None when the slot is available."""
    start = time.fromisoformat(candidate["heure_debut"])
    end = time.fromisoformat(candidate["heure_fin"])
    if start >= end:
        return "L'heure de fin doit être après l'heure de début."

    for session in sessions:
        if ignore_id is not None and session.get("id") == ignore_id:
            continue
        if session["jour"] != candidate["jour"]:
            continue

        other_start = time.fromisoformat(session["heure_debut"])
        other_end = time.fromisoformat(session["heure_fin"])
        overlaps = start < other_end and other_start < end
        if not overlaps:
            continue

        for field, label in RESOURCE_FIELDS.items():
            if candidate.get(field) == session.get(field):
                return f"Conflit : {label} déjà occupé(e) sur ce créneau."

    return None