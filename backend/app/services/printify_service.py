from __future__ import annotations

import base64
from pathlib import Path
from typing import Dict, List

import requests


class PrintifyClient:
    BASE_URL = "https://api.printify.com/v1"

    def __init__(self, api_key: str, shop_id: str):
        self.api_key = api_key
        self.shop_id = shop_id

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "printify-auto-local/1.0",
        }

    def _request(self, method: str, path: str, **kwargs) -> Dict:
        url = f"{self.BASE_URL}{path}"
        response = requests.request(method, url, headers=self.headers, timeout=90, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"Printify API error {response.status_code}: {response.text}")
        return response.json() if response.text else {}

    def upload_image(self, image_path: str) -> Dict:
        image_bytes = Path(image_path).read_bytes()
        payload = {
            "file_name": Path(image_path).name,
            "contents": base64.b64encode(image_bytes).decode("utf-8"),
        }
        return self._request("POST", "/uploads/images.json", json=payload)

    def get_variants(self, blueprint_id: int, provider_id: int) -> List[Dict]:
        data = self._request(
            "GET", f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json"
        )
        return data.get("variants", [])

    def get_print_areas(self, blueprint_id: int, provider_id: int) -> List[Dict]:
        data = self._request(
            "GET", f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/print_areas.json"
        )
        return data.get("print_areas", [])

    def get_mockup_candidates(self, blueprint_id: int, provider_id: int) -> List[Dict]:
        areas = self.get_print_areas(blueprint_id, provider_id)
        options: List[Dict] = []
        for area in areas:
            for placeholder in area.get("placeholders", []):
                position = placeholder.get("position", "front")
                options.append(
                    {
                        "mockup_id": position,
                        "display_name": position.replace("_", " ").title(),
                        "image_url": None,
                    }
                )
        dedup = {}
        for opt in options:
            dedup[opt["mockup_id"]] = opt
        return list(dedup.values())

    def create_draft_product(
        self,
        title: str,
        description: str,
        tags: List[str],
        blueprint_id: int,
        provider_id: int,
        uploaded_image_id: str,
        variants: List[Dict],
        mockup_ids: List[str],
    ) -> Dict:
        enabled_variants = [
            {
                "id": int(v["variant_id"]),
                "price": int(v["price"]),
                "is_enabled": True,
            }
            for v in variants
            if v.get("enabled", True)
        ]
        if not enabled_variants:
            raise RuntimeError("No variants selected.")

        print_areas = self.get_print_areas(blueprint_id, provider_id)
        placeholders = []
        for area in print_areas:
            for p in area.get("placeholders", []):
                position = p.get("position", "front")
                if (not mockup_ids) or (position in mockup_ids):
                    placeholders.append(
                        {
                            "position": position,
                            "images": [
                                {
                                    "id": uploaded_image_id,
                                    "x": 0.5,
                                    "y": 0.5,
                                    "scale": 1,
                                    "angle": 0,
                                }
                            ],
                        }
                    )

        if not placeholders:
            placeholders = [
                {
                    "position": "front",
                    "images": [{"id": uploaded_image_id, "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}],
                }
            ]

        payload = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id,
            "print_provider_id": provider_id,
            "tags": tags,
            "variants": enabled_variants,
            "print_areas": [
                {
                    "variant_ids": [v["id"] for v in enabled_variants],
                    "placeholders": placeholders,
                }
            ],
            "visible": False,
        }
        return self._request("POST", f"/shops/{self.shop_id}/products.json", json=payload)
