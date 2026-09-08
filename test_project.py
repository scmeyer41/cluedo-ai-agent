"""Deterministic unit and integration tests for Project 2 Part 2."""

import random
import tempfile
import unittest
from pathlib import Path

from cards import Card, Solution, create_deck, deal_cards
from game import CluedoGame
from knowledge import ENVELOPE, KnowledgeBase
from mansion import find_routes, shortest_route
from player import Player


class ProjectTests(unittest.TestCase):
    def make_knowledge(self, directory: str) -> KnowledgeBase:
        own_hand = [
            Card("Suspect", "Miss Scarlett"),
            Card("Weapon", "Dagger"),
            Card("Room", "Study"),
        ]
        return KnowledgeBase(
            "Miss Scarlett",
            ["Miss Scarlett", "Colonel Mustard", "Mrs. White"],
            {"Miss Scarlett": 3, "Colonel Mustard": 8, "Mrs. White": 7},
            own_hand,
            False,
            Path(directory),
        )

    def test_deck_contains_eighteen_cards(self):
        solution = Solution("Miss Scarlett", "Rope", "Study")
        deck = create_deck(solution)
        self.assertEqual(len(deck), 18)
        self.assertNotIn("Miss Scarlett", {card.name for card in deck})
        self.assertNotIn("Rope", {card.name for card in deck})
        self.assertNotIn("Study", {card.name for card in deck})

    def test_even_dealing(self):
        deck = create_deck(Solution("Miss Scarlett", "Rope", "Study"))
        hands = deal_cards(["A", "B", "C", "D", "E"], deck, random.Random(4))
        sizes = [len(hand) for hand in hands.values()]
        self.assertLessEqual(max(sizes) - min(sizes), 1)

    def test_shortest_path_and_low_roll(self):
        route = shortest_route("Study", "Billiard Room")
        self.assertIsNotNone(route)
        self.assertEqual(route.cost, 6)
        self.assertEqual(find_routes("Ballroom", 2), [])

    def test_private_hand_constraints(self):
        with tempfile.TemporaryDirectory() as directory:
            knowledge = self.make_knowledge(directory)
            self.assertEqual(knowledge.known_owner("Dagger"), "Miss Scarlett")
            self.assertNotIn("Miss Scarlett", knowledge.domains["Rope"])

    def test_passes_eliminate_possible_owners(self):
        with tempfile.TemporaryDirectory() as directory:
            knowledge = self.make_knowledge(directory)
            knowledge.observe_suggestion(
                "Mrs. White",
                ("Professor Plum", "Rope", "Kitchen"),
                ["Colonel Mustard"],
                None,
            )
            for card in ("Professor Plum", "Rope", "Kitchen"):
                self.assertNotIn("Colonel Mustard", knowledge.domains[card])

    def test_advanced_single_card_refutation_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            knowledge = self.make_knowledge(directory)
            knowledge.mark_not_has("Colonel Mustard", "Rope", "prior evidence")
            knowledge.mark_not_has("Colonel Mustard", "Kitchen", "prior evidence")
            knowledge.observe_suggestion(
                "Mrs. White",
                ("Professor Plum", "Rope", "Kitchen"),
                [],
                "Colonel Mustard",
            )
            self.assertEqual(
                knowledge.known_owner("Professor Plum"), "Colonel Mustard"
            )

    def test_unrefuted_card_can_be_confirmed_in_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            knowledge = self.make_knowledge(directory)
            knowledge.mark_not_has("Mrs. White", "Rope", "prior evidence")
            knowledge.observe_suggestion(
                "Mrs. White",
                ("Professor Plum", "Rope", "Kitchen"),
                ["Colonel Mustard"],
                None,
            )
            self.assertEqual(knowledge.known_owner("Rope"), ENVELOPE)

    def test_correct_and_incorrect_accusations(self):
        game = CluedoGame(seed=1)
        game.solution = Solution("Miss Scarlett", "Rope", "Study")
        wrong = Player("Miss Scarlett", "Lounge")
        self.assertFalse(game.resolve_accusation(wrong, ("Mrs. White", "Rope", "Study")))
        self.assertTrue(wrong.eliminated)
        right = Player("Colonel Mustard", "Dining Room")
        self.assertTrue(game.resolve_accusation(right, ("Miss Scarlett", "Rope", "Study")))
        self.assertTrue(game.game_over)


if __name__ == "__main__":
    unittest.main(verbosity=2)
