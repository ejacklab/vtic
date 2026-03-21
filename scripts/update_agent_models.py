#!/usr/bin/env python3
"""Update agent models in openclaw.json"""

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"

# Model assignments
UPDATES = {
    "cclow": "zai/glm-5",
    "calen": "minimax-portal/MiniMax-M2.5",
    "finan": "moonshot/kimi-k2.5",
    "dave": "modelstudio/glm-5",
    "email": "modelstudio/MiniMax-M2.5",
    "conte": "modelstudio/kimi-k2.5",
}

# Read config
with open(CONFIG_PATH) as f:
    config = json.load(f)

# Update agents
for agent in config["agents"]["list"]:
    agent_id = agent["id"]
    if agent_id in UPDATES:
        old_model = agent.get("model", "none")
        new_model = UPDATES[agent_id]
        agent["model"] = new_model
        print(f"✅ {agent_id}: {old_model} → {new_model}")

# Write config
with open(CONFIG_PATH, "w") as f:
    json.dump(config, f, indent=2)

print("\nDone! Config updated.")
