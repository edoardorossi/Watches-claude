"""Fair-value and resale-margin analysis.

Two facts drive every number here:

1. eBay's Browse API returns *active* listings, i.e. asking prices, not
   realized transaction prices. Asking prices sit consistently above what
   pieces actually sell for, so any baseline built from them must be
   discounted before it is treated as market value.

2. A discount off market is not a margin. Selling a watch costs roughly 13%
   in platform and payment fees, plus insured shipping, plus a service if the
   piece has not had one. Buying 15% under market and reselling is close to
   break-even, not a 15% gain. The margin reported here is net of all of that.
"""

import collections
import re
import statistics

# Reference-like tokens: SBGA211, 79030N, 250.8.86, Q2608110, 6146-8020,
# IW327001, 3570.50. A token needs at least three digits to qualify.
_REF_TOKEN = re.compile(r"\b[A-Za-z]{0,5}[0-9][A-Za-z0-9.\-/]{2,}\b")
# Sizes and years look like references but are not: "41MM", "300M", "1969".
# Four-digit numbers inside this window are years, and no target reference
# falls in it (Rolex 1601 and 5500 sit outside by construction).
_SIZE_TOKEN = re.compile(r"^\d+\s*MM?$", re.IGNORECASE)
_YEAR_RANGE = range(1900, 2031)


def extract_references(title):
    """Reference numbers mentioned in a listing title."""
    refs = set()
    for match in _REF_TOKEN.finditer(title):
        # Sellers write "Q2608110/260.8.86": each half is a reference another
        # listing may quote on its own, so both must be usable for matching.
        for token in match.group(0).upper().split("/"):
            token = token.strip(".-")
            if len(token) < 4 or sum(c.isdigit() for c in token) < 3:
                continue
            if _SIZE_TOKEN.match(token) or (token.isdigit() and int(token) in _YEAR_RANGE):
                continue
            refs.add(token)

            # "ST145.022" and "145.022" are the same reference with and
            # without a case-code prefix. Only keep the bare form when it is
            # still distinctive enough to not collide by accident.
            bare = re.sub(r"^[A-Z]+", "", token)
            if bare != token and sum(c.isdigit() for c in bare) >= 4:
                refs.add(bare)
    return refs

# eBay final value fee for watches plus payment processing. Varies by
# category and seller tier; 13% is a realistic all-in figure for a
# private seller.
PLATFORM_FEE_RATE = 0.13
INSURED_SHIPPING_EUR = 40
# Midpoint of the 400-900 EUR range a full service costs on a mechanical
# piece from any of the target brands.
SERVICE_COST_EUR = 650
# Asking prices run above realized prices. This converts a baseline built
# from active listings into an expected realized resale price.
ASKING_TO_REALIZED = 0.90

# A median over too few comparables is noise, not a market. Below this the
# configured reference value is used instead.
MIN_COMPS = 5
# Below this fraction of market, a listing is far more often a fake, a
# franken, a stolen piece or a scam than a bargain. Treated as a red flag.
TOO_GOOD_TO_BE_TRUE = 0.55
# Minimum net margin for a piece to count as a resale candidate at all.
# Below this the trade does not pay for the risk and the capital tied up.
MIN_RESALE_MARGIN = 0.05


def market_baseline(candidate_title, comps):
    """Fair market value for one specific piece.

    A baseline is only meaningful across the same product. Pooling every hit
    for a model name mixes men's and ladies' sizes, quartz and mechanical,
    base and limited editions — a Reverso search spans 3,500 to 9,000 EUR —
    and a median over that invents margins that do not exist. So comparables
    are restricted to listings quoting the same reference number, and when
    too few of those exist we report no baseline rather than a wrong one.
    """
    candidate_refs = extract_references(candidate_title)
    if not candidate_refs:
        return None, "referenza non identificabile dal titolo"

    prices = []
    matches_per_ref = collections.Counter()
    for listing in comps:
        shared = candidate_refs & extract_references(listing.get("title", ""))
        if not shared:
            continue
        try:
            prices.append(float(listing["price"]["value"]))
        except (KeyError, TypeError, ValueError):
            continue
        matches_per_ref.update(shared)

    if len(prices) < MIN_COMPS:
        return None, f"solo {len(prices)} annunci della stessa referenza, troppo pochi per un riferimento"

    # Titles also carry seller inventory codes, which look like references but
    # match nothing. Name the baseline after the token that actually matched
    # the most comparables, so the reported source is the real reference.
    ref = matches_per_ref.most_common(1)[0][0]
    return statistics.median(prices), f"mediana di {len(prices)} annunci della referenza {ref}"


def resale_analysis(buy_price, baseline, needs_service):
    """Net margin on reselling at market, after fees, shipping and service."""
    if not baseline:
        return None

    expected_resale = baseline * ASKING_TO_REALIZED
    net_proceeds = expected_resale * (1 - PLATFORM_FEE_RATE) - INSURED_SHIPPING_EUR

    total_cost = buy_price + (SERVICE_COST_EUR if needs_service else 0)
    margin_eur = net_proceeds - total_cost

    return {
        "baseline": round(baseline, 2),
        "discount_vs_market": round(1 - (buy_price / baseline), 4),
        "expected_resale": round(expected_resale, 2),
        "net_proceeds": round(net_proceeds, 2),
        "total_cost": round(total_cost, 2),
        "margin_eur": round(margin_eur, 2),
        "margin_pct": round(margin_eur / total_cost, 4) if total_cost else None,
        "suspiciously_cheap": buy_price < baseline * TOO_GOOD_TO_BE_TRUE,
    }
