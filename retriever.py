"""Agent 2: Retriever.

Searches eBay within Watch Scanner's constraints and builds a structured
dataset of listings, downloading a thumbnail image for each.
"""

import json
import os
from pathlib import Path

import requests

from ebay_client import EbayClient

DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = DATA_DIR / "images"


def _condition_ok(listing, criteria):
    condition = listing.get("condition", "")
    return any(c.lower() in condition.lower() for c in criteria.conditions_allowed)


def _price_ok(listing, criteria):
    price = listing.get("price", {})
    try:
        value = float(price.get("value", 0))
    except (TypeError, ValueError):
        return False
    return criteria.price_min <= value <= criteria.price_max and price.get("currency") == criteria.currency


def _download_image(url, item_id):
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    safe_id = item_id.replace("|", "_")
    path = IMAGES_DIR / f"{safe_id}{ext}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    path.write_bytes(response.content)
    return str(path)


def collect(criteria, client=None, limit_per_model=25):
    client = client or EbayClient()
    dataset = []

    for model in criteria.models:
        for listing in client.search(f"Rolex {model}", limit=limit_per_model):
            if not _price_ok(listing, criteria) or not _condition_ok(listing, criteria):
                continue

            image_url = listing.get("image", {}).get("imageUrl")
            image_path = None
            if image_url:
                try:
                    image_path = _download_image(image_url, listing["itemId"])
                except requests.RequestException:
                    image_path = None

            dataset.append(
                {
                    "item_id": listing["itemId"],
                    "model_family": model,
                    "title": listing["title"],
                    "price": listing["price"],
                    "condition": listing.get("condition"),
                    "seller_feedback_score": listing.get("seller", {}).get("feedbackScore", 0),
                    "item_url": listing["itemWebUrl"],
                    "image_url": image_url,
                    "image_path": image_path,
                }
            )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "listings.json").write_text(json.dumps(dataset, indent=2, ensure_ascii=False))

    return dataset
