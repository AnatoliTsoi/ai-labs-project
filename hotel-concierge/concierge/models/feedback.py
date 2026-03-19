from dataclasses import dataclass

VALID_ACTIONS = frozenset({
    "approve",
    "swap_stop",
    "change_time",
    "add_activity",
    "remove_stop",
    "change_pace",
    "restart",
})


@dataclass(frozen=True)
class FeedbackAction:
    action: str           # one of VALID_ACTIONS
    target_stop: int | None
    details: str

    def __post_init__(self) -> None:
        if self.action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action: {self.action!r}. Must be one of {VALID_ACTIONS}")

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "target_stop": self.target_stop,
            "details": self.details,
        }

    @staticmethod
    def from_dict(data: dict) -> "FeedbackAction":
        return FeedbackAction(
            action=data["action"],
            target_stop=data.get("target_stop"),
            details=data.get("details", ""),
        )
