from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    interest_match: float = 0.30
    rating_normalized: float = 0.25
    dietary_compatibility: float = 0.20
    proximity_score: float = 0.15
    price_match: float = 0.10

    def __post_init__(self) -> None:
        total = (
            self.interest_match
            + self.rating_normalized
            + self.dietary_compatibility
            + self.proximity_score
            + self.price_match
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")


DEFAULT_WEIGHTS = ScoringWeights()

# Partner venue boost (hotel revenue integration)
PARTNER_VENUE_BOOST = 0.10
