"""Property Management System (PMS) integration.

Phase 1: Uses mock data. Phase 2: Connect to real PMS via GuestHistoryRepository.
"""

from google.adk.tools import ToolContext


def get_guest_history(
    guest_id: str,
    tool_context: ToolContext = None,
) -> dict:
    """Fetch a guest's history and preferences from the PMS.

    Args:
        guest_id: Unique guest identifier from hotel PMS.

    Returns:
        Dict with past_stays, preferred_categories, special_notes.
    """
    # TODO Phase 2: Replace with real PMS API call via GuestHistoryRepository
    return {
        "guest_id": guest_id,
        "past_stays": 0,
        "preferred_categories": [],
        "special_notes": "",
        "loyalty_tier": "standard",
        "status": "mock",
    }
