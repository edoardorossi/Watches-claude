"""Renders the pipeline's findings as a standalone HTML dossier.

Everything ships inside the file — photos are embedded as data URIs — so the
report can be opened or shared without the pipeline or a network connection.
"""

import base64
import html
import io
import json
import statistics
from pathlib import Path

import pricing

DATA_DIR = Path(__file__).parent / "data"
OUTPUT = Path(__file__).parent / "report.html"
PHOTO_PX = 560


def _photo(path):
    """Listing photo as a data URI, downscaled to keep the file portable."""
    if not path or not Path(path).exists():
        return None
    try:
        from PIL import Image
    except ImportError:
        return "data:image/jpeg;base64," + base64.b64encode(Path(path).read_bytes()).decode()

    image = Image.open(path).convert("RGB")
    image.thumbnail((PHOTO_PX, PHOTO_PX), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def _breakeven_ratio(needs_service, baseline):
    """The fraction of market value you must buy at to merely break even.

    Fees and the asking-to-realized haircut set this well below 100%, which is
    the single most useful number on the page: paying market price guarantees
    a loss on resale.
    """
    net = baseline * pricing.ASKING_TO_REALIZED * (1 - pricing.PLATFORM_FEE_RATE) - pricing.INSURED_SHIPPING_EUR
    if needs_service:
        net -= pricing.SERVICE_COST_EUR
    return net / baseline


def _scale(candidate):
    """Positions along the price-versus-market scale, as percentages."""
    p = candidate["pricing"]
    # The evaluator already decided whether a service applies; it shows up as
    # a total cost above the asking price.
    needs_service = p["total_cost"] > float(candidate["price"]["value"])
    return {
        "asking": 100 * float(candidate["price"]["value"]) / p["baseline"],
        "breakeven": 100 * _breakeven_ratio(needs_service, p["baseline"]),
        "fraud": 100 * pricing.TOO_GOOD_TO_BE_TRUE,
    }


def _esc(text):
    return html.escape(str(text))


def _card(candidate, verdict):
    p = candidate["pricing"]
    s = _scale(candidate)
    photo = _photo(candidate.get("image_path"))
    price = float(candidate["price"]["value"])

    url = _esc(candidate["item_url"])
    photo_html = (
        f'<a class="shotlink" href="{url}" target="_blank" rel="noopener">'
        f'<img class="shot" src="{photo}" alt="{_esc(candidate["title"][:80])}" loading="lazy"></a>'
        if photo
        else '<div class="shot shot--empty">nessuna foto</div>'
    )

    notes = "".join(f"<li>{_esc(n)}</li>" for n in candidate["suggestions"])

    return f"""
      <article class="card">
        <div class="card__photo">{photo_html}</div>
        <div class="card__body">
          <header class="card__head">
            <p class="eyebrow">{_esc(candidate['brand'])} · Tier {_esc(candidate['tier'])}</p>
            <h3>{_esc(candidate['title'])}</h3>
          </header>

          <div class="figures">
            <div class="figure">
              <span class="figure__label">Richiesto</span>
              <span class="figure__value">{price:,.0f} €</span>
            </div>
            <div class="figure">
              <span class="figure__label">Mercato</span>
              <span class="figure__value">{p['baseline']:,.0f} €</span>
            </div>
            <div class="figure figure--{'pos' if p['margin_eur'] > 0 else 'neg'}">
              <span class="figure__label">Margine netto</span>
              <span class="figure__value">{p['margin_eur']:+,.0f} €</span>
            </div>
          </div>

          <div class="scale" role="img"
               aria-label="Prezzo richiesto al {s['asking']:.0f}% del valore di mercato; pareggio al {s['breakeven']:.0f}%; soglia rischio truffa al {s['fraud']:.0f}%.">
            <div class="scale__track">
              <div class="scale__zone scale__zone--profit" style="width:{s['breakeven']:.1f}%"></div>
              <div class="scale__zone scale__zone--risk" style="width:{s['fraud']:.1f}%"></div>
              <div class="scale__mark scale__mark--asking" style="left:{s['asking']:.1f}%"></div>
              <span class="scale__anchor">100% = mercato</span>
            </div>
            <div class="scale__keys">
              <span class="key key--asking">Richiesto {s['asking']:.0f}%</span>
              <span class="key key--profit">Margine sotto il {s['breakeven']:.0f}%</span>
              <span class="key key--risk">Sospetto sotto il {s['fraud']:.0f}%</span>
            </div>
          </div>

          <p class="source">{_esc(p['baseline_source'])}</p>

          <ul class="notes">{notes}</ul>

          <div class="verdict verdict--{verdict['tone']}">
            <p class="verdict__label">{_esc(verdict['label'])}</p>
            <p class="verdict__text">{verdict['text']}</p>
          </div>

          <div class="cta">
            <a class="button" href="{url}" target="_blank" rel="noopener">Vedi l'annuncio su eBay</a>
            <span class="cta__meta">venditore con {candidate['seller_feedback_score']:,} feedback</span>
          </div>
        </div>
      </article>"""


# The pipeline scores what the text says; these read what the photos show and
# what the reference numbers actually mean, which is where the text is wrong.
VERDICTS = {
    "Grand Seiko": {
        "tone": "reject",
        "label": "Scartare — la referenza non torna",
        "text": (
            "La foto mostra <strong>SEIKO a ore 12</strong> e “Grand Seiko” a ore 6: è la disposizione "
            "pre-2017 dell’<strong>SBGA011</strong>, non dell’SBGA211 dichiarato nel titolo. Cassa e "
            "movimento condividono il codice <code>9R65-0AE0</code>, quindi nulla nel testo distingue i due. "
            "Il margine qui sopra è calcolato contro annunci di veri SBGA211 e non regge: con ogni probabilità "
            "il pezzo è semplicemente prezzato per quello che è. Chiedere conferma della referenza al venditore."
        ),
    },
    "zenith-strap": {
        "tone": "watch",
        "label": "Valutare — margine reale ma su cinturino in pelle",
        "text": (
            "Il margine più alto della rosa, ma il confronto include esemplari su <strong>bracciale "
            "d’acciaio</strong>, che vale da solo 500-800 €. Contro un pari-configurazione in pelle lo scarto "
            "si assottiglia. Vale la trattativa, non l’acquisto immediato."
        ),
    },
    "zenith-bracelet": {
        "tone": "prefer",
        "label": "Il migliore della rosa, nonostante lo score",
        "text": (
            "Costa 300 € più dell’altro Zenith e prende un margine inferiore, ma monta il "
            "<strong>bracciale d’acciaio originale</strong> — un ricambio da 500-800 € che il modello non "
            "sa contare. A parità di referenza è la configurazione più liquida alla rivendita, e il venditore "
            "ha 8.043 feedback contro 257."
        ),
    },
}


def _verdict_for(candidate):
    if candidate["brand"] == "Grand Seiko":
        return VERDICTS["Grand Seiko"]
    return VERDICTS["zenith-bracelet"] if "Orologio da uomo" in candidate["title"] else VERDICTS["zenith-strap"]


def build():
    evaluations = json.loads((DATA_DIR / "evaluations.json").read_text())
    qualified = [e for e in evaluations if e["qualifies_for_resale"]]
    no_baseline = [e for e in evaluations if not e.get("pricing")]
    negative = [e for e in evaluations if e.get("pricing") and not e["qualifies_for_resale"]]

    cards = "".join(_card(c, _verdict_for(c)) for c in qualified)

    near_misses = sorted(negative, key=lambda e: -e["pricing"]["margin_eur"])[:6]
    rows = "".join(
        f"""<tr>
              <td>{_esc(e['brand'])}</td>
              <td class="t"><a href="{_esc(e['item_url'])}" target="_blank" rel="noopener">{_esc(e['title'][:58])}</a></td>
              <td class="n">{float(e['price']['value']):,.0f} €</td>
              <td class="n">{e['pricing']['baseline']:,.0f} €</td>
              <td class="n neg">{e['pricing']['margin_eur']:+,.0f} €</td>
            </tr>"""
        for e in near_misses
    )

    return TEMPLATE.format(
        cards=cards,
        rows=rows,
        n_total=len(evaluations),
        n_qualified=len(qualified),
        n_no_baseline=len(no_baseline),
        n_negative=len(negative),
        # Fixed shipping means the break-even ratio drifts with value, so quote
        # it at the median of the pieces actually on the shortlist.
        breakeven=f"{100 * statistics.median(_breakeven_ratio(False, e['pricing']['baseline']) for e in qualified):.0f}",
    )


TEMPLATE = """<title>Dossier Orologi da Investimento</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">
<style>
  :root {{
    --ground: #eef0f3;
    --surface: #ffffff;
    --surface-2: #f6f7f9;
    --ink: #131820;
    --ink-2: #4a5563;
    --muted: #6b7684;
    --rule: #d6dae0;
    --rule-strong: #b6bdc7;
    --accent: #24508f;
    --accent-soft: #dbe4f2;
    --on-accent: #ffffff;
    --pos: #17654a;
    --pos-soft: #d9ebe3;
    --neg: #8f3830;
    --neg-soft: #f2dedb;
    --warn: #7d6018;
    --warn-soft: #f0e7cf;
    --shadow: 0 1px 2px rgba(19,24,32,.06), 0 8px 24px -12px rgba(19,24,32,.18);
    --display: "IBM Plex Sans Condensed", "Helvetica Neue", Arial, sans-serif;
    --body: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --ground: #0d1117;
      --surface: #161c25;
      --surface-2: #1c232e;
      --ink: #e7ecf3;
      --ink-2: #b3becc;
      --muted: #8794a4;
      --rule: #2a323e;
      --rule-strong: #3d4855;
      --accent: #7ba7e8;
      --accent-soft: #1b2a41;
      --on-accent: #0d1117;
      --pos: #5fc39c;
      --pos-soft: #16302a;
      --neg: #e0847a;
      --neg-soft: #3a201d;
      --warn: #d8b25f;
      --warn-soft: #322816;
      --shadow: 0 1px 2px rgba(0,0,0,.4), 0 10px 28px -14px rgba(0,0,0,.7);
    }}
  }}
  :root[data-theme="dark"] {{
    --ground: #0d1117;
    --surface: #161c25;
    --surface-2: #1c232e;
    --ink: #e7ecf3;
    --ink-2: #b3becc;
    --muted: #8794a4;
    --rule: #2a323e;
    --rule-strong: #3d4855;
    --accent: #7ba7e8;
    --accent-soft: #1b2a41;
    --on-accent: #0d1117;
    --pos: #5fc39c;
    --pos-soft: #16302a;
    --neg: #e0847a;
    --neg-soft: #3a201d;
    --warn: #d8b25f;
    --warn-soft: #322816;
    --shadow: 0 1px 2px rgba(0,0,0,.4), 0 10px 28px -14px rgba(0,0,0,.7);
  }}

  *, *::before, *::after {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    background: var(--ground);
    color: var(--ink);
    font-family: var(--body);
    font-size: 16px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }}

  .wrap {{
    max-width: 940px;
    margin: 0 auto;
    padding: 40px 20px 72px;
    display: flex;
    flex-direction: column;
    gap: 44px;
  }}

  h1, h2, h3 {{ font-family: var(--display); margin: 0; text-wrap: balance; letter-spacing: -0.01em; }}
  h1 {{ font-size: clamp(30px, 5vw, 44px); font-weight: 700; line-height: 1.08; }}
  h2 {{ font-size: 22px; font-weight: 600; }}
  h3 {{ font-size: 19px; font-weight: 600; line-height: 1.3; }}
  p {{ margin: 0; }}

  .eyebrow {{
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: .13em;
    text-transform: uppercase;
    color: var(--muted);
  }}

  /* ---------- masthead ---------- */
  .masthead {{ display: flex; flex-direction: column; gap: 14px; }}
  .masthead__sub {{ color: var(--ink-2); max-width: 62ch; }}

  .readout {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 3px;
    overflow: hidden;
  }}
  .readout__cell {{
    padding: 14px 16px;
    border-right: 1px solid var(--rule);
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .readout__cell:last-child {{ border-right: 0; }}
  .readout__n {{
    font-family: var(--mono);
    font-size: 26px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
  }}
  .readout__n--hit {{ color: var(--accent); }}
  .readout__k {{
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--muted);
  }}

  /* ---------- sections ---------- */
  .section {{ display: flex; flex-direction: column; gap: 18px; }}
  .section__intro {{ color: var(--ink-2); max-width: 66ch; }}
  .section__head {{ display: flex; flex-direction: column; gap: 6px; }}

  /* ---------- candidate cards ---------- */
  .cards {{ display: flex; flex-direction: column; gap: 22px; }}
  .card {{
    display: grid;
    grid-template-columns: 232px 1fr;
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 3px;
    box-shadow: var(--shadow);
    overflow: hidden;
  }}
  @media (max-width: 680px) {{ .card {{ grid-template-columns: 1fr; }} }}

  .card__photo {{
    background: var(--surface-2);
    border-right: 1px solid var(--rule);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 18px;
  }}
  @media (max-width: 680px) {{
    .card__photo {{ border-right: 0; border-bottom: 1px solid var(--rule); }}
  }}
  .shot {{ width: 100%; height: auto; border-radius: 2px; display: block; }}
  .shot--empty {{
    aspect-ratio: 1; display: grid; place-items: center;
    font-family: var(--mono); font-size: 12px; color: var(--muted);
  }}

  .card__body {{ padding: 20px 22px 22px; display: flex; flex-direction: column; gap: 16px; min-width: 0; }}
  .card__head {{ display: flex; flex-direction: column; gap: 5px; }}

  .figures {{ display: flex; flex-wrap: wrap; gap: 26px; }}
  .figure {{ display: flex; flex-direction: column; gap: 1px; }}
  .figure__label {{
    font-family: var(--mono); font-size: 10.5px; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted);
  }}
  .figure__value {{
    font-family: var(--mono); font-size: 21px; font-weight: 600;
    font-variant-numeric: tabular-nums;
  }}
  .figure--pos .figure__value {{ color: var(--pos); }}
  .figure--neg .figure__value {{ color: var(--neg); }}

  /* ---------- the price-versus-market scale ---------- */
  .scale {{ display: flex; flex-direction: column; gap: 9px; }}
  .scale__track {{
    position: relative;
    height: 30px;
    background: var(--surface-2);
    border: 1px solid var(--rule);
    border-radius: 2px;
    overflow: hidden;
  }}
  .scale__zone {{ position: absolute; top: 0; bottom: 0; left: 0; }}
  .scale__zone--profit {{ background: var(--pos-soft); }}
  .scale__zone--risk {{ background: var(--neg-soft); }}
  .scale__mark {{ position: absolute; top: 0; bottom: 0; width: 2px; }}
  .scale__mark--asking {{ background: var(--accent); width: 3px; }}
  .scale__anchor {{
    position: absolute; right: 7px; top: 50%; transform: translateY(-50%);
    font-family: var(--mono); font-size: 10px; color: var(--muted);
    letter-spacing: .04em; pointer-events: none;
  }}
  .scale__mark--asking::after {{
    content: ""; position: absolute; top: -1px; left: 50%;
    transform: translateX(-50%);
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 7px solid var(--accent);
  }}
  .scale__keys {{ display: flex; flex-wrap: wrap; gap: 16px; }}
  .key {{
    font-family: var(--mono); font-size: 11px; font-variant-numeric: tabular-nums;
    color: var(--muted); display: inline-flex; align-items: center; gap: 6px;
  }}
  .key::before {{ content: ""; width: 9px; height: 9px; border-radius: 1px; }}
  .key--asking::before {{ background: var(--accent); }}
  .key--profit::before {{ background: var(--pos-soft); border: 1px solid var(--pos); }}
  .key--risk::before {{ background: var(--neg-soft); border: 1px solid var(--neg); }}

  .source {{ font-family: var(--mono); font-size: 11.5px; color: var(--muted); }}

  .notes {{ margin: 0; padding-left: 17px; display: flex; flex-direction: column; gap: 5px; color: var(--ink-2); font-size: 14.5px; }}

  .verdict {{ border-left: 3px solid var(--rule-strong); padding: 11px 0 11px 14px; display: flex; flex-direction: column; gap: 5px; }}
  .verdict--reject {{ border-left-color: var(--neg); }}
  .verdict--prefer {{ border-left-color: var(--pos); }}
  .verdict--watch {{ border-left-color: var(--warn); }}
  .verdict__label {{ font-family: var(--display); font-weight: 600; font-size: 15.5px; }}
  .verdict--reject .verdict__label {{ color: var(--neg); }}
  .verdict--prefer .verdict__label {{ color: var(--pos); }}
  .verdict--watch .verdict__label {{ color: var(--warn); }}
  .verdict__text {{ font-size: 14.5px; color: var(--ink-2); }}
  .verdict__text code {{ font-family: var(--mono); font-size: .92em; background: var(--surface-2); padding: 1px 4px; border-radius: 2px; }}
  .verdict strong {{ color: var(--ink); font-weight: 600; }}

  .cta {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; margin-top: 2px; }}
  .button {{
    display: inline-flex; align-items: center; gap: 8px;
    background: var(--accent); color: var(--on-accent);
    font-family: var(--display); font-size: 15px; font-weight: 600;
    padding: 10px 18px; border-radius: 2px; text-decoration: none;
    transition: filter .15s ease;
  }}
  .button::after {{ content: "→"; font-family: var(--body); }}
  .button:hover {{ filter: brightness(1.12); }}
  .cta__meta {{ font-family: var(--mono); font-size: 11.5px; color: var(--muted); }}

  .shotlink {{ display: block; width: 100%; border-radius: 2px; }}
  .shotlink:hover .shot {{ filter: brightness(1.04); }}

  a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 2px; }}
  td a {{ color: var(--ink-2); text-decoration: none; border-bottom: 1px solid var(--rule-strong); }}
  td a:hover {{ color: var(--accent); border-bottom-color: var(--accent); }}
  @media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}

  /* ---------- rejection table ---------- */
  .tablewrap {{ overflow-x: auto; border: 1px solid var(--rule); border-radius: 3px; background: var(--surface); }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14px; min-width: 560px; }}
  th, td {{ padding: 9px 14px; text-align: left; border-bottom: 1px solid var(--rule); }}
  thead th {{
    font-family: var(--mono); font-size: 10.5px; letter-spacing: .09em;
    text-transform: uppercase; color: var(--muted); font-weight: 500;
    background: var(--surface-2);
  }}
  tbody tr:last-child td {{ border-bottom: 0; }}
  td.n {{ font-family: var(--mono); font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }}
  td.neg {{ color: var(--neg); }}
  td.t {{ color: var(--ink-2); }}

  .split {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }}
  .panel {{
    background: var(--surface); border: 1px solid var(--rule); border-radius: 3px;
    padding: 16px 18px; display: flex; flex-direction: column; gap: 7px;
  }}
  .panel h3 {{ font-size: 15.5px; }}
  .panel p {{ font-size: 14px; color: var(--ink-2); }}
  .panel__n {{
    font-family: var(--mono); font-size: 30px; font-weight: 600;
    font-variant-numeric: tabular-nums; line-height: 1; color: var(--accent);
  }}

  .method {{ display: flex; flex-direction: column; gap: 11px; }}
  .method li {{ color: var(--ink-2); font-size: 14.5px; }}
  .method ul {{ margin: 0; padding-left: 17px; display: flex; flex-direction: column; gap: 7px; }}

  footer {{
    border-top: 1px solid var(--rule); padding-top: 18px;
    font-family: var(--mono); font-size: 11.5px; color: var(--muted);
    display: flex; flex-wrap: wrap; gap: 8px 20px;
  }}
</style>

<div class="wrap">

  <header class="masthead">
    <p class="eyebrow">eBay · Marketplace Italia · budget 4.000 €</p>
    <h1>Orologi da investimento:<br>cosa regge il conto della rivendita</h1>
    <p class="masthead__sub">
      Scansione di dieci referenze su otto marchi di alta orologeria, filtrate non per bellezza
      dell'annuncio ma per una sola domanda: rivendendolo a prezzo di mercato, dopo commissioni,
      spedizione ed eventuale revisione, resta un margine?
    </p>
    <div class="readout">
      <div class="readout__cell">
        <span class="readout__n">{n_total}</span>
        <span class="readout__k">annunci analizzati</span>
      </div>
      <div class="readout__cell">
        <span class="readout__n readout__n--hit">{n_qualified}</span>
        <span class="readout__k">superano il vaglio</span>
      </div>
      <div class="readout__cell">
        <span class="readout__n">{n_negative}</span>
        <span class="readout__k">in perdita alla rivendita</span>
      </div>
      <div class="readout__cell">
        <span class="readout__n">{n_no_baseline}</span>
        <span class="readout__k">senza comparabili</span>
      </div>
    </div>
  </header>

  <section class="section">
    <div class="section__head">
      <p class="eyebrow">La rosa</p>
      <h2>I tre che superano il vaglio del margine</h2>
      <p class="section__intro">
        Ogni scheda mostra dove cade il prezzo richiesto lungo la scala del valore di mercato. La fascia
        verde è dove resta un margine dopo tutti i costi; oltre il suo bordo destro si compra troppo caro,
        prima del suo bordo sinistro lo sconto diventa sospetto anziché conveniente. Il verdetto in fondo
        tiene conto di quello che si vede nelle foto e che i numeri non sanno leggere.
      </p>
    </div>
    <div class="cards">{cards}</div>
  </section>

  <section class="section">
    <div class="section__head">
      <p class="eyebrow">Il resto del campo</p>
      <h2>Perché {n_negative} annunci perdono alla rivendita</h2>
    </div>
    <div class="split">
      <div class="panel">
        <span class="panel__n">{breakeven}%</span>
        <h3>La soglia che quasi nessuno rispetta</h3>
        <p>
          Tra il 13% di commissioni eBay, la spedizione assicurata e lo scarto tra prezzo richiesto e
          prezzo realizzato, per andare in pareggio bisogna comprare a poco più di tre quarti del valore
          di mercato. Chi paga il prezzo di listino del mercato ha già perso.
        </p>
      </div>
      <div class="panel">
        <span class="panel__n">{n_no_baseline}</span>
        <h3>Impossibili da prezzare</h3>
        <p>
          Non bocciati: semplicemente non esistono almeno cinque annunci della <em>stessa referenza</em>
          per stimarne il valore. Preferisco non dare un numero piuttosto che darne uno sbagliato.
        </p>
      </div>
    </div>
    <div class="tablewrap">
      <table>
        <thead>
          <tr><th>Marchio</th><th>Annuncio</th><th class="n">Richiesto</th><th class="n">Mercato</th><th class="n">Margine</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </section>

  <section class="section method">
    <div class="section__head">
      <p class="eyebrow">Metodo e limiti</p>
      <h2>Cosa questi numeri sanno, e cosa no</h2>
    </div>
    <ul>
      <li><strong>Il mercato è stimato da prezzi richiesti, non da venduti.</strong> Gli annunci attivi
        sono domande, non transazioni, quindi la mediana viene decurtata del 10% per avvicinarla al
        realizzo. Resta una stima.</li>
      <li><strong>I comparabili sono della stessa referenza, non dello stesso modello.</strong> Una
        ricerca per nome mescola misure da uomo e da donna, quarzo e carica manuale, edizioni base e
        limitate: un Reverso spazia da 3.500 a 9.000 €, e una mediana su quell'insieme inventa margini
        che non esistono.</li>
      <li><strong>Il giudizio parte dai titoli.</strong> Solo tre venditori su {n_total} scrivono “full
        set” nel titolo, ma quasi tutti mettono scatola e documenti nella descrizione: l'assenza della
        parola non è assenza della scatola, e non viene penalizzata.</li>
      <li><strong>Le foto sono una sola, da catalogo.</strong> Mancano fondello, movimento e profilo
        laterale: la lucidatura della cassa e lo stato di servizio non sono verificabili. Su un pezzo da
        3.000 € sono esattamente le foto da chiedere prima di trattare.</li>
    </ul>
  </section>

  <footer>
    <span>Fonte: eBay Browse API · marketplace EBAY_IT</span>
    <span>{n_total} annunci · {n_qualified} qualificati</span>
  </footer>

</div>
"""


if __name__ == "__main__":
    OUTPUT.write_text(build())
    print(f"Scritto {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")
