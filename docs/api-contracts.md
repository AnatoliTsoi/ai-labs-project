# API Contracts — Frontend ↔ ADK Backend

Data shapes for every boundary between the React frontend and the Google ADK agent backend. All JSON, all snake_case.

---

## 1. Frontend → Backend: `POST /plan`

The questionnaire builds this payload and sends it when the user taps **"Build my day"**.

### Request

```
POST /plan
Content-Type: application/json
X-Session-ID: <session-id>
```

```jsonc
{
  "profile": {
    "interests": ["art", "food", "nature"],
    "dietary_restrictions": ["vegan", "nut-free"],
    "pace": "moderate",
    "budget_level": "luxury",
    "party_composition": "couple",
    "time_available": {
      "start_time": "09:00",
      "end_time": "21:00",
    },
  },
}
```

### Maps to ADK State

This profile maps directly to the `GuestProfile` Pydantic model in the architect plan. The backend should set `session.state["guest_profile"]` and can enrich it with server-side fields:

| Frontend field         | ADK `GuestProfile` field | Notes                                                |
| ---------------------- | ------------------------ | ---------------------------------------------------- |
| `interests`            | `interests`              | Direct pass-through                                  |
| `dietary_restrictions` | `dietary_restrictions`   | `["none"]` → empty tuple on backend                  |
| `pace`                 | `pace`                   | Enum: `relaxed`, `moderate`, `packed`                |
| `budget_level`         | `budget_level`           | Enum: `budget`, `moderate`, `luxury`                 |
| `party_composition`    | `party_composition`      | Enum: `solo`, `couple`, `family_young_kids`, `group` |
| `time_available`       | `time_available`         | `{start_time, end_time}` as `TimeWindow`             |
| _(not sent)_           | `guest_id`               | Set by backend from session/PMS                      |
| _(not sent)_           | `mobility`               | Defaults to `"full"` — future questionnaire step     |
| _(not sent)_           | `location_context`       | Set by backend from hotel config                     |
| _(not sent)_           | `special_requests`       | Empty — future free-text field                       |

---

## 2. Backend → Frontend: `DayPlan` Response

After the ADK **LoopAgent** completes (Intake → Discovery → Route Planner → Presenter), it returns:

### Response `200 OK`

```jsonc
{
  "day_plan": {
    "date": "2026-03-19",
    "stops": [
      {
        "order": 1,
        "place": {
          "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
          "name": "Café Moro",
          "category": "cafe", // "restaurant" | "cafe" | "museum" | "park" | "attraction" | "activity" | "nightlife"
          "rating": 4.7,
          "price_level": 2, // 1–4
          "address": "23 Riverside Walk",
          "lat_lng": [51.5074, -0.1278],
          "opening_hours": ["08:00–18:00"],
          "dietary_compatibility": 0.95, // 0.0–1.0
          "interest_match": 0.8, // 0.0–1.0
          "travel_time_from_hotel": 8, // minutes
          "booking_available": false,
          "source": "places_api", // "places_api" | "search" | "curated"
          "photo_url": "https://...", // optional
        },
        "arrival_time": "09:00", // HH:MM
        "departure_time": "10:15",
        "duration_minutes": 75,
        "travel_to_next": {
          // null for last stop
          "mode": "walking", // "walking" | "transit" | "driving" | "cycling"
          "duration_minutes": 12,
          "distance_km": 0.9,
        },
        "notes": "Great vegan menu, terrace overlooking the river.",
      },
      // ... more stops
    ],
    "total_travel_time": 53, // minutes across all segments
    "estimated_total_cost": "€80–€120",
    "weather_contingency": "If rain after 2pm, swap Botanical Gardens for Covered Market.",
    "back_at_hotel_by": "18:30",
    "map_url": "https://www.google.com/maps/dir/...", // optional
  },
}
```

### Error Response `4xx / 5xx`

```json
{
  "error": "Failed to generate plan",
  "detail": "Discovery agent timed out"
}
```

---

## 3. Future: Feedback Actions (Phase 2)

When the user taps **"Make changes"** on the itinerary, the frontend will send:

```
POST /plan/feedback
Content-Type: application/json
X-Session-ID: <session-id>
```

```jsonc
{
  "action": "swap_stop", // "approve" | "swap_stop" | "change_time" | "add_activity" | "remove_stop" | "restart"
  "target_stop": 3, // stop order number, or null
  "details": "Something more casual for lunch",
}
```

The **Presenter Agent** classifies this and decides which agent to loop back to:

- `approve` → exit loop, return final plan
- `swap_stop` / `change_time` → Route Planner
- `add_activity` → Discovery → Route Planner
- `restart` → Intake

---

## 4. Session Management

| Concern     | Approach                                                                          |
| ----------- | --------------------------------------------------------------------------------- |
| Session ID  | Frontend generates `session-<timestamp>-<random>`, sends as `X-Session-ID` header |
| Persistence | Backend stores in Firestore via ADK session store                                 |
| Resume      | Same session ID resumes interrupted conversations                                 |

---

## 5. ADK Agent Flow Diagram

```
Frontend                               ADK Backend
────────                               ───────────

[Questionnaire]
    │
    │  POST /plan {profile}
    ├──────────────────────────────────▶ Intake Agent
    │                                      │ sets session.state["guest_profile"]
    │                                      ▼
    │                                   Discovery Agent (parallel)
    │                                      │ Places API + Search + Curated
    │                                      │ sets session.state["discovered_options"]
    │                                      ▼
    │                                   Route Planner Agent
    │                                      │ Routes API for travel times
    │                                      │ sets session.state["current_plan"]
    │                                      ▼
    │                                   Presenter Agent
    │                                      │ formats DayPlan
    │   {day_plan}                         │
    │◀─────────────────────────────────────┘
    ▼
[Itinerary View]
    │
    │  POST /plan/feedback (Phase 2)
    ├──────────────────────────────────▶ Presenter classifies → loops back
    │◀──────────────────────────────────  Updated day_plan
```
