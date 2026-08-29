"""Agent 1: Watch Scanner.

Defines investment-grade Rolex selection criteria, independent of any
marketplace. Retriever must respect these constraints when searching.
"""

from dataclasses import dataclass


@dataclass
class Criteria:
    models: list
    price_min: float
    price_max: float
    currency: str
    conditions_allowed: list
    require_full_set: bool
    min_seller_feedback_score: int
    discontinued_models: list


def get_criteria() -> Criteria:
    """Steel sports Rolex models with a strong investment/resale track record:
    discontinued or hard-to-get references, verifiable condition, full set."""
    return Criteria(
        models=[
            "Submariner",
            "GMT-Master II",
            "Daytona",
            "Sky-Dweller",
            "Explorer",
            "Explorer II",
        ],
        price_min=5000,
        price_max=50000,
        currency="EUR",
        conditions_allowed=[
            "Nuovo",
            "Usato",
            "Ricondizionato certificato",
            "New",
            "Pre-owned",
            "Certified - Refurbished",
        ],
        require_full_set=True,
        min_seller_feedback_score=50,
        discontinued_models=[
            "Submariner 16610",
            "Daytona 116500LN",
            "GMT-Master II 116710LN",
        ],
    )
