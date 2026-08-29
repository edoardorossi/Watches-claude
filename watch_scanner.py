"""Agent 1: Watch Scanner.

Defines investment-grade selection criteria for a ~4,000 EUR budget across
high-luxury brands, independent of any marketplace.

Budget reality check: at this level the Rolex steel sports thesis
(Submariner, Daytona, GMT) is out of reach — those start at roughly
8,000-25,000 EUR. What is reachable is a mix of proven value-retention
pieces and a few genuine appreciation candidates, mostly discontinued
references with an established collector following.

Price bands are set per target and capped below the total budget to leave
headroom for shipping, import duty, and — critically on vintage — a full
service, which runs 400-900 EUR and is a hidden cost of any unserviced piece.
"""

from dataclasses import dataclass, field


@dataclass
class Target:
    brand: str
    model: str
    search_terms: list
    price_min: float
    price_max: float
    tier: str
    thesis: str
    risk: str
    premium_references: list = field(default_factory=list)


@dataclass
class Criteria:
    budget_total: float
    currency: str
    targets: list
    conditions_allowed: list
    require_full_set: bool
    min_seller_feedback_score: int
    exclude_keywords: list
    avoid_brands: list

    @property
    def premium_references(self):
        return [ref for target in self.targets for ref in target.premium_references]


# Tier A: the strongest track record available at this budget. Discontinued
# references with sustained secondary-market demand — the only places where
# real appreciation (not just retention) has actually happened.
TIER_A = [
    Target(
        brand="Omega",
        model="Speedmaster Professional Moonwatch",
        search_terms=["Omega Speedmaster Professional Moonwatch", "Omega Speedmaster 1861"],
        price_min=2800,
        price_max=3900,
        tier="A",
        thesis=(
            "Calibro 1861/hesalite discontinuato nel 2021 a favore del 3861. Le referenze "
            "pre-2021 sono il riferimento storico del modello (l'orologio dell'Apollo) e hanno "
            "il bacino di collezionisti più profondo di qualsiasi cronografo sotto i 5k."
        ),
        risk="Quadranti e lancette sostituiti in service sono comuni: chiedere sempre il service sheet.",
        premium_references=["311.30.42.30.01.005", "3570.50", "145.022"],
    ),
    Target(
        brand="Tudor",
        model="Black Bay 58",
        search_terms=["Tudor Black Bay 58", "Tudor Black Bay 79030"],
        price_min=2400,
        price_max=3400,
        tier="A",
        thesis=(
            "DNA Rolex (stessa proprietà, stessa rete di assistenza) con proporzioni 39mm molto "
            "richieste. Ha tenuto il prezzo meglio di quasi ogni altro sportivo sotto i 4k dal 2018."
        ),
        risk="Le versioni più recenti si svalutano più delle prime serie: preferire le referenze 79030 iniziali.",
        premium_references=["79030N", "79030B"],
    ),
    Target(
        brand="Cartier",
        model="Tank",
        search_terms=["Cartier Tank Must", "Cartier Tank Solo", "Cartier Tank vintage"],
        price_min=1800,
        price_max=3800,
        tier="A",
        thesis=(
            "Cartier è stato il vero ciclo di apprezzamento del 2021-2025: design iconico e "
            "riconoscibile, domanda trainata dal ritorno dei formati piccoli e rettangolari."
        ),
        risk="Molti pezzi al quarzo e molti 'Tank' non Cartier: verificare movimento e provenienza.",
        premium_references=["W5200014", "WSTA0041"],
    ),
    Target(
        brand="Rolex",
        model="Vintage Datejust / Oyster Perpetual",
        search_terms=["Rolex Datejust 1601", "Rolex Oyster Perpetual vintage", "Rolex Air-King 5500"],
        price_min=2500,
        price_max=3900,
        tier="A",
        thesis=(
            "L'unica porta d'ingresso Rolex a questo budget: referenze vintage anni 60-70 con "
            "cassa in acciaio. Il nome Rolex garantisce liquidità di rivendita superiore a tutto il resto."
        ),
        risk=(
            "Segmento con la più alta incidenza di quadranti ridipinti e pezzi assemblati "
            "(franken): senza documenti o perizia, il rischio supera il potenziale."
        ),
        premium_references=["1601", "5500", "1002"],
    ),
]

