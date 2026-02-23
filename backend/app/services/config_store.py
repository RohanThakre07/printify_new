import json
from typing import Any
from sqlalchemy.orm import Session

from backend.app.models import AppConfig


class ConfigStore:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str, default: Any = None):
        item = self.db.query(AppConfig).filter(AppConfig.key == key).first()
        if not item:
            return default
        return json.loads(item.value)

    def set(self, key: str, value: Any):
        payload = json.dumps(value)
        item = self.db.query(AppConfig).filter(AppConfig.key == key).first()
        if not item:
            item = AppConfig(key=key, value=payload)
            self.db.add(item)
        else:
            item.value = payload
        self.db.commit()
