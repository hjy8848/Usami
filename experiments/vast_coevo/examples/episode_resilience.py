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
            # Native evidence groups calls by role, not global chronology.
            last = next((call for call in reversed(value.model_calls) if call.role == 'customer'), None)
            if (value.track == 'discovery' and value.termination == 'CUSTOMER_OUTPUT_INVALID'
                    and value.replay.verified and last is not None
                    and last.response is not None and not last.error
                    and all(call.response is not None and not call.error for call in value.model_calls)):
                continue
            CoEvolutionController._check_main_evidence((value,))
