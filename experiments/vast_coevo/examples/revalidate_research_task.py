"""Revalidate a blocked Research Studio Task from its saved raw response.

Stop the local backend first. This command uses no model, changes no World or
proposal, archives the original record, and appends the native certification.
Restart the backend and refresh the same run URL afterwards.
"""
import argparse
import json
from pathlib import Path

from web.backend.human_customer import HumanSessionManager
from web.backend.research_studio import ResearchRunManager


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--records", type=Path, default=Path("research_records"))
    args = parser.parse_args()
    manager = ResearchRunManager(HumanSessionManager(), output_dir=args.records)
    row = manager.revalidate_saved_task(args.run_id)
    print(json.dumps({"run_id": row["run_id"], "status": row["status"],
        "revalidation": row["task_revalidations"][-1]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
