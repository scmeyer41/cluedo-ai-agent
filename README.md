# Cluedo AI Agent

A command-line implementation of Cluedo featuring autonomous agents that reason under partial observability. Each AI maintains private card-ownership domains, incorporates evidence from suggestions and refutations, and repeatedly applies general constraints until reaching a fixed point.

This project was completed by me for CS 670: Artificial Intelligence.

## Highlights

- Constraint-satisfaction model covering all 21 cards and their possible owners
- Fixed-point logical inference from private hands, missed refutations, revealed cards, hand sizes, and envelope rules
- Disjunctive reasoning when an opponent refutes a suggestion without revealing the card publicly
- Dijkstra shortest-path movement across a weighted mansion graph
- Information-driven room targeting and card suggestions
- Support for human, AI, and inactive player slots
- Private clockwise refutation, accusations, elimination, and complete game termination
- Persistent reasoning logs for inspecting AI decisions
- Eight deterministic unit tests

## How the AI works

Every card is represented as a variable whose domain contains its possible owners: the active players and the confidential envelope. Observations remove impossible owners or confirm a single owner.

For example, if a player refutes a three-card suggestion, the AI records that the player owns at least one of those cards. If later evidence eliminates two of the three possibilities, the remaining card is automatically assigned to that player. The same propagation engine also enforces exact hand sizes and exactly one suspect, weapon, and room in the envelope.

The AI makes an accusation only after its knowledge base has logically confirmed all three solution cards.

## Project structure

| File | Purpose |
| --- | --- |
| `main.py` | Application entry point |
| `game.py` | Setup, turn flow, decisions, refutations, accusations, and logging |
| `knowledge.py` | Constraint domains, evidence handling, and fixed-point inference |
| `mansion.py` | Weighted room graph and Dijkstra pathfinding |
| `cards.py` | Card definitions, solution generation, deck creation, and dealing |
| `player.py` | Human and AI player state |
| `config.py` | Debug-mode configuration |
| `test_project.py` | Deterministic unit tests |
| `docs/technical-documentation.pdf` | Detailed design, algorithms, and evaluation |

## Requirements

- Python 3.10 or newer
- No third-party packages

## Run the game

From the repository directory:

```bash
python main.py
```

Configure all six character slots as Human, AI, or Inactive when prompted. Miss Scarlett must remain active; the game requires three to six active players and at least one AI.

## Run the tests

```bash
python -m unittest -v test_project.py
```

All eight tests cover the following behaviors:

- Solution-card exclusion and even dealing
- Shortest paths and low-roll movement rejection
- Private-hand constraints
- Negative evidence from missed refutations
- Single-card inference from a refutation constraint
- Safe inference from an unrefuted suggestion
- Correct and incorrect accusation handling

## Verified result

All eight automated tests pass. In the seeded three-agent integration scenario documented in the report, the game terminated correctly on turn 38, with a mean solution-convergence time of 35 turns.

## Debugging and reasoning logs

Set `DEBUG_MODE = True` in `config.py` to print domain eliminations, confirmations, propagation iterations, and decisions. The program also generates character-specific reasoning logs during play. These runtime files are excluded from version control.

## Documentation

See [the technical documentation](docs/technical-documentation.pdf) for the full architecture, inference rules, gameplay implementation, test scenarios, and development discussion.

