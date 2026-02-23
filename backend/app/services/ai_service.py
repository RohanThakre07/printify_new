from __future__ import annotations
import json
import requests
from pathlib import Path
from typing import Dict
from PIL import Image

OPENROUTER_API_KEY = "USE_ENV"

class LocalAIService:

    def __init__(self, model="openrouter/auto"):
        self.model = model

    def analyze_image(self, image_path: str) -> Dict:
        filename = Path(image_path).stem

        prompt = f"""
Analyze this POD design name: {filename}

Return JSON:
theme
style
mood
target_audience
caption
"""

        result = self._llm(prompt)

        return {
            "theme": result.get("theme", "Graphic"),
            "style": result.get("style", "Modern"),
            "mood": result.get("mood", "Neutral"),
            "target_audience": result.get("target_audience", "Men Women"),
            "caption": result.get("caption", filename)
        }

    def generate_listing(self, analysis: Dict) -> Dict:

        prompt = f"""
Generate Amazon SEO listing for POD apparel.

Input:
{json.dumps(analysis)}

Return JSON:
title
bullets (5)
description
tags (10)
"""

        result = self._llm(prompt)

        return {
            "title": result.get("title","Graphic T-Shirt"),
            "bullets": result.get("bullets",[]),
            "description": result.get("description",""),
            "tags": result.get("tags",[])
        }

    def _llm(self, prompt):

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "openrouter/auto",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )

        try:
            return json.loads(r.json()['choices'][0]['message']['content'])
        except:
            return {}
