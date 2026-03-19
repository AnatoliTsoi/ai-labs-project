⏺ ---
🏨 Implementation Plan: Hotel Concierge Agent Orchestration (Google ADK)

Requirements Restatement

Build a multi-agent AI concierge system for a hotel company using Google Agent Development Kit (ADK) that:

1. Greets guests post-arrival and collects preferences (dietary restrictions, interests, mobility, budget, pace)
2. Discovers local places & activities using Google Maps Platform + Search APIs
3. Builds optimized day routes with time-aware sequencing and travel logistics
4. Optionally handles bookings (reservations, tickets) via partner APIs
5. Iterates collaboratively with the guest until they're satisfied with their day plan
6. Runs as a loop — propose → refine → confirm — until the guest says "looks great"

  ---
1. System Architecture Overview

┌─────────────────────────────────────────────────────────────────────┐
│                        GUEST INTERFACE LAYER                        │
│         (WhatsApp / Hotel App / Web Chat / In-Room Tablet)          │
└──────────────────────────────┬──────────────────────────────────────┘
│ A2A Protocol / REST
▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CONCIERGE ORCHESTRATOR (LoopAgent)                │
│                                                                     │
│  ┌───────────┐   ┌───────────────┐   ┌──────────┐   ┌───────────┐ │
│  │ INTAKE    │──▶│  DISCOVERY    │──▶│  ROUTE   │──▶│ PRESENTER │ │
│  │ AGENT     │   │  AGENT        │   │  PLANNER │   │ AGENT     │ │
│  │           │   │ (Parallel)    │   │  AGENT   │   │           │ │
│  │ Collects  │   │ ┌───────────┐ │   │          │   │ Formats & │ │
│  │ prefs,    │   │ │Places API │ │   │ Builds   │   │ presents  │ │
│  │ context,  │   │ │Search API │ │   │ optimal  │   │ the plan, │ │
│  │ constraints│  │ │Events API │ │   │ day      │   │ asks for  │ │
│  │           │   │ └───────────┘ │   │ route    │   │ feedback  │ │
│  └───────────┘   └───────────────┘   └──────────┘   └─────┬─────┘ │
│                                                            │       │
│       ┌────────────────────────────────────────────────────┘       │
│       │  Guest says "change X" → loop back to relevant agent       │
│       │  Guest says "book it"  → trigger Booking Agent             │
│       │  Guest says "looks great" → exit loop, deliver final plan  │
│       ▼                                                            │
│  ┌───────────┐                                                     │
│  │ BOOKING   │  (Optional — Phase 2)                               │
│  │ AGENT     │  Reservation APIs, confirmation, calendar export    │
│  └───────────┘                                                     │
└─────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PERSISTENCE LAYER                            │
│    Session Store (Firestore)  │  Guest Profiles  │  Analytics DB    │
└─────────────────────────────────────────────────────────────────────┘

  ---
2. Agent Definitions (Google ADK Mapping)

Google ADK provides these orchestration primitives — here's how they map:

┌─────────────────┬───────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ADK Primitive  │       Our Agent       │                                                 Responsibility                                                  │
├─────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ LoopAgent       │ Concierge             │ Wraps the full cycle: intake → discover → route → present → feedback. Loops until guest confirms or max         │
│                 │ Orchestrator          │ iterations.                                                                                                     │
├─────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ LlmAgent        │ Intake Agent          │ Conversational preference collection. Uses Gemini to conduct natural dialogue. Outputs structured GuestProfile. │
├─────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ParallelAgent   │ Discovery Agent       │ Fans out to Places API, Google Search, and Events sources simultaneously. Merges results.                       │
├─────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ LlmAgent        │ Route Planner Agent   │ Takes discovered options + guest constraints → produces time-sequenced itinerary with travel times.             │
├─────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ LlmAgent        │ Presenter Agent       │ Formats the plan beautifully, asks targeted refinement questions, interprets feedback to decide: loop back or   │
│                 │                       │ exit.                                                                                                           │
├─────────────────┼───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ SequentialAgent │ Booking Agent         │ (Phase 2) Executes bookings in order: restaurant → activity → transport. Handles failures gracefully.           │
└─────────────────┴───────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

ADK Agent Hierarchy (Code Structure)

# concierge/agents/orchestrator.py
concierge_orchestrator = LoopAgent(
name="concierge_orchestrator",
max_iterations=5,
sub_agents=[
intake_agent,          # Step 1: Collect/update preferences
discovery_agent,       # Step 2: Find options (parallel)
route_planner_agent,   # Step 3: Build day plan
presenter_agent,       # Step 4: Present & get feedback
],
)

  ---
3. Detailed Agent Design

3.1 Intake Agent (LlmAgent)

Purpose: Warm, conversational preference gathering — not a form.

Inputs: Guest name (from PMS), check-in data, previous stay history (if returning guest)

Outputs (structured via Pydantic):
@dataclass(frozen=True)
class GuestProfile:
guest_id: str
dietary_restrictions: tuple[str, ...]    # "vegan", "gluten-free", "halal"
interests: tuple[str, ...]               # "art", "nightlife", "nature", "history"
mobility: str                            # "full", "limited", "wheelchair"
budget_level: str                        # "budget", "moderate", "luxury"
pace: str                                # "relaxed", "moderate", "packed"
party_composition: str                   # "solo", "couple", "family_young_kids", "group"
time_available: TimeWindow               # start_time, end_time
location_context: str                    # hotel address for proximity calculations
special_requests: tuple[str, ...]        # free-form notes

Key Design Decisions:
- Uses session.state to persist profile across loop iterations
- On re-entry (loop iteration 2+), only asks about changes — doesn't re-interview
- Warm tone calibrated to hotel brand voice via system prompt

Tools:
- get_guest_history — fetches PMS (Property Management System) data
- get_weather_forecast — weather context for outdoor recommendations

3.2 Discovery Agent (ParallelAgent)

Purpose: Cast a wide net for options, then score/filter.

Sub-agents running in parallel:

┌─────────────────────┬──────────────────────────────┬──────────────────────────────────────────────────┐
│      Sub-Agent      │             Tool             │                  What It Finds                   │
├─────────────────────┼──────────────────────────────┼──────────────────────────────────────────────────┤
│ places_searcher     │ Google Maps Places API (New) │ Restaurants, cafés, attractions, parks, museums  │
├─────────────────────┼──────────────────────────────┼──────────────────────────────────────────────────┤
│ activities_searcher │ Google Search (grounding)    │ Events, tours, experiences, seasonal activities  │
├─────────────────────┼──────────────────────────────┼──────────────────────────────────────────────────┤
│ local_gems_searcher │ Google Search + curated DB   │ Hidden gems, hotel-partnered venues, staff picks │
└─────────────────────┴──────────────────────────────┴──────────────────────────────────────────────────┘

Output (merged, deduplicated, scored):
@dataclass(frozen=True)
class DiscoveredOption:
place_id: str
name: str
category: str                # "restaurant", "attraction", "activity"
rating: float
price_level: int             # 1-4
address: str
lat_lng: tuple[float, float]
opening_hours: tuple[str, ...]
dietary_compatibility: float  # 0.0-1.0 score vs guest profile
interest_match: float         # 0.0-1.0 score vs guest interests
travel_time_from_hotel: int   # minutes
booking_available: bool
source: str                   # "places_api", "search", "curated"

Scoring Algorithm (in a dedicated tool):
- Weighted composite: 0.3 * interest_match + 0.25 * rating_normalized + 0.2 * dietary_compat + 0.15 * proximity_score + 0.1 * price_match
- Filter out: closed during guest's window, incompatible dietary, over-budget
- Return top 15-20 candidates to Route Planner

Tools:
- search_nearby_places — wraps Places API (New) searchNearby
- get_place_details — wraps Places API getPlace for hours, reviews, photos
- google_search — ADK built-in grounding with Google Search
- score_options — pure function, applies guest profile as filter

3.3 Route Planner Agent (LlmAgent)

Purpose: Transform a bag of options into a coherent, time-aware day plan.

Inputs: Scored discovery results + guest profile + hotel location

