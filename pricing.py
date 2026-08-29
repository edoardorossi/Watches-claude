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

import statistics

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


def market_baseline(target, comps):
    """Fair market value for a target, preferring live comparables over the
    configured reference. Returns (value, source)."""
    prices = []
    for listing in comps:
        try:
            prices.append(float(listing["price"]["value"]))
        except (KeyError, TypeError, ValueError):
            continue

    if len(prices) >= MIN_COMPS:
        return statistics.median(prices), f"mediana di {len(prices)} annunci attivi"

    if target.market_reference:
        return float(target.market_reference), "riferimento configurato"

    return None, "nessun dato sufficiente"


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
