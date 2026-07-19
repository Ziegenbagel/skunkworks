from src.knowledge.loader import (
    KnowledgeLoader,
)


class GameplayKnowledge:
    """
    Provides access to static game knowledge.
    """

    def __init__(self):

        loader = KnowledgeLoader()

        self.data = loader.load()