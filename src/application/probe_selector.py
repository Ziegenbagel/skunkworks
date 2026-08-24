"""Resolve the probe that owns the current application context."""

import sys


class ProbeSelectionError(ValueError):
    """Raised when a requested probe cannot be selected."""


class ProbeSelector:
    """Select a probe by ID, name, default, or interactive prompt."""

    def __init__(
        self,
        input_fn=input,
        output_fn=print,
        interactive=None,
    ):
        self.input_fn = input_fn
        self.output_fn = output_fn
        self.interactive = interactive

    def select(
        self,
        probe_data,
        arguments=None,
        preferred_probe_id=None,
    ):
        probes = probe_data["probes"]
        arguments = list(
            sys.argv[1:]
            if arguments is None
            else arguments
        )

        if not probes:
            raise ProbeSelectionError(
                "The account does not own any probes."
            )

        if arguments == ["--default-probe"]:
            return self._by_id(
                probes,
                probe_data["defaultProbeId"],
            )

        if len(arguments) == 2:
            option, value = arguments

            if option == "--probe-id":
                try:
                    return self._by_id(
                        probes,
                        int(value),
                    )
                except ValueError as error:
                    raise ProbeSelectionError(
                        "Probe ID must be an integer."
                    ) from error

            if option == "--probe-name":
                return self._by_name(probes, value)

        if arguments == ["--select-probe"]:
            return self._prompt(probes)

        if arguments:
            raise ProbeSelectionError(self.usage())

        if preferred_probe_id is not None:
            try:
                return self._by_id(
                    probes,
                    preferred_probe_id,
                )
            except ProbeSelectionError:
                pass

        if self._interactive_enabled() and len(probes) > 1:
            return self._prompt(probes)

        return self._by_id(
            probes,
            probe_data["defaultProbeId"],
        )

    def _prompt(self, probes):
        self.output_fn("")
        self.output_fn("Select Probe")
        self.output_fn("-" * 40)

        for index, probe in enumerate(probes, start=1):
            markers = []

            if probe.get("isDefault"):
                markers.append("default")

            if not probe.get("isReachable", True):
                markers.append("out of range")

            suffix = (
                f" ({', '.join(markers)})"
                if markers
                else ""
            )
            self.output_fn(
                f"{index}. {probe['name']} "
                f"[{probe['status']}]{suffix}"
            )

        while True:
            response = self.input_fn(
                f"Choose 1-{len(probes)}: "
            ).strip()

            try:
                position = int(response)
            except ValueError:
                position = 0

            if 1 <= position <= len(probes):
                return probes[position - 1]

            self.output_fn("Invalid probe selection.")

    def _by_id(self, probes, probe_id):
        for probe in probes:
            if probe["id"] == probe_id:
                return probe

        raise ProbeSelectionError(
            f"Probe ID {probe_id} was not found."
        )

    def _by_name(self, probes, probe_name):
        matches = [
            probe
            for probe in probes
            if probe["name"].casefold()
            == probe_name.casefold()
        ]

        if len(matches) == 1:
            return matches[0]

        if not matches:
            raise ProbeSelectionError(
                f"Probe {probe_name!r} was not found."
            )

        raise ProbeSelectionError(
            f"Probe name {probe_name!r} is ambiguous."
        )

    def _interactive_enabled(self):
        if self.interactive is not None:
            return self.interactive

        # Windowed PyInstaller applications intentionally have no attached
        # console, so Python exposes stdin as None. Probe selection is handled
        # by the GUI in that environment; an implicit terminal prompt must not
        # make the initial fleet refresh fail.
        stream = getattr(sys, "stdin", None)
        if stream is None:
            return False
        try:
            return bool(stream.isatty())
        except (AttributeError, OSError, ValueError):
            return False

    def usage(self):
        return (
            "Usage: python main.py "
            "[--select-probe | --default-probe | "
            "--probe-id ID | --probe-name NAME]"
        )
