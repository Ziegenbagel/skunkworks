from tools.collect_release_licenses import collect


class FakeDistribution:
    metadata = {
        "Name": "Example Runtime",
        "License-Expression": "MIT",
    }
    version = "1.2.3"
    requires = []
    files = []


def test_license_inventory_is_generated_from_selected_distributions(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tools.collect_release_licenses.runtime_distributions",
        lambda: [FakeDistribution()],
    )

    inventory = collect(tmp_path)

    text = inventory.read_text()
    assert "Example Runtime" in text
    assert "1.2.3" in text
    assert "MIT" in text