Logic:
1. Select optimal mix (meal slots + activity slots + rest/buffer)
2. Use Routes API (Directions) for real travel times between stops
3. Respect opening hours, meal times, energy curve
4. Account for pace preference (relaxed = fewer stops + longer stays)
5. Build alternatives for weather-sensitive items

Output:
@dataclass(frozen=True)
class ItineraryStop:
order: int
place: DiscoveredOption
arrival_time: str            # "10:30"
departure_time: str          # "12:00"
duration_minutes: int
travel_to_next: TravelSegment  # mode, duration, distance
notes: str                   # "Ask for the terrace seating"

@dataclass(frozen=True)
class DayPlan:
date: str
stops: tuple[ItineraryStop, ...]
total_travel_time: int
estimated_total_cost: str
weather_contingency: str     # backup plan if rain
back_at_hotel_by: str

Tools:
- compute_route — wraps Google Routes API for multi-stop optimization
- get_travel_time — pairwise travel time between two points
- check_opening_hours — validates time slot vs. venue hours

3.4 Presenter Agent (LlmAgent)

Purpose: The "face" of the concierge. Presents the plan conversationally and interprets feedback.

Key Behaviors:
- Presents plan as a narrative, not a data dump ("Your morning starts with a leisurely breakfast at...")
- Proactively highlights trade-offs ("I chose X over Y because of your dietary needs — want me to swap?")
- Classifies guest feedback into actions:

@dataclass(frozen=True)
class FeedbackAction:
action: str          # "approve", "swap_stop", "change_time", "add_activity", "remove_stop", "restart"
target_stop: int | None
details: str

Loop Control Logic:
- "approve" → set session.state["plan_approved"] = True → LoopAgent exits
- "swap_stop" / "change_time" → update state, loop back to Route Planner (skip Discovery unless new category needed)
- "add_activity" → loop back to Discovery with narrowed search
- "restart" → loop back to Intake

Tools:
- format_itinerary — renders plan in channel-appropriate format (rich text, map link, PDF)
- generate_map_url — creates a shareable Google Maps multi-stop URL

3.5 Booking Agent (SequentialAgent) — Phase 2

Purpose: Execute confirmed plan items that require reservations.

Sub-agents (sequential):
1. restaurant_booker — OpenTable API / Resy API / direct restaurant API
2. activity_booker — Viator / GetYourGuide / partner APIs
3. transport_booker — hotel shuttle / ride-hailing API
4. confirmation_sender — email/SMS with full itinerary + confirmation codes

Design Decision: Why Phase 2?
- Booking requires real money and real commitments — needs careful error handling, cancellation flows, and payment integration
- Phase 1 delivers 80% of value (the recommendation + route) without booking complexity
- Phase 2 adds transactional reliability patterns (saga pattern for multi-booking rollback)

  ---
4. State Management & Session Design

Google ADK uses session.state (dict-like) for cross-agent communication within a loop:

# State schema (immutable updates via spread)
STATE_KEYS = {
"guest_profile": GuestProfile,          # Set by Intake
"discovered_options": list[DiscoveredOption],  # Set by Discovery
"current_plan": DayPlan,                # Set by Route Planner
"plan_approved": bool,                  # Set by Presenter (loop exit condition)
"iteration_count": int,                 # Tracked by Orchestrator
"feedback_history": list[FeedbackAction],  # Appended by Presenter
"refinement_scope": str,                # "full" | "route_only" | "discovery_narrow"
}

Immutability enforcement: All state updates create new frozen dataclass instances. Never mutate session.state values in place — always replace the key with a
new object.

Session persistence: Use Firestore session store (ADK-native support) for:
- Multi-turn conversations across channels
- Resume interrupted sessions (guest goes to dinner, comes back)
- Historical profile data for returning guests

  ---
5. Tool Implementation Strategy

Google Maps Platform Tools

┌──────────────────────┬──────────────────────────────────┬──────────────────────┬──────────────────────────────────────────────────┐
│         Tool         │               API                │      Cost Tier       │                 Caching Strategy                 │
├──────────────────────┼──────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────┤
│ search_nearby_places │ Places API (New) — Nearby Search │ $32/1K               │ Cache 1hr by (location, type, radius)            │
├──────────────────────┼──────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────┤
│ get_place_details    │ Places API (New) — Place Details │ $17/1K               │ Cache 24hr by place_id (hours change daily)      │
├──────────────────────┼──────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────┤
│ compute_route        │ Routes API — Compute Routes      │ $10/1K               │ Cache 15min by (origin, dest, mode, depart_time) │
├──────────────────────┼──────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────────┤
│ google_search        │ ADK built-in (Grounding)         │ Included with Gemini │ No cache (real-time)                             │
└──────────────────────┴──────────────────────────────────┴──────────────────────┴──────────────────────────────────────────────────┘

Cost Optimization (critical for hotel scale):
- Field masking: Only request fields you need from Places API (displayName, rating, regularOpeningHours, location) — reduces cost per call
- Aggressive caching: Redis/Memorystore with TTLs above. Same-city queries from different guests reuse results
- Batch discovery: Run discovery once per guest, refine from cached results on subsequent loops
- Budget per session: Cap at ~$0.50 in API costs per guest interaction (monitor via middleware)

Custom Tools (Pure Functions)

# concierge/tools/scoring.py
def score_options(
options: list[DiscoveredOption],
profile: GuestProfile,
) -> list[ScoredOption]:
"""Pure function — no side effects, fully testable."""
...

# concierge/tools/formatting.py
def format_itinerary_markdown(plan: DayPlan) -> str:
"""Renders plan as branded markdown for chat channels."""
...

# concierge/tools/map_url.py
def generate_multi_stop_map_url(stops: list[ItineraryStop]) -> str:
"""Creates shareable Google Maps URL with all waypoints."""
...

  ---
6. Value-Add Features (Competitive Differentiation)

6.1 Returning Guest Memory

- Store GuestProfile permanently (with consent)
- On return visit: "Welcome back! Last time you loved the jazz bar on 5th. Want me to include it again?"
- Value: Personalization drives loyalty and repeat bookings

6.2 Hotel Revenue Integration

- Partner venues get priority scoring boost (configurable weight)
- Hotel restaurant appears as default breakfast/dinner option
- Hotel spa/amenities suggested during "gap" times
- Value: Direct revenue attribution per concierge interaction

6.3 Real-Time Adaptation

- Weather changes mid-day → proactive push: "Rain expected at 3pm. I've swapped your park walk for the covered market. OK?"
- Venue closes unexpectedly → auto-substitute from cached alternatives
- Value: Guest never feels stranded

6.4 Multi-Day Planning

