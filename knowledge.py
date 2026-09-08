"""Constraint-based private knowledge model for a Cluedo AI player."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from cards import Card, SUSPECTS, WEAPONS
from mansion import ROOMS


ENVELOPE = "Envelope"
ALL_CARD_NAMES = tuple(SUSPECTS + WEAPONS + ROOMS)
CATEGORY_CARDS = {
    "Suspect": tuple(SUSPECTS),
    "Weapon": tuple(WEAPONS),
    "Room": tuple(ROOMS),
}


@dataclass(frozen=True)
class RefutationConstraint:
    """A disjunction stating that one owner has at least one listed card."""

    owner: str
    cards: frozenset[str]
    source: str


class KnowledgeBase:
    """Maintain and propagate possible-card-owner constraints for one AI."""

    def __init__(
        self,
        ai_name: str,
        player_names: Sequence[str],
        hand_sizes: Dict[str, int],
        own_hand: Sequence[Card],
        debug_mode: bool = False,
        log_directory: Optional[Path] = None,
    ) -> None:
        self.ai_name = ai_name
        self.player_names = tuple(player_names)
        self.hand_sizes = dict(hand_sizes)
        self.owners = set(player_names) | {ENVELOPE}
        self.domains: Dict[str, Set[str]] = {
            card: set(self.owners) for card in ALL_CARD_NAMES
        }
        self.constraints: List[RefutationConstraint] = []
        self.debug_mode = debug_mode
        safe_name = ai_name.lower().replace(" ", "_").replace(".", "")
        directory = log_directory or Path(__file__).resolve().parent
        self.log_path = directory / f"{safe_name}_log.txt"
        self.log_path.write_text(
            f"CLUEDO AI REASONING LOG: {ai_name}\n" + "=" * 60 + "\n",
            encoding="utf-8",
        )
        own_names = {card.name for card in own_hand}
        for card in ALL_CARD_NAMES:
            if card in own_names:
                self._set_owner(card, ai_name, "private hand")
            else:
                self._remove_owner(card, ai_name, "not in private hand")
        self.propagate("initial hand constraints")

    def log(self, message: str, detailed: bool = True) -> None:
        line = f"[{self.ai_name}] {message}"
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        if self.debug_mode or not detailed:
            print(line)

    def _remove_owner(self, card: str, owner: str, reason: str) -> bool:
        domain = self.domains[card]
        if owner not in domain:
            return False
        if len(domain) == 1:
            raise ValueError(f"Contradiction: cannot remove final owner of {card}")
        domain.remove(owner)
        self.log(f"ELIMINATE {owner} from {card}: {reason}")
        return True

    def _set_owner(self, card: str, owner: str, reason: str) -> bool:
        if owner not in self.domains[card]:
            raise ValueError(f"Contradiction: {owner} cannot own {card}")
        if self.domains[card] == {owner}:
            return False
        self.domains[card] = {owner}
        self.log(f"CONFIRM {card} -> {owner}: {reason}")
        return True

    def mark_has(self, owner: str, card: str, reason: str) -> None:
        self._set_owner(card, owner, reason)
        self.propagate(reason)

    def mark_not_has(self, owner: str, card: str, reason: str) -> None:
        self._remove_owner(card, owner, reason)
        self.propagate(reason)

    def observe_suggestion(
        self,
        suggester: str,
        cards: Sequence[str],
        passed_players: Sequence[str],
        refuter: Optional[str],
        shown_card: Optional[str] = None,
    ) -> None:
        triplet = tuple(cards)
        self.log(
            f"OBSERVE suggestion by {suggester}: {triplet}; passes={list(passed_players)}; "
            f"refuter={refuter or 'none'}"
        )
        for player in passed_players:
            for card in triplet:
                self._remove_owner(card, player, "passed clockwise refutation check")
        if refuter is not None:
            if shown_card is not None:
                self._set_owner(shown_card, refuter, "privately revealed card")
            else:
                constraint = RefutationConstraint(
                    refuter, frozenset(triplet), f"refuted {suggester}'s suggestion"
                )
                if constraint not in self.constraints:
                    self.constraints.append(constraint)
                    self.log(
                        f"ADD DISJUNCTION: {refuter} owns at least one of {sorted(triplet)}"
                    )
        else:
            for card in triplet:
                if suggester not in self.domains[card]:
                    self._set_owner(
                        card,
                        ENVELOPE,
                        "unrefuted and suggester already proven not to own card",
                    )
        self.propagate("suggestion evidence")

    def propagate(self, reason: str) -> None:
        self.log(f"PROPAGATION START: {reason}")
        changed = True
        iteration = 0
        while changed:
            iteration += 1
            changed = False
            self.log(f"Constraint iteration {iteration}")

            for constraint in list(self.constraints):
                candidates = [
                    card for card in constraint.cards
                    if constraint.owner in self.domains[card]
                ]
                if not candidates:
                    raise ValueError(
                        f"Contradiction in refutation constraint for {constraint.owner}"
                    )
                if len(candidates) == 1:
                    changed |= self._set_owner(
                        candidates[0], constraint.owner,
                        f"only remaining card in disjunction ({constraint.source})",
                    )

            for owner in self.player_names:
                confirmed = [
                    card for card, domain in self.domains.items() if domain == {owner}
                ]
                possible = [
                    card for card, domain in self.domains.items() if owner in domain
                ]
                target = self.hand_sizes[owner]
                if len(confirmed) == target:
                    for card in possible:
                        if self.domains[card] != {owner}:
                            changed |= self._remove_owner(
                                card, owner, f"{owner}'s hand size {target} is filled"
                            )
                elif len(possible) == target:
                    for card in possible:
                        changed |= self._set_owner(
                            card, owner, f"all {target} remaining owner slots required"
                        )

            for category, cards in CATEGORY_CARDS.items():
                envelope_confirmed = [
                    card for card in cards if self.domains[card] == {ENVELOPE}
                ]
                envelope_possible = [
                    card for card in cards if ENVELOPE in self.domains[card]
                ]
                if len(envelope_confirmed) == 1:
                    for card in envelope_possible:
                        if card != envelope_confirmed[0]:
                            changed |= self._remove_owner(
                                card, ENVELOPE,
                                f"{category} envelope slot already filled",
                            )
                elif len(envelope_possible) == 1:
                    changed |= self._set_owner(
                        envelope_possible[0], ENVELOPE,
                        f"only possible {category} envelope card",
                    )

            for card, domain in self.domains.items():
                if not domain:
                    raise ValueError(f"Contradiction: {card} has no possible owner")
        self.log(f"PROPAGATION FIXED POINT after {iteration} iteration(s)")

    def known_owner(self, card: str) -> Optional[str]:
        domain = self.domains[card]
        return next(iter(domain)) if len(domain) == 1 else None

    def solution(self) -> Optional[Tuple[str, str, str]]:
        solved: List[str] = []
        for cards in (SUSPECTS, WEAPONS, ROOMS):
            matches = [card for card in cards if self.domains[card] == {ENVELOPE}]
            if len(matches) != 1:
                return None
            solved.append(matches[0])
        return solved[0], solved[1], solved[2]

    def unknown_by_category(self, category: str) -> List[str]:
        return [
            card for card in CATEGORY_CARDS[category]
            if len(self.domains[card]) > 1
        ]

    def envelope_candidates(self, category: str) -> List[str]:
        return [
            card for card in CATEGORY_CARDS[category]
            if ENVELOPE in self.domains[card]
        ]

    def information_score(self, card: str) -> int:
        return len(self.domains[card])

    def matrix_lines(self) -> List[str]:
        lines = ["Card ownership domains:"]
        for category, cards in CATEGORY_CARDS.items():
            lines.append(f"  {category}s:")
            for card in cards:
                lines.append(f"    {card}: {', '.join(sorted(self.domains[card]))}")
        return lines

