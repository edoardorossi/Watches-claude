"""Agent 3: Evaluator.

Critically assesses listings collected by Retriever against Watch
Scanner's criteria and produces a score with personalized suggestions.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

FULL_SET_KEYWORDS = ["full set", "box and papers", "box & papers", "scatola e documenti", "garanzia"]
RED_FLAG_KEYWORDS = ["replica", "fake", "for parts", "non funzionante", "da riparare", "custom"]


def _has_any(text, keywords):
    text = text.lower()
    return any(k in text for k in keywords)


def _score(listing, criteria):
    score = 50
    reasons = []
    title = listing["title"]

    if any(ref.split()[-1] in title for ref in criteria.discontinued_models):
        score += 10
        reasons.append("Riferimento discontinuato: storicamente più propenso ad apprezzarsi.")

    if _has_any(title, FULL_SET_KEYWORDS):
        score += 15
        reasons.append("Full set (scatola/documenti) dichiarato: mantiene meglio il valore alla rivendita.")
    elif criteria.require_full_set:
        score -= 15
        reasons.append("Full set non dichiarato nel titolo: verificare con il venditore prima di procedere.")

    if _has_any(title, RED_FLAG_KEYWORDS):
        score -= 40
        reasons.append("Termini sospetti nel titolo (possibile replica o pezzo non originale).")

    feedback = listing.get("seller_feedback_score", 0)
    if feedback >= criteria.min_seller_feedback_score:
        score += 10
        reasons.append(f"Venditore con buona reputazione ({feedback} feedback).")
    else:
        score -= 10
        reasons.append(f"Venditore con reputazione limitata ({feedback} feedback): richiedere garanzie aggiuntive.")

    return max(0, min(100, score)), reasons


def evaluate(listings, criteria):
    evaluated = []
    for listing in listings:
        score, reasons = _score(listing, criteria)
        evaluated.append({**listing, "score": score, "suggestions": reasons})

    evaluated.sort(key=lambda item: item["score"], reverse=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "evaluations.json").write_text(json.dumps(evaluated, indent=2, ensure_ascii=False))

    return evaluated
