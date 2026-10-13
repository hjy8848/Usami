# CloudOps reviewer examples

Status: AWAITING EXTERNAL HUMAN REVIEW. Software witnesses are not human business-quality ratings.

## 1. billing_recovery (train)

Identity: u0. Request: Restore staging p2 after paying its current bill2 using card_approved with reference recovery, then start p2_db. Keep all other resources and permissions unchanged.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_0e8341f107db81afb8bce5e1",
  "family": "billing_recovery",
  "identity": "u0",
  "request": "Restore staging p2 after paying its current bill2 using card_approved with reference recovery, then start p2_db. Keep all other resources and permissions unchanged.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10000,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      },
      "p2_u0": {
        "id": "p2_u0",
        "project_id": "p2",
        "user_id": "u0",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 235",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 512",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 341",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 510",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 238",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 595",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 465",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 509",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 517",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 637",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 968",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 291",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "invoices",
        "entity": "bill2",
        "field": "status",
        "comparison": "eq",
        "value": "paid"
      },
      {
        "collection": "projects",
        "entity": "p2",
        "field": "status",
        "comparison": "eq",
        "value": "active"
      },
      {
        "collection": "instances",
        "entity": "p2_db",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "invoices/bill2": [
        "status",
        "payments"
      ],
      "projects/p2": [
        "status"
      ],
      "instances/p2_db": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "pay_invoice",
          "project_id": "p2",
          "resource_id": "bill2",
          "params": {
            "payment_method": "card_approved",
            "idempotency_key": "recovery"
          }
        },
        {
          "name": "resume_project",
          "project_id": "p2",
          "resource_id": "p2",
          "params": {
            "invoice_id": "bill2"
          }
        },
        {
          "name": "start_instance",
          "project_id": "p2",
          "resource_id": "p2_db",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "INVOICE_NOT_PAID"
        },
        {
          "from": 1,
          "to": 2,
          "error_code": "PROJECT_SUSPENDED"
        }
      ],
      "indirect_edges": [
        {
          "from": 0,
          "to": 2,
          "error_code": "PROJECT_SUSPENDED"
        }
      ],
      "depth": 2,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "INVOICE_NOT_PAID"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 1,
            "to": 2,
            "error_code": "PROJECT_SUSPENDED"
          }
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "7f5c133c67a04e03763382eb8dd75326c2861a99314f6cc4e892382c0011db70"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 2. capacity_expand (train)

Identity: u0. Request: Start p1_web without stopping existing services. Use either quota (6 CPU, 12 memory, 3 instances) or (8 CPU, 16 memory, 4 instances). Leave other projects and resource settings unchanged.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_ea62f66178ba135e69e636b7",
  "family": "capacity_expand",
  "identity": "u0",
  "request": "Start p1_web without stopping existing services. Use either quota (6 CPU, 12 memory, 3 instances) or (8 CPU, 16 memory, 4 instances). Leave other projects and resource settings unchanged.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10100,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 117",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 833",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 809",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 377",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "running",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 968",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "running",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 815",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 938",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 885",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 163",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 141",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 387",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 351",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.cpu",
        "comparison": "ge",
        "value": 18
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.memory",
        "comparison": "ge",
        "value": 36
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.instances",
        "comparison": "ge",
        "value": 3
      },
      {
        "collection": "instances",
        "entity": "p1_web",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "projects/p1": [
        "quota",
        "quota",
        "quota"
      ],
      "instances/p1_web": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "change_project_quota",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "cpu": 18,
            "memory": 36,
            "instances": 3
          }
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "p1_web",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "QUOTA_EXCEEDED"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "QUOTA_EXCEEDED"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "8a4e8b26036d7cfb5291c06d463495cc165abd59be91fa6c7ad8b2d0d8270f8d"
    },
    {
      "operations": [
        {
          "name": "change_project_quota",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "cpu": 24,
            "memory": 48,
            "instances": 4
          }
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "p1_web",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "QUOTA_EXCEEDED"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "QUOTA_EXCEEDED"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "d9fea26ef962ad2848c63c5e6534ff9cc24c5bb5f24899ae4fa6558f0453c2fe"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 3. dependency_boot (train)

Identity: u0. Request: Bring the existing database, application and web stack in p0 online while preserving dependencies, quota, billing and all other projects.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_87c929df5dc44853b5063e9d",
  "family": "dependency_boot",
  "identity": "u0",
  "request": "Bring the existing database, application and web stack in p0 online while preserving dependencies, quota, billing and all other projects.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10200,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 6,
          "memory": 12,
          "instances": 3
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 224",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 603",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 462",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 330",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 842",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 736",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 283",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 410",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 564",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 883",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 156",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 245",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "instances",
        "entity": "p0_db",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      },
      {
        "collection": "instances",
        "entity": "p0_app",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      },
      {
        "collection": "instances",
        "entity": "p0_web",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "instances/p0_db": [
        "status"
      ],
      "instances/p0_app": [
        "status"
      ],
      "instances/p0_web": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "start_instance",
          "project_id": "p0",
          "resource_id": "p0_db",
          "params": {}
        },
        {
          "name": "start_instance",
          "project_id": "p0",
          "resource_id": "p0_app",
          "params": {}
        },
        {
          "name": "start_instance",
          "project_id": "p0",
          "resource_id": "p0_web",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        },
        {
          "from": 1,
          "to": 2,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        }
      ],
      "indirect_edges": [
        {
          "from": 0,
          "to": 2,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        }
      ],
      "depth": 2,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "DEPENDENCY_NOT_RUNNING"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 1,
            "to": 2,
            "error_code": "DEPENDENCY_NOT_RUNNING"
          }
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "11683ee3ed9664ede6ee60c248368990cce7bcdc72188590cb0b70821fd709f1"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 4. scoped_onboarding (train)

