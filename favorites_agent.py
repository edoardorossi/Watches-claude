"""Agent 4: My Favorite.

Autonomous — saves watches above the score threshold without user
confirmation.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
FAVORITES_FILE = DATA_DIR / "favorites.json"
SCORE_THRESHOLD = 70


def _load_existing():
    if FAVORITES_FILE.exists():
        return json.loads(FAVORITES_FILE.read_text())
    return []


def save(evaluated, threshold=SCORE_THRESHOLD):
    existing = _load_existing()
    existing_ids = {item["item_id"] for item in existing}

    new_favorites = [
        item for item in evaluated if item["score"] >= threshold and item["item_id"] not in existing_ids
    ]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FAVORITES_FILE.write_text(json.dumps(existing + new_favorites, indent=2, ensure_ascii=False))

    return new_favorites
