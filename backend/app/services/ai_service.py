from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import ollama
from PIL import Image


class LocalAIService:
    """AI service with graceful fallback when BLIP or Ollama is unavailable."""

    def __init__(self, ollama_model: str):
        self.ollama_model = ollama_model
        self._captioner = None
        self._captioner_error: str | None = None

    @property
    def captioner(self):
        if self._captioner is not None or self._captioner_error is not None:
            return self._captioner

        try:
            from transformers import pipeline  # type: ignore

            self._captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
        except Exception as exc:
            self._captioner_error = str(exc)
            self._captioner = None

        return self._captioner

    def _caption_image(self, image_path: str) -> str:
        captioner = self.captioner
        if captioner is None:
            return Path(image_path).stem.replace("_", " ").replace("-", " ").strip() or "design"

        image = Image.open(image_path).convert("RGB")
        result = captioner(image)
        return result[0].get("generated_text", "") if result else ""

    def _ollama_json(self, prompt: str) -> Dict:
        try:
            raw = ollama.generate(model=self.ollama_model, prompt=prompt).get("response", "{}")
        except Exception:
            return {}
        return self._safe_json(raw)

    def analyze_image(self, image_path: str) -> Dict:
        caption = self._caption_image(image_path)

        prompt = (
            "Return strict JSON only with keys: theme, objects(array), style, mood, target_audience. "
            "You are classifying design intent for print-on-demand ecommerce. "
            f"Caption: {caption}"
        )
        parsed = self._ollama_json(prompt)

        result = {
            "theme": parsed.get("theme", "general"),
            "objects": parsed.get("objects", self._caption_words(caption)),
            "style": parsed.get("style", "graphic design"),
            "mood": parsed.get("mood", "neutral"),
            "target_audience": parsed.get("target_audience", "general"),
            "caption": caption,
        }
        if self._captioner_error:
            result["captioner_warning"] = "BLIP unavailable; using filename caption fallback"
        if not parsed:
            result["llm_warning"] = "Ollama unavailable; using deterministic fallback analysis"
        return result

    def generate_listing(self, analysis: Dict) -> Dict:
        prompt = (
            "Return strict JSON only with keys: title(string), bullets(array of 5 strings), description(string), tags(array of <=10 short strings). "
            "Generate natural, human-sounding, Amazon-optimized copy for a POD apparel listing. "
            f"Input analysis: {json.dumps(analysis)}"
        )
        parsed = self._ollama_json(prompt)

        bullets = parsed.get("bullets") or []
        while len(bullets) < 5:
            bullets.append("High-quality print-ready design with strong visual appeal.")

        tags: List[str] = [str(t).strip()[:20] for t in (parsed.get("tags") or []) if str(t).strip()]
        if not tags:
            tags = [str(x)[:20] for x in analysis.get("objects", [])][:10]

        listing = {
            "title": parsed.get("title", f"{analysis.get('theme', 'Unique')} Graphic Shirt"),
            "bullets": bullets[:5],
            "description": parsed.get("description", "A unique print-on-demand design for everyday wear."),
            "tags": tags[:10],
        }
        if not parsed:
            listing["llm_warning"] = "Ollama unavailable; using deterministic fallback listing"
        return listing

    @staticmethod
    def _safe_json(text: str) -> Dict:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    return {}
            return {}

    @staticmethod
    def _caption_words(caption: str) -> List[str]:
        words = [w.strip(".,!?:;\"'()[]{}") for w in caption.split()]
        words = [w for w in words if w]
        return words[:6] or ["design"]
