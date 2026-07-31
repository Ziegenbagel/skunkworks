"""Best-effort reads for dynamic server-owned hazard rules."""

import requests


class HazardContextLoader:
    def __init__(self, capabilities):
        self.capabilities = capabilities

    def load(self, world, probe_id, reachable=True):
        context = {
            "damageWarnings": None,
            "improvements": None,
            "scutNetworks": [],
            "failures": {},
        }

        if not reachable:
            return context

        self._attempt(
            context,
            "damage_warnings",
            lambda: self.capabilities.probes.damage_warnings(
                probe_id
            ),
            "damageWarnings",
        )
        self._attempt(
            context,
            "improvements",
            lambda: self.capabilities.probes.improvements(
                probe_id
            ),
            "improvements",
        )

        snapshot = world.sector.get("snapshot") or {}
        for network in snapshot.get(
            "sector",
            {},
        ).get("scutNetworks", []):
            try:
                response = self.capabilities.probes.scut_network(
                    probe_id,
                    network["id"],
                )
                context["scutNetworks"].append(response)
            except (
                KeyError,
                OSError,
                RuntimeError,
                requests.RequestException,
            ) as error:
                context["failures"][
                    f"scut_network_{network.get('id', 'unknown')}"
                ] = str(error)

        return context

    def _attempt(
        self,
        context,
        failure_name,
        load,
        result_name,
    ):
        try:
            context[result_name] = load()
        except (
            OSError,
            RuntimeError,
            requests.RequestException,
        ) as error:
            context["failures"][failure_name] = str(error)
