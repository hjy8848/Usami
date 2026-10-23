"""Shared nested ledger. Reservations protect complete reward/selection groups."""
from contextlib import contextmanager
from dataclasses import asdict
import time

from .protocol import BudgetExceeded, Limits


RESOURCES = ("model_calls", "model_tokens", "episodes", "tool_steps", "research_steps", "cpu_seconds")


class Ledger:
    def __init__(self, limits: Limits):
        self.limits = limits
        self.used = dict.fromkeys(RESOURCES, 0)
        self.reserved = dict.fromkeys(RESOURCES, 0)
        self.started = time.monotonic()
        self.events = []

    def charge(self, scope, **usage):
        if set(usage) - set(RESOURCES):
            raise ValueError("unknown budget resource")
        if any(type(v) not in (int, float) or v < 0 for v in usage.values()):
            raise ValueError("invalid measured usage")
        proposed = {key: self.used[key] + usage.get(key, 0) for key in RESOURCES}
        # Record real expenditure even if a provider reports more than reserved.
        self.used = proposed
        self.events.append({"scope": scope, "usage": usage})
        self.check()

    def check(self):
        for resource in RESOURCES:
            if self.used[resource] + self.reserved[resource] > getattr(self.limits, resource):
                raise BudgetExceeded(resource + " budget exceeded")
        if time.monotonic() - self.started > self.limits.wall_seconds:
            raise BudgetExceeded("root wall-clock budget exceeded")

    def remaining(self, resource):
        self.check()
        return getattr(self.limits, resource) - self.used[resource] - self.reserved[resource]

    @contextmanager
    def reserve(self, **maximum):
        if set(maximum) - set(RESOURCES) or any(type(v) is not int or v < 0 for v in maximum.values()):
            raise ValueError("invalid group reservation")
        for key, value in maximum.items():
            if value > self.remaining(key):
                raise BudgetExceeded("cannot reserve complete evaluation group: " + key)
        for key, value in maximum.items():
            self.reserved[key] += value
        try:
            yield Reservation(self, maximum)
        finally:
            for key, value in maximum.items():
                self.reserved[key] -= value

    def snapshot(self):
        return {"limits": asdict(self.limits), "used": dict(self.used),
                "reserved": dict(self.reserved), "wall_seconds": time.monotonic() - self.started,
                "cpu_accounting": "Host wall-time upper bound for one-vCPU workers; not measured utilization",
                "events": list(self.events)}


class Reservation:
    def __init__(self, ledger, maximum):
        self.ledger, self.maximum = ledger, maximum

    @contextmanager
    def spend(self):
        for key, value in self.maximum.items():
            self.ledger.reserved[key] -= value
        try:
            yield self.ledger
        finally:
            for key, value in self.maximum.items():
                self.ledger.reserved[key] += value
