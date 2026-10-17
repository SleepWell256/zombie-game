import pathlib
import sys

# Ensure project root is in sys.path regardless of how main.py is invoked
project_root = str(pathlib.Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.game.game import Game


def main() -> None:
    """Instantiate and run the game."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
