# Watches-claude

Python project using [chrono24](https://github.com/irahorecka/chrono24), an unofficial API wrapper for [chrono24.com](https://www.chrono24.com), to search and retrieve watch listings.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```python
import chrono24

for listing in chrono24.query("Rolex DateJust").search(limit=10):
    print(listing)
```

See `example.py` for a runnable example. `search()` consumes 1 request per 120 listings retrieved; `detailed_search()` consumes 1 request per listing but returns more detail.
