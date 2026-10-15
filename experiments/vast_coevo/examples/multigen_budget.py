"""At-most-once, secret-free real-call ledger with shared hard spending caps."""
import json
import threading
import time
from pathlib import Path
from vast_coevo.schema import atomic_json, digest
from vast_coevo.storage.runs import BudgetExhausted, InterruptedRun
from integrations.usami.cli import transport


class CallLedger:
    def __init__(self, root, limits):
        self.root, self.limits, self.lock = Path(root), limits, threading.RLock()
        path = self.root / 'usage.json'
        self.state = json.loads(path.read_text()) if path.exists() else {'buckets': {}, 'pending': {}}

    def save(self): atomic_json(self.root / 'usage.json', self.state)

    def client(self, spec, role, tag, bucket):
        return BudgetClient(self, transport(spec), role, tag, bucket)

    def start(self, key, bucket, role, request):
        # Conservative byte bound plus output cap and chat framing allowance.
        reserve = len(json.dumps(request, ensure_ascii=False).encode()) + int(request.get('max_tokens', 4096)) + 8192
        with self.lock:
            if (self.root / 'calls' / (key + '.started.json')).exists():
                raise InterruptedRun('call ID already started; no automatic retry: ' + key)
            pending = self.state['pending']
            counts = self.state['buckets']
            current = counts.get(bucket, {'calls': 0, 'tokens': 0})
            total_calls = sum(v['calls'] for v in counts.values())
            total_tokens = sum(v['tokens'] for v in counts.values())
            local_calls = current['calls'] + sum(v['bucket'] == bucket for v in pending.values())
            local_tokens = current['tokens'] + sum(v['reserve'] for v in pending.values() if v['bucket'] == bucket)
            limit = self.limits['buckets'][bucket]
            if (local_calls + 1 > limit['calls'] or local_tokens + reserve > limit['tokens'] or
                    total_calls + len(pending) + 1 > self.limits['calls'] or
                    total_tokens + sum(v['reserve'] for v in pending.values()) + reserve > self.limits['tokens']):
                raise BudgetExhausted('preregistered call/token cap before external request: ' + bucket)
            atomic_json(self.root / 'calls' / (key + '.started.json'),
                {'id': key, 'bucket': bucket, 'role': role, 'request': request, 'token_reservation': reserve}, immutable=True)
            pending[key] = dict(bucket=bucket, role=role, reserve=reserve)
            self.save()

    def finish(self, key, response, error, seconds):
        with self.lock:
            row = self.state['pending'][key]
            usage = response.get('usage') if isinstance(response, dict) else None
            tokens = usage.get('total_tokens') if isinstance(usage, dict) else None
            known = isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0
            atomic_json(self.root / 'calls' / (key + '.completed.json'),
                {'id': key, 'response': response, 'error': error, 'usage': usage, 'seconds': seconds,
                 'known_actual_tokens': tokens if known else None}, immutable=True)
            bucket = self.state['buckets'].setdefault(row['bucket'], {'calls': 0, 'tokens': 0, 'unknown_usage': 0, 'roles': {}})
            bucket['calls'] += 1; bucket['tokens'] += tokens if known else row['reserve']
            bucket['unknown_usage'] += int(not known)
            role = bucket['roles'].setdefault(row['role'], {'calls': 0, 'tokens': 0})
            role['calls'] += 1; role['tokens'] += tokens if known else row['reserve']
            del self.state['pending'][key]; self.save()
            if not known or tokens > row['reserve']:
                raise InterruptedRun('usage unknown or above conservative reservation; response retained, no retry')


class BudgetClient:
    def __init__(self, ledger, inner, role, tag, bucket):
        self.ledger, self.inner, self.role, self.tag, self.bucket = ledger, inner, role, tag, bucket
        self.settings, self.index = inner.settings, 0

    def close(self): self.inner.close()

    def complete(self, request):
        key = digest([self.tag, self.index, request]); self.index += 1
        self.ledger.start(key, self.bucket, self.role, request)
        begin = time.monotonic()
        try:
            response = self.inner.complete(request)
        except Exception as exc:
            self.ledger.finish(key, getattr(exc, 'response', None),
                {'type': type(exc).__name__, 'message': str(exc), 'code': getattr(exc, 'code', None)}, time.monotonic() - begin)
            raise
        self.ledger.finish(key, response, None, time.monotonic() - begin)
        return response
