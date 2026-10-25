"""ALFWorld P0: ask fixed model B to choose from the current observation."""
import json


def step(view, state):
    system = (
        "You control an ALFWorld TextWorld environment. Read the task goal and current observation, "
        "then choose one next command. Use the ALFWorld admissible command list and send the exact "
        "command string through choose_alfworld_action. Do not claim success; the environment decides. "
        "Use the prior public trajectory and service experience when useful."
    )
    request = {
        "observation": view["observation"],
        "admissible_actions": view["admissible_actions"],
        "history": view["history"],
        "service_experience": view["service_experience"],
    }
    return {"kind": "MODEL", "state": state,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": json.dumps(request, ensure_ascii=False)}]}
