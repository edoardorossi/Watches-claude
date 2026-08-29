"""Orchestrates the four-agent pipeline:
Watch Scanner -> Retriever -> Evaluator -> My Favorite.
"""

import evaluator
import favorites_agent
import retriever
import watch_scanner


def run():
    criteria = watch_scanner.get_criteria()
    tier_a = sum(1 for t in criteria.targets if t.tier == "A")
    print(
        f"[Watch Scanner] {len(criteria.targets)} target ({tier_a} Tier A), "
        f"budget {criteria.budget_total} {criteria.currency}"
    )

    listings = retriever.collect(criteria)
    print(f"[Retriever] {len(listings)} annunci conformi ai criteri")

    evaluated = evaluator.evaluate(listings, criteria)
    print(f"[Evaluator] {len(evaluated)} orologi valutati")

    new_favorites = favorites_agent.save(evaluated)
    print(f"[My Favorite] {len(new_favorites)} nuovi preferiti salvati (soglia score >= {favorites_agent.SCORE_THRESHOLD})")

    for item in evaluated[:5]:
        print(
            f"\n[{item['brand']} / Tier {item['tier']}] {item['title']} — "
            f"{item['price']['value']} {item['price']['currency']} — score {item['score']}"
        )
        for reason in item["suggestions"]:
            print(f"  - {reason}")


if __name__ == "__main__":
    run()
