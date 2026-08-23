from tools.release_readiness import audit


def test_release_readiness_has_expected_non_packaging_gates():
    checks = {check["name"]: check for check in audit()}

    assert checks["metadata:description"]["ok"]
    assert checks["metadata:version"]["ok"]
    assert checks["privacy:local-files"]["ok"]
    assert checks["privacy:policy-template"]["ok"]
    assert not checks["privacy:manual-screenshots"]["ok"]
    assert checks["legal:license"]["ok"]
    assert all(
        check["ok"] for name, check in checks.items()
        if name.startswith("file:")
    )
