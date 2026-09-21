from types import SimpleNamespace

from src.operations.containers import ContainerService


def test_attached_includes_full_container_reported_only_by_resource_placement():
    world = SimpleNamespace(probe={"inventory": {
        "containers": [],
        "resourceStocks": [{
            "type": "metals",
            "containers": [{
                "container": {
                    "id": "recovered-box", "kind": "container", "capacity": 1,
                },
                "amount": 1,
            }],
        }],
    }})

    assert ContainerService(world).attached() == ({
        "id": "recovered-box", "kind": "container", "capacity": 1,
        "usedCapacity": 1.0,
    },)


def test_resource_placements_merge_into_top_level_attached_container():
    world = SimpleNamespace(probe={"inventory": {
        "containers": [{
            "id": "mixed-box", "kind": "container", "capacity": 1,
            "usedCapacity": 0,
        }],
        "resourceStocks": [
            {"type": "metals", "containers": [{
                "container": {"id": "mixed-box", "kind": "container"},
                "amount": 0.6,
            }]},
            {"type": "ice", "containers": [{
                "container": {"id": "mixed-box", "kind": "container"},
                "amount": 0.4,
            }]},
        ],
    }})

    assert ContainerService(world).attached()[0]["usedCapacity"] == 1.0
