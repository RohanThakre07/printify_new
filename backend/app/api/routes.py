from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, get_db
from backend.app.services.ai_service import LocalAIService
from backend.app.services.config_store import ConfigStore
from backend.app.services.monitor_service import MonitorManager
from backend.app.services.printify_service import PrintifyClient

router = APIRouter()
ai_service = LocalAIService(settings.ollama_model)

UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------- PRINTIFY ----------------

def get_printify_from_config(config: Dict) -> PrintifyClient:
    key = config.get("printify_api_key") or settings.printify_api_key
    shop = config.get("printify_shop_id") or settings.printify_shop_id
    if not key or not shop:
        raise RuntimeError("Printify API key and shop ID are required")
    return PrintifyClient(key, shop)


def calculate_price(variant: Dict, base_price: float | None, profit_percent: float | None) -> int:
    if base_price is not None:
        return int(round(base_price * 100))
    cost_cents = int(variant.get("cost", 1000))
    margin = float(profit_percent or 30) / 100
    return int(round(cost_cents * (1 + margin)))


def ensure_variant_selection(config: Dict, printify: PrintifyClient) -> List[Dict]:
    variants = printify.get_variants(
        int(config["blueprint_id"]),
        int(config["print_provider_id"])
    )

    safe_variants = variants[:100]

    normalized = []
    for v in safe_variants:
        normalized.append(
            {
                "variant_id": int(v["id"]),
                "enabled": True,
                "price": calculate_price(
                    v,
                    config.get("base_price"),
                    config.get("profit_percent"),
                ),
            }
        )
    return normalized


# ---------------- AI PROCESSOR ----------------

def run_processor(image_path: str):
    db = SessionLocal()
    try:
        config = ConfigStore(db).get("settings", {})
    finally:
        db.close()

    printify = get_printify_from_config(config)

    analysis = ai_service.analyze_image(image_path)
    listing = ai_service.generate_listing(analysis)
    upload = printify.upload_image(image_path)
    variants = ensure_variant_selection(config, printify)

    description = f"{' '.join(listing['bullets'])}\n\n{listing['description']}"

    product = printify.create_draft_product(
        title=listing["title"],
        description=description,
        tags=listing["tags"],
        blueprint_id=int(config["blueprint_id"]),
        provider_id=int(config["print_provider_id"]),
        uploaded_image_id=upload["id"],
        variants=variants,
        mockup_ids=config.get("selected_mockups", []),
    )

    return {
        "analysis_json": json.dumps(analysis),
        "listing_json": json.dumps(listing),
        "printify_upload_id": upload.get("id"),
        "printify_product_id": product.get("id"),
    }


monitor_manager = MonitorManager(SessionLocal, run_processor)


# ---------------- HEALTH ----------------

@router.get("/health")
def health_check():
    return {"ok": True, "service": "printify-auto"}


# ---------------- ANALYZE ----------------

@router.post("/analyze")
async def analyze_uploaded(file: UploadFile = File(...)):
    try:
        temp_path = UPLOAD_DIR / file.filename

        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        analysis = ai_service.analyze_image(str(temp_path))
        listing = ai_service.generate_listing(analysis)

        return {
            "analysis": analysis,
            "listing": listing,
            "uploaded_path": str(temp_path)
        }

    except Exception as e:
        raise HTTPException(500, str(e))


# ---------------- DRAFT ----------------

@router.post("/draft")
async def draft_uploaded(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        temp_path = UPLOAD_DIR / file.filename

        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        config = ConfigStore(db).get("settings", {})
        printify = get_printify_from_config(config)

        analysis = ai_service.analyze_image(str(temp_path))
        listing = ai_service.generate_listing(analysis)

        upload = printify.upload_image(str(temp_path))

        variants = ensure_variant_selection(config, printify)

        description = f"{' '.join(listing['bullets'])}\n\n{listing['description']}"

        product = printify.create_draft_product(
            title=listing["title"],
            description=description,
            tags=listing["tags"],
            blueprint_id=int(config["blueprint_id"]),
            provider_id=int(config["print_provider_id"]),
            uploaded_image_id=upload["id"],
            variants=variants,
            mockup_ids=config.get("selected_mockups", []),
        )

        return {
            "ok": True,
            "printify_upload_id": upload.get("id"),
            "printify_product_id": product.get("id")
        }

    except Exception as e:
        return {"error": str(e)}