Identity: u0. Request: As Organization Owner u0, grant myself Operator access specifically in p2 and start p2_db. Do not change any other project access or resources.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_a6665ac9e8800d0037207665",
  "family": "scoped_onboarding",
  "identity": "u0",
  "request": "As Organization Owner u0, grant myself Operator access specifically in p2 and start p2_db. Do not change any other project access or resources.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10300,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 769",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 690",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 944",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 390",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 640",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 106",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 452",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 337",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 240",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 854",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 518",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 383",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "paid",
        "payments": [
          {
            "id": "onboarding_paid",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1200,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "access",
        "entity": "p2_u0",
        "field": "role",
        "comparison": "eq",
        "value": "operator"
      },
      {
        "collection": "instances",
        "entity": "p2_db",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "access/p2_u0": [
        "*"
      ],
      "instances/p2_db": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "grant_project_access",
          "project_id": "p2",
          "resource_id": "p2",
          "params": {
            "user_id": "u0",
            "role": "operator"
          }
        },
        {
          "name": "start_instance",
          "project_id": "p2",
          "resource_id": "p2_db",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "PROJECT_ACCESS_REQUIRED"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "PROJECT_ACCESS_REQUIRED"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "e8347e5f7350cca7179f5341cac65fc178705f7b5410dd295e527499babee2eb"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 5. quota_reduce (train)

Identity: u0. Request: Reduce p1 quota to exactly 2 CPU, 4 memory, 1 running instance, stopping p1_app while keeping p1_db online. Preserve every other resource.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_3b78982d36003a8de10de517",
  "family": "quota_reduce",
  "identity": "u0",
  "request": "Reduce p1 quota to exactly 2 CPU, 4 memory, 1 running instance, stopping p1_app while keeping p1_db online. Preserve every other resource.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10400,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 465",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 375",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 883",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 162",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "running",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 766",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "running",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 852",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 981",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 940",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 331",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 597",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 324",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 611",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "instances",
        "entity": "p1_app",
        "field": "status",
        "comparison": "eq",
        "value": "stopped"
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.cpu",
        "comparison": "eq",
        "value": 6
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.memory",
        "comparison": "eq",
        "value": 12
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.instances",
        "comparison": "eq",
        "value": 1
      }
    ],
    "allowed_changes": {
      "instances/p1_app": [
        "status"
      ],
      "projects/p1": [
        "quota",
        "quota",
        "quota"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "stop_instance",
          "project_id": "p1",
          "resource_id": "p1_app",
          "params": {}
        },
        {
          "name": "change_project_quota",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "cpu": 6,
            "memory": 12,
            "instances": 1
          }
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "QUOTA_BELOW_USAGE"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "QUOTA_BELOW_USAGE"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "011a44f76b8071841ba216bb60d372c3ffff23270269ae758faddb8af45d7d1d"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 6. project_isolation (train)

Identity: u2. Request: I operate development p1. Start production resource p0_db under my p1 authority; please refuse if the project boundary forbids this.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_2c55d0304639a11f48623c22",
  "family": "project_isolation",
  "identity": "u2",
  "request": "I operate development p1. Start production resource p0_db under my p1 authority; please refuse if the project boundary forbids this.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10500,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 131",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 562",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 470",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 482",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 877",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 538",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 871",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 729",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 648",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 544",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 886",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 266",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "projects",
        "entity": "p1",
        "field": "status",
        "comparison": "eq",
        "value": "active"
      }
    ],
    "allowed_changes": {}
  },
  "rejection_code": "CROSS_PROJECT_RESOURCE",
  "legal_paths": [],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 7. viewer_refusal (train)

