"""Tools that read/write session state shared between agents."""

from google.adk.tools import ToolContext

from concierge.models.day_plan import DayPlan
from concierge.models.feedback import FeedbackAction
from concierge.models.guest_profile import GuestProfile

# Session state keys — single source of truth
KEY_GUEST_PROFILE = "guest_profile"
KEY_DISCOVERED_OPTIONS = "discovered_options"
KEY_CURRENT_PLAN = "current_plan"
KEY_PLAN_APPROVED = "plan_approved"
KEY_ITERATION_COUNT = "iteration_count"
KEY_FEEDBACK_HISTORY = "feedback_history"
KEY_REFINEMENT_SCOPE = "refinement_scope"


def save_guest_profile(
    guest_id: str,
    dietary_restrictions: list[str],
    interests: list[str],
    mobility: str,
    budget_level: str,
    pace: str,
    party_composition: str,
    start_time: str,
    end_time: str,
    location_context: str,
    special_requests: list[str],
    tool_context: ToolContext,
) -> str:
    """Persist collected guest preferences to session state.

    Args:
        guest_id: Unique guest identifier.
        dietary_restrictions: e.g. ["vegan", "nut-allergy"].
        interests: e.g. ["art", "nightlife", "local-food"].
        mobility: "full", "limited", or "wheelchair".
        budget_level: "budget", "moderate", or "luxury".
        pace: "relaxed", "moderate", or "packed".
        party_composition: "solo", "couple", "family_young_kids", or "group".
        start_time: Day start in "HH:MM" format.
        end_time: Day end in "HH:MM" format.
        location_context: Hotel address for proximity calculations.
        special_requests: Free-form notes from the guest.

    Returns:
        Confirmation message.
    """
    from concierge.models.guest_profile import TimeWindow

    profile = GuestProfile(
        guest_id=guest_id,
        dietary_restrictions=tuple(dietary_restrictions),
        interests=tuple(interests),
        mobility=mobility,
        budget_level=budget_level,
        pace=pace,
        party_composition=party_composition,
        time_available=TimeWindow(start_time=start_time, end_time=end_time),
        location_context=location_context,
        special_requests=tuple(special_requests),
    )
    tool_context.state[KEY_GUEST_PROFILE] = profile.to_dict()
    return f"Guest profile saved for {guest_id}."


def save_day_plan(
    plan_dict: dict,
    tool_context: ToolContext,
) -> str:
    """Persist a built day plan to session state.

    Args:
        plan_dict: Serialized DayPlan as returned by the route planner.

    Returns:
        Confirmation message.
    """
    tool_context.state[KEY_CURRENT_PLAN] = plan_dict
    return f"Day plan saved with {len(plan_dict.get('stops', []))} stops."


def record_feedback(
    action: str,
    details: str,
    target_stop: int | None,
    tool_context: ToolContext,
) -> str:
    """Record guest feedback and set refinement scope.

    Args:
        action: One of approve, swap_stop, change_time, add_activity,
                remove_stop, change_pace, restart.
        details: Free-text elaboration of the feedback.
        target_stop: Stop index affected (if applicable).

    Returns:
        Next-step instruction for the orchestrator.
    """
    feedback = FeedbackAction(action=action, target_stop=target_stop, details=details)
    history = list(tool_context.state.get(KEY_FEEDBACK_HISTORY, []))
    tool_context.state[KEY_FEEDBACK_HISTORY] = history + [feedback.to_dict()]

    if action == "approve":
        tool_context.state[KEY_PLAN_APPROVED] = True
        tool_context.actions.escalate = True
        return "Plan approved! Exiting refinement loop."

    scope_map = {
        "swap_stop": "route_only",
        "change_time": "route_only",
        "remove_stop": "route_only",
        "change_pace": "route_only",
        "add_activity": "discovery_narrow",
        "restart": "full",
    }
    tool_context.state[KEY_REFINEMENT_SCOPE] = scope_map.get(action, "full")
    return f"Feedback recorded: {action}. Refinement scope: {tool_context.state[KEY_REFINEMENT_SCOPE]}."
