"""Public scan visibility remains authoritative for SCUT network discovery."""
from types import SimpleNamespace

import pytest

from src.application.hazard_context import HazardContextLoader


@pytest.mark.parametrize("status,networks", [("covered", [{"id": 14}]), ("unknown", None)])
def test_degraded_scan_loads_only_disclosed_networks(status, networks):
    sector = {"sensorMode": "degraded", "scutCoverageStatus": status}
    if networks is not None:
        sector["scutNetworks"] = networks
    calls = []
    response = {"network": {"id": 14, "relays": []}}
    capabilities = SimpleNamespace(probes=SimpleNamespace(
        damage_warnings=lambda _: {}, improvements=lambda _: {},
        scut_network=lambda probe, network: calls.append((probe, network)) or response,
    ))
    world = SimpleNamespace(sector={"snapshot": {"sector": sector}})
    context = HazardContextLoader(capabilities).load(world, 7)
    assert calls == ([(7, 14)] if networks else [])
    assert context["scutNetworks"] == ([response] if networks else [])
    assert not context["failures"]
