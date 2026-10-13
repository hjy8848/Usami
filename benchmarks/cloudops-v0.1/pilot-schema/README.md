# Live attempts after schema repair, before empty-tool transport repair

This complete preregistered profile retained three successful real Service runs and three Qwen Customer format failures (0, 0 and 1 valid Service turns). These outcomes are not replaced by the release pilot. `original-source/customer.py.txt` pins the exact implementation used here.

```bash
python examples/cloudops/replay_initial.py --evidence benchmarks/cloudops-v0.1/pilot-schema
```

The isolated replay checks original source hashes, every model request, actual state transitions, authorization and all scores without network calls. The later transport repair omits empty `tools`/`tool_choice` fields for Customer requests; it changes no business rule or Oracle.
