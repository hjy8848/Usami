"""Explicit experiment policy: isolate recorded Customer output failures.

Business packages and historical source pins remain unchanged. This controller
only changes orchestration, never evidence, output parsing, or Service gates.
"""
from vast_coevo.evolution.controller import CoEvolutionController

POLICY = 'isolate-recorded-customer-output-v1'


class ResilientController(CoEvolutionController):
    @staticmethod
    def _check_main_evidence(evidence):
        for value in evidence:
            # Only a fully recorded, replayable Customer reply may fail locally.
            # Unknown transport outcomes, unverified evidence, Service errors and
            # other protocol violations retain the original fail-closed behavior.
            last = value.model_calls[-1] if value.model_calls else None
            if (value.track == 'discovery' and value.termination == 'CUSTOMER_OUTPUT_INVALID'
                    and value.replay.verified and last is not None
                    and last.role == 'customer' and last.response is not None and not last.error):
                continue
            CoEvolutionController._check_main_evidence((value,))
