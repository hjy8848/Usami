"""Permission-filtered initial observation, without policy decisions or Oracle data."""
from usami.protocol import Operation
from usami.service.tools import customer_context
from usami.world.rules import ReferenceRules


def initial_observation(world, identity):
    if identity not in world.users:
        raise ValueError("customer identity is not present in the world")
    context = customer_context(world, identity)
    view = {"customer_context": context, "business_time": world.clock.isoformat(), "organizations": [], "subscriptions": [],
            "memberships": [], "invoices": [], "users": [],
            "plan_catalog": [{"id": p.id, "name": p.name} for p in world.rules.plans.values()]}
    users = {}
    rules = ReferenceRules()

    def read(name, org, target):
        decision = rules.decide(world, identity, Operation(name=name, org_id=org, resource_id=target))
        return decision.expected_data if decision.allowed else None

    for org_id in sorted({m.org_id for m in world.memberships.values() if m.user_id == identity}):
        org = world.organizations[org_id]
        for name, target, collection in (("get_organization", org.id, "organizations"),
                ("get_subscription", org.subscription_id, "subscriptions")):
            data = read(name, org_id, target)
            if data is not None:
                view[collection].append(data)
        members = read("list_members", org_id, org.id)
        if members is not None:
            view["memberships"].extend(members["memberships"])
            for member in members["memberships"]:
                user = world.users[member["user_id"]]
                users[user.id] = user.model_dump(mode="json")
        for invoice in world.invoices.values():
            if invoice.org_id == org_id:
                data = read("get_invoice", org_id, invoice.id)
                if data is not None:
                    view["invoices"].append(data)
    view["users"] = list(users.values())
    return view


def observed_ids(view):
    ids = set()
    context = view["customer_context"]
    for collection in ("organizations", "memberships"):
        ids.update(entity["id"] for entity in context[collection])
    for collection in ("organizations", "subscriptions", "memberships", "invoices"):
        ids.update(entity["id"] for entity in view[collection])
    return ids