# Tier B: solide, ma la tesi è tenuta di valore più che apprezzamento.
# Vanno comprate bene (sotto mercato) perché il rialzo non arriva da solo.
TIER_B = [
    Target(
        brand="Jaeger-LeCoultre",
        model="Reverso Classique",
        search_terms=["Jaeger-LeCoultre Reverso Classique", "JLC Reverso manual"],
        price_min=2800,
        price_max=3900,
        tier="B",
        thesis="Manifattura di alta orologeria a un prezzo di ingresso anomalo; design brevettato e inimitabile.",
        risk="Mercato secondario sottile: la rivendita può richiedere mesi.",
    ),
    Target(
        brand="Zenith",
        model="El Primero Chronomaster",
        search_terms=["Zenith El Primero Chronomaster", "Zenith El Primero 36000"],
        price_min=2800,
        price_max=3900,
        tier="B",
        thesis="Cronografo automatico integrato in-house storico (1969) a una frazione del prezzo dei concorrenti.",
        risk="Brand con riconoscibilità inferiore: sconta sempre rispetto a Omega a parità di qualità.",
    ),
    Target(
        brand="Grand Seiko",
        model="Snowflake",
        search_terms=["Grand Seiko SBGA211", "Grand Seiko Snowflake"],
        price_min=2800,
        price_max=3900,
        tier="B",
        thesis="Finiture di cassa e quadrante fuori categoria per il prezzo; base collezionisti in crescita costante.",
        risk="Svalutazione iniziale forte dal nuovo: comprare solo usato, mai al retail.",
        premium_references=["SBGA211"],
    ),
    Target(
        brand="IWC",
        model="Mark XVIII",
        search_terms=["IWC Mark XVIII", "IWC Pilot Mark XVIII"],
        price_min=2500,
        price_max=3600,
        tier="B",
        thesis="Pilot essenziale con lunga continuità di modello; tenuta prevedibile, poche sorprese.",
        risk="Movimento base ETA/Sellita su alcune referenze: incide sulla percezione di valore.",
    ),
    Target(
        brand="Omega",
        model="Seamaster 300M",
        search_terms=["Omega Seamaster 300M 42mm", "Omega Seamaster Diver 300M"],
        price_min=2600,
        price_max=3800,
        tier="B",
        thesis="Co-Axial Master Chronometer certificato METAS: contenuto tecnico alto per la fascia.",
        risk="Prodotto in grandi volumi: l'offerta abbondante limita l'apprezzamento.",
    ),
    Target(
        brand="Omega",
        model="Vintage Seamaster / Constellation",
        search_terms=["Omega Seamaster vintage 1960", "Omega Constellation vintage"],
        price_min=1200,
        price_max=2800,
        tier="B",
        thesis="Punto di ingresso più economico al vintage di qualità; calibri 5xx tra i migliori dell'epoca.",
        risk="Quadranti ridipinti diffusissimi: un quadrante rifatto dimezza il valore.",
    ),
]


def get_criteria() -> Criteria:
    return Criteria(
        budget_total=4000,
        currency="EUR",
        targets=TIER_A + TIER_B,
        conditions_allowed=[
            "Nuovo",
            "Usato",
            "Ricondizionato certificato",
            "New",
            "Pre-owned",
            "Certified - Refurbished",
        ],
        # A questo budget il full set pesa di più in proporzione: scatola e
        # documenti valgono il 15-25% su un vintage, contro il 5-10% su un moderno.
        require_full_set=True,
        # Soglia alzata rispetto ai Rolex sportivi: il rischio franken/replica
        # cresce quanto più si scende di prezzo, e il feedback è l'unico
        # segnale di affidabilità disponibile prima di contattare il venditore.
        min_seller_feedback_score=100,
        exclude_keywords=[
            "replica",
            "fake",
            "omaggio",
            "homage",
            "style",
            "for parts",
            "non funzionante",
            "da riparare",
            "custom",
            "aftermarket",
            "quadrante rifatto",
            "redial",
            "franken",
        ],
        # Marchi esclusi per tenuta di valore storicamente debole: la
        # svalutazione dal nuovo supera regolarmente il 50% e il mercato
        # secondario è illiquido.
        avoid_brands=["Hublot", "Bell & Ross", "Panerai", "Breitling", "TAG Heuer", "Montblanc"],
    )
