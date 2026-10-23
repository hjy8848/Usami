"""Shared nested ledger. Reservations protect complete reward/selection groups."""
from contextlib import contextmanager, ExitStack
from dataclasses import asdict
import math
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
        self.active = []

    def charge(self, scope, **usage):
        if set(usage) - set(RESOURCES):
            raise ValueError("unknown budget resource")
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in usage.values()):
            raise ValueError("invalid measured usage")
        proposed = {key: self.used[key] + usage.get(key, 0) for key in RESOURCES}
        # Record real expenditure even if a provider reports more than reserved.
        self.used = proposed
        self.events.append({"scope": scope, "usage": usage})
        for reservation in self.active:
            for key, value in usage.items():
                reservation.remaining[key] -= value
        self.check()

    def check(self):
        for reservation in self.active:
            if any(value < 0 for value in reservation.remaining.values()):
                raise BudgetExceeded("reserved evaluation allocation exceeded")
        for resource in RESOURCES:
            if self.used[resource] + self.reserved[resource] > getattr(self.limits, resource):
                raise BudgetExceeded(resource + " budget exceeded")
        if time.monotonic() - self.started > self.limits.wall_seconds:
            raise BudgetExceeded("root wall-clock budget exceeded")

    def remaining(self, resource):
        self.check()
        available = getattr(self.limits, resource) - self.used[resource] - self.reserved[resource]
        return min([available] + [r.remaining[resource] for r in self.active])

    @contextmanager
    def reserve(self, **maximum):
        if self.active:
            raise ValueError("reserve group allocations before starting expenditure")
        if set(maximum) - set(RESOURCES) or any(type(v) is not int or v < 0 for v in maximum.values()):
            raise ValueError("invalid group reservation")
        for key, value in maximum.items():
            if value > self.remaining(key):
                raise BudgetExceeded("cannot reserve complete evaluation group: " + key)
        for key, value in maximum.items():
            self.reserved[key] += value
        reservation = Reservation(self, maximum)
        try:
            yield reservation
        finally:
            for key, value in reservation.remaining.items():
                self.reserved[key] -= max(0, value)
            reservation.closed = True

    @contextmanager
    def reserve_group(self, allocations):
        """Reserve all root, selection and reward phases before any sampling.

        Allocations are spent sequentially; nested evaluations charge the same
        active allocation through this ledger, without opening new budgets.
        """
        if not allocations:
            raise ValueError("evaluation group requires budget allocations")
        with ExitStack() as stack:
            reservations = {name: stack.enter_context(self.reserve(**maximum))
                            for name, maximum in allocations.items()}
            yield reservations

    def snapshot(self):
        return {"limits": asdict(self.limits), "used": dict(self.used),
                "reserved": dict(self.reserved), "wall_seconds": time.monotonic() - self.started,
                "cpu_accounting": "Host wall-time upper bound for one-vCPU workers; not measured utilization",
                "events": list(self.events)}


class Reservation:
    def __init__(self, ledger, maximum):
        self.ledger, self.maximum = ledger, maximum
        # Omitted resources have zero allocation, rather than unlimited access
        # to the root's unreserved balance.
        self.remaining = {key: maximum.get(key, 0) for key in RESOURCES}
        self.closed = False
        self.spending = False

    @contextmanager
    def spend(self):
        if self.closed or self.spending or self.ledger.active:
            raise ValueError("reservation is closed or another allocation is spending")
        if any(value < 0 for value in self.remaining.values()):
            raise BudgetExceeded("reserved evaluation allocation already exceeded")
        self.ledger.check()
        for key, value in self.remaining.items():
            self.ledger.reserved[key] -= value
        self.spending = True
        self.ledger.active.append(self)
        try:
            yield self.ledger
        finally:
            self.ledger.active.pop()
            self.spending = False
            for key, value in self.remaining.items():
                self.ledger.reserved[key] += max(0, value)
