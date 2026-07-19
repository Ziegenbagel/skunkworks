from pathlib import Path
import json


class KnowledgeLoader:
    """
    Load static game knowledge from the local
    game data directory.
    """

    def __init__(self):

        self.data_directory = (
            Path(__file__)
            .resolve()
            .parents[2]
            / "data"
            / "game"
        )

        self.gameplay_file = (
            self.data_directory
            / "gameplay.json"
        )

    def load(self):
        """
        Load gameplay.json and return its contents.
        """

        with open(
            self.gameplay_file,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)