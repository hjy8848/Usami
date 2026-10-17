"""Counterfactuals must change the native allowed-action set and bind real traces."""
import pytest
from usami_dialogue.dependencies import certify_dependencies,verify_dependency
from test_vnext_aftersales import prepared,quoted,commit,operation,customer


def test_refund_proves_missing_information_preference_and_consent_without_turn_reward():
    s,order,line=prepared();cid,q=quoted(s,order,line);commit(s,order,q)
    trace=s.finish();proofs=certify_dependencies(s.adapter,trace)
    kinds={p.proof.kind for p in proofs}
    assert {'missing_information','preference_resolution','explicit_consent'}<=kinds
    assert all(p.proof.control_allowed!=p.proof.changed_allowed for p in proofs)
    assert all(verify_dependency(s.adapter,trace,p) for p in proofs)
    consent=next(p for p in proofs if p.proof.kind=='explicit_consent')
    assert consent.proof.expected_changed_code=='EXPLICIT_CONSENT_REQUIRED'
    # Re-sealing hashes does not authorize an evaluator to change business facts.
    tampered=consent.model_copy(deep=True)
    tampered.changed_world['orders'][order.id]['paid_cents']+=1
    tampered.certificate_hash=tampered.computed_hash()
    with pytest.raises(ValueError,match='exceed'):verify_dependency(s.adapter,trace,tampered)


def test_redundant_fact_is_not_evidence_of_dialogue_necessity():
    s,order,line=prepared();cid,q=quoted(s,order,line);commit(s,order,q)
    proofs=certify_dependencies(s.adapter,s.finish())
    # Deadline disclosure cannot be claimed necessary for a cash refund.
    assert not any(p.proof.kind=='missing_information' and p.intervention=={'fact':'deadline'} for p in proofs)


def test_external_manager_event_changes_actual_reference_choices():
    from usami_aftersales import adapter
    from usami_aftersales.rules import eligibility
    from usami_dialogue.engine import DialogueSession
    selected=None
    for seed in range(10):
        world=adapter.generate_world(seed)
        for pid,p in world.profiles.items():
            line=world.lines[p.facts['line_id']];order=world.orders[line.order_id]
            event=world.external_events['manager_review_'+line.id]
            if not eligibility(world,order,line) and world.evidence[p.facts['evidence_id']].simulated_valid and event.outcome=='approved' and line.quantity*line.unit_price_cents>world.merchants[order.merchant_id].refund_approval_limit_cents:
                selected=(world,pid,order,line);break
        if selected:break
    assert selected is not None
    world,pid,order,line=selected;s=DialogueSession(adapter,world,pid)
    opening=operation(s,'open_case',order,line_id=line.id,issue=s.private.facts['issue'])
    customer(s,opening,preferences={'resolution':'refund'})
    cid=s.act(opening)['data']['case_id']
    verify=operation(s,'verify_evidence',order,case_id=cid,evidence_id=s.private.facts['evidence_id'])
    review=operation(s,'request_manager_review',order,case_id=cid)
    customer(s,verify,review);assert s.act(verify)['success'];assert s.act(review)['success']
    s.external('manager_review_'+line.id)
    trace=s.finish();proofs=certify_dependencies(adapter,trace)
    state=next(p for p in proofs if p.proof.kind=='state_update' and p.proof.operation['name']=='quote_resolution')
    assert not state.proof.control_allowed and state.proof.changed_allowed
    assert state.proof.expected_control_code=='APPROVAL_REQUIRED'
    assert verify_dependency(adapter,trace,state)
