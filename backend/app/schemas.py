from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VariantSelection(BaseModel):
    variant_id: int
    enabled: bool = True
    price: int = 1999


class SettingsPayload(BaseModel):
    watch_folder: str = ""
    printify_api_key: str = ""
    printify_shop_id: str = ""

    blueprint_id: int = 0
    print_provider_id: int = 0

    base_price: Optional[float] = None
    profit_percent: Optional[float] = 30.0

    selected_variants: List[VariantSelection] = Field(default_factory=list)
    selected_mockups: List[str] = Field(default_factory=list)

    copy_previous: bool = True


class StatusResponse(BaseModel):
    monitoring: bool
    watch_folder: str
    queue_size: int
    current_file: Optional[str] = None


class AnalysisOutput(BaseModel):
    theme: str
    objects: List[str]
    style: str
    mood: str
    target_audience: str
    caption: str


class ListingOutput(BaseModel):
    title: str
    bullets: List[str]
    description: str
    tags: List[str]


class AnalyzeRequest(BaseModel):
    image_path: str


class DraftRequest(BaseModel):
    image_path: str
    analysis: Optional[Dict[str, Any]] = None
    listing: Optional[Dict[str, Any]] = None


class QueueItemResponse(BaseModel):
    ok: bool
    queued_path: str