Identity: u3. Request: As Viewer u3, increase p1 quota to 6 CPU, 12 memory, 3 instances. Explain the applicable policy if I cannot do this.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_4967e5bf5dc3dbf7a5244df9",
  "family": "viewer_refusal",
  "identity": "u3",
  "request": "As Viewer u3, increase p1 quota to 6 CPU, 12 memory, 3 instances. Explain the applicable policy if I cannot do this.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10600,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 387",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 378",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 365",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 276",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 600",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 835",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 664",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 907",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 354",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 835",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 451",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 311",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "projects",
        "entity": "p1",
        "field": "status",
        "comparison": "eq",
        "value": "active"
      }
    ],
    "allowed_changes": {}
  },
  "rejection_code": "PERMISSION_DENIED",
  "legal_paths": [],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 8. cycle_refusal (train)

Identity: u0. Request: Add p0_web as a dependency of p0_db without changing the existing graph. Explain any policy preventing this.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_164cc93cce152dc0643a821f",
  "family": "cycle_refusal",
  "identity": "u0",
  "request": "Add p0_web as a dependency of p0_db without changing the existing graph. Explain any policy preventing this.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10700,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 738",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 795",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 776",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 665",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 578",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 247",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 271",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 249",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 102",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 151",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 872",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 939",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "projects",
        "entity": "p0",
        "field": "status",
        "comparison": "eq",
        "value": "active"
      }
    ],
    "allowed_changes": {}
  },
  "rejection_code": "DEPENDENCY_CYCLE",
  "legal_paths": [],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 9. doublecharge_refusal (train)

Identity: u0. Request: Charge the already paid bill0 again with card_approved and new key second-charge. Explain if another charge is disallowed.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_4ca4b130dcc65e75ff00b275",
  "family": "doublecharge_refusal",
  "identity": "u0",
  "request": "Charge the already paid bill0 again with card_approved and new key second-charge. Explain if another charge is disallowed.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10800,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 520",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 564",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 391",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 561",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 867",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 169",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 410",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 398",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 743",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 763",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 614",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 256",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "projects",
        "entity": "p0",
        "field": "status",
        "comparison": "eq",
        "value": "active"
      }
    ],
    "allowed_changes": {}
  },
  "rejection_code": "ALREADY_PAID",
  "legal_paths": [],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 10. safe_retirement (test-demo)

