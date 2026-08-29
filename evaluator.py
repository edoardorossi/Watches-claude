"""Agent 3: Evaluator.

Critically assesses listings collected by Retriever against Watch
Scanner's criteria and produces a score with personalized suggestions.
"""

import json
import re
from pathlib import Path

import pricing

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


def _score_price(analysis, reasons):
    """Margin is the point of the exercise, so it carries the most weight —
    but a price far under market is a warning, not a discount."""
    if not analysis:
        reasons.append("Nessun riferimento di mercato affidabile: valutare manualmente prima di trattare.")
        return 0

    if analysis["suspiciously_cheap"]:
        reasons.append(
            f"Prezzo al {analysis['discount_vs_market']:.0%} sotto mercato: a questo scarto "
            "è più probabile un falso, un pezzo assemblato o una truffa che un affare."
        )
        return -25

    margin_pct = analysis["margin_pct"]
    margin_eur = analysis["margin_eur"]

    if margin_pct >= 0.15:
        reasons.append(
            f"Margine netto stimato {margin_pct:.0%} ({margin_eur:+.0f} EUR) dopo commissioni, "
            "spedizione ed eventuale service: rivendibile con profitto reale."
        )
        return 30
    if margin_pct >= 0.05:
        reasons.append(
            f"Margine netto stimato {margin_pct:.0%} ({margin_eur:+.0f} EUR): sottile, "
            "va trattato sul prezzo per avere senso in ottica rivendita."
        )
        return 10
    if margin_pct >= 0:
        reasons.append(
            f"Margine netto stimato {margin_pct:.0%} ({margin_eur:+.0f} EUR): di fatto pari, "
            "si compra solo per tenerlo, non per rivenderlo."
        )
        return -5

    reasons.append(
        f"Margine netto stimato {margin_pct:.0%} ({margin_eur:+.0f} EUR): rivendendo si perde, "
        "il prezzo è sopra mercato una volta contati i costi."
    )
    return -25


def _score(listing, criteria):
    score = 50
    reasons = []
    title = listing["title"]

    score += _score_price(listing.get("pricing"), reasons)

    if listing.get("tier") == "A":
        score += 10
        reasons.append("Tier A: tra le poche referenze sotto i 4k con apprezzamento storicamente dimostrato.")

    if _has_reference(title, criteria.premium_references):
        score += 10
        reasons.append("Referenza specifica ad alta domanda dichiarata nel titolo.")

    # Only the title is available at search time, and sellers put box and
    # papers in the description far more often than in 80 characters of
    # title. Absence of the words is therefore not evidence of absence of
    # the box: reward the declaration, but never penalise its silence.
    if _mentions(title, FULL_SET_KEYWORDS):
        score += 15
        reasons.append("Full set dichiarato: a questo budget scatola e documenti valgono il 15-25% del prezzo.")
    elif criteria.require_full_set:
        reasons.append("Full set da verificare: il titolo non lo dice, chiedere foto di scatola, garanzia e punzonatura.")

    if _mentions(title, ORIGINALITY_KEYWORDS):
        score += 10
        reasons.append("Originalità di cassa/quadrante dichiarata: è il fattore che regge il valore sul vintage.")

    if _mentions(title, SERVICE_KEYWORDS):
        score += 5
        reasons.append("Service dichiarato: evita un costo nascosto di 400-900 EUR.")

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


def evaluate(listings, criteria, comps_by_target=None):
    comps_by_target = comps_by_target or {}
    targets_by_model = {t.model: t for t in criteria.targets}

    evaluated = []
    for listing in listings:
        target = targets_by_model.get(listing.get("model_family"))
        analysis = None
        if target:
            baseline, source = pricing.market_baseline(
                listing["title"], comps_by_target.get(target.model, [])
            )
            analysis = pricing.resale_analysis(
                float(listing["price"]["value"]),
                baseline,
                needs_service=target.vintage and not _mentions(listing["title"], SERVICE_KEYWORDS),
            )
            if analysis:
                analysis["baseline_source"] = source

        listing = {**listing, "pricing": analysis}
        score, reasons = _score(listing, criteria)

        # Margin is the purpose of the exercise, not one factor among many:
        # a piece that loses money on resale cannot qualify however good it
        # looks otherwise, and a price far under market is a fraud signal
        # rather than an opportunity.
        blocker = None
        if not analysis:
            blocker = "nessun riferimento di mercato affidabile"
        elif analysis["suspiciously_cheap"]:
            blocker = f"prezzo al {analysis['discount_vs_market']:.0%} sotto mercato, rischio falso o truffa"
        elif analysis["margin_pct"] < pricing.MIN_RESALE_MARGIN:
            blocker = f"margine netto {analysis['margin_pct']:.0%}, sotto la soglia del {pricing.MIN_RESALE_MARGIN:.0%}"

        evaluated.append(
            {
                **listing,
                "score": score,
                "qualifies_for_resale": blocker is None,
                "disqualified_because": blocker,
                "suggestions": reasons,
            }
        )

    # Qualifying pieces first, then by margin in euro — the ranking a buyer
    # acts on, not the prettiest listing.
    evaluated.sort(
        key=lambda item: (
            item["qualifies_for_resale"],
            item["pricing"]["margin_eur"] if item.get("pricing") else float("-inf"),
            item["score"],
        ),
        reverse=True,
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "evaluations.json").write_text(json.dumps(evaluated, indent=2, ensure_ascii=False))

    return evaluated
