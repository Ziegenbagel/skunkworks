## World State

Skunkworks will build its own internal representation of the game.

This world state combines information from multiple API endpoints rather than relying on a single endpoint.

Example:

Player

↓

Probes

↓

Sector

↓

Resources

↓

Planner

↓

Automation

Automation should operate from this combined world model instead of directly consuming individual API responses.