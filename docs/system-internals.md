# System Internals: How the Hotel Concierge Works

This document explains the complete internal mechanics of the hotel concierge system — how agents are structured, how they communicate, how data flows from user input to a finished itinerary, and how the frontend connects to the agent backend. It is written entirely from the implementation.

---

## 1. What the System Does

A hotel guest opens a web app, answers a few questions about their preferences (dietary needs, interests, budget, how much they want to walk around, etc.), and receives a personalised day itinerary — a list of places to visit with travel times, opening hours, cost estimates, and a weather contingency. They can then approve it or ask for changes.

---

## 2. Technology Stack at a Glance

| Layer | Technology |
|---|---|
| AI runtime | Google ADK (Agent Development Kit) |
| LLM | Gemini 2.5 Flash (one model per agent, all configurable) |
| Backend language | Python 3.12+ |
| Frontend | React 19, TypeScript, Vite |
| External APIs | Google Places (New), Google Routes, Google Maps URLs |
| Session storage | ADK `InMemoryRunner` (Phase 1) → Firestore (Phase 2) |
| Testing | pytest + Playwright |

---

## 3. The Backend Agent Architecture

### 3.1 The Four Agents

The backend is built around four LLM agents chained together inside one loop:

```
LoopAgent: concierge_orchestrator
  ├─ LlmAgent: intake_agent
  ├─ LlmAgent: discovery_agent
  ├─ LlmAgent: route_planner_agent
  └─ LlmAgent: presenter_agent
```

Each agent is an `LlmAgent` from `google.adk.agents`. It has:
- a model (Gemini 2.5 Flash by default, overridable per agent in `.env`)
- a system instruction loaded from a `.md` file in `concierge/prompts/`
- a specific set of Python functions it is allowed to call (its `tools`)

The outer wrapper is a `LoopAgent` with `max_iterations=5` (configurable). The loop runs the four sub-agents in sequence on every iteration. It exits early when the presenter calls `record_feedback(action="approve")`, which sets `tool_context.actions.escalate = True` — the ADK signal for "I am done, stop looping".

### 3.2 Agent Construction

All agents are built by factory functions (e.g., `build_intake_agent()` in `concierge/agents/intake.py`). The orchestrator calls all four:

```python
# concierge/agents/orchestrator.py
LoopAgent(
    name="concierge_orchestrator",
    max_iterations=settings.max_loop_iterations,
    sub_agents=[
        build_intake_agent(),
        build_discovery_agent(),
        build_route_planner_agent(),
        build_presenter_agent(),
    ],
)
```

The `root_agent` export in `concierge/__init__.py` is what the ADK runtime uses to serve the system. `adk web concierge` picks up `root_agent` automatically from this module.

---

## 4. How Agents Communicate: Session State

Agents do **not** talk to each other directly. There are no function calls between agents, no message queues, no shared Python objects. **All inter-agent communication happens through a single shared dictionary called `session.state`.**

### 4.1 The State Keys

```python
# concierge/tools/state_tools.py
KEY_GUEST_PROFILE     = "guest_profile"      # written by intake, read by all
KEY_DISCOVERED_OPTIONS = "discovered_options" # written by discovery, read by route planner
KEY_CURRENT_PLAN      = "current_plan"        # written by route planner, read by presenter
KEY_PLAN_APPROVED     = "plan_approved"       # written by presenter on approve
KEY_ITERATION_COUNT   = "iteration_count"     # internal loop counter
KEY_FEEDBACK_HISTORY  = "feedback_history"    # append-only list of FeedbackAction dicts
KEY_REFINEMENT_SCOPE  = "refinement_scope"    # "full" | "route_only" | "discovery_narrow"
```

