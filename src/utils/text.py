import re


def humanize_name(name):
    """
    Convert game identifiers into readable text.

    Examples:
        steel_bar -> Steel Bar
        linearActuator -> Linear Actuator
        batteryPack -> Battery Pack
    """

    name = name.replace("_", " ")

    name = re.sub(
        r"(?<!^)(?=[A-Z])",
        " ",
        name,
    )

    return name.title()