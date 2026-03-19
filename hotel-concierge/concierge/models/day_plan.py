from dataclasses import dataclass

from concierge.models.discovered_option import DiscoveredOption


@dataclass(frozen=True)
class TravelSegment:
    mode: str            # "walk", "transit", "drive"
    duration_minutes: int
    distance_meters: int


@dataclass(frozen=True)
class ItineraryStop:
    order: int
    place: DiscoveredOption
    arrival_time: str         # "10:30"
    departure_time: str       # "12:00"
    duration_minutes: int
    travel_to_next: TravelSegment | None
    notes: str

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "place": self.place.to_dict(),
            "arrival_time": self.arrival_time,
            "departure_time": self.departure_time,
            "duration_minutes": self.duration_minutes,
            "travel_to_next": {
                "mode": self.travel_to_next.mode,
                "duration_minutes": self.travel_to_next.duration_minutes,
                "distance_meters": self.travel_to_next.distance_meters,
            } if self.travel_to_next else None,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict) -> "ItineraryStop":
        seg_data = data.get("travel_to_next")
        travel_to_next = TravelSegment(
            mode=seg_data["mode"],
            duration_minutes=seg_data["duration_minutes"],
            distance_meters=seg_data["distance_meters"],
        ) if seg_data else None

        return ItineraryStop(
            order=data["order"],
            place=DiscoveredOption.from_dict(data["place"]),
            arrival_time=data["arrival_time"],
            departure_time=data["departure_time"],
            duration_minutes=data["duration_minutes"],
            travel_to_next=travel_to_next,
            notes=data.get("notes", ""),
        )


@dataclass(frozen=True)
class DayPlan:
    date: str
    stops: tuple[ItineraryStop, ...]
    total_travel_time: int
    estimated_total_cost: str
    weather_contingency: str
    back_at_hotel_by: str
    map_url: str = ""

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "stops": [s.to_dict() for s in self.stops],
            "total_travel_time": self.total_travel_time,
            "estimated_total_cost": self.estimated_total_cost,
            "weather_contingency": self.weather_contingency,
            "back_at_hotel_by": self.back_at_hotel_by,
            "map_url": self.map_url,
        }

    @staticmethod
    def from_dict(data: dict) -> "DayPlan":
        return DayPlan(
            date=data["date"],
            stops=tuple(ItineraryStop.from_dict(s) for s in data["stops"]),
            total_travel_time=data["total_travel_time"],
            estimated_total_cost=data["estimated_total_cost"],
            weather_contingency=data.get("weather_contingency", ""),
            back_at_hotel_by=data["back_at_hotel_by"],
            map_url=data.get("map_url", ""),
        )
