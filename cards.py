"""Card definitions and game setup helpers."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from mansion import ROOMS


SUSPECTS = [
    "Miss Scarlett",
    "Colonel Mustard",
    "Mrs. White",
    "Reverend Green",
    "Mrs. Peacock",
    "Professor Plum",
]

WEAPONS = [
    "Candlestick",
    "Dagger",
    "Lead Pipe",
    "Revolver",
    "Rope",
    "Wrench",
]

STARTING_POSITIONS = {
    "Miss Scarlett": "Lounge",
    "Colonel Mustard": "Dining Room",
    "Mrs. White": "Kitchen",
    "Reverend Green": "Ballroom",
    "Mrs. Peacock": "Conservatory",
    "Professor Plum": "Library",
}


@dataclass(frozen=True)
class Card:
    """A Cluedo card."""

    category: str
    name: str

    def __str__(self) -> str:
        return f"{self.category}: {self.name}"


@dataclass(frozen=True)
class Solution:
    """The hidden murder solution."""

    suspect: str
    weapon: str
    room: str


def create_solution(rng: random.Random) -> Solution:
    """Randomly choose one suspect, weapon, and room for the envelope."""
    return Solution(
        suspect=rng.choice(SUSPECTS),
        weapon=rng.choice(WEAPONS),
        room=rng.choice(ROOMS),
    )


def create_deck(solution: Solution) -> List[Card]:
    """Create all cards except the three hidden solution cards."""
    deck: List[Card] = []

    deck.extend(
        Card("Suspect", suspect)
        for suspect in SUSPECTS
        if suspect != solution.suspect
    )
    deck.extend(
        Card("Weapon", weapon)
        for weapon in WEAPONS
        if weapon != solution.weapon
    )
    deck.extend(
        Card("Room", room)
        for room in ROOMS
        if room != solution.room
    )

    return deck


def deal_cards(
    player_names: Sequence[str],
    deck: List[Card],
    rng: random.Random,
) -> Dict[str, List[Card]]:
    """Shuffle and distribute cards as evenly as possible."""
    shuffled = list(deck)
    rng.shuffle(shuffled)

    hands: Dict[str, List[Card]] = {name: [] for name in player_names}

    for index, card in enumerate(shuffled):
        player_name = player_names[index % len(player_names)]
        hands[player_name].append(card)

    for hand in hands.values():
        hand.sort(key=lambda card: (card.category, card.name))

    return hands