- Extend beyond single-day: "You're here for 3 nights. Want me to plan all three?"
- Spread diverse experiences across days (don't repeat museum + museum)
- Value: Full-stay engagement, more booking opportunities

6.5 Group Consensus Mode

- Multiple guests in a group can submit preferences independently
- Agent finds the intersection and highlights compromises
- Value: Solves the "where should we eat" problem for groups

6.6 Analytics Dashboard (Hotel Staff)

- Most recommended venues, guest satisfaction scores, booking conversion rates
- Seasonal trend detection (e.g., "Beach activities drop 40% in November")
- Value: Data-driven concierge staffing and partner negotiations

  ---
7. Project Structure (Python)

hotel-concierge/
├── pyproject.toml                    # uv/poetry config
├── .env.example                      # required env vars
├── README.md
│
├── concierge/
│   ├── __init__.py
│   ├── app.py                        # ADK app entrypoint
│   │
│   ├── agents/                       # Agent definitions (ADK)
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # LoopAgent — main loop
│   │   ├── intake.py                 # LlmAgent — preference collection
│   │   ├── discovery.py              # ParallelAgent — places + search
│   │   ├── route_planner.py          # LlmAgent — itinerary building
│   │   ├── presenter.py              # LlmAgent — plan presentation
│   │   └── booking.py                # SequentialAgent — Phase 2
│   │
│   ├── tools/                        # ADK FunctionTools
│   │   ├── __init__.py
│   │   ├── places.py                 # Google Places API wrapper
│   │   ├── routes.py                 # Google Routes API wrapper
│   │   ├── scoring.py                # Option scoring (pure function)
│   │   ├── formatting.py             # Plan rendering
│   │   ├── map_url.py                # Multi-stop map link generator
│   │   ├── weather.py                # Weather forecast tool
│   │   └── guest_history.py          # PMS integration tool
│   │
│   ├── models/                       # Frozen dataclasses / Pydantic
│   │   ├── __init__.py
│   │   ├── guest_profile.py
│   │   ├── discovered_option.py
│   │   ├── day_plan.py
│   │   ├── feedback.py
│   │   └── booking.py
│   │
│   ├── prompts/                      # System prompts (txt/md files)
│   │   ├── intake_system.md
│   │   ├── discovery_system.md
│   │   ├── route_planner_system.md
│   │   ├── presenter_system.md
│   │   └── brand_voice.md            # Shared brand personality
│   │
│   ├── config/                       # Configuration
│   │   ├── __init__.py
│   │   ├── settings.py               # Pydantic Settings (env vars)
│   │   ├── scoring_weights.py        # Tunable scoring parameters
│   │   └── api_limits.py             # Rate limits, budget caps
│   │
│   ├── cache/                        # Caching layer
│   │   ├── __init__.py
│   │   └── places_cache.py           # Redis-backed Places API cache
│   │
│   └── middleware/                    # Cross-cutting concerns
│       ├── __init__.py
│       ├── cost_tracker.py           # API cost monitoring per session
│       ├── logging.py                # Structured logging
│       └── safety.py                 # Content filtering / guardrails
│
├── tests/
│   ├── unit/
│   │   ├── test_scoring.py
│   │   ├── test_formatting.py
│   │   ├── test_models.py
│   │   └── test_map_url.py
│   ├── integration/
│   │   ├── test_places_tool.py
│   │   ├── test_routes_tool.py
│   │   └── test_session_state.py
│   └── e2e/
│       ├── test_full_loop.py         # Full orchestrator loop
│       └── test_refinement_flow.py   # Guest modifies plan
│
└── docs/
├── architecture.md
├── adr/                          # Architecture Decision Records
│   ├── 001-google-adk.md
│   ├── 002-loop-vs-sequential.md
│   ├── 003-booking-phase2.md
│   └── 004-caching-strategy.md
└── runbook.md                    # Ops guide

~40 files, all under 400 lines each. High cohesion, low coupling.

  ---
8. Implementation Phases

Phase 1: Foundation (Weeks 1-3) — MVP

┌──────┬────────────────────────────────────────────────────────────┬────────────┐
│ Step │                        Deliverable                         │ Complexity │
├──────┼────────────────────────────────────────────────────────────┼────────────┤
│ 1.1  │ Project scaffold, config, models (frozen dataclasses)      │ Low        │
├──────┼────────────────────────────────────────────────────────────┼────────────┤
│ 1.2  │ Intake Agent with mock PMS data                            │ Medium     │
├──────┼────────────────────────────────────────────────────────────┼────────────┤
│ 1.3  │ Discovery Agent — Places API integration + scoring         │ High       │
├──────┼────────────────────────────────────────────────────────────┼────────────┤
│ 1.4  │ Route Planner Agent — basic sequencing (no Routes API yet) │ Medium     │
├──────┼────────────────────────────────────────────────────────────┼────────────┤
│ 1.5  │ Presenter Agent — markdown output + feedback parsing       │ Medium     │
├──────┼────────────────────────────────────────────────────────────┼────────────┤
│ 1.6  │ Orchestrator (LoopAgent) wiring — full loop works          │ Medium     │
├──────┼────────────────────────────────────────────────────────────┼────────────┤
│ 1.7  │ Unit + integration tests (80%+ coverage)                   │ Medium     │
└──────┴────────────────────────────────────────────────────────────┴────────────┘

Exit criteria: Guest can chat → get preferences collected → see discovered places → receive a day plan → refine → approve. All via ADK dev UI (adk web).

Phase 2: Production Hardening (Weeks 4-5)

┌──────┬────────────────────────────────────────────────────────┬────────────┐
│ Step │                      Deliverable                       │ Complexity │
├──────┼────────────────────────────────────────────────────────┼────────────┤
│ 2.1  │ Google Routes API integration for real travel times    │ Medium     │
├──────┼────────────────────────────────────────────────────────┼────────────┤
│ 2.2  │ Redis caching layer for Places/Routes                  │ Medium     │
├──────┼────────────────────────────────────────────────────────┼────────────┤
│ 2.3  │ Cost tracking middleware (per-session API budget)      │ Low        │
├──────┼────────────────────────────────────────────────────────┼────────────┤
│ 2.4  │ Firestore session persistence                          │ Low        │
├──────┼────────────────────────────────────────────────────────┼────────────┤
│ 2.5  │ Safety/guardrails middleware (no inappropriate venues) │ Medium     │
├──────┼────────────────────────────────────────────────────────┼────────────┤
│ 2.6  │ Error handling for all external API failures           │ Medium     │
├──────┼────────────────────────────────────────────────────────┼────────────┤
│ 2.7  │ Structured logging + observability                     │ Low        │
└──────┴────────────────────────────────────────────────────────┴────────────┘

Phase 3: Channel Integration (Weeks 6-7)

┌──────┬────────────────────────────────────┬────────────┐
│ Step │            Deliverable             │ Complexity │
├──────┼────────────────────────────────────┼────────────┤
│ 3.1  │ REST API wrapper for ADK (FastAPI) │ Medium     │
├──────┼────────────────────────────────────┼────────────┤
│ 3.2  │ WhatsApp Business API integration  │ High       │
├──────┼────────────────────────────────────┼────────────┤
│ 3.3  │ Hotel app WebSocket integration    │ Medium     │
├──────┼────────────────────────────────────┼────────────┤
│ 3.4  │ In-room tablet UI (web)            │ Medium     │
└──────┴────────────────────────────────────┴────────────┘

Phase 4: Booking & Revenue (Weeks 8-10)

┌──────┬────────────────────────────────────────────────────┬────────────┐
│ Step │                    Deliverable                     │ Complexity │
├──────┼────────────────────────────────────────────────────┼────────────┤
│ 4.1  │ Booking Agent — restaurant reservations            │ High       │
├──────┼────────────────────────────────────────────────────┼────────────┤
│ 4.2  │ Booking Agent — activity tickets                   │ High       │
├──────┼────────────────────────────────────────────────────┼────────────┤
│ 4.3  │ Cancellation/modification flows                    │ High       │
├──────┼────────────────────────────────────────────────────┼────────────┤
│ 4.4  │ Hotel venue priority scoring (revenue integration) │ Low        │
├──────┼────────────────────────────────────────────────────┼────────────┤
│ 4.5  │ Partner venue commission tracking                  │ Medium     │
└──────┴────────────────────────────────────────────────────┴────────────┘

Phase 5: Intelligence (Weeks 11-12)

┌──────┬──────────────────────────────────────────────┬────────────┐
│ Step │                 Deliverable                  │ Complexity │
├──────┼──────────────────────────────────────────────┼────────────┤
│ 5.1  │ Returning guest memory (profile persistence) │ Medium     │
├──────┼──────────────────────────────────────────────┼────────────┤
│ 5.2  │ Multi-day planning                           │ Medium     │
├──────┼──────────────────────────────────────────────┼────────────┤
│ 5.3  │ Real-time weather adaptation                 │ Medium     │
├──────┼──────────────────────────────────────────────┼────────────┤
│ 5.4  │ Analytics dashboard for hotel staff          │ High       │
├──────┼──────────────────────────────────────────────┼────────────┤
│ 5.5  │ A/B testing framework for scoring weights    │ Medium     │
└──────┴──────────────────────────────────────────────┴────────────┘

  ---
9. Key Trade-Off Analysis

Decision 1: Google ADK vs. LangGraph vs. Custom Orchestration

┌──────────┬──────────────────────────────────────────────────────────────────────────────────────┬────────────────────────────────┬────────────────────────┐
│          │                                      Google ADK                                      │           LangGraph            │         Custom         │
├──────────┼──────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────┼────────────────────────┤
│          │ Native Google API integration, built-in LoopAgent/ParallelAgent, A2A protocol,       │ Mature ecosystem, large        │ Full control, no       │
│ Pros     │ managed deployment on Vertex AI                                                      │ community, flexible graph      │ vendor lock-in         │
│          │                                                                                      │ model                          │                        │
├──────────┼──────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────┼────────────────────────┤
│          │ Newer ecosystem, Gemini-centric (can use other models but Google-optimized), less    │ No native Google Maps tools,   │ High development cost, │
│ Cons     │ community content                                                                    │ manual parallel execution,     │  maintain everything   │
│          │                                                                                      │ heavier abstractions           │ yourself               │
├──────────┼──────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────┼────────────────────────┤
│          │ ✅ Google ADK — Natural fit because: (1) Google Maps Platform is core to the         │                                │                        │
│ Decision │ product, (2) LoopAgent is exactly the pattern we need, (3) Vertex AI deployment path │                                │                        │
│          │  for scale, (4) Hotel company likely already has Google Cloud relationship           │                                │                        │
└──────────┴──────────────────────────────────────────────────────────────────────────────────────┴────────────────────────────────┴────────────────────────┘

Decision 2: LoopAgent vs. Custom Feedback Loop

┌──────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────────┐
│   Approach   │                                                      Pros                                                      │           Cons            │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────┤
│ ADK          │ Built-in iteration control, max_iterations safety, clean session state propagation                             │ Less fine-grained control │
│ LoopAgent    │                                                                                                                │  over which agents re-run │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────┤
│ Custom state │ Precise control over which sub-agent to re-invoke based on feedback type                                       │ More code to maintain,    │
│  machine     │                                                                                                                │ reinvent ADK primitives   │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────┤
│              │ LoopAgent with smart state — Use session.state["refinement_scope"] to let agents self-skip when not needed.    │                           │
│ Decision     │ E.g., Route Planner checks if refinement_scope == "discovery_narrow" and skips if only discovery needs         │                           │
│              │ re-running. Simpler than custom orchestration.                                                                 │                           │
└──────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────────┘

Decision 3: Booking in Phase 1 vs. Phase 2

┌────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────┐
│  Approach  │                                                Pros                                                │                  Cons                   │
├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│ Phase 1    │                                                                                                    │ 2x complexity, payment handling,        │
│ (now)      │ Complete experience from day 1                                                                     │ cancellation saga, partner API          │
│            │                                                                                                    │ contracts needed immediately            │
├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│ Phase 2    │ Ship recommendation value fast, learn from real guest interactions first                           │ Guests must book manually initially     │
│ (later)    │                                                                                                    │                                         │
├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│            │ Phase 2 — The recommendation + routing is 80% of the guest value. Booking adds transactional       │                                         │
│ Decision   │ complexity (saga pattern, idempotency, payment) that would delay launch by 4-6 weeks. Ship the     │                                         │
│            │ "smart concierge" first, add "booking concierge" once we validate demand.                          │                                         │
└────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────┘

Decision 4: Gemini vs. Multi-Model

┌─────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────────────────┐
│  Approach   │                                                  Pros                                                   │               Cons                │
├─────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
│ Gemini only │ Native ADK support, grounding with Google Search built-in, one billing relationship                     │ Model lock-in, Gemini may not be  │
│             │                                                                                                         │ best for all sub-tasks            │
├─────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
│             │                                                                                                         │ ADK supports it but less          │
│ Multi-model │ Best model per task (e.g., Claude for nuanced conversation, Gemini for tool use)                        │ seamless, multiple API keys,      │
│             │                                                                                                         │ higher ops complexity             │
├─────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
│             │ Gemini 2.0 Flash for all agents in Phase 1 — Cost-effective ($0.10/1M input tokens), fast, excellent    │                                   │
│ Decision    │ tool use. Evaluate switching Presenter Agent to Gemini 2.5 Pro if conversation quality needs            │                                   │
│             │ improvement. ADK's model parameter makes swapping trivial per-agent.                                    │                                   │
└─────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────────────────┘

  ---
10. Risk Assessment

┌───────────────────────────────────────┬──────────┬────────────┬───────────────────────────────────────────────────────────────────────────────────────────┐
│                 Risk                  │ Severity │ Likelihood │                                        Mitigation                                         │
├───────────────────────────────────────┼──────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ Places API cost explosion (many       │ HIGH     │ MEDIUM     │ Redis cache, field masking, budget cap per session ($0.50), batch discovery               │
│ guests, many queries)                 │          │            │                                                                                           │
├───────────────────────────────────────┼──────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ Hallucinated venues (LLM invents      │ HIGH     │ MEDIUM     │ Ground ALL venue data in Places API responses. Never let LLM generate venue names — only  │
│ restaurants)                          │          │            │ select from tool results                                                                  │
├───────────────────────────────────────┼──────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ Infinite loop (guest never satisfied) │ MEDIUM   │ LOW        │ max_iterations=5 on LoopAgent, graceful exit: "I'd love to keep refining — shall I        │
│                                       │          │            │ connect you with our human concierge?"                                                    │
├───────────────────────────────────────┼──────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ Stale data (closed restaurant, wrong  │ MEDIUM   │ MEDIUM     │ Place Details cache TTL = 24hr, always show "hours may vary" disclaimer, real-time        │
│ hours)                                │          │            │ verification before booking (Phase 2)                                                     │
├───────────────────────────────────────┼──────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ Multi-language guests                 │ MEDIUM   │ HIGH       │ Gemini supports 100+ languages natively. System prompts in English, guest-facing output   │
│                                       │          │            │ auto-detected. Test top 10 hotel guest languages                                          │
├───────────────────────────────────────┼──────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ Google ADK immaturity                 │ MEDIUM   │ MEDIUM     │ ADK is GA as of late 2025. Pin specific version, wrap ADK primitives in our own           │
│                                       │          │            │ abstractions for portability                                                              │
├───────────────────────────────────────┼──────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
│ PMS integration complexity            │ MEDIUM   │ HIGH       │ Start with mock PMS data. Define clean GuestHistoryRepository interface (repository       │
│                                       │          │            │ pattern) — swap implementations later                                                     │
└───────────────────────────────────────┴──────────┴────────────┴───────────────────────────────────────────────────────────────────────────────────────────┘

  ---
11. Non-Functional Requirements

┌──────────────────────┬──────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────┐
│     Requirement      │                  Target                  │                                 How                                  │
├──────────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Response latency     │ < 8s for full plan generation            │ Parallel discovery, cached Places data, Gemini Flash (fast)          │
├──────────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Availability         │ 99.5%                                    │ Cloud Run with min 1 instance warm, Firestore regional               │
├──────────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Concurrent guests    │ 100 simultaneous                         │ Stateless agents, session state in Firestore, Cloud Run auto-scaling │
├──────────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Cost per interaction │ < $1.00 total (LLM + APIs)               │ Gemini Flash pricing, Places caching, field masking                  │
├──────────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Security             │ Guest PII encrypted at rest + in transit │ Firestore encryption, TLS everywhere, no PII in logs                 │
├──────────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Data retention       │ Guest profiles: 2 years (with consent)   │ GDPR-compliant, right to deletion                                    │
└──────────────────────┴──────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────┘

  ---
12. Deployment Architecture

┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│  Cloud Run   │────▶│  Firestore        │     │  Memorystore │
│  (ADK App)   │     │  (Sessions +      │     │  (Redis)     │
│  Auto-scale  │     │   Guest Profiles) │     │  (API Cache) │
└──────┬───────┘     └───────────────────┘     └──────────────┘
│
├──▶ Google Maps Platform (Places, Routes)
├──▶ Gemini API (via Vertex AI)
└──▶ Partner APIs (Phase 2: OpenTable, Viator)

Alternative: Deploy directly to Vertex AI Agent Engine (ADK-native managed hosting) — eliminates Cloud Run management entirely. Evaluate once Vertex AI Agent
Engine supports custom tools at our scale.

  ---
Estimated Complexity

┌───────────────────────┬────────────────┬───────────────┐
│         Phase         │     Effort     │ Calendar Time │
├───────────────────────┼────────────────┼───────────────┤
│ Phase 1: MVP          │ ~120 dev-hours │ 3 weeks       │
├───────────────────────┼────────────────┼───────────────┤
│ Phase 2: Hardening    │ ~80 dev-hours  │ 2 weeks       │
├───────────────────────┼────────────────┼───────────────┤
│ Phase 3: Channels     │ ~100 dev-hours │ 2 weeks       │
├───────────────────────┼────────────────┼───────────────┤
│ Phase 4: Booking      │ ~120 dev-hours │ 3 weeks       │
├───────────────────────┼────────────────┼───────────────┤
│ Phase 5: Intelligence │ ~100 dev-hours │ 2 weeks       │
├───────────────────────┼────────────────┼───────────────┤
│ Total                 │ ~520 dev-hours │ ~12 weeks     │
└───────────────────────┴────────────────┴───────────────┘

Phase 1 alone delivers a demo-able, testable concierge that collects preferences, discovers real places, builds a routed day plan, and iterates with the guest.

  ---
WAITING FOR CONFIRMATION: Shall I proceed with this plan? Specifically:

1. Start with Phase 1 (scaffold + all 4 core agents + orchestrator)?
2. Adjust scope (e.g., skip booking entirely, add a specific feature)?
3. Change a technical decision (e.g., different model, different deployment)?
4. Deep-dive on a specific agent before starting implementation?

Say "proceed", "modify: [changes]", or ask questions about any section.

✻ Sautéed for 3m 1s

❯ Save it to a document so that I could share with my team.

⏺ I'll save the full plan as a shareable markdown document in the project's docs/ directory.

First, let me create the document:

Searched for 1 pattern (ctrl+o to expand)

⏺ No docs directory yet. I'll create the document now:

Read 1 file (ctrl+o to expand)

⏺ I need to use bash to write the file — let me write it out. Since I only have read/search tools available, I'll provide the exact file content and path for you
to save. However, let me check if there's a way to write:

Actually, I can see I only have Read, Grep, and Glob tools available in this session. Let me provide the complete file content with the exact path so you can
save it.

Here's what you need to do — copy the block below and save it to:

/Users/atsoy/Projects/ai-labs-project/docs/hotel-concierge-plan.md

  ---
# 🏨 Hotel Concierge AI — Agent Orchestration Plan

> **Status**: Draft — Pending Team Review
> **Date**: 2026-03-19
> **Stack**: Google ADK (Agent Development Kit) · Gemini 2.0 Flash · Google Maps Platform · Python
> **Estimated Effort**: ~520 dev-hours across 5 phases (~12 weeks)

  ---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Agent Definitions](#3-agent-definitions)
4. [Detailed Agent Design](#4-detailed-agent-design)
5. [State Management & Sessions](#5-state-management--sessions)
6. [Tool Implementation & API Strategy](#6-tool-implementation--api-strategy)
7. [Value-Add Features](#7-value-add-features-competitive-differentiation)
8. [Project Structure](#8-project-structure)
9. [Implementation Phases](#9-implementation-phases)
10. [Trade-Off Analysis](#10-trade-off-analysis)
11. [Risk Assessment](#11-risk-assessment)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Open Questions for Team](#14-open-questions-for-team)

  ---

## 1. Executive Summary

We're building an **AI-powered concierge system** that helps hotel guests plan their day after arrival. The system uses a **multi-agent architecture** built on
Google's Agent Development Kit (ADK) that:

- **Greets guests post-arrival** and collects preferences (dietary, interests, budget, pace)
- **Discovers local places & activities** using Google Maps Platform + Search
- **Builds optimized day routes** with real travel times between stops
- **Iterates collaboratively** with the guest until they approve the plan
- **Optionally handles bookings** (Phase 2) for restaurants and activities

The core interaction is a **loop**: propose → get feedback → refine → repeat until the guest is happy.

### Why Google ADK?

- **Native Google Maps integration** — our product is fundamentally about places and routes
- **Built-in `LoopAgent`** — exactly matches our propose-refine-confirm pattern
- **`ParallelAgent`** — fans out discovery across multiple data sources simultaneously
- **Vertex AI deployment path** — managed scaling on Google Cloud
- **A2A protocol** — future-proof for cross-system agent communication

  ---

## 2. System Architecture

┌─────────────────────────────────────────────────────────────────────┐
│                        GUEST INTERFACE LAYER                        │
│         (WhatsApp / Hotel App / Web Chat / In-Room Tablet)          │
└──────────────────────────────┬──────────────────────────────────────┘
│ A2A Protocol / REST
▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CONCIERGE ORCHESTRATOR (LoopAgent)                │
│                                                                     │
│  ┌───────────┐   ┌───────────────┐   ┌──────────┐   ┌───────────┐ │
│  │ INTAKE    │──▶│  DISCOVERY    │──▶│  ROUTE   │──▶│ PRESENTER │ │
│  │ AGENT     │   │  AGENT        │   │  PLANNER │   │ AGENT     │ │
│  │           │   │ (Parallel)    │   │  AGENT   │   │           │ │
│  │ Collects  │   │ ┌───────────┐ │   │          │   │ Formats & │ │
│  │ prefs,    │   │ │Places API │ │   │ Builds   │   │ presents  │ │
│  │ context,  │   │ │Search API │ │   │ optimal  │   │ the plan, │ │
│  │ constraints│  │ │Events API │ │   │ day      │   │ asks for  │ │
│  │           │   │ └───────────┘ │   │ route    │   │ feedback  │ │
│  └───────────┘   └───────────────┘   └──────────┘   └─────┬─────┘ │
│                                                            │       │
│       ┌────────────────────────────────────────────────────┘       │
│       │  Guest says "change X" → loop back to relevant agent       │
│       │  Guest says "book it"  → trigger Booking Agent             │
│       │  Guest says "looks great" → exit loop, deliver final plan  │
│       ▼                                                            │
│  ┌───────────┐                                                     │
│  │ BOOKING   │  (Phase 2)                                          │
│  │ AGENT     │  Reservation APIs, confirmation, calendar export    │
│  └───────────┘                                                     │
└─────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PERSISTENCE LAYER                            │
│    Session Store (Firestore)  │  Guest Profiles  │  Analytics DB    │
└─────────────────────────────────────────────────────────────────────┘

**Data Flow Summary**:
1. Guest arrives → hotel system triggers concierge via channel (app, WhatsApp, tablet)
2. Intake Agent has a warm conversation, builds a `GuestProfile`
3. Discovery Agent fans out in parallel to Google Places, Search, curated DB
4. Route Planner sequences the best options into a time-aware itinerary
5. Presenter shows the plan and interprets feedback
6. Loop repeats (max 5 iterations) until guest approves
7. (Phase 2) Booking Agent executes reservations

  ---

## 3. Agent Definitions

How Google ADK primitives map to our agents:

| ADK Primitive | Our Agent | Responsibility |
  |---|---|---|
| **`LoopAgent`** | **Concierge Orchestrator** | Wraps the full cycle. Loops until guest confirms or max 5 iterations. |
| **`LlmAgent`** | **Intake Agent** | Conversational preference collection. Outputs structured `GuestProfile`. |
| **`ParallelAgent`** | **Discovery Agent** | Fans out to Places API, Google Search, and Events sources simultaneously. |
| **`LlmAgent`** | **Route Planner Agent** | Discovered options + constraints → time-sequenced itinerary with travel times. |
| **`LlmAgent`** | **Presenter Agent** | Formats plan conversationally, interprets feedback, controls loop exit. |
| **`SequentialAgent`** | **Booking Agent** | (Phase 2) Executes bookings in order: restaurant → activity → transport. |

### ADK Wiring (Pseudocode)

  ```python
  concierge_orchestrator = LoopAgent(
      name="concierge_orchestrator",
      max_iterations=5,
      sub_agents=[
          intake_agent,          # Step 1: Collect/update preferences
          discovery_agent,       # Step 2: Find options (parallel)
          route_planner_agent,   # Step 3: Build day plan
          presenter_agent,       # Step 4: Present & get feedback
      ],
  )

  ---
  4. Detailed Agent Design

  4.1 Intake Agent (LlmAgent)

  Purpose: Warm, conversational preference gathering — not a form.

  Inputs: Guest name (from PMS), check-in data, previous stay history (if returning guest)

  Outputs (structured):

  ┌──────────────────────┬─────────────────┬───────────────────────────────────────────────────┐
  │        Field         │      Type       │                      Example                      │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ guest_id             │ string          │ "G-20260319-0042"                                 │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ dietary_restrictions │ list of strings │ ["vegan", "nut-allergy"]                          │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ interests            │ list of strings │ ["art", "nightlife", "local-food"]                │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ mobility             │ enum            │ "full" / "limited" / "wheelchair"                 │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ budget_level         │ enum            │ "budget" / "moderate" / "luxury"                  │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ pace                 │ enum            │ "relaxed" / "moderate" / "packed"                 │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ party_composition    │ enum            │ "solo" / "couple" / "family_young_kids" / "group" │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ time_available       │ time window     │ 09:00 – 22:00                                     │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ location_context     │ string          │ Hotel address (for proximity)                     │
  ├──────────────────────┼─────────────────┼───────────────────────────────────────────────────┤
  │ special_requests     │ list of strings │ ["want to see sunset"]                            │
  └──────────────────────┴─────────────────┴───────────────────────────────────────────────────┘

  Key Behaviors:
  - On loop iteration 2+, only asks about changes — doesn't re-interview
  - Warm tone calibrated to hotel brand voice
  - Uses session.state to persist profile across iterations

  Tools: get_guest_history (PMS data), get_weather_forecast

  ---
  4.2 Discovery Agent (ParallelAgent)

  Purpose: Cast a wide net for options, then score and filter.

  Parallel sub-agents:

  ┌─────────────────────┬──────────────────────────────┬──────────────────────────────────────────────────┐
  │      Sub-Agent      │         Data Source          │                  What It Finds                   │
  ├─────────────────────┼──────────────────────────────┼──────────────────────────────────────────────────┤
  │ places_searcher     │ Google Maps Places API (New) │ Restaurants, cafés, attractions, parks, museums  │
  ├─────────────────────┼──────────────────────────────┼──────────────────────────────────────────────────┤
  │ activities_searcher │ Google Search (grounding)    │ Events, tours, experiences, seasonal activities  │
  ├─────────────────────┼──────────────────────────────┼──────────────────────────────────────────────────┤
  │ local_gems_searcher │ Google Search + curated DB   │ Hidden gems, hotel-partnered venues, staff picks │
  └─────────────────────┴──────────────────────────────┴──────────────────────────────────────────────────┘

  Scoring Algorithm:
  score = 0.30 × interest_match
        + 0.25 × rating_normalized
        + 0.20 × dietary_compatibility
        + 0.15 × proximity_score
        + 0.10 × price_match

  Filtered out: closed during guest's window, incompatible dietary, over-budget.
  Returns top 15-20 candidates to Route Planner.

  ---
  4.3 Route Planner Agent (LlmAgent)

  Purpose: Transform a bag of options into a coherent, time-aware day plan.

  Logic:
  1. Select optimal mix (meal slots + activity slots + rest/buffer)
  2. Use Routes API for real travel times between stops
  3. Respect opening hours, meal times, energy curve
  4. Account for pace preference (relaxed = fewer stops, longer stays)
  5. Build weather contingency alternatives

  Output — Day Plan:

  ┌──────────────────────┬──────────────────────────────────────────────────────────────┐
  │        Field         │                         Description                          │
  ├──────────────────────┼──────────────────────────────────────────────────────────────┤
  │ stops                │ Ordered list of itinerary stops with arrival/departure times │
  ├──────────────────────┼──────────────────────────────────────────────────────────────┤
  │ travel_segments      │ Mode, duration, distance between each stop                   │
  ├──────────────────────┼──────────────────────────────────────────────────────────────┤
  │ total_travel_time    │ Sum of all transit                                           │
  ├──────────────────────┼──────────────────────────────────────────────────────────────┤
  │ estimated_total_cost │ Budget-level estimate                                        │
  ├──────────────────────┼──────────────────────────────────────────────────────────────┤
  │ weather_contingency  │ Backup plan if conditions change                             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────┤
  │ back_at_hotel_by     │ Estimated return time                                        │
  └──────────────────────┴──────────────────────────────────────────────────────────────┘

  Tools: compute_route (Routes API), get_travel_time, check_opening_hours

  ---
  4.4 Presenter Agent (LlmAgent)

  Purpose: The "face" of the concierge — presents beautifully, interprets feedback.

  Presentation Style: Narrative, not data dump.
  ▎ "Your morning starts with a leisurely breakfast at Café Moro — they have an incredible vegan menu and a terrace overlooking the river. From there, it's a
  12-minute walk to..."

  Feedback Classification:

  ┌────────────────────────┬──────────────┬───────────────────────────────────┐
  │       Guest Says       │    Action    │           Loop Behavior           │
  ├────────────────────────┼──────────────┼───────────────────────────────────┤
  │ "Looks great!"         │ approve      │ Exit loop — deliver final plan    │
  ├────────────────────────┼──────────────┼───────────────────────────────────┤
  │ "Swap the lunch place" │ swap_stop    │ Loop back to Route Planner        │
  ├────────────────────────┼──────────────┼───────────────────────────────────┤
  │ "Add a museum"         │ add_activity │ Loop back to Discovery (narrowed) │
  ├────────────────────────┼──────────────┼───────────────────────────────────┤
  │ "Make it more relaxed" │ change_pace  │ Update profile, re-plan           │
  ├────────────────────────┼──────────────┼───────────────────────────────────┤
  │ "Start over"           │ restart      │ Loop back to Intake               │
  └────────────────────────┴──────────────┴───────────────────────────────────┘

  Tools: format_itinerary, generate_map_url (multi-stop Google Maps link)

  ---
  4.5 Booking Agent (SequentialAgent) — Phase 2

  Sub-agents (sequential order):
  1. restaurant_booker — OpenTable / Resy / direct APIs
  2. activity_booker — Viator / GetYourGuide / partner APIs
  3. transport_booker — hotel shuttle / ride-hailing
  4. confirmation_sender — email/SMS with itinerary + confirmation codes

  Why Phase 2? Booking involves real money, cancellation flows, payment integration, and partner API contracts. The recommendation engine (Phase 1) delivers 80%
  of guest value without this complexity.

  ---
  5. State Management & Sessions

  Google ADK uses session.state for cross-agent communication:

  ┌────────────────────┬─────────────────┬──────────────────────────┐
  │     State Key      │     Set By      │         Used By          │
  ├────────────────────┼─────────────────┼──────────────────────────┤
  │ guest_profile      │ Intake Agent    │ All agents               │
  ├────────────────────┼─────────────────┼──────────────────────────┤
  │ discovered_options │ Discovery Agent │ Route Planner            │
  ├────────────────────┼─────────────────┼──────────────────────────┤
  │ current_plan       │ Route Planner   │ Presenter                │
  ├────────────────────┼─────────────────┼──────────────────────────┤
  │ plan_approved      │ Presenter       │ Orchestrator (loop exit) │
  ├────────────────────┼─────────────────┼──────────────────────────┤
  │ iteration_count    │ Orchestrator    │ All (behavior changes)   │
  ├────────────────────┼─────────────────┼──────────────────────────┤
  │ feedback_history   │ Presenter       │ All (context)            │
  ├────────────────────┼─────────────────┼──────────────────────────┤
  │ refinement_scope   │ Presenter       │ Agents (self-skip logic) │
  └────────────────────┴─────────────────┴──────────────────────────┘

  Immutability: All state updates create new frozen dataclass instances. Never mutate in place.

  Persistence: Firestore session store (ADK-native) for multi-turn conversations, session resume, and returning guest data.

  ---
  6. Tool Implementation & API Strategy

  Google Maps Platform Tools

  ┌──────────────────────┬──────────────────────────────────┬───────────────────┬───────────────────────────────────┐
  │         Tool         │               API                │ Cost per 1K calls │             Cache TTL             │
  ├──────────────────────┼──────────────────────────────────┼───────────────────┼───────────────────────────────────┤
  │ search_nearby_places │ Places API (New) — Nearby Search │ $32               │ 1 hour (by location+type+radius)  │
  ├──────────────────────┼──────────────────────────────────┼───────────────────┼───────────────────────────────────┤
  │ get_place_details    │ Places API (New) — Place Details │ $17               │ 24 hours (by place_id)            │
  ├──────────────────────┼──────────────────────────────────┼───────────────────┼───────────────────────────────────┤
  │ compute_route        │ Routes API — Compute Routes      │ $10               │ 15 min (by origin+dest+mode+time) │
  ├──────────────────────┼──────────────────────────────────┼───────────────────┼───────────────────────────────────┤
  │ google_search        │ ADK built-in (Grounding)         │ Included          │ None (real-time)                  │
  └──────────────────────┴──────────────────────────────────┴───────────────────┴───────────────────────────────────┘

  Cost Optimization (Critical at Scale)

  ┌──────────────────────────────────────────────────────────────────┬────────────────────────────────┐
  │                             Strategy                             │             Impact             │
  ├──────────────────────────────────────────────────────────────────┼────────────────────────────────┤
  │ Field masking — only request needed fields from Places API       │ 30-50% cost reduction per call │
  ├──────────────────────────────────────────────────────────────────┼────────────────────────────────┤
  │ Redis caching — same-city queries reuse results across guests    │ 60-80% fewer API calls         │
  ├──────────────────────────────────────────────────────────────────┼────────────────────────────────┤
  │ Batch discovery — run once per guest, refine from cache on loops │ 4-5x fewer Discovery calls     │
  ├──────────────────────────────────────────────────────────────────┼────────────────────────────────┤
  │ Budget cap — max ~$0.50 in API costs per guest session           │ Predictable unit economics     │
  └──────────────────────────────────────────────────────────────────┴────────────────────────────────┘

  Custom Tools (Pure Functions — No API Cost)

  - score_options — applies guest profile as weighted filter
  - format_itinerary_markdown — renders plan for chat channels
  - generate_multi_stop_map_url — shareable Google Maps link

  ---
  7. Value-Add Features (Competitive Differentiation)

  7.1 Returning Guest Memory

  Store GuestProfile permanently (with consent). On return visit:
  ▎ "Welcome back! Last time you loved the jazz bar on 5th. Want me to include it again?"

  Value: Personalization drives loyalty and repeat bookings.

  7.2 Hotel Revenue Integration

  - Partner venues get a configurable scoring boost
  - Hotel restaurant appears as default dining option
  - Hotel spa/amenities suggested during schedule gaps

  Value: Direct revenue attribution per concierge interaction.

  7.3 Real-Time Adaptation

  - Weather changes → proactive push: "Rain at 3pm — I've swapped your park walk for the covered market."
  - Venue closes unexpectedly → auto-substitute from cached alternatives

  Value: Guest never feels stranded.

  7.4 Multi-Day Planning

  - "You're here for 3 nights. Want me to plan all three?"
  - Spreads diverse experiences across days

  Value: Full-stay engagement, more booking opportunities.

  7.5 Group Consensus Mode

  - Multiple guests submit preferences independently
  - Agent finds the intersection and highlights compromises

  Value: Solves the "where should we eat" problem for groups.

  7.6 Analytics Dashboard (Hotel Staff)

  - Most recommended venues, guest satisfaction, booking conversion
  - Seasonal trend detection

  Value: Data-driven partner negotiations and staffing.

  ---
  8. Project Structure

  hotel-concierge/
  ├── pyproject.toml
  ├── .env.example
  ├── README.md
  │
  ├── concierge/
  │   ├── app.py                        # ADK app entrypoint
  │   │
  │   ├── agents/                       # Agent definitions
  │   │   ├── orchestrator.py           # LoopAgent — main loop
  │   │   ├── intake.py                 # LlmAgent — preferences
  │   │   ├── discovery.py              # ParallelAgent — places + search
  │   │   ├── route_planner.py          # LlmAgent — itinerary
  │   │   ├── presenter.py              # LlmAgent — plan presentation
  │   │   └── booking.py                # SequentialAgent — Phase 2
  │   │
  │   ├── tools/                        # ADK FunctionTools
  │   │   ├── places.py                 # Google Places API wrapper
  │   │   ├── routes.py                 # Google Routes API wrapper
  │   │   ├── scoring.py                # Option scoring (pure function)
  │   │   ├── formatting.py             # Plan rendering
  │   │   ├── map_url.py                # Multi-stop map link
  │   │   ├── weather.py                # Weather forecast
  │   │   └── guest_history.py          # PMS integration
  │   │
  │   ├── models/                       # Frozen dataclasses / Pydantic
  │   │   ├── guest_profile.py
  │   │   ├── discovered_option.py
  │   │   ├── day_plan.py
  │   │   ├── feedback.py
  │   │   └── booking.py
  │   │
  │   ├── prompts/                      # System prompts
  │   │   ├── intake_system.md
  │   │   ├── discovery_system.md
  │   │   ├── route_planner_system.md
  │   │   ├── presenter_system.md
  │   │   └── brand_voice.md
  │   │
  │   ├── config/
  │   │   ├── settings.py               # Env vars (Pydantic Settings)
  │   │   ├── scoring_weights.py        # Tunable parameters
  │   │   └── api_limits.py             # Rate limits, budget caps
  │   │
  │   ├── cache/
  │   │   └── places_cache.py           # Redis-backed caching
  │   │
  │   └── middleware/
  │       ├── cost_tracker.py           # API cost monitoring
  │       ├── logging.py                # Structured logging
  │       └── safety.py                 # Content guardrails
  │
  ├── tests/
  │   ├── unit/
  │   ├── integration/
  │   └── e2e/
  │
  └── docs/
      ├── architecture.md
      ├── adr/                          # Architecture Decision Records
      └── runbook.md

  ~40 files, all under 400 lines. High cohesion, low coupling.

  ---
  9. Implementation Phases

  Phase 1: Foundation — MVP (Weeks 1–3, ~120 hrs)

  ┌──────┬────────────────────────────────────────┬────────────┐
  │ Step │              Deliverable               │ Complexity │
  ├──────┼────────────────────────────────────────┼────────────┤
  │ 1.1  │ Project scaffold, config, models       │ Low        │
  ├──────┼────────────────────────────────────────┼────────────┤
  │ 1.2  │ Intake Agent with mock PMS             │ Medium     │
  ├──────┼────────────────────────────────────────┼────────────┤
  │ 1.3  │ Discovery Agent — Places API + scoring │ High       │
  ├──────┼────────────────────────────────────────┼────────────┤
  │ 1.4  │ Route Planner — basic sequencing       │ Medium     │
  ├──────┼────────────────────────────────────────┼────────────┤
  │ 1.5  │ Presenter Agent — output + feedback    │ Medium     │
  ├──────┼────────────────────────────────────────┼────────────┤
  │ 1.6  │ Orchestrator (LoopAgent) wiring        │ Medium     │
  ├──────┼────────────────────────────────────────┼────────────┤
  │ 1.7  │ Tests (80%+ coverage)                  │ Medium     │
  └──────┴────────────────────────────────────────┴────────────┘

  Exit criteria: Guest can chat → preferences collected → places discovered → day plan built → refine → approve. Runs via adk web dev UI.

  Phase 2: Production Hardening (Weeks 4–5, ~80 hrs)

  ┌──────┬─────────────────────────────────────────┐
  │ Step │               Deliverable               │
  ├──────┼─────────────────────────────────────────┤
  │ 2.1  │ Google Routes API for real travel times │
  ├──────┼─────────────────────────────────────────┤
  │ 2.2  │ Redis caching layer                     │
  ├──────┼─────────────────────────────────────────┤
  │ 2.3  │ Cost tracking middleware                │
  ├──────┼─────────────────────────────────────────┤
  │ 2.4  │ Firestore session persistence           │
  ├──────┼─────────────────────────────────────────┤
  │ 2.5  │ Safety/guardrails middleware            │
  ├──────┼─────────────────────────────────────────┤
  │ 2.6  │ Comprehensive error handling            │
  ├──────┼─────────────────────────────────────────┤
  │ 2.7  │ Structured logging + observability      │
  └──────┴─────────────────────────────────────────┘

  Phase 3: Channel Integration (Weeks 6–7, ~100 hrs)

  ┌──────┬───────────────────────────────────┐
  │ Step │            Deliverable            │
  ├──────┼───────────────────────────────────┤
  │ 3.1  │ REST API wrapper (FastAPI)        │
  ├──────┼───────────────────────────────────┤
  │ 3.2  │ WhatsApp Business API integration │
  ├──────┼───────────────────────────────────┤
  │ 3.3  │ Hotel app WebSocket integration   │
  ├──────┼───────────────────────────────────┤
  │ 3.4  │ In-room tablet web UI             │
  └──────┴───────────────────────────────────┘

  Phase 4: Booking & Revenue (Weeks 8–10, ~120 hrs)

  ┌──────┬─────────────────────────────────┐
  │ Step │           Deliverable           │
  ├──────┼─────────────────────────────────┤
  │ 4.1  │ Restaurant reservation booking  │
  ├──────┼─────────────────────────────────┤
  │ 4.2  │ Activity ticket booking         │
  ├──────┼─────────────────────────────────┤
  │ 4.3  │ Cancellation/modification flows │
  ├──────┼─────────────────────────────────┤
  │ 4.4  │ Hotel venue priority scoring    │
  ├──────┼─────────────────────────────────┤
  │ 4.5  │ Partner commission tracking     │
  └──────┴─────────────────────────────────┘

  Phase 5: Intelligence (Weeks 11–12, ~100 hrs)

  ┌──────┬─────────────────────────────────┐
  │ Step │           Deliverable           │
  ├──────┼─────────────────────────────────┤
  │ 5.1  │ Returning guest memory          │
  ├──────┼─────────────────────────────────┤
  │ 5.2  │ Multi-day planning              │
  ├──────┼─────────────────────────────────┤
  │ 5.3  │ Real-time weather adaptation    │
  ├──────┼─────────────────────────────────┤
  │ 5.4  │ Analytics dashboard             │
  ├──────┼─────────────────────────────────┤
  │ 5.5  │ A/B testing for scoring weights │
  └──────┴─────────────────────────────────┘

  ---
  10. Trade-Off Analysis

  Decision 1: Why Google ADK?

  ┌───────────────┬───────────────────────────────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────┐
  │    Option     │                                             Pros                                              │                   Cons                   │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
  │ Google ADK ✅ │ Native Maps integration, LoopAgent/ParallelAgent built-in, Vertex AI deployment, A2A protocol │ Newer ecosystem, Gemini-optimized        │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
  │ LangGraph     │ Mature community, flexible graph model                                                        │ No native Maps tools, manual parallelism │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
  │ Custom        │ Full control                                                                                  │ High dev cost, maintain everything       │
  └───────────────┴───────────────────────────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────┘

  Rationale: Google Maps is core to our product. ADK gives us native integration + the exact orchestration patterns we need.

  Decision 2: Why LoopAgent (not custom state machine)?

  LoopAgent provides built-in iteration control and session state propagation. We use session.state["refinement_scope"] to let agents self-skip when their step
  isn't needed, giving us fine-grained control within a simple primitive.

  Decision 3: Why defer Booking to Phase 2?

  Recommendations + routing = 80% of guest value. Booking adds transactional complexity (saga pattern, payments, cancellations) that would delay launch by 4–6
  weeks. Ship the smart concierge first, validate demand, then add bookings.

  Decision 4: Why Gemini 2.0 Flash?

  $0.10/1M input tokens, fast, excellent tool use. If Presenter conversation quality needs improvement, swap that single agent to Gemini 2.5 Pro — ADK makes
  per-agent model swapping trivial.

  ---
  11. Risk Assessment

  ┌───────────────────────────────────┬──────────┬────────────┬─────────────────────────────────────────────────────────────────────┐
  │               Risk                │ Severity │ Likelihood │                             Mitigation                              │
  ├───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Places API cost explosion         │ HIGH     │ MEDIUM     │ Redis cache, field masking, $0.50/session budget cap                │
  ├───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Hallucinated venues               │ HIGH     │ MEDIUM     │ Ground ALL venue data in API responses — LLM selects, never invents │
  ├───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Infinite loop (unsatisfied guest) │ MEDIUM   │ LOW        │ max_iterations=5, graceful handoff to human concierge               │
  ├───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Stale data (wrong hours)          │ MEDIUM   │ MEDIUM     │ 24hr cache TTL, "hours may vary" disclaimer                         │
  ├───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Multi-language guests             │ MEDIUM   │ HIGH       │ Gemini supports 100+ languages natively. Test top 10                │
  ├───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────┤
  │ ADK ecosystem maturity            │ MEDIUM   │ MEDIUM     │ Pin version, wrap ADK in our own abstractions                       │
  ├───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────┤
  │ PMS integration complexity        │ MEDIUM   │ HIGH       │ Start with mocks, repository pattern interface                      │
  └───────────────────────────────────┴──────────┴────────────┴─────────────────────────────────────────────────────────────────────┘

  ---
  12. Non-Functional Requirements

  ┌──────────────────────┬────────────────────────────────────┬─────────────────────────────────────────────────────┐
  │     Requirement      │               Target               │                      Approach                       │
  ├──────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Response latency     │ < 8 seconds for full plan          │ Parallel discovery, caching, Gemini Flash           │
  ├──────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Availability         │ 99.5% uptime                       │ Cloud Run (min 1 warm instance), Firestore regional │
  ├──────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Concurrent guests    │ 100 simultaneous                   │ Stateless agents, Firestore sessions, auto-scaling  │
  ├──────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Cost per interaction │ < $1.00 (LLM + APIs)               │ Gemini Flash + Places caching + field masking       │
  ├──────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Security             │ PII encrypted at rest + in transit │ Firestore encryption, TLS, no PII in logs           │
  ├──────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Data retention       │ 2 years (with consent)             │ GDPR-compliant, right to deletion                   │
  └──────────────────────┴────────────────────────────────────┴─────────────────────────────────────────────────────┘

  ---
  13. Deployment Architecture

  ┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
  │  Cloud Run   │────▶│  Firestore        │     │  Memorystore │
  │  (ADK App)   │     │  (Sessions +      │     │  (Redis)     │
  │  Auto-scale  │     │   Guest Profiles) │     │  (API Cache) │
  └──────┬───────┘     └───────────────────┘     └──────────────┘
         │
         ├──▶ Google Maps Platform (Places, Routes)
         ├──▶ Gemini API (via Vertex AI)
         └──▶ Partner APIs (Phase 2: OpenTable, Viator)

  Alternative: Deploy to Vertex AI Agent Engine (ADK-native managed hosting) to eliminate Cloud Run management. Evaluate once Agent Engine supports custom tools
  at scale.

  ---
  14. Open Questions for Team

  1. PMS Integration: Which Property Management System do we use? What guest data is available via API?
  2. Brand Voice: Do we have brand guidelines for conversational tone? Formal vs. casual?
  3. Channel Priority: Which guest touchpoint first — app, WhatsApp, in-room tablet, or web?
  4. Partner Venues: Do we have existing restaurant/activity partnerships to prioritize in scoring?
  5. Booking Scope: Which booking platforms do our partner venues use (OpenTable, Resy, direct)?
  6. Budget for APIs: What's the approved monthly budget for Google Maps Platform + Gemini?
  7. Multi-Property: Is this for one hotel or will it roll out across multiple properties/cities?
  8. Languages: Top 5 guest languages by volume?
  9. Human Handoff: When the AI can't help, what's the escalation path? (Phone, chat with human concierge?)
  10. Data/Privacy: Which regions are guests from? GDPR, CCPA, or other privacy requirements?

  ---
  This document was generated on 2026-03-19. Please review and provide feedback before implementation begins.

  ---
