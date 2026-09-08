"""Player model for the Cluedo game."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cards import Card


@dataclass
class Player:
    """Represents an active Cluedo character."""

    character: str
    location: str
    player_type: str = "Human"
    hand: List[Card] = field(default_factory=list)
    moved_by_suggestion: bool = False
    eliminated: bool = False
    knowledge: Optional[object] = None
    suggestion_history: List[str] = field(default_factory=list)
    deduction_notes: List[str] = field(default_factory=list)

    def show_hand(self) -> str:
        if not self.hand:
            return "(no cards)"
        return "\n".join(f"  - {card}" for card in self.hand)

    @property
    def is_ai(self) -> bool:
        return self.player_type == "AI"

    @property
    def can_take_turn(self) -> bool:
        return not self.eliminated
