import json
from sqlalchemy.orm import Session

from backend.app.models import ProcessingLog


def log_event(db: Session, message: str, level: str = "INFO", image_path: str | None = None, details: dict | None = None):
    log = ProcessingLog(
        image_path=image_path,
        level=level,
        message=message,
        details=json.dumps(details) if details else None,
    )
    db.add(log)
    db.commit()
