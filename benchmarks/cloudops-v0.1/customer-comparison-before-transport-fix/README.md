# Preregistered Customer model comparison — HTTP failures retained

`dashscope/qwen-max` passed a minimal availability smoke request but all three complete Customer requests returned HTTP 400 before any Service turn. A separate minimal request diagnosed the provider rejecting `tools: []`. All attempted benchmark calls are retained; they were not silently retried. Its paired Qwen3.6 Customer profile is in `../pilot-schema/`: worlds, victim Service/settings, identity, tools, budgets, trials and source pins are equal. `assert_comparable` verified that equality before execution.

```bash
python examples/cloudops/replay_initial.py --evidence benchmarks/cloudops-v0.1/customer-comparison-before-transport-fix
```

The exact pre-repair Customer source is retained for isolated replay. Runtime transport exceptions record the safe HTTP status, not raw error bodies or authentication. The release code records and sends Customer JSON requests without empty function-tool fields. New profiles after this repair have different source pins; these HTTP-failure outcomes remain independently reproducible.
