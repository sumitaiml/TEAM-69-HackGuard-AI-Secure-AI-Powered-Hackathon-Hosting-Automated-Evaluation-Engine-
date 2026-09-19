from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app import models


def record_audit_event(
    db: Session,
    actor_user_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> models.AuditLog:
    """Adds an AuditLog row to the session without committing - callers add
    this alongside their own change and let their existing db.commit() cover
    both atomically."""
    entry = models.AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
    )
    db.add(entry)
    return entry
