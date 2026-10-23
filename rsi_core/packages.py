"""Trusted, finite certified package banks with resumable no-replacement draws.

Provenance labels must come from an independently audited data registry. This
module checks their consistency; changing a seed never creates a new family.
"""
from dataclasses import asdict, dataclass
import random

from .protocol import AdaptationPackage, digest, validate_partitions


class PackagePoolExhausted(RuntimeError):
    """Trusted sampling protocol lacks enough unused registered packages."""


@dataclass(frozen=True)
class TaskProof:
    task_ref: str
    origin_ref: str
    certificate_ref: str

    def __post_init__(self):
        if not all((self.task_ref, self.origin_ref, self.certificate_ref)):
            raise ValueError("task identity, original source and independent certificate are required")


@dataclass(frozen=True)
class PackageRegistration:
    package: AdaptationPackage
    support_origins: tuple
    task_proofs: tuple

    def __post_init__(self):
        p = self.package
        if len(self.support_origins) != len(p.support) or not all(self.support_origins):
            raise ValueError("every support item requires a registered original source")
        refs = [row.task_ref for row in self.task_proofs]
        if len(refs) != len(set(refs)) or set(refs) != set(p.probe_refs + p.query_refs):
            raise ValueError("independent task proofs must cover exactly all probes and queries")
        if p.partition != "meta-train" and p.purpose != "audit":
            raise ValueError("validation/test banks cannot provide training reward or selection packages")


@dataclass(frozen=True)
class PackageDraw:
    packages: tuple
    archive_ref: str
    state_ref: str


@dataclass(frozen=True)
class TrainingPackages:
    probe: tuple
    selection: tuple
    reward: tuple
    archive_ref: str
    state_ref: str


def _registration(value):
    data = value["package"]
    package = AdaptationPackage(**{**data, "support": tuple(data["support"]),
                                  "probe_refs": tuple(data["probe_refs"]),
                                  "query_refs": tuple(data["query_refs"])})
    return PackageRegistration(package, tuple(value["support_origins"]),
                               tuple(TaskProof(**row) for row in value["task_proofs"]))