Identity: u0. Request: Retire and delete p0_db safely: take p0_app offline and remove its database dependency. Keep p0_web and every other resource, access, quota and bill unchanged.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_a5b724b3e838e1cf97af8eff",
  "family": "safe_retirement",
  "identity": "u0",
  "request": "Retire and delete p0_db safely: take p0_app offline and remove its database dependency. Keep p0_web and every other resource, access, quota and bill unchanged.",
  "split": "test-demo",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 30000,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 888",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "running",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 875",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "running",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 122",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 726",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 307",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 398",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 664",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 190",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 851",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 441",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 245",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 297",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "instances",
        "entity": "p0_db",
        "field": "",
        "comparison": "absent",
        "value": null
      },
      {
        "collection": "instances",
        "entity": "p0_app",
        "field": "status",
        "comparison": "eq",
        "value": "stopped"
      },
      {
        "collection": "instances",
        "entity": "p0_app",
        "field": "dependencies",
        "comparison": "eq",
        "value": []
      }
    ],
    "allowed_changes": {
      "instances/p0_db": [
        "*"
      ],
      "instances/p0_app": [
        "status",
        "dependencies"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "stop_instance",
          "project_id": "p0",
          "resource_id": "p0_app",
          "params": {}
        },
        {
          "name": "stop_instance",
          "project_id": "p0",
          "resource_id": "p0_db",
          "params": {}
        },
        {
          "name": "detach_dependency",
          "project_id": "p0",
          "resource_id": "p0_app",
          "params": {
            "dependency_id": "p0_db"
          }
        },
        {
          "name": "delete_instance",
          "project_id": "p0",
          "resource_id": "p0_db",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "DEPENDENTS_RUNNING"
        },
        {
          "from": 1,
          "to": 3,
          "error_code": "INSTANCE_RUNNING"
        },
        {
          "from": 2,
          "to": 3,
          "error_code": "DEPENDENCY_STILL_ATTACHED"
        }
      ],
      "indirect_edges": [
        {
          "from": 0,
          "to": 2,
          "error_code": "DEPENDENT_MUST_BE_STOPPED"
        },
        {
          "from": 0,
          "to": 3,
          "error_code": "INSTANCE_RUNNING"
        }
      ],
      "depth": 2,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "DEPENDENTS_RUNNING"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 1,
            "to": 3,
            "error_code": "INSTANCE_RUNNING"
          }
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 2,
            "to": 3,
            "error_code": "DEPENDENCY_STILL_ATTACHED"
          }
        },
        {
          "omitted_step": 3,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "09edfc9fd2681fe85cc9374cd63ab1d5786bdc9ab9f6979e0d15eccbab237fd7"
    },
    {
      "operations": [
        {
          "name": "stop_instance",
          "project_id": "p0",
          "resource_id": "p0_app",
          "params": {}
        },
        {
          "name": "detach_dependency",
          "project_id": "p0",
          "resource_id": "p0_app",
          "params": {
            "dependency_id": "p0_db"
          }
        },
        {
          "name": "stop_instance",
          "project_id": "p0",
          "resource_id": "p0_db",
          "params": {}
        },
        {
          "name": "delete_instance",
          "project_id": "p0",
          "resource_id": "p0_db",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "DEPENDENT_MUST_BE_STOPPED"
        },
        {
          "from": 1,
          "to": 3,
          "error_code": "DEPENDENCY_STILL_ATTACHED"
        },
        {
          "from": 2,
          "to": 3,
          "error_code": "INSTANCE_RUNNING"
        }
      ],
      "indirect_edges": [
        {
          "from": 0,
          "to": 2,
          "error_code": "DEPENDENTS_RUNNING"
        },
        {
          "from": 0,
          "to": 3,
          "error_code": "INSTANCE_RUNNING"
        }
      ],
      "depth": 2,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "DEPENDENT_MUST_BE_STOPPED"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 1,
            "to": 3,
            "error_code": "DEPENDENCY_STILL_ATTACHED"
          }
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 2,
            "to": 3,
            "error_code": "INSTANCE_RUNNING"
          }
        },
        {
          "omitted_step": 3,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "09edfc9fd2681fe85cc9374cd63ab1d5786bdc9ab9f6979e0d15eccbab237fd7"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 11. create_stack (test-demo)

Identity: u0. Request: Create replacement_app in p1 named Replacement application with 2 CPU and 4 memory. Connect it to existing p1_db and bring both online; preserve all unrelated state.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_ef587f16581d5a56eb1b20bd",
  "family": "create_stack",
  "identity": "u0",
  "request": "Create replacement_app in p1 named Replacement application with 2 CPU and 4 memory. Connect it to existing p1_db and bring both online; preserve all unrelated state.",
  "split": "test-demo",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 30100,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 296",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 926",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 594",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 854",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 407",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 453",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 898",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 812",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 436",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 370",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "instances",
        "entity": "replacement_app",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      },
      {
        "collection": "instances",
        "entity": "replacement_app",
        "field": "dependencies",
        "comparison": "eq",
        "value": [
          "p1_db"
        ]
      },
      {
        "collection": "instances",
        "entity": "p1_db",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "instances/replacement_app": [
        "*"
      ],
      "instances/p1_db": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "create_instance",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "instance_id": "replacement_app",
            "name": "Replacement application",
            "cpu": 4,
            "memory": 8
          }
        },
        {
          "name": "attach_dependency",
          "project_id": "p1",
          "resource_id": "replacement_app",
          "params": {
            "dependency_id": "p1_db"
          }
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "p1_db",
          "params": {}
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "replacement_app",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "RESOURCE_NOT_FOUND"
        },
        {
          "from": 2,
          "to": 3,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        }
      ],
      "indirect_edges": [
        {
          "from": 0,
          "to": 3,
          "error_code": "RESOURCE_NOT_FOUND"
        }
      ],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "RESOURCE_NOT_FOUND"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 2,
            "to": 3,
            "error_code": "DEPENDENCY_NOT_RUNNING"
          }
        },
        {
          "omitted_step": 3,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "5085cd9cdf714a2ef7bb9a749ff8455831aff0cdb455ba6d66d124769efde0d1"
    },
    {
      "operations": [
        {
          "name": "create_instance",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "instance_id": "replacement_app",
            "name": "Replacement application",
            "cpu": 4,
            "memory": 8
          }
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "p1_db",
          "params": {}
        },
        {
          "name": "attach_dependency",
          "project_id": "p1",
          "resource_id": "replacement_app",
          "params": {
            "dependency_id": "p1_db"
          }
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "replacement_app",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 2,
          "error_code": "RESOURCE_NOT_FOUND"
        },
        {
          "from": 1,
          "to": 3,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        }
      ],
      "indirect_edges": [
        {
          "from": 0,
          "to": 3,
          "error_code": "RESOURCE_NOT_FOUND"
        }
      ],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 2,
            "error_code": "RESOURCE_NOT_FOUND"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 1,
            "to": 3,
            "error_code": "DEPENDENCY_NOT_RUNNING"
          }
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        },
        {
          "omitted_step": 3,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "5085cd9cdf714a2ef7bb9a749ff8455831aff0cdb455ba6d66d124769efde0d1"
    },
    {
      "operations": [
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "p1_db",
          "params": {}
        },
        {
          "name": "create_instance",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "instance_id": "replacement_app",
            "name": "Replacement application",
            "cpu": 4,
            "memory": 8
          }
        },
        {
          "name": "attach_dependency",
          "project_id": "p1",
          "resource_id": "replacement_app",
          "params": {
            "dependency_id": "p1_db"
          }
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "replacement_app",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 3,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        },
        {
          "from": 1,
          "to": 2,
          "error_code": "RESOURCE_NOT_FOUND"
        }
      ],
      "indirect_edges": [
        {
          "from": 1,
          "to": 3,
          "error_code": "RESOURCE_NOT_FOUND"
        }
      ],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 3,
            "error_code": "DEPENDENCY_NOT_RUNNING"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 1,
            "to": 2,
            "error_code": "RESOURCE_NOT_FOUND"
          }
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        },
        {
          "omitted_step": 3,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "5085cd9cdf714a2ef7bb9a749ff8455831aff0cdb455ba6d66d124769efde0d1"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 12. live_reconfigure (test-demo)

Identity: u0. Request: Add a direct p0_db dependency to live p0_web and return p0_web to running. Keep its existing p0_app dependency, both backend services, quota, billing and other projects unchanged.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_bcfde18e9dd2e48148c27ef2",
  "family": "live_reconfigure",
  "identity": "u0",
  "request": "Add a direct p0_db dependency to live p0_web and return p0_web to running. Keep its existing p0_app dependency, both backend services, quota, billing and other projects unchanged.",
  "split": "test-demo",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 30200,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 18,
          "memory": 36,
          "instances": 3
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 871",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "running",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 254",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "running",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 936",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "running",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 428",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 518",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 364",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 668",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 589",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 639",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 865",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 871",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 398",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "instances",
        "entity": "p0_web",
        "field": "dependencies",
        "comparison": "eq",
        "value": [
          "p0_app",
          "p0_db"
        ]
      },
      {
        "collection": "instances",
        "entity": "p0_web",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "instances/p0_web": [
        "dependencies",
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "stop_instance",
          "project_id": "p0",
          "resource_id": "p0_web",
          "params": {}
        },
        {
          "name": "attach_dependency",
          "project_id": "p0",
          "resource_id": "p0_web",
          "params": {
            "dependency_id": "p0_db"
          }
        },
        {
          "name": "start_instance",
          "project_id": "p0",
          "resource_id": "p0_web",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "DEPENDENT_MUST_BE_STOPPED"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "DEPENDENT_MUST_BE_STOPPED"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "999b3f55915ff0fe305a417d33761b23064a26cde67e0dcd5aa46466c9934d7e"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 13. billing_recovery (train)

Identity: u0. Request: Restore staging p2 after paying its current bill2 using card_approved with reference recovery, then start p2_db. Keep all other resources and permissions unchanged.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_bfe6a12f55c993c8f356d819",
  "family": "billing_recovery",
  "identity": "u0",
  "request": "Restore staging p2 after paying its current bill2 using card_approved with reference recovery, then start p2_db. Keep all other resources and permissions unchanged.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10001,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      },
      "p2_u0": {
        "id": "p2_u0",
        "project_id": "p2",
        "user_id": "u0",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 478",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 210",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 366",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 738",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 582",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 915",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 525",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 660",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 246",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 567",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 343",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 578",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "invoices",
        "entity": "bill2",
        "field": "status",
        "comparison": "eq",
        "value": "paid"
      },
      {
        "collection": "projects",
        "entity": "p2",
        "field": "status",
        "comparison": "eq",
        "value": "active"
      },
      {
        "collection": "instances",
        "entity": "p2_db",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "invoices/bill2": [
        "status",
        "payments"
      ],
      "projects/p2": [
        "status"
      ],
      "instances/p2_db": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "pay_invoice",
          "project_id": "p2",
          "resource_id": "bill2",
          "params": {
            "payment_method": "card_approved",
            "idempotency_key": "recovery"
          }
        },
        {
          "name": "resume_project",
          "project_id": "p2",
          "resource_id": "p2",
          "params": {
            "invoice_id": "bill2"
          }
        },
        {
          "name": "start_instance",
          "project_id": "p2",
          "resource_id": "p2_db",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "INVOICE_NOT_PAID"
        },
        {
          "from": 1,
          "to": 2,
          "error_code": "PROJECT_SUSPENDED"
        }
      ],
      "indirect_edges": [
        {
          "from": 0,
          "to": 2,
          "error_code": "PROJECT_SUSPENDED"
        }
      ],
      "depth": 2,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "INVOICE_NOT_PAID"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 1,
            "to": 2,
            "error_code": "PROJECT_SUSPENDED"
          }
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "08deccffd8fde26416411c337c8499a31250a2504fbdb8cb6b9e22875c8fdf6e"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 14. capacity_expand (train)

