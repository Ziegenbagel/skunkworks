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


def get_display_name(
    resource_name,
):
    """
    Return the user-facing name for a
    resource.
    """

    definition = RESOURCE_DEFINITIONS.get(
        resource_name
    )

    if definition is None:

        return resource_name

    return definition[
        "display_name"
    ]