class PackageProvider:
    """Host-only registry; never expose it as a candidate-callable tool.

    ``verify_task(domain, TaskProof)`` must validate a native certificate and its
    binding to the actual task, returning exactly True or raising an error.
    No evaluator answers/certificates enter the package's public projection.
    """

    def __init__(self, registrations, archive, verify_task, *, state_ref=None):
        registrations = tuple(registrations)
        if not registrations:
            raise ValueError("a package registry cannot be empty")
        groups, identities, origins, references, query_owners = {}, set(), {}, {}, {}
        verified = set()
        for row in registrations:
            p = row.package
            if p.package_id in identities:
                raise ValueError("duplicate registered package identity")
            identities.add(p.package_id)
            label = (p.partition, p.purpose)
            groups.setdefault(label, []).append(p)
            roles = [(origin, "support") for origin in row.support_origins]
            for proof in row.task_proofs:
                role = "probe" if proof.task_ref in p.probe_refs else "query"
                roles.append((proof.origin_ref, role))
                reference = (p.domain_id, proof.task_ref)
                binding = (proof.origin_ref, proof.certificate_ref)
                if reference in references and references[reference] != binding:
                    raise ValueError("same task reference has different source or certificate")
                references[reference] = binding
                check = (p.domain_id, proof)
                if check not in verified:
                    if verify_task(p.domain_id, proof) is not True:
                        raise ValueError("native task certificate was not independently verified")
                    verified.add(check)
            for origin, role in roles:
                key, binding = (p.domain_id, origin), (label, role)
                if key in origins and origins[key] != binding:
                    raise ValueError("original source crosses a partition, purpose or support/probe/query role")
                origins[key] = binding
                if role == "query":
                    if key in query_owners:
                        raise ValueError("private query source is repeated under another package identity")
                    query_owners[key] = p.package_id
            if len(set(origin for origin, _ in roles)) != len(roles):
                raise ValueError("a package repeats an original source under different references")
        validate_partitions(groups)
        self.archive = archive
        self.manifest_ref = archive.save({"kind": "certified_package_bank_v1",
                                          "registrations": [asdict(row) for row in registrations]})
        self.draw_refs = []
        if state_ref is not None:
            saved = archive.load(state_ref)
            if saved["kind"] != "package_sampling_state_v1" or saved["manifest_ref"] != self.manifest_ref:
                raise ValueError("sampling state belongs to a different package bank")
            # Recompute every draw against the same prior history, rather than
            # trusting a saved set of IDs that could silently reset sampling.
            for ref in saved["draw_refs"]:
                if ref in self.draw_refs:
                    raise ValueError("sampling state repeats a draw")
                self.verify_draw(ref)
                self.draw_refs.append(ref)

    def _bank(self):
        return tuple(_registration(row).package for row in
                     self.archive.load(self.manifest_ref)["registrations"])

    def _used(self, prior_refs):
        return {identity for ref in prior_refs
                for identity in self.archive.load(ref)["package_ids"]}

    def _choose(self, partition, purpose, seed, count, *, prior_refs=None):
        if type(seed) is not int or type(count) is not int or count < 1:
            raise ValueError("sampling requires an integer seed and positive count")
        used = self._used(self.draw_refs if prior_refs is None else prior_refs)
        eligible = sorted((p for p in self._bank() if p.partition == partition
                           and p.purpose == purpose and p.package_id not in used),
                          key=lambda p: p.package_id)
        if len(eligible) < count:
            raise PackagePoolExhausted("insufficient unused registered packages for " + partition + "/" + purpose)
        rng = random.Random(digest({"bank": self.manifest_ref, "partition": partition,
                                    "purpose": purpose, "seed": seed}))
        return tuple(rng.sample(eligible, count))

    def state(self):
        return self.archive.save({"kind": "package_sampling_state_v1", "manifest_ref": self.manifest_ref,
                                  "draw_refs": list(self.draw_refs)})

    def sample(self, partition, purpose, seed, *, count=1):
        packages = self._choose(partition, purpose, seed, count)
        ref = self.archive.save({"kind": "package_draw_v1", "manifest_ref": self.manifest_ref,
                                 "previous_draw_refs": list(self.draw_refs), "partition": partition,
                                 "purpose": purpose, "seed": seed, "count": count,
                                 "package_ids": [p.package_id for p in packages]})
        self.draw_refs.append(ref)
        return PackageDraw(packages, ref, self.state())

    def verify_draw(self, ref):
        saved = self.archive.load(ref)
        prior = self.draw_refs[:self.draw_refs.index(ref)] if ref in self.draw_refs else self.draw_refs
        if (saved["kind"] != "package_draw_v1" or saved["manifest_ref"] != self.manifest_ref
                or saved["previous_draw_refs"] != prior):
            raise ValueError("draw belongs to another bank or sampling history")
        packages = self._choose(saved["partition"], saved["purpose"], saved["seed"], saved["count"], prior_refs=prior)
        if [p.package_id for p in packages] != saved["package_ids"]:
            raise ValueError("draw differs from preregistered deterministic sampling")
        return {"verified": True, "package_ids": saved["package_ids"]}

    def sample_training_context(self, seed, *, counts):
        if set(counts) != {"C_probe", "C_select", "C_reward"}:
            raise ValueError("training contexts require all three independently sourced purposes")
        # Preflight all pools before consuming any of them. These pools are
        # independent, so no successful preflight can reduce another's supply.
        for purpose, count in counts.items():
            self._choose("meta-train", purpose, seed, count)
        draws = {purpose: self.sample("meta-train", purpose, seed, count=counts[purpose])
                 for purpose in ("C_probe", "C_select", "C_reward")}
        ref = self.archive.save({"kind": "sampled_training_packages_v1", "manifest_ref": self.manifest_ref,
                                 "seed": seed, "counts": counts,
                                 "draw_refs": {key: draw.archive_ref for key, draw in draws.items()}})
        return TrainingPackages(draws["C_probe"].packages, draws["C_select"].packages,
                                draws["C_reward"].packages, ref, self.state())

    def public_view(self, package_id):
        matches = [p for p in self._bank() if p.package_id == package_id]
        if len(matches) != 1:
            raise ValueError("unknown registered package")
        return matches[0].public_view()
