"""Capability-oriented gateways for the public game API."""

from .account import AccountGateway
from .community import CommunityGateway
from .galaxy import GalaxyGateway
from .mannies import MannyGateway
from .messaging import MessagingGateway
from .missions import MissionGateway
from .probes import ProbeGateway
from .storage import StorageGateway

__all__ = [
    "AccountGateway",
    "CommunityGateway",
    "GalaxyGateway",
    "MannyGateway",
    "MessagingGateway",
    "MissionGateway",
    "ProbeGateway",
    "StorageGateway",
]
