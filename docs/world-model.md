# World Model

Player
│
├── Fleet
│     ├── Probe
│     ├── Inventory
│     └── Status
│
├── Snapshot
│
├── Sector
│     ├── Persistent Resources
│     └── Dynamic Resources
│
└── Planner

## Intelligence Layer

The Intelligence Layer converts raw API responses into normalized information used by the dashboard and planner.

Current analyzers:

- SnapshotAnalyzer
- ResourceAnalyzer
- InventoryAnalyzer

Future analyzers:

- FleetAnalyzer
- PlannerAnalyzer
- ForecastAnalyzer