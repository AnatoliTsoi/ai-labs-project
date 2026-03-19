# Agent Breakdown — Who Does What & Where They Connect

> **Date**: 2026-03-19
> **System**: Hotel Concierge AI — Google ADK (Agent Development Kit)

---

## The Pipeline at a Glance

```
Frontend (React)               ADK Backend (Python)
─────────────────               ────────────────────
[Questionnaire UI]
      │
      │ POST /plan {profile}
      ▼
                          ┌─── CONCIERGE ORCHESTRATOR (LoopAgent, max 5 iterations) ───┐
                          │                                                             │
                          │  ① INTAKE ──▶ ② DISCOVERY ──▶ ③ ROUTE PLANNER ──▶ ④ PRESENTER
                          │     │              │                 │                 │    │
                          │     │              │                 │                 │    │
                          │     └──────────────┴─────────────────┴────── loop ◀────┘    │
                          └─────────────────────────────────────────────────────────────┘
      │
      │ {day_plan} JSON
      ▼
[Itinerary View]
```

---

## Agent Details

### ① Intake Agent — `LlmAgent`

| | |
|---|---|
| **File** | `concierge/agents/intake.py` |
| **Purpose** | Receive the structured `GuestProfile` JSON from the frontend, enrich it with server-side context (hotel location, PMS data, weather), persist to session state |
| **Input** | `POST /plan` body → `profile` JSON from questionnaire |
| **Output** | `session.state["guest_profile"]` — frozen `GuestProfile` dataclass |

**Tools:**
- `get_guest_history` — fetches Property Management System data
- `get_weather_forecast` — weather context for outdoor recs

**Key behavior on loop iteration 2+:** Merges feedback changes into existing profile rather than collecting from scratch.

---

### ② Discovery Agent — `ParallelAgent`

| | |
|---|---|
| **File** | `concierge/agents/discovery.py` |
| **Purpose** | Fan out to multiple data sources simultaneously, score & filter options against guest profile |
| **Input** | `session.state["guest_profile"]` |
| **Output** | `session.state["discovered_options"]` — list of `DiscoveredOption` (top 15–20) |

**3 parallel sub-agents:**

| Sub-Agent | Data Source | Finds |
|---|---|---|
| `places_searcher` | Google Maps Places API (New) | Restaurants, cafés, attractions, parks, museums |
| `activities_searcher` | Google Search (grounding) | Events, tours, experiences, seasonal activities |
| `local_gems_searcher` | Google Search + curated DB | Hidden gems, hotel-partnered venues, staff picks |

**Tools:**
- `search_nearby_places` — wraps Places API Nearby Search
- `get_place_details` — wraps Places API Place Details (hours, reviews, photos)
- `google_search` — ADK built-in grounding
- `score_options` — pure function, weighted composite scoring:
  ```
  score = 0.30 × interest_match
        + 0.25 × rating_normalized
        + 0.20 × dietary_compatibility
        + 0.15 × proximity_score
        + 0.10 × price_match
  ```

---

### ③ Route Planner Agent — `LlmAgent`

| | |
|---|---|
| **File** | `concierge/agents/route_planner.py` |
| **Purpose** | Turn a bag of scored options into a coherent, time-aware day plan |
| **Input** | `session.state["discovered_options"]` + `session.state["guest_profile"]` |
| **Output** | `session.state["current_plan"]` — frozen `DayPlan` dataclass |

**Logic:**
1. Select optimal mix (meals + activities + buffer time)
2. Use Routes API for real travel times between stops
3. Respect opening hours, meal times, energy curve
4. Honor pace preference (relaxed → fewer stops, longer stays)
5. Build weather contingency alternatives

**Tools:**
- `compute_route` — wraps Google Routes API (multi-stop optimization)
- `get_travel_time` — pairwise travel time between two points
- `check_opening_hours` — validates time slots vs. venue hours

---

### ④ Presenter Agent — `LlmAgent`

| | |
|---|---|
| **File** | `concierge/agents/presenter.py` |
| **Purpose** | Serialize the `DayPlan` as structured JSON for the React frontend. Classify guest feedback into loop-control actions |
| **Input** | `session.state["current_plan"]` |
| **Output** | `DayPlan` JSON response to frontend + loop control decisions |

**Tools:**
- `generate_map_url` — creates shareable Google Maps multi-stop URL
- `generate_stop_notes` — Gemini-generated per-stop tips

**Feedback classification (Phase 2):**

| User Action | Feedback Type | Where It Loops Back |
|---|---|---|
| "Looks great!" | `approve` | **Exit loop** → return final plan |
| "Swap the lunch place" | `swap_stop` | → Route Planner |
| "Add a museum" | `add_activity` | → Discovery → Route Planner |
| "Change the timing" | `change_time` | → Route Planner |
| "Start over" | `restart` | → Intake |

---

### ⑤ Booking Agent — `SequentialAgent` *(Phase 2, not yet built)*

| | |
|---|---|
| **File** | `concierge/agents/booking.py` |
| **Purpose** | Execute confirmed bookings in order |

**Sequential sub-agents:**
1. `restaurant_booker` — OpenTable / Resy / direct APIs
2. `activity_booker` — Viator / GetYourGuide / partner APIs
3. `transport_booker` — hotel shuttle / ride-hailing
4. `confirmation_sender` — email/SMS with itinerary + confirmation codes

---

## How They Connect — Session State Flow

All agents communicate via `session.state` (dict-like, Firestore-backed):

```
                     session.state
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  guest_profile ──────── set by ① ──── read by ②③④       │
│  discovered_options ─── set by ② ──── read by ③         │
│  current_plan ───────── set by ③ ──── read by ④         │
│  plan_approved ──────── set by ④ ──── read by orchestr. │
│  iteration_count ────── set by orch.─ read by all       │
│  feedback_history ───── set by ④ ──── read by all       │
│  refinement_scope ───── set by ④ ──── read by ①②③      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

| State Key | Set By | Used By |
|---|---|---|
| `guest_profile` | Intake | All agents |
| `discovered_options` | Discovery | Route Planner |
| `current_plan` | Route Planner | Presenter |
| `plan_approved` | Presenter | Orchestrator (loop exit condition) |
| `iteration_count` | Orchestrator | All (behavior changes per iteration) |
| `feedback_history` | Presenter | All (context for refinement) |
| `refinement_scope` | Presenter | Agents (self-skip logic: `"full"` / `"route_only"` / `"discovery_narrow"`) |

---

## Frontend ↔ Backend Boundary

| Direction | Endpoint | Payload |
|---|---|---|
| **Frontend → Backend** | `POST /plan` | `{profile: {interests, dietary_restrictions, pace, budget_level, party_composition, time_available}}` + `X-Session-ID` header |
| **Backend → Frontend** | 200 response | `{day_plan: {date, stops[], total_travel_time, estimated_total_cost, weather_contingency, back_at_hotel_by, map_url}}` |
| **Frontend → Backend** *(Phase 2)* | `POST /plan/feedback` | `{action, target_stop, details}` |

> **Note:** The frontend currently uses **mock data** (`VITE_USE_MOCK` env var). The real Python ADK backend has not been built yet — only the React questionnaire + itinerary view exist.

---

*See also: [api-contracts.md](./api-contracts.md) for exact JSON schemas, [architect-plan.md](./architect-plan.md) for full system design.*
