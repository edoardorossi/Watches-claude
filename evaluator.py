"""Agent 3: Evaluator.

Critically assesses listings collected by Retriever against Watch
Scanner's criteria and produces a score with personalized suggestions.
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

FULL_SET_KEYWORDS = [
    "full set",
    "box and papers",
    "box & papers",
    "scatola e documenti",
    "scatola e garanzia",
    "completo di scatola",
    "con documenti",
    "garanzia originale",
]
# On vintage, an over-polished case or a refinished dial is the single
# largest value destroyer — worth more than most other factors combined.
ORIGINALITY_KEYWORDS = ["non lucidato", "unpolished", "quadrante originale", "original dial"]
SERVICE_KEYWORDS = ["revisionato", "serviced", "tagliando", "service completo"]


def _mentions(text, keywords):
    text = text.lower()
    return any(k in text for k in keywords)


def _has_reference(title, references):
    return any(re.search(rf"\b{re.escape(ref)}\b", title, re.IGNORECASE) for ref in references)


def _score(listing, criteria):
    score = 50
    reasons = []
    title = listing["title"]

    if listing.get("tier") == "A":
        score += 10
        reasons.append("Tier A: tra le poche referenze sotto i 4k con apprezzamento storicamente dimostrato.")

    if _has_reference(title, criteria.premium_references):
        score += 10
        reasons.append("Referenza specifica ad alta domanda dichiarata nel titolo.")

    if _mentions(title, FULL_SET_KEYWORDS):
        score += 15
        reasons.append("Full set dichiarato: a questo budget scatola e documenti valgono il 15-25% del prezzo.")
    elif criteria.require_full_set:
        score -= 15
        reasons.append("Full set non dichiarato: chiedere foto di scatola, garanzia e punzonatura prima di trattare.")

    if _mentions(title, ORIGINALITY_KEYWORDS):
        score += 10
        reasons.append("Originalità di cassa/quadrante dichiarata: è il fattore che regge il valore sul vintage.")

    if _mentions(title, SERVICE_KEYWORDS):
        score += 5
        reasons.append("Service dichiarato: evita un costo nascosto di 400-900 EUR.")
    else:
        reasons.append("Nessun service dichiarato: preventivare 400-900 EUR di revisione nel costo reale.")

    if _mentions(title, criteria.exclude_keywords):
        score -= 40
        reasons.append("Termini che segnalano replica, pezzo assemblato o quadrante rifatto: da evitare.")

    if any(brand.lower() in title.lower() for brand in criteria.avoid_brands):
        score -= 20
        reasons.append("Marchio con tenuta di valore storicamente debole sul secondario.")

    feedback = listing.get("seller_feedback_score", 0)
    if feedback >= criteria.min_seller_feedback_score:
        score += 10
        reasons.append(f"Venditore con reputazione solida ({feedback} feedback).")
    else:
        score -= 15
        reasons.append(
            f"Venditore poco tracciato ({feedback} feedback): a questa fascia il rischio frode è concreto, "
            "pretendere garanzie o pagamento tutelato."
        )

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