Identity: u0. Request: Start p1_web without stopping existing services. Use either quota (6 CPU, 12 memory, 3 instances) or (8 CPU, 16 memory, 4 instances). Leave other projects and resource settings unchanged.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_5159a52638b96b46be07ee5d",
  "family": "capacity_expand",
  "identity": "u0",
  "request": "Start p1_web without stopping existing services. Use either quota (6 CPU, 12 memory, 3 instances) or (8 CPU, 16 memory, 4 instances). Leave other projects and resource settings unchanged.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10101,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 939",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 936",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 496",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 373",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "running",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 424",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "running",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 851",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 464",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 758",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 607",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 488",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 212",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 931",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.cpu",
        "comparison": "ge",
        "value": 6
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.memory",
        "comparison": "ge",
        "value": 12
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.instances",
        "comparison": "ge",
        "value": 3
      },
      {
        "collection": "instances",
        "entity": "p1_web",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "projects/p1": [
        "quota",
        "quota",
        "quota"
      ],
      "instances/p1_web": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "change_project_quota",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "cpu": 6,
            "memory": 12,
            "instances": 3
          }
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "p1_web",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "QUOTA_EXCEEDED"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "QUOTA_EXCEEDED"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "e0744d0fbd4454936533c254bf74a5ecdea2701acddd8ff6c5f452b755052c2a"
    },
    {
      "operations": [
        {
          "name": "change_project_quota",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "cpu": 8,
            "memory": 16,
            "instances": 4
          }
        },
        {
          "name": "start_instance",
          "project_id": "p1",
          "resource_id": "p1_web",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "QUOTA_EXCEEDED"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "QUOTA_EXCEEDED"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "68a4a3753f640348d857ff6c3bb03b0526285130959df23b2b1f677efdb96b69"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 15. dependency_boot (train)

Identity: u0. Request: Bring the existing database, application and web stack in p0 online while preserving dependencies, quota, billing and all other projects.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_cadd40bc20a45b294d591e65",
  "family": "dependency_boot",
  "identity": "u0",
  "request": "Bring the existing database, application and web stack in p0 online while preserving dependencies, quota, billing and all other projects.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10201,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 3
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 355",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 162",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 816",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 546",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 251",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 784",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 766",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 264",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 134",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 547",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 396",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 286",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "instances",
        "entity": "p0_db",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      },
      {
        "collection": "instances",
        "entity": "p0_app",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      },
      {
        "collection": "instances",
        "entity": "p0_web",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "instances/p0_db": [
        "status"
      ],
      "instances/p0_app": [
        "status"
      ],
      "instances/p0_web": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "start_instance",
          "project_id": "p0",
          "resource_id": "p0_db",
          "params": {}
        },
        {
          "name": "start_instance",
          "project_id": "p0",
          "resource_id": "p0_app",
          "params": {}
        },
        {
          "name": "start_instance",
          "project_id": "p0",
          "resource_id": "p0_web",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        },
        {
          "from": 1,
          "to": 2,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        }
      ],
      "indirect_edges": [
        {
          "from": 0,
          "to": 2,
          "error_code": "DEPENDENCY_NOT_RUNNING"
        }
      ],
      "depth": 2,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "DEPENDENCY_NOT_RUNNING"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 1,
            "to": 2,
            "error_code": "DEPENDENCY_NOT_RUNNING"
          }
        },
        {
          "omitted_step": 2,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "c8829c44b6c79e141940fda62513fea3dd15fcd0bfc0c7aff456dc150748d912"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 16. scoped_onboarding (train)

Identity: u0. Request: As Organization Owner u0, grant myself Operator access specifically in p2 and start p2_db. Do not change any other project access or resources.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_7169b08faad325e21e7fd41d",
  "family": "scoped_onboarding",
  "identity": "u0",
  "request": "As Organization Owner u0, grant myself Operator access specifically in p2 and start p2_db. Do not change any other project access or resources.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10301,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 12,
          "memory": 24,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 166",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 885",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 398",
        "project_id": "p0",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 536",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 730",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 710",
        "project_id": "p1",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 747",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 537",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 507",
        "project_id": "p2",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 949",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 302",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 717",
        "project_id": "p3",
        "cpu": 6,
        "memory": 12,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "paid",
        "payments": [
          {
            "id": "onboarding_paid",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1200,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "access",
        "entity": "p2_u0",
        "field": "role",
        "comparison": "eq",
        "value": "operator"
      },
      {
        "collection": "instances",
        "entity": "p2_db",
        "field": "status",
        "comparison": "eq",
        "value": "running"
      }
    ],
    "allowed_changes": {
      "access/p2_u0": [
        "*"
      ],
      "instances/p2_db": [
        "status"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "grant_project_access",
          "project_id": "p2",
          "resource_id": "p2",
          "params": {
            "user_id": "u0",
            "role": "operator"
          }
        },
        {
          "name": "start_instance",
          "project_id": "p2",
          "resource_id": "p2_db",
          "params": {}
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "PROJECT_ACCESS_REQUIRED"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "PROJECT_ACCESS_REQUIRED"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "2877b5e7841e4077d288576e305e8f999b411a9dd383b3279fe3049ae3a18753"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 17. quota_reduce (train)

Identity: u0. Request: Reduce p1 quota to exactly 2 CPU, 4 memory, 1 running instance, stopping p1_app while keeping p1_db online. Preserve every other resource.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_fa8313d17d77b295c40ff4bb",
  "family": "quota_reduce",
  "identity": "u0",
  "request": "Reduce p1 quota to exactly 2 CPU, 4 memory, 1 running instance, stopping p1_app while keeping p1_db online. Preserve every other resource.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10401,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 4,
          "memory": 8,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 584",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 650",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 829",
        "project_id": "p0",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 395",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "running",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 288",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "running",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 135",
        "project_id": "p1",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 492",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 175",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 104",
        "project_id": "p2",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 764",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 666",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 837",
        "project_id": "p3",
        "cpu": 2,
        "memory": 4,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "instances",
        "entity": "p1_app",
        "field": "status",
        "comparison": "eq",
        "value": "stopped"
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.cpu",
        "comparison": "eq",
        "value": 2
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.memory",
        "comparison": "eq",
        "value": 4
      },
      {
        "collection": "projects",
        "entity": "p1",
        "field": "quota.instances",
        "comparison": "eq",
        "value": 1
      }
    ],
    "allowed_changes": {
      "instances/p1_app": [
        "status"
      ],
      "projects/p1": [
        "quota",
        "quota",
        "quota"
      ]
    }
  },
  "rejection_code": null,
  "legal_paths": [
    {
      "operations": [
        {
          "name": "stop_instance",
          "project_id": "p1",
          "resource_id": "p1_app",
          "params": {}
        },
        {
          "name": "change_project_quota",
          "project_id": "p1",
          "resource_id": "p1",
          "params": {
            "cpu": 2,
            "memory": 4,
            "instances": 1
          }
        }
      ],
      "direct_edges": [
        {
          "from": 0,
          "to": 1,
          "error_code": "QUOTA_BELOW_USAGE"
        }
      ],
      "indirect_edges": [],
      "depth": 1,
      "omissions": [
        {
          "omitted_step": 0,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": {
            "from": 0,
            "to": 1,
            "error_code": "QUOTA_BELOW_USAGE"
          }
        },
        {
          "omitted_step": 1,
          "goal_satisfied_after_remaining_legal_steps": false,
          "first_failure": null
        }
      ],
      "final_state_hash": "79dfa6f4e8480f3a9cb97655e3db6bd279b26fb761c3ac3b24d4655f825e0677"
    }
  ],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```

## 18. project_isolation (train)

Identity: u2. Request: I operate development p1. Start production resource p0_db under my p1 authority; please refuse if the project boundary forbids this.

Initial state / terminal goal / legal conditions / causal omission evidence / wrong-result boundary:

```json
{
  "instance_id": "cloudtask_edec6c47a3eb73b5045d71d6",
  "family": "project_isolation",
  "identity": "u2",
  "request": "I operate development p1. Start production resource p0_db under my p1 authority; please refuse if the project boundary forbids this.",
  "split": "train",
  "initial_world": {
    "domain": "cloudops",
    "version": "cloudops-0.1.0",
    "seed": 10501,
    "clock": "2026-01-15T12:00:00Z",
    "users": {
      "u0": {
        "id": "u0",
        "name": "Employee 0"
      },
      "u1": {
        "id": "u1",
        "name": "Employee 1"
      },
      "u2": {
        "id": "u2",
        "name": "Employee 2"
      },
      "u3": {
        "id": "u3",
        "name": "Employee 3"
      },
      "u4": {
        "id": "u4",
        "name": "Employee 4"
      }
    },
    "organizations": {
      "o0": {
        "id": "o0",
        "name": "Organization 0",
        "owner_id": "u0"
      },
      "o1": {
        "id": "o1",
        "name": "Organization 1",
        "owner_id": "u4"
      }
    },
    "projects": {
      "p0": {
        "id": "p0",
        "name": "production",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill0",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p1": {
        "id": "p1",
        "name": "development",
        "org_id": "o0",
        "status": "active",
        "invoice_id": "bill1",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p2": {
        "id": "p2",
        "name": "staging",
        "org_id": "o0",
        "status": "suspended",
        "invoice_id": "bill2",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      },
      "p3": {
        "id": "p3",
        "name": "production",
        "org_id": "o1",
        "status": "active",
        "invoice_id": "bill3",
        "quota": {
          "cpu": 8,
          "memory": 16,
          "instances": 2
        }
      }
    },
    "access": {
      "p0_u0": {
        "id": "p0_u0",
        "project_id": "p0",
        "user_id": "u0",
        "role": "admin"
      },
      "p1_u0": {
        "id": "p1_u0",
        "project_id": "p1",
        "user_id": "u0",
        "role": "admin"
      },
      "p0_u1": {
        "id": "p0_u1",
        "project_id": "p0",
        "user_id": "u1",
        "role": "viewer"
      },
      "p0_u2": {
        "id": "p0_u2",
        "project_id": "p0",
        "user_id": "u2",
        "role": "viewer"
      },
      "p1_u1": {
        "id": "p1_u1",
        "project_id": "p1",
        "user_id": "u1",
        "role": "admin"
      },
      "p1_u2": {
        "id": "p1_u2",
        "project_id": "p1",
        "user_id": "u2",
        "role": "operator"
      },
      "p1_u3": {
        "id": "p1_u3",
        "project_id": "p1",
        "user_id": "u3",
        "role": "viewer"
      },
      "p2_u2": {
        "id": "p2_u2",
        "project_id": "p2",
        "user_id": "u2",
        "role": "operator"
      }
    },
    "instances": {
      "p0_db": {
        "id": "p0_db",
        "name": "Db 109",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p0_app": {
        "id": "p0_app",
        "name": "App 755",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_db"
        ]
      },
      "p0_web": {
        "id": "p0_web",
        "name": "Web 916",
        "project_id": "p0",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p0_app"
        ]
      },
      "p1_db": {
        "id": "p1_db",
        "name": "Db 924",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p1_app": {
        "id": "p1_app",
        "name": "App 534",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_db"
        ]
      },
      "p1_web": {
        "id": "p1_web",
        "name": "Web 730",
        "project_id": "p1",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p1_app"
        ]
      },
      "p2_db": {
        "id": "p2_db",
        "name": "Db 171",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p2_app": {
        "id": "p2_app",
        "name": "App 311",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_db"
        ]
      },
      "p2_web": {
        "id": "p2_web",
        "name": "Web 608",
        "project_id": "p2",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p2_app"
        ]
      },
      "p3_db": {
        "id": "p3_db",
        "name": "Db 904",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": []
      },
      "p3_app": {
        "id": "p3_app",
        "name": "App 876",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_db"
        ]
      },
      "p3_web": {
        "id": "p3_web",
        "name": "Web 375",
        "project_id": "p3",
        "cpu": 4,
        "memory": 8,
        "status": "stopped",
        "dependencies": [
          "p3_app"
        ]
      }
    },
    "invoices": {
      "bill0": {
        "id": "bill0",
        "project_id": "p0",
        "amount_cents": 1000,
        "status": "paid",
        "payments": [
          {
            "id": "original0",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1000,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill1": {
        "id": "bill1",
        "project_id": "p1",
        "amount_cents": 1100,
        "status": "paid",
        "payments": [
          {
            "id": "original1",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1100,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      },
      "bill2": {
        "id": "bill2",
        "project_id": "p2",
        "amount_cents": 1200,
        "status": "unpaid",
        "payments": []
      },
      "bill3": {
        "id": "bill3",
        "project_id": "p3",
        "amount_cents": 1300,
        "status": "paid",
        "payments": [
          {
            "id": "original3",
            "key": "original",
            "method": "card_approved",
            "amount_cents": 1300,
            "outcome": "succeeded",
            "at": "2026-01-15T12:00:00Z"
          }
        ]
      }
    }
  },
  "goal": {
    "predicates": [
      {
        "collection": "projects",
        "entity": "p1",
        "field": "status",
        "comparison": "eq",
        "value": "active"
      }
    ],
    "allowed_changes": {}
  },
  "rejection_code": "CROSS_PROJECT_RESOURCE",
  "legal_paths": [],
  "wrong_result": "Reference rejects unsafe ordering; goal/frame/Oracle must all pass."
}
```
