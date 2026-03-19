"""Plan rendering — pure functions, no side effects."""

from concierge.models.day_plan import DayPlan, ItineraryStop

_PACE_EMOJI = {"relaxed": "☕", "moderate": "🚶", "packed": "⚡"}


def _format_stop(stop: ItineraryStop, index: int) -> str:
    lines = [
        f"### Stop {index}: {stop.place.name}",
        f"**{stop.arrival_time} – {stop.departure_time}** "
        f"({stop.duration_minutes} min)",
        f"📍 {stop.place.address}",
        f"⭐ {stop.place.rating:.1f} · {'$' * stop.place.price_level}",
    ]

    if stop.notes:
        lines.append(f"💬 *{stop.notes}*")

    if stop.travel_to_next:
        seg = stop.travel_to_next
        mode_icon = {"walk": "🚶", "transit": "🚌", "drive": "🚗"}.get(seg.mode, "➡️")
        lines.append(
            f"\n{mode_icon} {seg.duration_minutes} min to next stop "
            f"({seg.distance_meters / 1000:.1f} km)"
        )

    return "\n".join(lines)


def format_itinerary_markdown(plan: DayPlan) -> str:
    """Render a DayPlan as branded markdown for chat channels."""
    header = [
        f"## Your Day Plan — {plan.date}",
        "",
        f"**Back at hotel by:** {plan.back_at_hotel_by}  "
        f"**Total travel:** {plan.total_travel_time} min  "
        f"**Est. cost:** {plan.estimated_total_cost}",
        "",
    ]

    stop_sections = []
    for i, stop in enumerate(plan.stops, start=1):
        stop_sections.append(_format_stop(stop, i))

    footer = []
    if plan.weather_contingency:
        footer += ["", "---", f"☔ **Rain plan:** {plan.weather_contingency}"]

    return "\n\n".join(header + stop_sections + footer)


def format_itinerary_summary(plan: DayPlan) -> str:
    """One-line summary suitable for a confirmation message."""
    stop_names = " → ".join(s.place.name for s in plan.stops)
    return (
        f"{len(plan.stops)} stops on {plan.date}: {stop_names}. "
        f"Back by {plan.back_at_hotel_by}. ~{plan.estimated_total_cost}."
    )
