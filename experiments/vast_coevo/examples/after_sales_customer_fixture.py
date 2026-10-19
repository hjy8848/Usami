"""Controlled Service for isolating the Customer simulator, not a scored Agent.

It reads exact current grants and its actual tool results only. No World,
Reference witness, Oracle or task certificate is available to this fixture.
"""
import json

from usami.service.models import ModelSettings


class ControlledRefundService:
    def __init__(self):
        self.settings = ModelSettings(model='local/controlled-refund-service-v1',
            base_url='http://127.0.0.1/usami-local', options={})
        self.phase = 'open_case'
        self.pending = None
        self.quote = None
        self.return_operation = None
        self.sequence = 0

    def _completion(self, name, arguments):
        self.sequence += 1
        return {'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
            'tool_calls': [{'id': 'fixture_' + str(self.sequence), 'type': 'function',
                            'function': {'name': name, 'arguments': json.dumps(arguments)}}]}}]}

    def _reply(self, message, offer=None):
        return self._completion('respond_to_customer_v3', {'message': message, 'offer_ref': offer})

    def complete(self, request):
        if self.pending is not None:
            call_id, operation = self.pending
            result = next((json.loads(message['content']) for message in reversed(request['messages'])
                           if message.get('role') == 'tool' and message.get('tool_call_id') == call_id), None)
            if result is None:
                raise ValueError('fixture has no actual response for its pending operation')
            self.pending = None
            if not result.get('success'):
                self.phase = 'blocked'
                return self._reply('The business system did not allow this step: ' + str(result.get('error_code')) +
                                   '. I will not claim it was completed. Would you like to stop or clarify?')
            data = result.get('data', {})
            if operation == 'schedule_return':
                op = self.return_operation
                reply = self._completion('get_case', {'scope_id': op['scope_id'], 'resource_id': op['resource_id'],
                                                     'params': {'case_id': op['params']['case_id']}})
                self.pending = ('fixture_' + str(self.sequence), 'get_case')
                return reply
            if operation == 'get_case':
                self.phase = 'release_refund' if any(r['status'] == 'received' for r in data.get('returns', [])) else 'blocked'
                return self._question()
            self.phase = {
                'open_case': 'verify_evidence', 'verify_evidence': 'request_manager_review',
                'request_manager_review': 'quote_resolution', 'quote_resolution': 'commit_resolution',
                'schedule_return': 'release_refund', 'release_refund': 'done',
            }.get(operation, 'done')
            if operation == 'quote_resolution':
                self.quote = data['quote']
            elif operation == 'commit_resolution':
                self.phase = 'schedule_return' if data.get('line_status') == 'return_pending' else 'done'
            # A new Customer decision is required for every preparation step and
            # every offer. Never use an unused grant from a previous turn.
            return self._question()

        marker = '\nExact Customer-declared single-use writes for this turn: '
        latest = next((message['content'] for message in reversed(request['messages'])
                       if message.get('role') == 'user' and marker in message.get('content', '')), '')
        grants = json.loads(latest.split(marker, 1)[1]) if marker in latest else []
        selected = next((operation for operation in grants if operation['name'] == self.phase and
                         (self.phase != 'quote_resolution' or operation['params'].get('option') == 'refund')), None)
        if selected is None:
            return self._question()
        reply = self._completion(selected['name'], {k: selected[k] for k in ('scope_id', 'resource_id', 'params')})
        if selected['name'] == 'schedule_return':
            self.return_operation = selected
        self.pending = ('fixture_' + str(self.sequence), selected['name'])
        return reply

    def _question(self):
        if self.phase in {'commit_resolution', 'release_refund'}:
            return self._reply('Please review the actual presented refund amount and payment channel. '
                + ('Do you agree to this settlement?' if self.phase == 'commit_resolution'
                   else 'The return step is complete. Do you separately authorize releasing this refund?'),
                {'kind': self.phase, 'quote_id': self.quote['id']})
        questions = {
            'open_case': 'Which order and item were damaged? May I open a support case for that item?',
            'verify_evidence': 'Please provide the evidence you have. May I verify it for this case?',
            'request_manager_review': 'May I submit the evidence-backed case for manager review?',
            'quote_resolution': 'Would you like me to prepare a refund offer for this case?',
            'schedule_return': 'This agreed remedy requires a return. Which pickup slot works, and may I arrange collection?',
            'done': 'The business system reports the remedy completed. Please check your visible order status.',
            'blocked': 'The requested step could not be completed. Would you like to stop or clarify?',
        }
        return self._reply(questions[self.phase])
