"""Complete command-line Cluedo game with constraint-based AI players."""

from __future__ import annotations

import random
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional, Sequence, Tuple

from cards import (
    STARTING_POSITIONS,
    SUSPECTS,
    WEAPONS,
    Card,
    create_deck,
    create_solution,
    deal_cards,
)
from knowledge import KnowledgeBase
from mansion import ROOMS, Route, distance, find_routes, secret_passages
from player import Player


class CluedoGame:
    """Run classic Cluedo with humans, autonomous agents, and inactive slots."""

    def __init__(
        self,
        seed: Optional[int] = None,
        debug_mode: bool = False,
        input_function=input,
    ) -> None:
        self.rng = random.Random(seed)
        self.debug_mode = debug_mode
        self.input = input_function
        self.players: List[Player] = []
        self.player_lookup: Dict[str, Player] = {}
        self.solution = create_solution(self.rng)
        self.weapon_locations: Dict[str, Optional[str]] = {
            weapon: None for weapon in WEAPONS
        }
        self.turn_number = 1
        self.game_over = False
        self.winner: Optional[str] = None
        self.convergence_turns: Dict[str, int] = {}
        self.source_directory = Path(__file__).resolve().parent

    def run(self) -> None:
        self.print_title()
        self.setup_players()
        self.setup_cards()
        self.initialize_knowledge_bases()
        self.initialize_human_logs()
        self.print_setup_summary()
        self.turn_loop()
        self.print_final_statistics()

    @staticmethod
    def print_title() -> None:
        print("=" * 68)
        print("             WELCOME TO CLUEDO: AI EXPLORATION EDITION")
        print("=" * 68)
        print("Initializing Board Configuration... Done.")
        print("Loading 9 Rooms, 6 Suspects, 6 Weapons... Done.")
        print("Shortest-Path Distance Matrices Generated... Done.")

    def setup_players(self) -> None:
        while True:
            print("\n[STEP 1]: CONFIGURING ACTIVE PLAYER SLOTS")
            print("Select 1 = Human, 2 = AI Engine, 3 = Inactive/Skip.")
            configured: List[Player] = []
            for index, character in enumerate(SUSPECTS, start=1):
                minimum = 1 if index == 1 else 1
                choice = self.read_int(
                    f"Slot {index} - {character} type [1/2/3]: ", minimum, 3
                )
                if index == 1 and choice == 3:
                    print("Miss Scarlett is mandatory and cannot be inactive.")
                    choice = self.read_int(
                        f"Slot {index} - {character} type [1 Human/2 AI]: ", 1, 2
                    )
                if choice == 3:
                    print(f"-> Slot {index} disabled.")
                    continue
                player_type = "Human" if choice == 1 else "AI"
                configured.append(
                    Player(character, STARTING_POSITIONS[character], player_type)
                )
                print(f"-> Slot {index} assigned to {player_type.upper()} player.")
            ai_count = sum(player.is_ai for player in configured)
            if len(configured) < 3:
                print("Configuration rejected: at least 3 active players are required.")
                continue
            if ai_count < 1:
                print("Configuration rejected: at least one AI player is required.")
                continue
            self.players = configured
            self.player_lookup = {player.character: player for player in self.players}
            print(
                f"Configuration Complete: {len(configured)} Active Players "
                f"({len(configured) - ai_count} Human, {ai_count} AI)."
            )
            return

    def setup_cards(self) -> None:
        print("\n[STEP 2]: CONFIDENTIAL ENVELOPE GENERATION")
        print("> Extracting 1 Random Suspect Card... [CONFIDENTIAL]")
        print("> Extracting 1 Random Weapon Card... [CONFIDENTIAL]")
        print("> Extracting 1 Random Room Card... [CONFIDENTIAL]")
        print(">> Murder Envelope locked and sealed.")
        deck = create_deck(self.solution)
        hands = deal_cards([player.character for player in self.players], deck, self.rng)
        for player in self.players:
            player.hand = hands[player.character]
        print("\n[STEP 3]: CARD DEALING & ENGINE INITIALIZATION")
        print("Remaining 18 cards shuffled and dealt clockwise.")

    def initialize_knowledge_bases(self) -> None:
        hand_sizes = {player.character: len(player.hand) for player in self.players}
        names = [player.character for player in self.players]
        for player in self.players:
            if player.is_ai:
                player.knowledge = KnowledgeBase(
                    player.character,
                    names,
                    hand_sizes,
                    player.hand,
                    self.debug_mode,
                    self.source_directory,
                )
                print(f"[AI BOOT] {player.character}: private matrix initialized.")

    def initialize_human_logs(self) -> None:
        for player in self.players:
            if not player.is_ai:
                self.write_human_log(player)

    def print_setup_summary(self) -> None:
        print("\n" + "=" * 68)
        print("SETUP COMPLETE. Active clockwise order:")
        for index, player in enumerate(self.players, start=1):
            print(f"Slot {index}: {player.character} -> {player.player_type.upper()}")
        print(f"Miss Scarlett begins turn execution.")
        print("=" * 68)
        self.pause("Press ENTER to begin...")

    def turn_loop(self) -> None:
        while not self.game_over:
            for player in self.players:
                if self.game_over:
                    break
                if not player.can_take_turn:
                    continue
                print("\n" + "#" * 68)
                print(
                    f"[TURN {self.turn_number}] {player.character} "
                    f"[{player.player_type.upper()}] - Start of Turn"
                )
                print("#" * 68)
                self.take_turn(player)
                self.record_convergence()
                self.turn_number += 1
                self.check_last_player()

    def take_turn(self, player: Player) -> None:
        if player.is_ai:
            self.take_ai_turn(player)
        else:
            self.take_human_turn(player)

    def take_human_turn(self, player: Player) -> None:
        self.private_screen(player)
        print(self.human_sheet(player))
        action = self.choose_from_menu(
            "Options:", ["Roll/Move", "Make Formal Accusation"]
        )
        if action == 2:
            accusation = self.prompt_accusation()
            self.resolve_accusation(player, accusation)
            return
        if player.moved_by_suggestion:
            action = self.choose_from_menu(
                "You were moved here by a suggestion:",
                ["Suggest immediately", "Roll and move"],
            )
            player.moved_by_suggestion = False
            if action == 1:
                self.make_suggestion(player)
                return
        self.perform_human_movement(player)

    def take_ai_turn(self, player: Player) -> None:
        knowledge = self.ai_knowledge(player)
        solution = knowledge.solution()
        if solution is not None:
            knowledge.log(f"DECISION: definitive solution {solution}; accuse now", False)
            self.resolve_accusation(player, solution)
            return
        if player.moved_by_suggestion:
            player.moved_by_suggestion = False
            knowledge.log("DECISION: use current room for immediate information gain", False)
            self.make_suggestion(player)
            return
        self.perform_ai_movement(player)

    def perform_human_movement(self, player: Player) -> None:
        passages = secret_passages(player.location)
        options = ["Roll the die", "Stay in current room"]
        if passages:
            options.insert(0, "Use secret passage")
        action = self.choose_from_menu("Movement:", options)
        if passages and action == 1:
            destination = self.choose_named_item("Secret passage destination: ", passages)
            self.move_and_suggest(player, Route((player.location, destination), 0))
            return
        stay_index = 3 if passages else 2
        if action == stay_index:
            print(f"{player.character} forfeits movement.")
            return
        self.pause("Press ENTER to roll...")
        roll = self.rng.randint(1, 6)
        print(f"> You rolled a {roll}.")
        routes = find_routes(player.location, roll)
        if not routes:
            print("Low-roll validation: no adjacent route is affordable.")
            return
        self.select_human_route(player, routes, roll)

    def select_human_route(self, player: Player, routes: List[Route], roll: int) -> None:
        print(f"Valid destinations for roll {roll}:")
        for index, route in enumerate(routes, start=1):
            print(f"  {index}. {route.display()}")
        print(f"  {len(routes) + 1}. Forfeit movement")
        choice = self.read_int("Choose route: ", 1, len(routes) + 1)
        if choice == len(routes) + 1:
            print("Movement forfeited.")
            return
        self.move_and_suggest(player, routes[choice - 1])

    def perform_ai_movement(self, player: Player) -> None:
        knowledge = self.ai_knowledge(player)
        room_candidates = knowledge.envelope_candidates("Room")
        target = max(
            room_candidates,
            key=lambda room: (knowledge.information_score(room), -distance(player.location, room)),
        )
        passages = secret_passages(player.location)
        if target in passages:
            route = Route((player.location, target), 0)
            knowledge.log(f"MOVEMENT: secret passage targets unknown room {target}", False)
            self.move_and_suggest(player, route)
            return
        roll = self.rng.randint(1, 6)
        print(f"[AI ROLL] {player.character} rolled {roll}.")
        routes = find_routes(player.location, roll)
        if not routes:
            knowledge.log("MOVEMENT: low roll; no valid adjacent edge", False)
            return
        route = min(
            routes,
            key=lambda candidate: (
                distance(candidate.destination, target),
                -knowledge.information_score(candidate.destination),
                candidate.cost,
            ),
        )
        knowledge.log(
            f"MOVEMENT: target={target}; chose {route.destination} by shortest-path heuristic",
            False,
        )
        self.move_and_suggest(player, route)

    def move_and_suggest(self, player: Player, route: Route) -> None:
        old = player.location
        player.location = route.destination
        print(f"> Moving {player.character}: {old} -> {player.location}")
        print(f"> Route validated: {route.display()}")
        self.make_suggestion(player)

    def make_suggestion(self, player: Player) -> None:
        if player.is_ai:
            suspect, weapon = self.choose_ai_suggestion(player)
        else:
            print(f"[LOCATION LOCKED]: suggestion room is {player.location}.")
            suspect = self.choose_named_item("Suspect: ", SUSPECTS)
            weapon = self.choose_named_item("Weapon: ", WEAPONS)
        cards = (suspect, weapon, player.location)
        print(f"SUGGESTION: {suspect}, {weapon}, {player.location}")
        player.suggestion_history.append(", ".join(cards))
        suggested_player = self.player_lookup.get(suspect)
        if suggested_player is not None and suggested_player.location != player.location:
            suggested_player.location = player.location
            suggested_player.moved_by_suggestion = True
        self.weapon_locations[weapon] = player.location
        self.resolve_refutation(player, cards)

    def choose_ai_suggestion(self, player: Player) -> Tuple[str, str]:
        knowledge = self.ai_knowledge(player)
        suspect = max(
            SUSPECTS,
            key=lambda card: (
                knowledge.information_score(card),
                card not in {owned.name for owned in player.hand},
            ),
        )
        weapon = max(
            WEAPONS,
            key=lambda card: (
                knowledge.information_score(card),
                card not in {owned.name for owned in player.hand},
            ),
        )
        knowledge.log(
            f"SUGGESTION DECISION: selected {suspect}, {weapon}, {player.location} "
            "to maximize unresolved ownership domains",
            False,
        )
        return suspect, weapon

    def resolve_refutation(self, suggester: Player, cards: Sequence[str]) -> None:
        print("--- Clockwise Refutation Loop Started ---")
        passed: List[str] = []
        refuter: Optional[Player] = None
        shown_card: Optional[str] = None
        start = self.players.index(suggester)
        for offset in range(1, len(self.players)):
            candidate = self.players[(start + offset) % len(self.players)]
            matches = [card for card in candidate.hand if card.name in cards]
            if not matches:
                passed.append(candidate.character)
                print(f"> Checking {candidate.character}... PASSES.")
                continue
            refuter = candidate
            print(f"> Checking {candidate.character}... REFUTES.")
            shown_card = self.choose_refutation_card(candidate, matches, suggester)
            break
        for ai in self.ai_players():
            private_card = shown_card if ai is suggester else None
            self.ai_knowledge(ai).observe_suggestion(
                suggester.character,
                cards,
                passed,
                refuter.character if refuter else None,
                private_card,
            )
        if refuter is None:
            print("No player could refute the suggestion.")
        elif suggester.is_ai:
            print(f"{refuter.character} privately showed the AI one card.")
            self.ai_knowledge(suggester).log(
                f"PRIVATE REVEAL: {refuter.character} showed {shown_card}", False
            )
        else:
            print(f"[PRIVATE FOR {suggester.character}] {refuter.character} showed {shown_card}.")
        public_note = (
            f"{suggester.character} suggested {', '.join(cards)}; "
            f"passes: {', '.join(passed) or 'none'}; "
            f"refuter: {refuter.character if refuter else 'none'}"
        )
        for human in self.human_players():
            human.deduction_notes.append(public_note)
        if not suggester.is_ai and refuter is not None and shown_card is not None:
            suggester.deduction_notes.append(
                f"CONFIRMED: {refuter.character} owns {shown_card} (private reveal)."
            )
        for human in self.human_players():
            self.write_human_log(human)
        print("--- Clockwise Refutation Loop Terminated ---")

    def choose_refutation_card(
        self, refuter: Player, matches: List[Card], suggester: Player
    ) -> str:
        if refuter.is_ai:
            previous = [card.name for card in matches if card.name in suggester.suggestion_history]
            chosen = next((card for card in matches if card.name in previous), matches[0])
            self.ai_knowledge(refuter).log(
                f"REFUTATION: privately selected {chosen.name} from {len(matches)} match(es)"
            )
            return chosen.name
        print(f"\n[PRIVATE SECURITY SCREEN] Pass device to {refuter.character}.")
        self.pause("Press ENTER when ready...")
        if len(matches) == 1:
            chosen = matches[0]
        else:
            chosen_name = self.choose_named_item(
                "Choose exactly one card to reveal: ", [card.name for card in matches]
            )
            chosen = next(card for card in matches if card.name == chosen_name)
        print(f"Card selected privately for {suggester.character}.")
        return chosen.name

    def prompt_accusation(self) -> Tuple[str, str, str]:
        print("Formal accusation (location is not restricted):")
        return (
            self.choose_named_item("Suspect: ", SUSPECTS),
            self.choose_named_item("Weapon: ", WEAPONS),
            self.choose_named_item("Room: ", ROOMS),
        )

    def resolve_accusation(self, player: Player, accusation: Sequence[str]) -> bool:
        print(f"FORMAL ACCUSATION by {player.character}: {tuple(accusation)}")
        actual = (self.solution.suspect, self.solution.weapon, self.solution.room)
        if tuple(accusation) == actual:
            self.winner = player.character
            self.game_over = True
            print(f"CORRECT. {player.character} wins immediately!")
            print(f"Solution: {actual}")
            return True
        player.eliminated = True
        print(
            f"INCORRECT. {player.character} is eliminated from turns, "
            "but retains cards and must continue refuting."
        )
        return False

    def check_last_player(self) -> None:
        remaining = [player for player in self.players if not player.eliminated]
        if not self.game_over and len(remaining) == 1:
            self.winner = remaining[0].character
            self.game_over = True
            print(f"Only {self.winner} remains eligible to win. Game over.")

    def record_convergence(self) -> None:
        for player in self.ai_players():
            if (
                player.character not in self.convergence_turns
                and self.ai_knowledge(player).solution() is not None
            ):
                self.convergence_turns[player.character] = self.turn_number
                self.ai_knowledge(player).log(
                    f"CONVERGENCE at total game turn {self.turn_number}", False
                )

    def print_final_statistics(self) -> None:
        print("\n" + "=" * 68)
        print("GAME TERMINATED")
        print(f"Winner: {self.winner or 'none'}")
        if self.convergence_turns:
            value = mean(self.convergence_turns.values())
            print(f"Mean Turn-to-Convergence: {value:.2f} total game turns")
        else:
            print("Mean Turn-to-Convergence: N/A (no AI reached a definitive solution)")
        print("=" * 68)

    def private_screen(self, player: Player) -> None:
        print(f"[PRIVATE SECURITY SCREEN] Pass the device to {player.character}.")
        self.pause("Press ENTER to view secret hand...")
        print("Your dealt cards:")
        print(player.show_hand())

    def human_sheet(self, player: Player) -> str:
        own_names = {card.name for card in player.hand}
        own = ", ".join(sorted(own_names)) or "none"
        suspects = len([name for name in SUSPECTS if name not in own_names])
        weapons = len([name for name in WEAPONS if name not in own_names])
        rooms = len([name for name in ROOMS if name not in own_names])
        history = player.suggestion_history[-5:]
        lines = [
            "\n[HUMAN ASSISTANCE SHEET]",
            f"Confirmed in your hand: {own}",
            f"Unknown variables: {suspects} suspects, {weapons} weapons, {rooms} rooms.",
            "Recent suggestions:",
        ]
        lines.extend(f"  - {item}" for item in history)
        if not history:
            lines.append("  - none")
        lines.append("Confirmed/eliminated tracking notes:")
        lines.extend(f"  - {item}" for item in player.deduction_notes[-10:])
        if not player.deduction_notes:
            lines.append("  - none")
        return "\n".join(lines)

    def write_human_log(self, player: Player) -> None:
        safe = player.character.lower().replace(" ", "_").replace(".", "")
        path = self.source_directory / f"{safe}_human_sheet.txt"
        path.write_text(self.human_sheet(player) + "\n", encoding="utf-8")

    def ai_players(self) -> List[Player]:
        return [player for player in self.players if player.is_ai]

    def human_players(self) -> List[Player]:
        return [player for player in self.players if not player.is_ai]

    @staticmethod
    def ai_knowledge(player: Player) -> KnowledgeBase:
        if not isinstance(player.knowledge, KnowledgeBase):
            raise RuntimeError(f"AI knowledge was not initialized for {player.character}")
        return player.knowledge

    def pause(self, prompt: str) -> None:
        self.input(prompt)

    def read_int(self, prompt: str, minimum: int, maximum: int) -> int:
        while True:
            raw = self.input(prompt).strip()
            try:
                value = int(raw)
            except ValueError:
                print("Invalid input: enter a whole number.")
                continue
            if minimum <= value <= maximum:
                return value
            print(f"Invalid input: enter a number from {minimum} through {maximum}.")

    @staticmethod
    def resolve_choice(raw_choice: str, options: Sequence[str]) -> Optional[str]:
        if raw_choice.isdigit():
            index = int(raw_choice) - 1
            if 0 <= index < len(options):
                return options[index]
        return next(
            (option for option in options if option.casefold() == raw_choice.casefold()),
            None,
        )

    def choose_named_item(self, prompt: str, options: Sequence[str]) -> str:
        for index, option in enumerate(options, start=1):
            print(f"  {index}. {option}")
        while True:
            resolved = self.resolve_choice(self.input(prompt).strip(), options)
            if resolved is not None:
                return resolved
            print("Invalid choice. Enter a listed number or exact name.")

    def choose_from_menu(self, heading: str, options: Sequence[str]) -> int:
        print(f"\n{heading}")
        for index, option in enumerate(options, start=1):
            print(f"  {index}. {option}")
        return self.read_int("Enter choice: ", 1, len(options))
