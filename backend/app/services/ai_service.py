from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from PIL import Image


class LocalAIService:
    """Render-safe AI fallback system (100% free)."""

    def __init__(self, ollama_model: str | None = None):
        self.ollama_model = ollama_model

    def analyze_image(self, image_path: str) -> Dict:

        name_caption = Path(image_path).stem.replace("_", " ").replace("-", " ").strip()

        theme = self._detect_theme(name_caption)
        style = self._detect_style(name_caption)
        audience = self._detect_audience(name_caption)

        return {
            "theme": theme,
            "objects": self._caption_words(name_caption),
            "style": style,
            "mood": "neutral",
            "target_audience": audience,
            "caption": name_caption
        }

    def generate_listing(self, analysis: Dict) -> Dict:

        theme = analysis.get("theme", "Graphic")
        objects = analysis.get("objects", [])
        style = analysis.get("style", "Modern")
        audience = analysis.get("target_audience", "Men Women")

        keywords = " ".join(objects[:3])

        title = f"{theme} {keywords} {style} T-Shirt for {audience}"

        bullets = [
            f"Unique {theme.lower()} inspired design",
            f"Perfect for {audience.lower()}",
            f"Modern {style.lower()} style",
            "Great gift for everyday wear",
            "High-quality print-ready artwork"
        ]

        description = (
            f"This {theme.lower()} themed design features {keywords}. "
            f"Designed in a {style.lower()} style for {audience.lower()} who love expressive apparel. "
            "Perfect for casual wear and gifting."
        )

        tags = list(set(objects + [theme, style, audience]))[:10]

        return {
            "title": title.strip(),
            "bullets": bullets,
            "description": description,
            "tags": tags
        }

    def _detect_theme(self, caption: str) -> str:
        caption = caption.lower()
        if any(x in caption for x in ["krishna", "shiva", "ram", "ganesha"]):
            return "Spiritual"
        if any(x in caption for x in ["funny", "joke", "lol"]):
            return "Funny"
        if any(x in caption for x in ["minimal", "simple"]):
            return "Minimalist"
        if any(x in caption for x in ["vintage"]):
            return "Vintage"
        return "Graphic"

    def _detect_style(self, caption: str) -> str:
        caption = caption.lower()
        if "retro" in caption:
            return "Retro"
        if "aesthetic" in caption:
            return "Aesthetic"
        return "Modern"

    def _detect_audience(self, caption: str) -> str:
        caption = caption.lower()
        if "kids" in caption:
            return "Kids"
        if "women" in caption:
            return "Women"
        if "men" in caption:
            return "Men"
        return "Men Women"

    @staticmethod
    def _caption_words(caption: str) -> List[str]:
        words = [w.strip(".,!?:;\"'()[]{}") for w in caption.split()]
        words = [w for w in words if w]
        return words[:6] or ["design"]
