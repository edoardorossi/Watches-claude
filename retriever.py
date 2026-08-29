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


def _price_ok(listing, criteria, target):
    price = listing.get("price", {})
    try:
        value = float(price.get("value", 0))
    except (TypeError, ValueError):
        return False
    if price.get("currency") != criteria.currency:
        return False
    # The per-target band is the real filter; the total budget is a hard ceiling
    # no listing may cross, whatever the target allows.
    return target.price_min <= value <= min(target.price_max, criteria.budget_total)


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
    seen_ids = set()

    for target in criteria.targets:
        for term in target.search_terms:
            for listing in client.search(term, limit=limit_per_model):
                if listing["itemId"] in seen_ids:
                    continue
                if not _price_ok(listing, criteria, target) or not _condition_ok(listing, criteria):
                    continue

                image_url = listing.get("image", {}).get("imageUrl")
                image_path = None
                if image_url:
                    try:
                        image_path = _download_image(image_url, listing["itemId"])
                    except requests.RequestException:
                        image_path = None

                seen_ids.add(listing["itemId"])
                dataset.append(
                    {
                        "item_id": listing["itemId"],
                        "brand": target.brand,
                        "model_family": target.model,
                        "tier": target.tier,
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
