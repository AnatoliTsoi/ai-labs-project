from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveredOption:
    place_id: str
    name: str
    category: str                  # "restaurant", "attraction", "activity"
    rating: float                  # 1.0-5.0
    price_level: int               # 1-4
    address: str
    lat_lng: tuple[float, float]
    opening_hours: tuple[str, ...]
    dietary_compatibility: float   # 0.0-1.0 score vs guest profile
    interest_match: float          # 0.0-1.0 score vs guest interests
    travel_time_from_hotel: int    # minutes
    booking_available: bool
    source: str                    # "places_api", "search", "curated"

    def to_dict(self) -> dict:
        return {
            "place_id": self.place_id,
            "name": self.name,
            "category": self.category,
            "rating": self.rating,
            "price_level": self.price_level,
            "address": self.address,
            "lat_lng": list(self.lat_lng),
            "opening_hours": list(self.opening_hours),
            "dietary_compatibility": self.dietary_compatibility,
            "interest_match": self.interest_match,
            "travel_time_from_hotel": self.travel_time_from_hotel,
            "booking_available": self.booking_available,
            "source": self.source,
        }

    @staticmethod
    def from_dict(data: dict) -> "DiscoveredOption":
        return DiscoveredOption(
            place_id=data["place_id"],
            name=data["name"],
            category=data["category"],
            rating=float(data["rating"]),
            price_level=int(data["price_level"]),
            address=data["address"],
            lat_lng=tuple(data["lat_lng"]),
            opening_hours=tuple(data.get("opening_hours", [])),
            dietary_compatibility=float(data.get("dietary_compatibility", 0.5)),
            interest_match=float(data.get("interest_match", 0.5)),
            travel_time_from_hotel=int(data.get("travel_time_from_hotel", 15)),
            booking_available=bool(data.get("booking_available", False)),
            source=data.get("source", "places_api"),
        )
