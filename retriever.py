"""Agent 2: Retriever.

Searches eBay within Watch Scanner's constraints and builds a structured
dataset of listings, downloading a thumbnail image for each.
"""

import json
import os
import re
from pathlib import Path

import requests

from ebay_client import EbayClient

DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = DATA_DIR / "images"

# eBay category for wristwatches. Without it a keyword search returns straps,
# bracelet links, buckles and unrelated models alongside the watches, which
# poisons any median built from the results: a search for "Grand Seiko
# SBGA211" returns 136 EUR straps next to 5,000 EUR watches.
WRISTWATCH_CATEGORY = "31387"
# Second line of defence for the comparables: a listing far outside the
# target's expected range is a different product, not a data point about this
# one — a spare bracelet at one end, a limited edition at the other.
COMP_RANGE = (0.4, 2.5)


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


def _is_valid_comp(listing, criteria, target):
    """A comparable must be the same product, priced in the same currency.
    Anything far outside the target's expected range is something else."""
    price = listing.get("price", {})
    if price.get("currency") != criteria.currency:
        return False
    try:
        value = float(price.get("value", 0))
    except (TypeError, ValueError):
        return False

    low, high = COMP_RANGE
    return target.market_reference * low <= value <= target.market_reference * high


def _download_image(url, item_id):
    """eBay serves the same photo at several sizes from one path, and the
    search response points at the 225px thumbnail. Nothing that matters
    visually — dial printing, branding, case wear — survives at that size, so
    ask for the full-size file and fall back to the thumbnail if it is absent.
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    safe_id = item_id.replace("|", "_")
    path = IMAGES_DIR / f"{safe_id}{ext}"

    full_size = re.sub(r"/s-l\d+\.", "/s-l1600.", url)
    for candidate in (full_size, url):
        response = requests.get(candidate, timeout=10)
        if response.ok:
            path.write_bytes(response.content)
            return str(path)
    response.raise_for_status()


def collect(criteria, client=None, limit_per_model=25):
    """Returns (dataset, comps_by_target).

    The dataset is what fits the budget and condition rules. The comps are
    every listing seen for a target regardless of price — market value is set
    by the whole market, including pieces above what we can afford, so
    filtering comps to our budget would bias the baseline downwards.
    """
    client = client or EbayClient()
    dataset = []
    comps_by_target = {}
    seen_ids = set()

    for target in criteria.targets:
        comps = comps_by_target.setdefault(target.model, [])
        for term in target.search_terms:
            for listing in client.search(term, limit=limit_per_model, category_ids=WRISTWATCH_CATEGORY):
                if listing["itemId"] in seen_ids:
                    continue

                if _is_valid_comp(listing, criteria, target):
                    comps.append(listing)

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

    return dataset, comps_by_target