Every piece of data that one agent needs from a prior agent lives here. An agent writes to this dict via a **tool call**, reads from it via its system prompt instruction (the ADK runtime injects current state into the agent's context).

### 4.2 The Write/Read Contract Per Agent

| Agent | Reads from state | Writes to state |
|---|---|---|
| `intake_agent` | `guest_profile` (if loop iteration 2+, to skip re-interview) | `guest_profile` via `save_guest_profile` |
| `discovery_agent` | `guest_profile` | `discovered_options` via `save_discovered_options` |
| `route_planner_agent` | `guest_profile`, `discovered_options`, `refinement_scope` | `current_plan` via `save_day_plan` |
| `presenter_agent` | `current_plan`, `feedback_history` | `feedback_history`, `plan_approved`, `refinement_scope` via `record_feedback` |

### 4.3 State as Serialised Dicts

All models (GuestProfile, DayPlan, etc.) are frozen Python dataclasses. Before being stored in session state, they are converted to plain dicts via `.to_dict()`. When read back, they are reconstructed via `.from_dict()`. The ADK state dict is plain JSON-serialisable — no live objects persist across agent boundaries.

```python
# Inside save_guest_profile tool (state_tools.py)
profile = GuestProfile(...)
tool_context.state[KEY_GUEST_PROFILE] = profile.to_dict()  # ← stored as dict
```

---

## 5. How Tools Work

### 5.1 What a Tool Is

A tool is a plain Python function. The LLM calls it by generating a function-call JSON block; the ADK runtime intercepts that, calls the real Python function, and feeds the return value back to the LLM as a tool result. The LLM sees the return value in natural language and decides what to do next.

Most tools take a `tool_context: ToolContext` parameter — this gives the function access to `tool_context.state` (the session dict) and `tool_context.actions` (control flow signals).

### 5.2 Tool Assignments Per Agent

**Intake Agent tools:**
- `save_guest_profile` — persists the collected GuestProfile to `session.state["guest_profile"]`
- `get_guest_history` — Phase 2 stub, returns mock PMS data about returning guests
- `get_weather_forecast` — returns mock weather so the intake agent can hint at outdoor vs indoor preferences

**Discovery Agent tools:**
- `search_nearby_places(query, lat, lng, radius_meters)` — calls Google Places API (mocked in Phase 1); returns a list of place dicts
- `get_place_details(place_id)` — fetches extra detail on a specific place
- `save_discovered_options(options)` — writes the filtered list to `session.state["discovered_options"]`

**Route Planner Agent tools:**
- `compute_route(origin_lat, origin_lng, dest_lat, dest_lng, mode)` — calls Google Routes API (mocked in Phase 1); returns `{duration_minutes, distance_meters, mode}`
- `check_opening_hours(place_id, arrival_time)` — checks whether a place is open at a planned arrival time; returns `{is_open, next_open}`
- `save_day_plan(plan_dict)` — persists the assembled DayPlan dict to `session.state["current_plan"]`

**Presenter Agent tools:**
- `record_feedback(action, details, target_stop)` — the single most important tool in the system. It:
  1. Validates the action string against `VALID_ACTIONS` (a frozenset)
  2. Appends the FeedbackAction to `session.state["feedback_history"]`
  3. If `action == "approve"`: sets `session.state["plan_approved"] = True` and `tool_context.actions.escalate = True` → loop exits
  4. Otherwise: sets `session.state["refinement_scope"]` to one of `"route_only"`, `"discovery_narrow"`, or `"full"` → loop continues

### 5.3 The Refinement Scope Signal

The `refinement_scope` key in session state tells subsequent agents on the next loop iteration how much work to redo:

| Guest feedback | `record_feedback` action | `refinement_scope` | Effect on next iteration |
|---|---|---|---|
| "Swap stop 2" | `swap_stop` | `route_only` | Route planner rebuilds the route; discovery reuses existing options |
| "Move dinner to 7pm" | `change_time` | `route_only` | Route planner adjusts timing only |
| "Add a jazz bar" | `add_activity` | `discovery_narrow` | Discovery does a narrow search; route planner rebuilds |
| "Start over" | `restart` | `full` | All agents re-run from scratch |
| "Looks perfect" | `approve` | (loop exits) | — |

The route planner reads `refinement_scope` from state in its system prompt instruction: *"If `refinement_scope` is `route_only`, reuse existing discovered options."*

---

## 6. The Loop Lifecycle in Detail

Here is exactly what happens from first message to approved itinerary:

### Iteration 1

```
User: "Hello, I just checked in."
  │
  └─► LoopAgent starts iteration 1
        │
        ├─► intake_agent receives the message
        │     • Checks state: no guest_profile yet
        │     • Asks the guest questions conversationally
        │     • Guest answers; intake_agent calls save_guest_profile(...)
        │     • state["guest_profile"] = { dietary_restrictions: [...], interests: [...], ... }
        │     • Summarises collected preferences back to the guest
        │
        ├─► discovery_agent runs (no user turn needed — driven by state)
        │     • Reads state["guest_profile"]
        │     • Calls search_nearby_places("restaurant", 48.8566, 2.3522, 5000)
        │     • Calls search_nearby_places("museum", 48.8566, 2.3522, 5000)
        │     • Calls search_nearby_places("park", ...) etc.
        │     • Calls save_discovered_options([...20 places...])
        │     • state["discovered_options"] = [...]
        │
        ├─► route_planner_agent runs
        │     • Reads state["guest_profile"] and state["discovered_options"]
        │     • Reads state["refinement_scope"] → not set yet, treat as "full"
        │     • Picks best 4-5 stops matching pace, budget, interests
        │     • For each pair of stops: compute_route(lat1, lng1, lat2, lng2, "walk")
        │     • For each stop: check_opening_hours(place_id, "10:30")
        │     • Calls save_day_plan({ date, stops: [...], total_travel_time, ... })
        │     • state["current_plan"] = { ... }
        │
        └─► presenter_agent runs
              • Reads state["current_plan"]
              • Tells the day as a story, referencing the guest's specific preferences
              • Ends with: "Does this work for you, or would you like to change anything?"
              • Waits for guest reply
```

### Iteration 2 (if guest asks for a change)

```
Guest: "Can you swap the lunch restaurant for something more casual?"
  │
  └─► LoopAgent starts iteration 2
        │
        ├─► intake_agent runs
        │     • Checks state: guest_profile EXISTS
        │     • Greets briefly, asks only what needs to change
        │     • (In this case: no profile change needed, may pass through quickly)
        │
        ├─► discovery_agent runs
        │     • Reads state["refinement_scope"] = "route_only" (set by presenter)
        │     • Skips new searches, uses existing discovered_options
        │
        ├─► route_planner_agent runs
        │     • Reads state["refinement_scope"] = "route_only"
        │     • Rebuilds route: swaps out the lunch stop for a more casual option
        │     • Calls save_day_plan with updated plan
        │
        └─► presenter_agent runs
              • Presents the revised plan
              • Guest says "Looks great!"
              • Calls record_feedback(action="approve", ...)
              • tool_context.actions.escalate = True ← ADK exits the loop
```

### Loop Exit

The `escalate = True` signal on `tool_context.actions` is the ADK mechanism for a sub-agent to tell the parent `LoopAgent` to stop. Once set, the loop does not start another iteration. The final response to the user (the presenter's "Plan approved!" message) is returned as the last output.

---

## 7. Data Models and Their Lifecycle

### 7.1 Data Flow Diagram

```
User input (natural language)
        │
        ▼
  GuestProfile (frozen dataclass)
  ┌─────────────────────────────┐
  │ guest_id                    │
  │ dietary_restrictions: tuple │
  │ interests: tuple            │
  │ mobility: str               │
  │ budget_level: str           │
  │ pace: str                   │
  │ party_composition: str      │
  │ time_available: TimeWindow  │
  │ special_requests: tuple     │
  └──────────────┬──────────────┘
                 │ .to_dict() → session.state["guest_profile"]
                 ▼
  DiscoveredOption × N (frozen dataclass, one per place found)
  ┌─────────────────────────────┐
  │ place_id, name, category    │
  │ rating, price_level         │
  │ lat_lng: tuple[float,float] │
  │ dietary_compatibility: float│
  │ interest_match: float       │
  │ travel_time_from_hotel: int │
  └──────────────┬──────────────┘
                 │ → scoring.score_and_filter_options() → top 20
                 │ .to_dict() × N → session.state["discovered_options"]
                 ▼
  DayPlan (frozen dataclass)
  ┌────────────────────────────────────────┐
  │ date: str                              │
  │ stops: tuple[ItineraryStop, ...]       │
  │   ItineraryStop:                       │
  │     order, arrival_time, departure_time│
  │     duration_minutes                   │
  │     place: DiscoveredOption            │
  │     travel_to_next: TravelSegment|None │
  │     notes: str                         │
  │ total_travel_time: int                 │
  │ estimated_total_cost: str              │
  │ weather_contingency: str               │
  │ back_at_hotel_by: str                  │
  └──────────────┬─────────────────────────┘
                 │ .to_dict() → session.state["current_plan"]
                 ▼
  FeedbackAction (frozen dataclass)
  ┌─────────────────────────────┐
  │ action: str (approve / ...) │
  │ target_stop: int | None     │
  │ details: str                │
  └──────────────┬──────────────┘
                 │ appended to session.state["feedback_history"]
                 │ (if approve) → tool_context.actions.escalate = True
```

### 7.2 Immutability

All models use `@dataclass(frozen=True)`. `tuple` is used instead of `list` for all collections inside models. No agent or tool mutates an existing model object; when a change is needed (e.g., updating the day plan), a new object is constructed and serialised via `.to_dict()`. Session state is updated by replacement, not mutation.

### 7.3 The Scoring Formula

Before the route planner sees candidates, the discovery agent scores and filters them. The formula lives in `concierge/tools/scoring.py` as a pure function:

```
composite_score =
    0.30 × interest_match           (how well the place matches stated interests)
  + 0.25 × rating_normalized        (1–5 star rating mapped to 0–1)
  + 0.20 × dietary_compatibility    (0–1; 0 = hard conflict with dietary restrictions)
  + 0.15 × proximity_score          (linear decay: 0 min → 1.0, 60+ min → 0.0)
  + 0.10 × price_match              (exact budget level match = 1.0; −0.25 per level off)
```

Places with `dietary_compatibility < 0.5` or `interest_match == 0.0` are filtered out entirely before scoring. The top 20 results are passed to the route planner. The weights are a frozen dataclass (`ScoringWeights`) that validates they sum to 1.0 in `__post_init__`.

---

## 8. The Entry Points

### 8.1 ADK Web UI (`adk web concierge`)

The ADK CLI discovers `root_agent` from `concierge/__init__.py`:

```python
from concierge.agents.orchestrator import build_concierge_orchestrator
root_agent = build_concierge_orchestrator()
```

Running `adk web concierge` from the `hotel-concierge/` directory starts a local web server that streams agent responses in real time. The runner used here is `InMemoryRunner` — session state lives in memory, scoped to a `(user_id, session_id)` pair.

### 8.2 CLI Runner (`python -m concierge.app`)

`concierge/app.py` creates an `InMemoryRunner`, sends an initial greeting message, then enters a read-eval-print loop. Each user input is wrapped in `types.UserContent` and sent via `runner.run_async()`. The async generator yields events; the CLI prints any `event.content.parts[].text`.

```python
runner = InMemoryRunner(agent=orchestrator, app_name=settings.app_name)
async for event in runner.run_async(user_id, session_id, new_message):
    if event.content and event.content.parts:
        for part in event.content.parts:
            if part.text:
                print(f"Concierge: {part.text}")
```

---

## 9. How the Frontend Communicates with the Backend

### 9.1 Frontend State Machine

The React app (`App.tsx`) is a four-state machine:

```
welcome ──[Start]──► questionnaire ──[Submit profile]──► loading ──[Plan ready]──► itinerary
                           ▲                                 │
                           └─────────[Error / Start over]────┘
```

The transitions are pure `useState` updates. There is no router; each state renders a different component.

### 9.2 The API Call

When the questionnaire completes, `App.tsx` calls `submitProfile(profile, sessionId)` from `src/api/agent.ts`:

```typescript
// Phase 1 (VITE_USE_MOCK !== 'false'): returns mock day plan after 2.5s delay
// Phase 2: POST http://localhost:8000/plan
const response = await fetch(`${API_BASE}/plan`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,        // ← session continuity
    },
    body: JSON.stringify({ profile }),
});
const data = await response.json();
return data.day_plan;   // → DayPlan type
```

The `session_id` is generated once per browser session with `generateSessionId()` and persisted in `localStorage` via the `useSession` hook. This means if the guest refreshes the page, their session continues (Phase 2: the backend ADK runner looks up the same session from Firestore by this ID).

### 9.3 Phase 1: Mock Mode

Currently (`VITE_USE_MOCK` defaults to `true`), the frontend never hits a real server. `submitProfile` waits 2,500ms (simulating agent processing time) and returns a hardcoded `mockDayPlan` with five example stops. This allows the frontend to be fully functional and testable without a running Python backend.

### 9.4 Data Contract: Frontend ↔ Backend

The TypeScript types in `src/types/index.ts` mirror the Python dataclass field names exactly. For example:

| Python (DayPlan) | TypeScript (DayPlan) |
|---|---|
| `date: str` | `date: string` |
| `stops: tuple[ItineraryStop, ...]` | `stops: ItineraryStop[]` |
| `total_travel_time: int` | `total_travel_time: number` |
| `back_at_hotel_by: str` | `back_at_hotel_by: string` |

The Python `.to_dict()` output is what the API endpoint will return as JSON. The TypeScript interface describes the shape of that JSON on the client side. They are maintained in sync manually (no codegen yet).

---

## 10. Configuration and Environment

All runtime behaviour is controlled through `concierge/config/settings.py`, a `pydantic_settings.BaseSettings` class that reads from `.env`:

```
GOOGLE_API_KEY=...            # Gemini
GOOGLE_MAPS_API_KEY=...       # Places & Routes

HOTEL_NAME="Grand Hotel"
HOTEL_ADDRESS="123 Main Street"
HOTEL_LAT=48.8566
HOTEL_LNG=2.3522

GEMINI_MODEL=gemini-2.5-flash
INTAKE_MODEL=gemini-2.5-flash      # override per agent
DISCOVERY_MODEL=gemini-2.5-flash
ROUTE_PLANNER_MODEL=gemini-2.5-flash
PRESENTER_MODEL=gemini-2.5-flash

MAX_LOOP_ITERATIONS=5
MAX_API_COST_PER_SESSION_USD=0.50
```

`get_settings()` returns a singleton. Every agent factory and tool reads from this singleton at construction time — if `INTAKE_MODEL` is set, the intake agent uses a different model than the others.

---

## 11. What Is Mocked in Phase 1

Phase 1 is fully runnable with zero real API keys. Three external services are mocked:

| Service | File | Phase 2 replacement |
|---|---|---|
| Google Places API (New) | `concierge/tools/places.py` | Real `POST /v1/places:searchNearby` |
| Google Routes API | `concierge/tools/routes.py` | Real `POST /directions/v2:computeRoutes` |
| Weather API | `concierge/tools/weather.py` | Open-Meteo or Google Weather |
| PMS (hotel system) | `concierge/tools/guest_history.py` | Real PMS API call |

Mock functions return dicts with `"status": "mock"` so logs make it obvious when real data is not being used. The `places.py` mock generates plausible-looking venue data (names, ratings, coordinates) seeded from the search query string.

---

## 12. Complete Call Sequence: First Guest Interaction

```
Browser                    React App              ADK Runner / Agents
  │                           │                         │
  │── clicks "Start" ────────►│                         │
  │                           │── setAppState(          │
  │                           │    'questionnaire')     │
  │                           │                         │
  │── answers questions ─────►│                         │
  │                           │── handleProfileComplete(│
  │                           │    profile)             │
  │                           │── setAppState('loading')│
  │                           │                         │
  │                           │── submitProfile(────────►│
  │                           │    profile,             │ POST /plan {profile}
  │                           │    sessionId)           │     OR mock delay
  │                           │                         │
  │                           │                         │── InMemoryRunner.run_async()
  │                           │                         │── LoopAgent iteration 1:
  │                           │                         │     intake_agent
  │                           │                         │       save_guest_profile()
  │                           │                         │     discovery_agent
  │                           │                         │       search_nearby_places()×3
  │                           │                         │       save_discovered_options()
  │                           │                         │     route_planner_agent
  │                           │                         │       compute_route()×4
  │                           │                         │       check_opening_hours()×4
  │                           │                         │       save_day_plan()
  │                           │                         │     presenter_agent
  │                           │                         │       (presents to user)
  │                           │                         │       record_feedback("approve")
  │                           │                         │       → escalate = True
  │                           │                         │── returns DayPlan dict
  │                           │◄── DayPlan ─────────────│
  │                           │── setDayPlan(plan)      │
  │                           │── setAppState(          │
  │                           │    'itinerary')         │
  │◄── renders DayPlanView ───│                         │
```

---

## 13. What Does Not Exist Yet (Phase 2)

The following are planned but not implemented:

- **FastAPI server** — the `POST /plan` endpoint that bridges the React frontend to the ADK runner
- **Feedback loop UI** — `POST /plan/feedback` for the guest to request changes from the itinerary view without going back through the questionnaire
- **Streaming responses** — the ADK runner supports streaming; the Phase 2 API will use SSE or WebSockets to stream the presenter's narrative in real time
- **Booking agent** — a fifth agent that calls OpenTable, Viator, etc. when the plan is approved
- **Google Sheets export** — the itinerary written to a shareable sheet
- **Email/SMS confirmation** — sending the approved plan to the guest
- **Firestore persistence** — swapping `InMemoryRunner` for a persistent session store so guests can return to their plan later
