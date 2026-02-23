from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, get_db
from backend.app.models import ProductRun, ProcessingLog
from backend.app.schemas import SettingsPayload, StatusResponse
from backend.app.services.ai_service import LocalAIService
from backend.app.services.config_store import ConfigStore
from backend.app.services.monitor_service import MonitorManager
from backend.app.services.printify_service import PrintifyClient

router = APIRouter()
ai_service = LocalAIService(settings.ollama_model)

UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------- PRINTIFY ---------------- #

def get_printify_from_config(config: Dict) -> PrintifyClient:
    key = config.get("printify_api_key") or settings.printify_api_key
    shop = config.get("printify_shop_id") or settings.printify_shop_id
    if not key or not shop:
        raise RuntimeError("Printify API key and shop ID are required")
    return PrintifyClient(key, shop)


# ---------------- SETTINGS ---------------- #

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return ConfigStore(db).get("settings", {})


@router.post("/settings")
def set_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    ConfigStore(db).set("settings", payload.model_dump())
    return {"ok": True}


@router.post("/settings/reset")
def reset_settings(db: Session = Depends(get_db)):
    ConfigStore(db).set("settings", SettingsPayload().model_dump())
    return {"ok": True}


# ---------------- HEALTH ---------------- #

@router.get("/health")
def health_check():
    return {"ok": True, "service": "printify-auto"}


# ---------------- ANALYZE ---------------- #

@router.post("/analyze")
def analyze_uploaded(file: UploadFile = File(...)):
    temp_path = UPLOAD_DIR / file.filename

    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    analysis = ai_service.analyze_image(str(temp_path))
    listing = ai_service.generate_listing(analysis)

    return {
        "analysis": analysis,
        "listing": listing
    }


# ---------------- DRAFT ---------------- #

@router.post("/draft")
def draft_uploaded(file: UploadFile = File(...), db: Session = Depends(get_db)):

    temp_path = UPLOAD_DIR / file.filename

    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    config = ConfigStore(db).get("settings", {})

    if not config.get("blueprint_id") or not config.get("print_provider_id"):
        raise HTTPException(400, "Blueprint & Provider missing in settings")

    printify = get_printify_from_config(config)

    analysis = ai_service.analyze_image(str(temp_path))
    listing = ai_service.generate_listing(analysis)

    upload = printify.upload_image(str(temp_path))

    variants = printify.get_variants(
        int(config["blueprint_id"]),
        int(config["print_provider_id"])
    )[:100]

    enabled_variants = [
        {
            "id": int(v["id"]),
            "price": int(v.get("price", 1999)),
            "is_enabled": True,
        }
        for v in variants
    ]

    description = f"{' '.join(listing['bullets'])}\n\n{listing['description']}"

    product = printify.create_draft_product(
        title=listing["title"],
        description=description,
        tags=listing["tags"],
        blueprint_id=int(config["blueprint_id"]),
        provider_id=int(config["print_provider_id"]),
        uploaded_image_id=upload["id"],
        variants=enabled_variants,
        mockup_ids=[],
    )

    return {
        "ok": True,
        "printify_product_id": product.get("id")
    }


# ---------------- DASHBOARD ---------------- #

@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(ProductRun.id)).scalar() or 0
    total_logs = db.query(func.count(ProcessingLog.id)).scalar() or 0
    error_logs = db.query(func.count(ProcessingLog.id)).filter(ProcessingLog.level == "ERROR").scalar() or 0

    return {
        "total_products": total,
        "draft_products": total,
        "total_logs": total_logs,
        "error_logs": error_logs,
    }
