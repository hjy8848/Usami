"""Simple task controller. Domain-native request is supplied by the Adapter."""


def step(public_view, memory):
    if "model_observation" in public_view:
        return {"kind": "ACTION", "state": {}, "action": public_view["model_observation"]}
    return {"kind": "MODEL", "state": {}, "request": public_view["baseline_request"]}
