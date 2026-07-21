"""
Canonical resource definitions used throughout
Skunkworks.
"""

RESOURCE_DEFINITIONS = {
    "metals": {
        "display_name": "Metals",
    },
    "ice": {
        "display_name": "Ice",
    },
    "organic": {
        "display_name": "Organic Compounds",
    },
    "deuterium": {
        "display_name": "Deuterium",
    },
}

class ResourceKnowledge:
    """
    Provides normalized access to
    resource definitions.
    """

    def __init__(self):

        self._resources = (
            RESOURCE_DEFINITIONS
        )

    def get_display_name(
        self,
        resource_name,
    ):
        """
        Return the user-facing name for a
        resource.
        """

        definition = self._resources.get(
            resource_name
        )

        if definition is None:

            return resource_name

        return definition[
            "display_name"
        ]
    
    def list_resources(
        self,
    ):
        """
        Return all known resources.
        """

        return sorted(
            self._resources.keys()
        )
    
    def resource_exists(
        self,
        resource_name,
    ):
        """
        Return whether a resource exists.
        """

        return (
            resource_name
            in self._resources
        )