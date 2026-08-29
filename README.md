# Watches-claude

Python project to search and retrieve watch listings.

## eBay Browse API (recommended)

Uses eBay's official, public [Browse API](https://developer.ebay.com/api-docs/buy/browse/overview.html) via OAuth2 client credentials — no scraping, no anti-bot blocking.

### Setup

1. Create a developer account at [developer.ebay.com](https://developer.ebay.com/) and get a production **App ID (Client ID)** and **Client Secret**.
2. Export them as environment variables:
   ```bash
   export EBAY_CLIENT_ID="your-client-id"
   export EBAY_CLIENT_SECRET="your-client-secret"
   ```
3. Install dependencies and run:
   ```bash
   pip install -r requirements.txt
   python3 ebay_example.py
   ```

`ebay_client.py` handles OAuth2 token retrieval and caching; `ebay_example.py` searches for "Rolex DateJust" listings and prints title, price, and URL.

## Multi-agent investment pipeline

Four-stage pipeline for scouting investment-grade Rolex watches, orchestrated by `pipeline.py`:

1. **`watch_scanner.py`** — Watch Scanner. Defines investment criteria (models, price range, condition, discontinued references), independent of any marketplace.
2. **`retriever.py`** — Retriever. Searches eBay for each model in the criteria, filters by price/condition, downloads a thumbnail image per listing, and writes `data/listings.json`.
3. **`evaluator.py`** + **`pricing.py`** — Evaluator. Scores each listing (reference, full set, originality, service, seller feedback, red-flag keywords) *and* runs the resale-margin analysis below. Writes to `data/evaluations.json`.
4. **`favorites_agent.py`** — My Favorite. Autonomous: saves listings that both clear the resale gate and score at or above `SCORE_THRESHOLD` (default 70) to `data/favorites.json`, no confirmation required.

### Resale-margin analysis

The point is finding pieces priced low enough to resell at a profit, so margin is a gate, not a scoring factor — a watch that loses money on resale is never saved, however good the listing looks.

Two corrections make the number honest:

- **Asking ≠ realized.** The Browse API returns active listings, so the baseline (median of comparables, or a configured per-target reference when there are fewer than 5) is haircut by 10% to approximate what pieces actually sell for.
- **A discount is not a margin.** Reselling costs ~13% in platform and payment fees, plus insured shipping, plus 650 EUR of service if the piece has not had one. Buying 15% under market is roughly break-even, not a 15% gain.

A listing priced below 55% of market is flagged as a fraud risk and disqualified, not rewarded — at that spread a fake, a franken or a scam is likelier than a bargain.

Run the whole pipeline:
```bash
python3 pipeline.py
```

`data/` (listings, evaluations, favorites, downloaded images) is gitignored — it's generated output, not source.

## chrono24 (blocked by Cloudflare, kept for reference)

[`chrono24`](https://github.com/irahorecka/chrono24) is an unofficial scraping wrapper for [chrono24.com](https://www.chrono24.com). chrono24.com actively blocks automated requests with a Cloudflare managed challenge, so `example.py` will fail with a 403 from any network. See `example.py` for the (non-functional, without bypassing anti-bot protection) code.
