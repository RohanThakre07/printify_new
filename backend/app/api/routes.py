import json
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, get_db
from backend.app.models import ProductRun, ProcessingLog
from backend.app.schemas import AnalyzeRequest, DraftRequest, QueueItemResponse, SettingsPayload, StatusResponse
from backend.app.services.ai_service import LocalAIService
from backend.app.services.config_store import ConfigStore
from backend.app.services.monitor_service import MonitorManager
from backend.app.services.printify_service import PrintifyClient

router = APIRouter()
ai_service = LocalAIService(settings.ollama_model)


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
    selected = config.get("selected_variants", [])
    if not selected:
        variants = printify.get_variants(int(config["blueprint_id"]), int(config["print_provider_id"]))
        selected = [{"variant_id": v["id"], "enabled": True, "price": v.get("price", 1999), "cost": v.get("cost")} for v in variants[:100]]

    if len(selected) > 100:
        raise RuntimeError("Variant selection exceeds Printify limit of 100")

    normalized = []
    for v in selected:
        normalized.append(
            {
                "variant_id": int(v["variant_id"]),
                "enabled": bool(v.get("enabled", True)),
                "price": int(v.get("price") or calculate_price(v, config.get("base_price"), config.get("profit_percent"))),
            }
        )
    return normalized


def run_processor(image_path: str):
    db = SessionLocal()
    try:
        config = ConfigStore(db).get("settings", {})
    finally:
        db.close()

    if not config.get("blueprint_id") or not config.get("print_provider_id"):
        raise RuntimeError("Blueprint ID and Print Provider ID are required")

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



@router.get("/health")
def health_check():
    return {"ok": True, "service": "printify-auto"}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return ConfigStore(db).get("settings", {})


@router.post("/settings")
def set_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if len(data.get("selected_variants", [])) > 100:
        raise HTTPException(400, "Selected variants exceed 100")
    ConfigStore(db).set("settings", data)
    return {"ok": True}


@router.post("/settings/reset")
def reset_settings(db: Session = Depends(get_db)):
    ConfigStore(db).set("settings", SettingsPayload().model_dump())
    return {"ok": True}


@router.post("/monitor/start")
def start_monitor(db: Session = Depends(get_db)):
    config = ConfigStore(db).get("settings", {})
    folder = config.get("watch_folder")
    if not folder:
        raise HTTPException(400, "watch_folder is required")
    monitor_manager.start(folder)
    return {"ok": True}


@router.post("/monitor/stop")
def stop_monitor():
    monitor_manager.stop()
    return {"ok": True}


@router.get("/monitor/status", response_model=StatusResponse)
def monitor_status(db: Session = Depends(get_db)):
    config = ConfigStore(db).get("settings", {})
    return StatusResponse(
        monitoring=monitor_manager.running,
        watch_folder=config.get("watch_folder", ""),
        queue_size=monitor_manager.work_queue.qsize(),
        current_file=monitor_manager.current_file,
    )


@router.post("/queue", response_model=QueueItemResponse)
def queue_manual_image(payload: AnalyzeRequest):
    path = str(Path(payload.image_path))
    if not monitor_manager.enqueue_path(path):
        raise HTTPException(400, "Invalid image path or unsupported extension")
    return QueueItemResponse(ok=True, queued_path=path)


@router.post("/analyze")
def analyze_single(payload: AnalyzeRequest):
    image_path = payload.image_path
    if not Path(image_path).exists():
        raise HTTPException(404, "Image path not found")
    analysis = ai_service.analyze_image(image_path)
    listing = ai_service.generate_listing(analysis)
    return {"analysis": analysis, "listing": listing}


@router.post("/draft")
def draft_single(payload: DraftRequest, db: Session = Depends(get_db)):
    config = ConfigStore(db).get("settings", {})
    printify = get_printify_from_config(config)

    if not Path(payload.image_path).exists():
        raise HTTPException(404, "Image path not found")

    analysis = payload.analysis or ai_service.analyze_image(payload.image_path)
    listing = payload.listing or ai_service.generate_listing(analysis)

    upload = printify.upload_image(payload.image_path)
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

    return {"ok": True, "printify_upload_id": upload.get("id"), "printify_product_id": product.get("id")}


@router.get("/printify/variants")
def fetch_variants(blueprint_id: int, print_provider_id: int, db: Session = Depends(get_db)):
    config = ConfigStore(db).get("settings", {})
    client = get_printify_from_config(config)
    return {"variants": client.get_variants(blueprint_id, print_provider_id)}


@router.get("/printify/mockups")
def fetch_mockups(blueprint_id: int, print_provider_id: int, db: Session = Depends(get_db)):
    config = ConfigStore(db).get("settings", {})
    client = get_printify_from_config(config)
    return {"mockups": client.get_mockup_candidates(blueprint_id, print_provider_id)}


@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(ProductRun).order_by(ProductRun.id.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "image_path": r.image_path,
            "status": r.status,
            "success": r.success,
            "printify_upload_id": r.printify_upload_id,
            "printify_product_id": r.printify_product_id,
            "analysis": json.loads(r.analysis_json) if r.analysis_json else None,
            "listing": json.loads(r.listing_json) if r.listing_json else None,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/logs")
def list_logs(db: Session = Depends(get_db)):
    logs = db.query(ProcessingLog).order_by(ProcessingLog.id.desc()).limit(200).all()
    return [
        {
            "id": l.id,
            "level": l.level,
            "message": l.message,
            "image_path": l.image_path,
            "details": l.details,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(ProductRun.id)).scalar() or 0
    drafts = db.query(func.count(ProductRun.id)).filter(ProductRun.success.is_(True)).scalar() or 0
    total_logs = db.query(func.count(ProcessingLog.id)).scalar() or 0
    error_logs = db.query(func.count(ProcessingLog.id)).filter(ProcessingLog.level == "ERROR").scalar() or 0
    return {
        "total_products": total,
        "draft_products": drafts,
        "total_logs": total_logs,
        "error_logs": error_logs,
    }
