"""Program entry point for Cluedo Project 2 Part 2."""

from config import DEBUG_MODE
from game import CluedoGame


def main() -> None:
    game = CluedoGame(debug_mode=DEBUG_MODE)
    game.run()


if __name__ == "__main__":
    main()
