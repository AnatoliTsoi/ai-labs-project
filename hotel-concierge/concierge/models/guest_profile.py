from dataclasses import dataclass


@dataclass(frozen=True)
class TimeWindow:
    start_time: str  # "09:00"
    end_time: str    # "22:00"


@dataclass(frozen=True)
class GuestProfile:
    guest_id: str
    dietary_restrictions: tuple[str, ...]    # "vegan", "gluten-free", "halal"
    interests: tuple[str, ...]               # "art", "nightlife", "nature"
    mobility: str                            # "full", "limited", "wheelchair"
    budget_level: str                        # "budget", "moderate", "luxury"
    pace: str                                # "relaxed", "moderate", "packed"
    party_composition: str                   # "solo", "couple", "family_young_kids", "group"
    time_available: TimeWindow
    location_context: str                    # hotel address for proximity calculations
    special_requests: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "guest_id": self.guest_id,
            "dietary_restrictions": list(self.dietary_restrictions),
            "interests": list(self.interests),
            "mobility": self.mobility,
            "budget_level": self.budget_level,
            "pace": self.pace,
            "party_composition": self.party_composition,
            "time_available": {
                "start_time": self.time_available.start_time,
                "end_time": self.time_available.end_time,
            },
            "location_context": self.location_context,
            "special_requests": list(self.special_requests),
        }

    @staticmethod
    def from_dict(data: dict) -> "GuestProfile":
        tw = data["time_available"]
        return GuestProfile(
            guest_id=data["guest_id"],
            dietary_restrictions=tuple(data.get("dietary_restrictions", [])),
            interests=tuple(data.get("interests", [])),
            mobility=data.get("mobility", "full"),
            budget_level=data.get("budget_level", "moderate"),
            pace=data.get("pace", "moderate"),
            party_composition=data.get("party_composition", "solo"),
            time_available=TimeWindow(
                start_time=tw["start_time"],
                end_time=tw["end_time"],
            ),
            location_context=data.get("location_context", ""),
            special_requests=tuple(data.get("special_requests", [])),
        )
